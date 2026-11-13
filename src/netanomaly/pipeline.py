"""Experiment stages: prepare, fit and calibrate on validation, then one evaluation on test."""
from __future__ import annotations

import csv
import gc
import hashlib
import json
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from . import data as data_module
from .data import EVENT_TIME, prepare_data
from .evaluation import compute_metrics, downsample_curve, per_attack_recall, select_threshold, threshold_curve
from .models import IsolationForestDetector, LOFDetector, RobustZScoreDetector
from .preprocess import build_preprocessor, dropped_constant_features, model_feature_names
from .schema import (
    BENIGN_LABEL,
    DRAFT_FEATURE_MAPPING,
    EXCLUDED_COLUMNS,
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    NUMERIC_FEATURES,
    PROTOCOL_SPEC,
)

SOURCE_ARCHIVE = "GeneratedLabelledFlows.zip"
TEST_EVALUATION_FILE = "test_metrics.json"


class EvaluationAlreadyDone(RuntimeError):
    """The test split of this run was already used."""


@dataclass
class ExperimentConfig:
    run_id: str = "full_seed42"
    seed: int = 42
    sample_fraction: float | None = None
    lof_train_size: int = 100000
    lof_n_neighbors: int = 20
    if_n_estimators: int = 200
    if_max_samples: int = 256
    data_root: str = "data"
    artifacts_root: str = "artifacts"
    reports_root: str = "reports"
    extra: dict = field(default_factory=dict)

    @property
    def data_mode(self) -> str:
        return "full" if self.sample_fraction is None else "sample"

    @property
    def raw_archive(self) -> Path:
        return Path(self.data_root) / "raw" / SOURCE_ARCHIVE

    @property
    def processed_dir(self) -> Path:
        tag = "full" if self.sample_fraction is None else f"sample_f{self.sample_fraction:g}_s{self.seed}"
        return Path(self.data_root) / "processed" / tag

    @property
    def report_dir(self) -> Path:
        return Path(self.reports_root) / self.run_id

    @property
    def artifact_dir(self) -> Path:
        return Path(self.artifacts_root) / self.run_id

    @property
    def bundle_path(self) -> Path:
        return self.artifact_dir / "model_bundle.joblib"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_split(cfg: ExperimentConfig, split: str) -> pd.DataFrame:
    return pd.read_parquet(cfg.processed_dir / f"{split}.parquet")


def _labels(frame: pd.DataFrame) -> np.ndarray:
    return (frame[LABEL_COLUMN].astype(str) != BENIGN_LABEL).to_numpy(dtype=int)


def environment_info() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
    }


def stage_prepare(cfg: ExperimentConfig) -> dict:
    cfg.report_dir.mkdir(parents=True, exist_ok=True)
    manifest = prepare_data(cfg.raw_archive, cfg.processed_dir, cfg.sample_fraction, cfg.seed)
    _write_json(cfg.report_dir / "data_manifest.json", manifest)
    for name in ("data_quality.json", "split_summary.csv"):
        (cfg.report_dir / name).write_bytes((cfg.processed_dir / name).read_bytes())
    return manifest


def _feature_stats(train: pd.DataFrame) -> pd.DataFrame:
    return train[list(FEATURE_COLUMNS)].replace([np.inf, -np.inf], np.nan).describe().T


def write_feature_dictionary(cfg: ExperimentConfig, preprocessor, train: pd.DataFrame) -> None:
    dropped = set(dropped_constant_features(preprocessor))
    stats = _feature_stats(train)
    rows = []

    def row(name, group, unit, description, status, reason, model_names):
        s = stats.loc[name] if name in stats.index else None
        rows.append(
            {
                "name": name, "group": group, "unit": unit, "description": description,
                "status": status, "reason": reason, "model_inputs": ";".join(model_names),
                "train_median": "" if s is None else float(s["50%"]),
                "train_min": "" if s is None else float(s["min"]),
                "train_max": "" if s is None else float(s["max"]),
            }
        )

    row(PROTOCOL_SPEC.name, PROTOCOL_SPEC.group, PROTOCOL_SPEC.unit, PROTOCOL_SPEC.description,
        "used", "", ["protocol_tcp", "protocol_udp"])
    for feature in NUMERIC_FEATURES:
        if feature.name in dropped:
            row(feature.name, feature.group, feature.unit, feature.description, "dropped_constant_on_train",
                "Стала на навчальній вибірці; вилучено автоматично", [])
        else:
            row(feature.name, feature.group, feature.unit, feature.description, "used", "", [feature.name])
    for name, reason in EXCLUDED_COLUMNS.items():
        rows.append({"name": name, "group": "excluded", "unit": "", "description": "", "status": "excluded",
                     "reason": reason, "model_inputs": "", "train_median": "", "train_min": "", "train_max": ""})
    pd.DataFrame(rows).to_csv(cfg.report_dir / "feature_dictionary.csv", index=False, encoding="utf-8")
    pd.DataFrame(DRAFT_FEATURE_MAPPING, columns=["draft_feature", "available", "cicids2017_column", "comment"]).to_csv(
        cfg.report_dir / "draft_feature_mapping.csv", index=False, encoding="utf-8"
    )


