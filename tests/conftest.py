from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from netanomaly.pipeline import ExperimentConfig, stage_fit, stage_prepare
from netanomaly.schema import DUPLICATE_COLUMN, EXPECTED_COLUMNS, FEATURE_COLUMNS, FILE_SPLITS, LABEL_COLUMN


def raw_frame(seed: int, n_benign: int, attacks: dict[str, int] | None = None, day: str = "3/7/2017") -> pd.DataFrame:
    """A small table with the exact raw CICIDS2017 layout; attacks are far from benign traffic."""
    attacks = attacks or {}
    rng = np.random.default_rng(seed)
    n_attack = sum(attacks.values())
    n = n_benign + n_attack
    numeric = [c for c in FEATURE_COLUMNS if c != "Protocol"]
    values = rng.lognormal(mean=2.0, sigma=0.4, size=(n, len(numeric)))
    if n_attack:
        values[n_benign:] = rng.lognormal(mean=9.0, sigma=0.4, size=(n_attack, len(numeric)))
    frame = pd.DataFrame(values, columns=numeric)
    frame["Bwd PSH Flags"] = 0.0  # stays constant, as in the real data
    frame["Protocol"] = rng.choice([6, 17], size=n)
    frame[DUPLICATE_COLUMN] = frame["Fwd Header Length"]
    frame["Flow ID"] = [f"flow-{seed}-{i}" for i in range(n)]
    frame["Source IP"] = "10.0.0.1"
    frame["Destination IP"] = "10.0.0.2"
    frame["Source Port"] = 40000
    frame["Destination Port"] = 80
    frame["Timestamp"] = [f"{day} {9 + i % 3}:{i % 60:02d}" for i in range(n)]
    labels = ["BENIGN"] * n_benign
    for label, count in attacks.items():
        labels += [label] * count
    frame[LABEL_COLUMN] = labels
    return frame[list(EXPECTED_COLUMNS)]


FILE_CONTENT = {
    "Monday-WorkingHours.pcap_ISCX.csv": (1, 800, {}),
    "Tuesday-WorkingHours.pcap_ISCX.csv": (2, 300, {"FTP-Patator": 30}),
    "Wednesday-workingHours.pcap_ISCX.csv": (3, 300, {"DoS Hulk": 40}),
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv": (4, 200, {"Web Attack \x96 XSS": 20}),
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv": (5, 200, {"Infiltration": 5}),
    "Friday-WorkingHours-Morning.pcap_ISCX.csv": (6, 200, {"Bot": 10}),
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv": (7, 200, {"PortScan": 30}),
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv": (8, 200, {"DDoS": 30}),
}

def write_archive(path: Path, frames: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, frame in frames.items():
            archive.writestr(f"TrafficLabelling /{name}", frame.to_csv(index=False).encode("latin-1"))


def synthetic_frames() -> dict[str, pd.DataFrame]:
    frames = {}
    for name, (seed, benign, attacks) in FILE_CONTENT.items():
        day = next(d for n, d, _ in FILE_SPLITS if n == name)
        y, m, d = day.split("-")
        frames[name] = raw_frame(seed, benign, attacks, day=f"{int(d)}/{int(m)}/{y}")
    return frames


@pytest.fixture()
def experiment_config(tmp_path: Path) -> ExperimentConfig:
    root = tmp_path / "exp"
    write_archive(root / "data" / "raw" / "GeneratedLabelledFlows.zip", synthetic_frames())
    return ExperimentConfig(
        run_id="unit", seed=7, lof_train_size=300, lof_n_neighbors=10, if_n_estimators=30, if_max_samples=128,
        data_root=str(root / "data"), artifacts_root=str(root / "artifacts"), reports_root=str(root / "reports"),
    )


@pytest.fixture(scope="session")
def fitted_config(tmp_path_factory) -> ExperimentConfig:
    root = tmp_path_factory.mktemp("fitted")
    write_archive(root / "data" / "raw" / "GeneratedLabelledFlows.zip", synthetic_frames())
    cfg = ExperimentConfig(
        run_id="served", seed=7, lof_train_size=300, lof_n_neighbors=10, if_n_estimators=30, if_max_samples=128,
        data_root=str(root / "data"), artifacts_root=str(root / "artifacts"), reports_root=str(root / "reports"),
    )
    stage_prepare(cfg)
    stage_fit(cfg)
    return cfg
