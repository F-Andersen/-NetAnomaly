"""Copy experiment results from report files into PostgreSQL for the Grafana dashboards."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import delete

from .db import ExperimentMetric, ExperimentPerAttack, init_db, make_engine, make_session_factory

_METRIC_FIELDS = ("data_mode", "n", "n_attack", "n_benign", "tp", "fp", "tn", "fn", "accuracy", "precision", "recall",
                  "f1", "fpr", "pr_auc", "roc_auc", "threshold", "score_seconds", "microseconds_per_record")


def load_results(run_id: str, reports_root: str = "reports", database_url: str | None = None) -> dict:
    report_dir = Path(reports_root) / run_id
    payload = json.loads((report_dir / "test_metrics.json").read_text(encoding="utf-8"))
    per_attack = pd.read_csv(report_dir / "test_per_attack.csv")

    engine = make_engine(database_url or os.environ["DATABASE_URL"])
    init_db(engine)
    with make_session_factory(engine).begin() as session:
        session.execute(delete(ExperimentMetric).where(ExperimentMetric.run_id == run_id))
        session.execute(delete(ExperimentPerAttack).where(ExperimentPerAttack.run_id == run_id))
        for result in payload["results"]:
            session.add(ExperimentMetric(run_id=run_id, model=result["model"], **{k: result[k] for k in _METRIC_FIELDS}))
        for row in per_attack.to_dict("records"):
            session.add(ExperimentPerAttack(run_id=run_id, model=row["model"], label=row["label"], n=int(row["n"]),
                                            flagged=int(row["flagged"]), flagged_share=float(row["flagged_share"])))
    return {"run_id": run_id, "metrics_rows": len(payload["results"]), "per_attack_rows": len(per_attack)}
