import json

import numpy as np
import pandas as pd
import pytest

from conftest import raw_frame
from netanomaly.evaluation import compute_metrics, per_attack_recall, select_threshold, threshold_curve
from netanomaly.models import IsolationForestDetector, LOFDetector, RobustZScoreDetector
from netanomaly.pipeline import EvaluationAlreadyDone, compare_runs, stage_evaluate, stage_fit, stage_prepare
from netanomaly.preprocess import build_preprocessor, dropped_constant_features, model_feature_names
from netanomaly.schema import FEATURE_COLUMNS


def features(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[list(FEATURE_COLUMNS)].astype(float)


def test_metrics_match_hand_counted_confusion_matrix():
    y = np.array([1, 1, 1, 0, 0, 0, 0, 0])
    s = np.array([0.9, 0.8, 0.2, 0.7, 0.1, 0.1, 0.1, 0.1])
    m = compute_metrics(y, s, 0.5)
    assert (m["tp"], m["fn"], m["fp"], m["tn"]) == (2, 1, 1, 4)
    assert m["precision"] == pytest.approx(2 / 3)
    assert m["recall"] == pytest.approx(2 / 3)
    assert m["f1"] == pytest.approx(2 / 3)
    assert m["fpr"] == pytest.approx(0.2)
    assert m["accuracy"] == pytest.approx(0.75)


def test_decision_at_exact_threshold_is_anomalous():
    assert compute_metrics(np.array([1, 0]), np.array([0.5, 0.4]), 0.5)["tp"] == 1


def test_metrics_without_predicted_positives_do_not_fail():
    m = compute_metrics(np.array([1, 0]), np.array([0.1, 0.1]), 0.5)
    assert m["precision"] == 0.0 and m["f1"] == 0.0


def test_threshold_maximises_validation_f1():
    y = np.array([0, 0, 0, 1, 1, 0, 1])
    s = np.array([0.1, 0.2, 0.3, 0.6, 0.7, 0.75, 0.9])
    choice = select_threshold(y, s)
    assert choice.threshold == 0.6
    assert choice.validation_recall == 1.0
    assert choice.validation_precision == pytest.approx(0.75)
    assert choice.validation_fpr == pytest.approx(0.25)


def test_threshold_tie_prefers_highest():
    y = np.array([1, 0, 1, 0])
    s = np.array([0.8, 0.6, 0.4, 0.2])
    curve = threshold_curve(y, s)
    assert curve[curve["threshold"] == 0.4]["f1"].iloc[0] == pytest.approx(0.8)
    assert select_threshold(y, s).threshold == 0.4


def test_threshold_curve_treats_equal_scores_as_one_candidate():
    curve = threshold_curve(np.array([1, 0, 1]), np.array([0.5, 0.5, 0.2]))
    assert curve["threshold"].tolist() == [0.5, 0.2]
    assert curve["recall"].tolist() == [0.5, 1.0]


def test_threshold_requires_both_classes():
    with pytest.raises(ValueError):
        select_threshold(np.array([0, 0]), np.array([0.1, 0.2]))


def test_per_attack_counts():
    labels = pd.Series(["BENIGN", "DDoS", "DDoS", "Bot"])
    out = per_attack_recall(labels, np.array([0.9, 0.9, 0.1, 0.1]), 0.5).set_index("label")
    assert out.loc["DDoS", "flagged_share"] == 0.5
    assert out.loc["BENIGN", "flagged"] == 1
    assert out.loc["Bot", "flagged"] == 0


def test_preprocessor_learns_only_from_fit_data():
    train = features(raw_frame(1, 200))
    pre_a = build_preprocessor().fit(train)
    pre_b = build_preprocessor().fit(train)
    other = features(raw_frame(2, 50, {"DDoS": 50}))
    pre_b.transform(other)  # transforming new data must not change learned statistics
    assert np.array_equal(pre_a.named_steps["impute"].statistics_, pre_b.named_steps["impute"].statistics_)
    assert np.array_equal(pre_a.named_steps["scale"].center_, pre_b.named_steps["scale"].center_)


def test_invalid_values_are_replaced_by_train_medians():
    train = features(raw_frame(1, 200))
    pre = build_preprocessor().fit(train)
    clean = train.iloc[[0]].copy()
    broken = clean.copy()
    median = float(np.nanmedian(train["Flow Duration"].to_numpy(dtype=np.float32)))
    clean["Flow Duration"] = median
    broken["Flow Duration"] = -5
    assert np.allclose(pre.transform(clean), pre.transform(broken))
    broken["Flow Duration"] = np.inf
    assert np.allclose(pre.transform(clean), pre.transform(broken))


def test_tcp_window_sentinel_is_preserved():
    train = features(raw_frame(1, 200))
    pre = build_preprocessor().fit(train)
    row = train.iloc[[0]].copy()
    out_valid = pre.transform(row)
    row["Init_Win_bytes_forward"] = -1
    assert not np.allclose(out_valid, pre.transform(row))


def test_constant_features_are_dropped_and_protocol_is_encoded():
    pre = build_preprocessor().fit(features(raw_frame(1, 200)))
    assert "Bwd PSH Flags" in dropped_constant_features(pre)
    names = model_feature_names(pre)
    assert "Bwd PSH Flags" not in names
    assert {"protocol_tcp", "protocol_udp"} <= set(names) and "Protocol" not in names


def test_detectors_rank_obvious_outliers_higher():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, 8)).astype(np.float32)
    outliers = (rng.normal(size=(20, 8)) + 15).astype(np.float32)
    for detector in (IsolationForestDetector(n_estimators=50), LOFDetector(n_neighbors=10), RobustZScoreDetector()):
        detector.fit(X)
        assert detector.score(outliers).min() > np.quantile(detector.score(X[:100]), 0.5), detector.name