def stage_fit(cfg: ExperimentConfig) -> dict:
    """Fit on train and freeze thresholds on validation. The test split is not read here."""
    report_dir, artifact_dir = cfg.report_dir, cfg.artifact_dir
    if (report_dir / TEST_EVALUATION_FILE).exists():
        raise EvaluationAlreadyDone(f"run '{cfg.run_id}' is finished; use a new run id for a repeat")
    report_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _write_json(report_dir / "config.json", {**asdict(cfg), "data_mode": cfg.data_mode})
    _write_json(report_dir / "environment.json", environment_info())

    train = _load_split(cfg, "train")
    if (_labels(train) != 0).any():
        raise ValueError("train split must contain only benign records")

    started = time.perf_counter()
    preprocessor = build_preprocessor().fit(train[list(FEATURE_COLUMNS)])
    preprocess_fit_seconds = time.perf_counter() - started
    write_feature_dictionary(cfg, preprocessor, train)

    started = time.perf_counter()
    X_train = preprocessor.transform(train[list(FEATURE_COLUMNS)])
    preprocess_train_seconds = time.perf_counter() - started
    train_size = len(train)
    del train
    gc.collect()

    validation = _load_split(cfg, "validation")
    y_validation = _labels(validation)
    val_rows = len(validation)
    started = time.perf_counter()
    X_validation = preprocessor.transform(validation[list(FEATURE_COLUMNS)])
    preprocess_val_seconds = time.perf_counter() - started
    del validation
    gc.collect()

    rng = np.random.default_rng(cfg.seed)
    lof_size = min(cfg.lof_train_size, len(X_train))
    lof_index = np.sort(rng.choice(len(X_train), size=lof_size, replace=False))

    detectors = [
        (RobustZScoreDetector(), X_train),
        (IsolationForestDetector(n_estimators=cfg.if_n_estimators, max_samples=cfg.if_max_samples, random_state=cfg.seed), X_train),
        (LOFDetector(n_neighbors=cfg.lof_n_neighbors), X_train[lof_index]),
    ]

    fitted: dict = {}
    thresholds: dict = {}
    timing: list[dict] = []
    for detector, X_fit in detectors:
        started = time.perf_counter()
        detector.fit(X_fit)
        fit_seconds = time.perf_counter() - started

        started = time.perf_counter()
        scores = detector.score(X_validation)
        predict_seconds = time.perf_counter() - started

        choice = select_threshold(y_validation, scores)
        thresholds[detector.name] = choice.to_dict()
        downsample_curve(threshold_curve(y_validation, scores)).to_csv(
            report_dir / f"validation_threshold_curve_{detector.name}.csv", index=False
        )
        timing.append(
            {
                "model": detector.name, "split": "validation", "fit_rows": len(X_fit), "fit_seconds": fit_seconds,
                "score_rows": val_rows, "score_seconds": predict_seconds,
                "microseconds_per_record": predict_seconds / val_rows * 1e6,
            }
        )
        fitted[detector.name] = detector
        print(f"{detector.name}: fit {fit_seconds:.1f}s, validation scoring {predict_seconds:.1f}s", flush=True)
        del scores
        gc.collect()

    _write_json(report_dir / "thresholds.json", thresholds)
    _write_json(
        report_dir / "model_parameters.json",
        {name: {**detector.params(), "fit_rows": next(t["fit_rows"] for t in timing if t["model"] == name)}
         for name, detector in fitted.items()},
    )
    _write_json(
        report_dir / "preprocessing.json",
        {
            "steps": [name for name, _ in preprocessor.steps],
            "input_columns": list(FEATURE_COLUMNS),
            "model_features": model_feature_names(preprocessor),
            "dropped_constant_on_train": dropped_constant_features(preprocessor),
            "fit_rows_train_only": train_size,
            "fit_seconds": preprocess_fit_seconds,
            "transform_seconds": {"train": preprocess_train_seconds, "validation": preprocess_val_seconds},
        },
    )
    pd.DataFrame(timing).to_csv(report_dir / "timing_validation.csv", index=False)

    joblib.dump({"preprocessor": preprocessor, "detector": fitted["isolation_forest"]}, artifact_dir / "_primary.joblib", compress=3)
    joblib.dump(fitted["lof_novelty"], artifact_dir / "lof_novelty.joblib", compress=3)
    joblib.dump(fitted["robust_zscore_baseline"], artifact_dir / "robust_zscore_baseline.joblib")

    primary_hash = hashlib.sha256((artifact_dir / "_primary.joblib").read_bytes()).hexdigest()[:8]
    version = f"iforest-{cfg.run_id}-{primary_hash}"
    joblib.dump(
        {
            "preprocessor": preprocessor,
            "detector": fitted["isolation_forest"],
            "threshold": thresholds["isolation_forest"]["threshold"],
            "feature_columns": list(FEATURE_COLUMNS),
            "model_version": version,
            "run_id": cfg.run_id,
            "data_mode": cfg.data_mode,
            "seed": cfg.seed,
            "params": fitted["isolation_forest"].params(),
        },
        cfg.bundle_path,
        compress=3,
    )
    (artifact_dir / "_primary.joblib").unlink()
    return {"thresholds": thresholds, "timing": timing, "model_version": version}


