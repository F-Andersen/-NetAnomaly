import re
from pathlib import Path

from sqlalchemy import select

from netanomaly.db import ExperimentMetric, ExperimentPerAttack, make_engine, make_session_factory
from netanomaly.pipeline import stage_evaluate, stage_fit, stage_prepare
from netanomaly.results_loader import load_results
from netanomaly.schema import DRAFT_FEATURE_MAPPING, EXCLUDED_COLUMNS, EXPECTED_COLUMNS, FEATURE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def test_load_results_is_idempotent(experiment_config, tmp_path):
    stage_prepare(experiment_config)
    stage_fit(experiment_config)
    stage_evaluate(experiment_config)
    url = f"sqlite:///{(tmp_path / 'results.db').as_posix()}"
    load_results("unit", experiment_config.reports_root, url)
    load_results("unit", experiment_config.reports_root, url)
    with make_session_factory(make_engine(url))() as session:
        assert len(session.scalars(select(ExperimentMetric)).all()) == 3
        assert session.scalars(select(ExperimentPerAttack)).first() is not None


def test_every_raw_column_is_used_or_explicitly_excluded():
    assert set(EXPECTED_COLUMNS) == set(FEATURE_COLUMNS) | set(EXCLUDED_COLUMNS)
    assert len(EXPECTED_COLUMNS) == 85


def test_identifier_columns_are_not_model_inputs():
    for name in ("Flow ID", "Source IP", "Destination IP", "Source Port", "Destination Port", "Timestamp", "Label"):
        assert name not in FEATURE_COLUMNS


def test_http_metrics_from_the_draft_are_marked_unavailable():
    verdicts = {row[0]: row[1] for row in DRAFT_FEATURE_MAPPING}
    assert verdicts["error_rate"] == verdicts["status_code_group"] == verdicts["avg_response_time"] == "Немає"


def test_env_example_holds_only_placeholders():
    example = ROOT / ".env.example"
    if not example.exists():  # the image contains only src and tests
        return
    for line in example.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\w*(PASSWORD|SECRET|TOKEN)\w*=(.*)", line)
        if match:
            assert match.group(2).startswith("change_me"), line