def test_isolation_forest_score_follows_the_paper_definition():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, 4)).astype(np.float32)
    scores = IsolationForestDetector(n_estimators=30).fit(X).score(X)
    assert ((scores > 0) & (scores <= 1)).all()


def test_isolation_forest_is_deterministic_for_a_seed():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, 4)).astype(np.float32)
    a = IsolationForestDetector(n_estimators=30, random_state=5).fit(X).score(X)
    b = IsolationForestDetector(n_estimators=30, random_state=5).fit(X).score(X)
    assert np.array_equal(a, b)


def test_lof_is_in_novelty_mode():
    rng = np.random.default_rng(0)
    detector = LOFDetector(n_neighbors=5).fit(rng.normal(size=(50, 3)))
    assert detector.model_.novelty is True
    with pytest.raises(AttributeError):
        detector.model_.fit_predict(rng.normal(size=(50, 3)))


def test_fit_stage_does_not_read_test_split(experiment_config):
    stage_prepare(experiment_config)
    (experiment_config.processed_dir / "test.parquet").unlink()
    stage_fit(experiment_config)  # must succeed with test data absent
    assert not (experiment_config.report_dir / "test_metrics.json").exists()


def test_end_to_end_reports_and_single_test_evaluation(experiment_config):
    stage_prepare(experiment_config)
    stage_fit(experiment_config)
    report_dir = experiment_config.report_dir
    thresholds_before = (report_dir / "thresholds.json").read_text(encoding="utf-8")

    payload = stage_evaluate(experiment_config)

    assert [r["model"] for r in payload["results"]] == ["robust_zscore_baseline", "isolation_forest", "lof_novelty"]
    assert len({r["n"] for r in payload["results"]}) == 1
    assert payload["data_mode"] == "full"
    assert (report_dir / "thresholds.json").read_text(encoding="utf-8") == thresholds_before
    for name in ("config.json", "environment.json", "data_quality.json", "split_summary.csv", "data_manifest.json",
                 "test_metrics.csv", "test_metrics.json", "confusion_matrices.csv", "test_per_attack.csv", "timing_test.csv",
                 "timing_validation.csv", "feature_dictionary.csv", "draft_feature_mapping.csv", "model_parameters.json",
                 "preprocessing.json"):
        assert (report_dir / name).exists(), name
    config = json.loads((report_dir / "config.json").read_text(encoding="utf-8"))
    assert config["seed"] == 7

    with pytest.raises(EvaluationAlreadyDone):
        stage_evaluate(experiment_config)
    with pytest.raises(EvaluationAlreadyDone):
        stage_fit(experiment_config)
    assert (report_dir / "thresholds.json").read_text(encoding="utf-8") == thresholds_before


def test_sample_mode_is_marked_in_results(experiment_config):
    experiment_config.sample_fraction = 0.5
    experiment_config.run_id = "sampled"
    stage_prepare(experiment_config)
    stage_fit(experiment_config)
    payload = stage_evaluate(experiment_config)
    assert payload["data_mode"] == "sample" and payload["sample_fraction"] == 0.5
    assert all(r["data_mode"] == "sample" for r in payload["results"])


def test_rerun_with_same_seed_gives_identical_metrics(experiment_config, tmp_path):
    stage_prepare(experiment_config)
    stage_fit(experiment_config)
    stage_evaluate(experiment_config)
    experiment_config.run_id = "unit_repeat"
    stage_prepare(experiment_config)
    stage_fit(experiment_config)
    stage_evaluate(experiment_config)
    from pathlib import Path

    assert compare_runs(Path(experiment_config.reports_root), "unit", "unit_repeat")["identical"] is True
