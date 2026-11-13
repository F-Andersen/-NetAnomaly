"""Replay recorded CICIDS2017 flows through the API for demonstration.

This sends rows from a historical dataset file. It is not capture of live network traffic.
"""
from __future__ import annotations

import math
import time
from datetime import timezone
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from .data import EVENT_TIME, clean_frame, normalize_columns
from .schema import FEATURE_COLUMNS, LABEL_COLUMN

REPLAY_SOURCE = "csv_replay"


def load_replay_frame(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    raw = pd.read_csv(path, encoding="latin-1", low_memory=False)
    raw.columns = normalize_columns(raw.columns)
    clean, _ = clean_frame(raw, path.name)
    return clean


def select_records(frame: pd.DataFrame, limit: int, seed: int) -> pd.DataFrame:
    """Take a seeded random subset and keep it in event-time order, as the flows were recorded."""
    if limit < len(frame):
        positions = np.random.default_rng(seed).choice(len(frame), size=limit, replace=False)
        frame = frame.iloc[np.sort(positions)]
    return frame.sort_values(EVENT_TIME, kind="stable").reset_index(drop=True)


def _json_number(value) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def to_payload(row: dict) -> dict:
    event_time = pd.Timestamp(row[EVENT_TIME]).to_pydatetime().replace(tzinfo=timezone.utc)
    return {
        "features": {name: _json_number(row[name]) for name in FEATURE_COLUMNS},
        "event_time": event_time.isoformat(),
        "source": REPLAY_SOURCE,
        "src_ip": str(row["Source IP"]),
        "src_port": int(row["Source Port"]),
        "dst_ip": str(row["Destination IP"]),
        "dst_port": int(row["Destination Port"]),
        "true_label": str(row[LABEL_COLUMN]),
    }


def send_records(records: list[dict], client: httpx.Client, api_url: str, batch_size: int, delay: float) -> dict:
    sent = anomalies = batches = 0
    started = time.perf_counter()
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        response = client.post(f"{api_url.rstrip('/')}/predict/batch", json={"records": batch})
        response.raise_for_status()
        anomalies += sum(item["is_anomaly"] for item in response.json()["predictions"])
        sent += len(batch)
        batches += 1
        if delay:
            time.sleep(delay)
    seconds = time.perf_counter() - started
    return {"sent": sent, "batches": batches, "flagged_as_anomaly": anomalies, "seconds": seconds,
            "records_per_second": sent / seconds if seconds else 0.0, "source": REPLAY_SOURCE}


def replay_file(path: str, api_url: str, limit: int, batch_size: int, delay: float, seed: int) -> dict:
    frame = select_records(load_replay_frame(path), limit, seed)
    records = [to_payload(row) for row in frame.to_dict("records")]
    with httpx.Client(timeout=120.0) as client:
        result = send_records(records, client, api_url, batch_size, delay)
    return {"input": str(path), **result}
