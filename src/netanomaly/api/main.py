"""FastAPI prediction service."""
import hashlib
import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from ..db import FlowEvent, ModelVersion, Prediction, init_db, make_engine, make_session_factory, utc_now
from . import metrics

MAX_BATCH = 1000
LOF = "lof_novelty"
IFOREST = "isolation_forest"
ALGORITHMS = (LOF, IFOREST)
DEFAULT_ALGORITHM = LOF


class FlowRecord(BaseModel):
    features: dict[str, float | None] = Field(description="All model input columns; null means the value is unavailable")
    event_time: datetime | None = Field(default=None, description="Flow time; the receive time is used when absent")
    source: Literal["api", "csv_replay"] = "api"
    src_ip: str | None = None
    src_port: int | None = None
    dst_ip: str | None = None
    dst_port: int | None = None
    true_label: str | None = Field(default=None, description="Dataset label, stored for replay analysis only")


class BatchRequest(BaseModel):
    records: list[FlowRecord] = Field(min_length=1, max_length=MAX_BATCH)


class PredictionOut(BaseModel):
    event_id: int
    score: float
    threshold: float
    is_anomaly: bool
    event_time: datetime
    model_version: str
    source: str


class BatchResponse(BaseModel):
    predictions: list[PredictionOut]


class AnomalyOut(PredictionOut):
    received_at: datetime
    src_ip: str | None
    src_port: int | None
    dst_ip: str | None
    dst_port: int | None
    true_label: str | None


class ModelService:
    def __init__(self, bundle: dict, algorithm: str):
        self.algorithm = algorithm
        self.preprocessor = bundle["preprocessor"]
        self.detector = bundle["detector"]
        self.threshold = float(bundle["threshold"])
        self.columns = list(bundle["feature_columns"])
        self.version = bundle["model_version"]
        self.bundle = bundle
        self.detector.model_.set_params(n_jobs=1)

    def validate(self, record: FlowRecord) -> None:
        expected, given = set(self.columns), set(record.features)
        missing, unknown = sorted(expected - given), sorted(given - expected)
        if missing or unknown:
            raise HTTPException(status_code=422, detail={"missing_features": missing, "unknown_features": unknown})

    def score(self, records: list[FlowRecord]) -> np.ndarray:
        frame = pd.DataFrame([[r.features[c] for c in self.columns] for r in records], columns=self.columns, dtype=np.float64)
        return self.detector.score(self.preprocessor.transform(frame))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _load_lof_bundle(bundle_path: Path, thresholds_path: Path | None) -> dict | None:
    """Combine the saved preprocessor, LOF detector and validation threshold of one experiment run."""
    lof_path = bundle_path.parent / "lof_novelty.joblib"
    if not lof_path.exists():
        return None
    base = joblib.load(bundle_path)
    thresholds_path = thresholds_path or Path("reports") / base["run_id"] / "thresholds.json"
    if not thresholds_path.exists():
        return None
    threshold = float(json.loads(thresholds_path.read_text(encoding="utf-8"))[LOF]["threshold"])
    digest = hashlib.sha256(lof_path.read_bytes() + bundle_path.read_bytes() + repr(threshold).encode()).hexdigest()
    detector = joblib.load(lof_path)
    return {
        **base,
        "detector": detector,
        "threshold": threshold,
        "model_version": f"lof-{base['run_id']}-{digest[:8]}",
        "params": {**detector.params(), "fit_rows": int(detector.model_.n_samples_fit_)},
    }


def _load_model(path: str, algorithm: str, thresholds_path: str | None) -> ModelService | None:
    bundle_path = Path(path)
    if not bundle_path.exists():
        return None
    if algorithm == IFOREST:
        return ModelService(joblib.load(bundle_path), IFOREST)
    bundle = _load_lof_bundle(bundle_path, Path(thresholds_path) if thresholds_path else None)
    return ModelService(bundle, LOF) if bundle is not None else None


def _register_model(sessions, model: ModelService) -> None:
    with sessions.begin() as session:
        if session.get(ModelVersion, model.version) is None:
            session.add(
                ModelVersion(
                    version=model.version, algorithm=model.algorithm, run_id=model.bundle["run_id"],
                    data_mode=model.bundle["data_mode"], threshold=model.threshold, seed=model.bundle["seed"],
                    params=model.bundle["params"],
                )
            )


