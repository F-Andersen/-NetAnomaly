import json
import os
from pathlib import Path

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from netanomaly.api.main import create_app
from netanomaly.db import FlowEvent, ModelVersion, Prediction
from netanomaly.replay import REPLAY_SOURCE, select_records, send_records, to_payload
from netanomaly.schema import FEATURE_COLUMNS

SERVER_URL = os.environ.get("TEST_DATABASE_URL")


def benign_features() -> dict:
    return {name: 7.0 for name in FEATURE_COLUMNS} | {"Protocol": 6.0}


def attack_features() -> dict:
    return {name: 8.0e6 for name in FEATURE_COLUMNS} | {"Protocol": 6.0}


@pytest.fixture()
def client(fitted_config):
    url = SERVER_URL or "sqlite://"
    app = create_app(database_url=url, model_path=str(fitted_config.bundle_path),
                     thresholds_path=str(_thresholds(fitted_config)))
    with TestClient(app) as test_client:
        if SERVER_URL:
            with app.state.engine.begin() as connection:
                connection.exec_driver_sql("TRUNCATE predictions, flow_events RESTART IDENTITY CASCADE")
        yield test_client


def _thresholds(config) -> Path:
    return config.report_dir / "thresholds.json"


def _saved_threshold(config, algorithm: str) -> float:
    return json.loads(_thresholds(config).read_text(encoding="utf-8"))[algorithm]["threshold"]


def _offline_score(config, detector, features: dict) -> float:
    bundle = joblib.load(config.bundle_path)
    frame = pd.DataFrame([[features[c] for c in bundle["feature_columns"]]], columns=bundle["feature_columns"], dtype=float)
    return float(detector.score(bundle["preprocessor"].transform(frame))[0])