def stage_evaluate(cfg: ExperimentConfig) -> dict:
    """Apply the frozen thresholds to test. A run can do this only once."""
    report_dir = cfg.report_dir
    target = report_dir / TEST_EVALUATION_FILE
    if target.exists():
        raise EvaluationAlreadyDone(
            f"test split of run '{cfg.run_id}' was already evaluated; use a new run id for a repeat"
        )
    thresholds_file = report_dir / "thresholds.json"
    thresholds = _read_json(thresholds_file)
    thresholds_sha256 = hashlib.sha256(thresholds_file.read_bytes()).hexdigest()

    bundle = joblib.load(cfg.bundle_path)
    preprocessor = bundle["preprocessor"]
    detectors = {
        "robust_zscore_baseline": joblib.load(cfg.artifact_dir / "robust_zscore_baseline.joblib"),
        "isolation_forest": bundle["detector"],
        "lof_novelty": joblib.load(cfg.artifact_dir / "lof_novelty.joblib"),
    }

    test = _load_split(cfg, "test")
    y_test = _labels(test)
    labels = test[LABEL_COLUMN].astype(str).copy()
    event_range = [str(test[EVENT_TIME].min()), str(test[EVENT_TIME].max())]
    n_test = len(test)
    started = time.perf_counter()
    X_test = preprocessor.transform(test[list(FEATURE_COLUMNS)])
    preprocess_seconds = time.perf_counter() - started
    del test
    gc.collect()

    results, per_attack_rows, timing_rows = [], [], []
    for name in ("robust_zscore_baseline", "isolation_forest", "lof_novelty"):
        started = time.perf_counter()
        scores = detectors[name].score(X_test)
        score_seconds = time.perf_counter() - started
        threshold = thresholds[name]["threshold"]
        metrics = compute_metrics(y_test, scores, threshold)
        results.append({"model": name, "data_mode": cfg.data_mode, **metrics, "score_seconds": score_seconds,
                        "microseconds_per_record": score_seconds / n_test * 1e6})
        attack = per_attack_recall(labels, scores, threshold)
        attack.insert(0, "model", name)
        per_attack_rows.append(attack)
        timing_rows.append({"model": name, "split": "test", "score_rows": n_test, "score_seconds": score_seconds,
                            "microseconds_per_record": score_seconds / n_test * 1e6,
                            "preprocess_seconds_shared": preprocess_seconds})
        print(f"{name}: test scoring {score_seconds:.1f}s", flush=True)
        del scores
        gc.collect()

    frame = pd.DataFrame(results)
    frame.to_csv(report_dir / "test_metrics.csv", index=False)
    frame[["model", "tn", "fp", "fn", "tp"]].to_csv(report_dir / "confusion_matrices.csv", index=False)
    pd.concat(per_attack_rows, ignore_index=True).to_csv(report_dir / "test_per_attack.csv", index=False)
    pd.DataFrame(timing_rows).to_csv(report_dir / "timing_test.csv", index=False, quoting=csv.QUOTE_MINIMAL)

    payload = {
        "run_id": cfg.run_id,
        "data_mode": cfg.data_mode,
        "seed": cfg.seed,
        "sample_fraction": cfg.sample_fraction,
        "thresholds_sha256": thresholds_sha256,
        "test_rows": n_test,
        "test_event_time_range": event_range,
        "results": results,
    }
    _write_json(target, payload)
    return payload


def run_all(cfg: ExperimentConfig) -> dict:
    stage_prepare(cfg)
    stage_fit(cfg)
    return stage_evaluate(cfg)


_QUALITY_COLUMNS = ("tp", "fp", "tn", "fn", "precision", "recall", "f1", "fpr", "pr_auc", "roc_auc", "threshold")


def compare_runs(reports_root: Path, first: str, second: str) -> dict:
    """Compare the deterministic parts of two runs; wall-clock timings are expected to differ."""
    a, b = (_read_json(reports_root / run / TEST_EVALUATION_FILE) for run in (first, second))
    differences = []
    for left, right in zip(a["results"], b["results"]):
        for key in _QUALITY_COLUMNS:
            if left[key] != right[key]:
                differences.append({"model": left["model"], "metric": key, first: left[key], second: right[key]})
    return {"identical": not differences and a["test_rows"] == b["test_rows"], "differences": differences,
            "test_rows": [a["test_rows"], b["test_rows"]]}


__all__ = ["ExperimentConfig", "EvaluationAlreadyDone", "stage_prepare", "stage_fit", "stage_evaluate",
           "run_all", "compare_runs", "data_module"]