def create_app(
    database_url: str | None = None,
    model_path: str | None = None,
    algorithm: str | None = None,
    thresholds_path: str | None = None,
) -> FastAPI:
    selected = algorithm or os.environ.get("MODEL_ALGORITHM", DEFAULT_ALGORITHM)
    if selected not in ALGORITHMS:
        raise ValueError(f"unknown model algorithm '{selected}'; expected one of {ALGORITHMS}")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        url = database_url or os.environ["DATABASE_URL"]
        path = model_path or os.environ.get("MODEL_BUNDLE_PATH", "artifacts/full_seed42/model_bundle.joblib")
        thresholds = thresholds_path or os.environ.get("MODEL_THRESHOLDS_PATH")
        engine = make_engine(url)
        init_db(engine)
        app.state.engine = engine
        app.state.sessions = make_session_factory(engine)
        app.state.model_path = f"{selected} from {path}"
        app.state.model = _load_model(path, selected, thresholds)
        if app.state.model is not None:
            _register_model(app.state.sessions, app.state.model)
            metrics.MODEL_INFO.labels(version=app.state.model.version).set(1)
        yield
        engine.dispose()

    app = FastAPI(title="Network flow anomaly detection", version="1.0.0", lifespan=lifespan)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        path = route.path if route is not None else "unmatched"
        metrics.HTTP_REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        metrics.HTTP_LATENCY.labels(path).observe(time.perf_counter() - started)
        return response

    def require_model(request: Request) -> ModelService:
        model = request.app.state.model
        if model is None:
            raise HTTPException(status_code=503, detail=f"model artifacts not found: {request.app.state.model_path}")
        return model

    def predict_records(request: Request, model: ModelService, records: list[FlowRecord]) -> list[PredictionOut]:
        for record in records:
            model.validate(record)
        started = time.perf_counter()
        scores = model.score(records)
        metrics.INFERENCE_SECONDS.observe(time.perf_counter() - started)
        metrics.BATCH_SIZE.observe(len(records))

        received_at = utc_now()
        rows = []
        try:
            with request.app.state.sessions.begin() as session:
                for record, score in zip(records, scores):
                    event_time = _as_utc(record.event_time) if record.event_time else received_at
                    score = float(score)
                    is_anomaly = score >= model.threshold
                    event = FlowEvent(
                        event_time=event_time, received_at=received_at, source=record.source, src_ip=record.src_ip,
                        src_port=record.src_port, dst_ip=record.dst_ip, dst_port=record.dst_port,
                        true_label=record.true_label,
                        features={k: (v if v is None or np.isfinite(v) else None) for k, v in record.features.items()},
                    )
                    event.prediction = Prediction(
                        model_version=model.version, score=score, threshold=model.threshold,
                        is_anomaly=is_anomaly, event_time=event_time, decided_at=received_at,
                    )
                    session.add(event)
                    rows.append(event)
                session.flush()
                out = [
                    PredictionOut(event_id=e.id, score=e.prediction.score, threshold=e.prediction.threshold,
                                  is_anomaly=e.prediction.is_anomaly, event_time=e.event_time,
                                  model_version=e.prediction.model_version, source=e.source)
                    for e in rows
                ]
        except SQLAlchemyError as error:
            metrics.DB_WRITE_ERRORS.inc()
            raise HTTPException(status_code=503, detail="prediction could not be saved") from error

        for item in out:
            metrics.PREDICTIONS.labels("anomaly" if item.is_anomaly else "normal").inc()
            metrics.SCORES.observe(item.score)
        return out

    @app.get("/health")
    def health(request: Request, response: Response) -> dict:
        model = request.app.state.model
        try:
            with request.app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            database = "ok"
        except SQLAlchemyError:
            database = "unavailable"
        healthy = model is not None and database == "ok"
        if not healthy:
            response.status_code = 503
        return {
            "status": "ok" if healthy else "degraded",
            "database": database,
            "model_loaded": model is not None,
            "algorithm": model.algorithm if model else None,
            "model_version": model.version if model else None,
            "threshold": model.threshold if model else None,
            "data_mode": model.bundle["data_mode"] if model else None,
        }

    @app.post("/predict", response_model=PredictionOut)
    def predict(record: FlowRecord, request: Request, model: Annotated[ModelService, Depends(require_model)]):
        return predict_records(request, model, [record])[0]

    @app.post("/predict/batch", response_model=BatchResponse)
    def predict_batch(body: BatchRequest, request: Request, model: Annotated[ModelService, Depends(require_model)]):
        return BatchResponse(predictions=predict_records(request, model, body.records))

    @app.get("/anomalies/recent", response_model=list[AnomalyOut])
    def recent_anomalies(
        request: Request,
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
        source: Literal["api", "csv_replay"] | None = None,
    ):
        statement = (
            select(FlowEvent, Prediction)
            .join(Prediction, Prediction.event_id == FlowEvent.id)
            .where(Prediction.is_anomaly.is_(True))
            .order_by(Prediction.id.desc())
            .limit(limit)
        )
        if source:
            statement = statement.where(FlowEvent.source == source)
        with request.app.state.sessions() as session:
            rows = session.execute(statement).all()
        return [
            AnomalyOut(
                event_id=e.id, score=p.score, threshold=p.threshold, is_anomaly=p.is_anomaly, event_time=e.event_time,
                model_version=p.model_version, source=e.source, received_at=e.received_at, src_ip=e.src_ip,
                src_port=e.src_port, dst_ip=e.dst_ip, dst_port=e.dst_port, true_label=e.true_label,
            )
            for e, p in rows
        ]

    @app.get("/model/features")
    def model_features(model: Annotated[ModelService, Depends(require_model)]) -> dict:
        return {"algorithm": model.algorithm, "model_version": model.version, "feature_columns": model.columns}

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        return Response(generate_latest(metrics.REGISTRY), media_type=CONTENT_TYPE_LATEST)

    return app


def app_factory() -> FastAPI:
    return create_app()