def test_health_reports_model_and_database(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["model_loaded"] is True


def test_lof_novelty_is_the_default_model(client, fitted_config):
    body = client.get("/health").json()
    assert body["algorithm"] == "lof_novelty"
    assert body["model_version"].startswith("lof-served-")
    assert body["threshold"] == _saved_threshold(fitted_config, "lof_novelty")
    assert client.app.state.model.detector.model_.novelty is True


def test_default_prediction_equals_saved_lof_and_threshold(client, fitted_config):
    detector = joblib.load(fitted_config.artifact_dir / "lof_novelty.joblib")
    body = client.post("/predict", json={"features": attack_features()}).json()
    assert body["score"] == pytest.approx(_offline_score(fitted_config, detector, attack_features()))
    assert body["threshold"] == _saved_threshold(fitted_config, "lof_novelty")
    with client.app.state.sessions() as session:
        version = session.get(ModelVersion, body["model_version"])
        assert version.algorithm == "lof_novelty" and version.params["novelty"] is True
        assert version.threshold == body["threshold"] and version.run_id == "served"


def test_api_can_switch_to_isolation_forest(fitted_config):
    app = create_app(database_url="sqlite://", model_path=str(fitted_config.bundle_path),
                     thresholds_path=str(_thresholds(fitted_config)), algorithm="isolation_forest")
    bundle = joblib.load(fitted_config.bundle_path)
    with TestClient(app) as local:
        health = local.get("/health").json()
        assert health["algorithm"] == "isolation_forest" and health["model_version"] == bundle["model_version"]
        assert health["threshold"] == _saved_threshold(fitted_config, "isolation_forest")
        body = local.post("/predict", json={"features": attack_features()}).json()
        assert body["score"] == pytest.approx(_offline_score(fitted_config, bundle["detector"], attack_features()))
        with local.app.state.sessions() as session:
            assert session.get(ModelVersion, body["model_version"]).algorithm == "isolation_forest"


def test_algorithm_is_selected_by_environment(fitted_config, monkeypatch):
    monkeypatch.setenv("MODEL_ALGORITHM", "isolation_forest")
    app = create_app(database_url="sqlite://", model_path=str(fitted_config.bundle_path))
    with TestClient(app) as local:
        assert local.get("/health").json()["algorithm"] == "isolation_forest"


def test_unknown_algorithm_is_rejected():
    with pytest.raises(ValueError, match="unknown model algorithm"):
        create_app(database_url="sqlite://", algorithm="random_forest")


def test_loading_the_api_leaves_saved_files_unchanged(fitted_config):
    files = [fitted_config.bundle_path, fitted_config.artifact_dir / "lof_novelty.joblib", _thresholds(fitted_config)]
    before = [p.read_bytes() for p in files]
    with TestClient(create_app(database_url="sqlite://", model_path=str(files[0]), thresholds_path=str(files[2]))) as local:
        local.post("/predict", json={"features": benign_features()})
    assert [p.read_bytes() for p in files] == before


def test_lof_without_saved_threshold_is_degraded(fitted_config, tmp_path):
    app = create_app(database_url="sqlite://", model_path=str(fitted_config.bundle_path),
                     thresholds_path=str(tmp_path / "absent.json"))
    with TestClient(app) as local:
        assert local.get("/health").status_code == 503
        assert local.post("/predict", json={"features": benign_features()}).status_code == 503


def test_health_without_model_is_degraded_and_predict_refuses():
    app = create_app(database_url="sqlite://", model_path="no/such/model.joblib")
    with TestClient(app) as local:
        response = local.get("/health")
        assert response.status_code == 503 and response.json()["model_loaded"] is False
        assert local.post("/predict", json={"features": benign_features()}).status_code == 503


def test_predict_single_stores_all_required_fields(client):
    response = client.post("/predict", json={"features": attack_features(), "event_time": "2017-07-07T15:30:00Z"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"score", "threshold", "is_anomaly", "event_time", "model_version"}
    assert body["is_anomaly"] is True and body["score"] >= body["threshold"]
    assert body["event_time"].startswith("2017-07-07T15:30")

    with client.app.state.sessions() as session:
        event = session.get(FlowEvent, body["event_id"])
        stored = session.scalar(select(Prediction).where(Prediction.event_id == body["event_id"]))
        assert stored.score == pytest.approx(body["score"])
        assert stored.threshold == pytest.approx(body["threshold"])
        assert stored.is_anomaly is True
        assert stored.model_version == body["model_version"]
        assert stored.event_time.replace(tzinfo=None) == pd.Timestamp("2017-07-07 15:30").to_pydatetime()
        assert event.features["Protocol"] == 6.0
        assert session.get(ModelVersion, body["model_version"]).algorithm == "lof_novelty"


def test_batch_returns_one_prediction_per_record_in_order(client):
    response = client.post("/predict/batch", json={"records": [{"features": benign_features()}, {"features": attack_features()}]})
    assert response.status_code == 200
    predictions = response.json()["predictions"]
    assert [p["is_anomaly"] for p in predictions] == [False, True]


def test_event_time_defaults_to_receive_time(client):
    body = client.post("/predict", json={"features": benign_features()}).json()
    assert body["event_time"].startswith(str(pd.Timestamp.now("UTC").year))


def test_null_feature_is_accepted_and_imputed(client):
    features = benign_features() | {"Flow Bytes/s": None}
    assert client.post("/predict", json={"features": features}).status_code == 200


def test_missing_feature_is_rejected(client):
    features = benign_features()
    del features["Flow Duration"]
    response = client.post("/predict", json={"features": features})
    assert response.status_code == 422
    assert response.json()["detail"]["missing_features"] == ["Flow Duration"]


def test_unknown_feature_is_rejected(client):
    response = client.post("/predict", json={"features": benign_features() | {"error_rate": 0.5}})
    assert response.status_code == 422
    assert response.json()["detail"]["unknown_features"] == ["error_rate"]


def test_non_numeric_feature_is_rejected(client):
    assert client.post("/predict", json={"features": benign_features() | {"Flow Duration": "abc"}}).status_code == 422


def test_batch_limits(client):
    assert client.post("/predict/batch", json={"records": []}).status_code == 422
    too_many = [{"features": benign_features()}] * 1001
    assert client.post("/predict/batch", json={"records": too_many}).status_code == 422


def test_recent_anomalies_contains_only_anomalies_newest_first(client):
    client.post("/predict", json={"features": benign_features()})
    first = client.post("/predict", json={"features": attack_features(), "src_ip": "10.1.1.1"}).json()
    second = client.post("/predict", json={"features": attack_features(), "source": "csv_replay", "true_label": "DDoS"}).json()
    rows = client.get("/anomalies/recent").json()
    assert [r["event_id"] for r in rows] == [second["event_id"], first["event_id"]]
    assert rows[1]["src_ip"] == "10.1.1.1" and rows[0]["true_label"] == "DDoS"
    assert [r["event_id"] for r in client.get("/anomalies/recent", params={"source": "api"}).json()] == [first["event_id"]]
    assert len(client.get("/anomalies/recent", params={"limit": 1}).json()) == 1
    assert client.get("/anomalies/recent", params={"limit": 0}).status_code == 422


def test_failed_save_returns_503_and_is_counted(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    from netanomaly.api import metrics

    def broken_begin():
        raise OperationalError("insert", {}, Exception("database is down"))

    before = metrics.DB_WRITE_ERRORS._value.get()
    monkeypatch.setattr(client.app.state.sessions, "begin", broken_begin)
    response = client.post("/predict", json={"features": benign_features()})
    assert response.status_code == 503
    assert metrics.DB_WRITE_ERRORS._value.get() == before + 1


def test_metrics_endpoint_exposes_service_metrics(client):
    client.post("/predict", json={"features": attack_features()})
    text = client.get("/metrics").text
    assert 'netanomaly_predictions_total{decision="anomaly"}' in text
    assert 'path="/predict"' in text
    assert "netanomaly_model_inference_seconds_bucket" in text
    assert "netanomaly_model_info" in text


def _replay_frame() -> pd.DataFrame:
    row = {name: 7.0 for name in FEATURE_COLUMNS}
    return pd.DataFrame(
        [
            {**row, "Source IP": "1.1.1.1", "Source Port": 5, "Destination IP": "2.2.2.2", "Destination Port": 80,
             "event_time": pd.Timestamp("2017-07-07") + pd.Timedelta(minutes=9 - i), "Label": "BENIGN"}
            for i in range(10)
        ]
    )


def test_replay_selection_is_seeded_and_time_ordered():
    frame = _replay_frame()
    first = select_records(frame, 4, seed=1)
    assert first["event_time"].is_monotonic_increasing and len(first) == 4
    assert first.equals(select_records(frame, 4, seed=1))


def test_replay_payload_marks_source_and_maps_nonfinite_to_null():
    row = _replay_frame().iloc[0].to_dict() | {"Flow Bytes/s": float("inf")}
    payload = to_payload(row)
    assert payload["source"] == REPLAY_SOURCE == "csv_replay"
    assert payload["features"]["Flow Bytes/s"] is None
    assert payload["event_time"].startswith("2017-07-07T00:09")


def test_replay_sends_batches_and_stores_events(client):
    records = [to_payload(r) for r in _replay_frame().to_dict("records")]
    result = send_records(records, client, "http://testserver", batch_size=3, delay=0.0)
    assert result["sent"] == 10 and result["batches"] == 4
    with client.app.state.sessions() as session:
        assert len(session.scalars(select(FlowEvent).where(FlowEvent.source == "csv_replay")).all()) == 10
