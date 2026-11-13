"""Load, validate and clean the raw CICIDS2017 CSV files, then split them chronologically."""
from __future__ import annotations

import gc
import hashlib
import json
import zipfile
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from .schema import (
    BENIGN_LABEL,
    DUPLICATE_COLUMN,
    EXPECTED_COLUMNS,
    FEATURE_COLUMNS,
    FILE_SPLITS,
    KNOWN_LABELS,
    LABEL_COLUMN,
    META_COLUMNS,
    NEGATIVE_ALLOWED,
    SPLIT_ORDER,
    TIMESTAMP_COLUMN,
)

EVENT_TIME = "event_time"
SOURCE_FILE = "source_file"
RECORD_COLUMNS = [*META_COLUMNS, EVENT_TIME, SOURCE_FILE, LABEL_COLUMN, *FEATURE_COLUMNS]


class SchemaError(ValueError):
    """The input file does not match the expected CICIDS2017 structure."""


def normalize_columns(columns) -> list[str]:
    return [str(c).strip() for c in columns]


def validate_schema(columns: list[str], name: str = "") -> None:
    expected, actual = list(EXPECTED_COLUMNS), list(columns)
    if actual == expected:
        return
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    raise SchemaError(f"{name}: schema mismatch (missing={missing}, unexpected={extra}, order_ok={not missing and not extra})")


def normalize_labels(labels: pd.Series) -> pd.Series:
    """Unify the dash in web-attack labels, which the source files store as cp1252 0x96."""
    return (
        labels.astype(str)
        .str.replace("\x96", "-", regex=False)
        .str.replace("–", "-", regex=False)
        .str.replace("�", "-", regex=False)
        .str.strip()
    )


def parse_timestamps(values: pd.Series) -> pd.Series:
    """Parse day-first timestamps recorded on a 12-hour clock without AM/PM.

    Capture ran during working hours (about 08:00-18:00), so hours below 8 are afternoon hours.
    """
    text = values.astype(str).str.strip()
    parsed = pd.to_datetime(text, format="%d/%m/%Y %H:%M:%S", errors="coerce")
    missing = parsed.isna()
    if missing.any():
        parsed = parsed.where(~missing, pd.to_datetime(text[missing], format="%d/%m/%Y %H:%M", errors="coerce"))
    return parsed.where(parsed.dt.hour >= 8, parsed + pd.Timedelta(hours=12))


def read_member(archive: zipfile.ZipFile, file_name: str) -> pd.DataFrame:
    matches = [m for m in archive.namelist() if m.rsplit("/", 1)[-1] == file_name]
    if len(matches) != 1:
        raise SchemaError(f"{file_name}: expected exactly one archive member, found {len(matches)}")
    with archive.open(matches[0]) as handle:
        frame = pd.read_csv(handle, encoding="latin-1", low_memory=False)
    frame.columns = normalize_columns(frame.columns)
    return frame


def _port(values: pd.Series) -> np.ndarray:
    return pd.to_numeric(values, errors="coerce").fillna(-1).to_numpy(dtype=np.int32)


def clean_frame(raw: pd.DataFrame, name: str) -> tuple[pd.DataFrame, dict]:
    """Validate one raw file and return its clean records together with a quality report."""
    validate_schema(list(raw.columns), name)
    report: dict = {"file": name, "raw_rows": int(len(raw))}

    blank = raw.isna().all(axis=1)
    report["blank_rows_removed"] = int(blank.sum())
    frame = raw.loc[~blank].copy()

    unlabeled = frame[LABEL_COLUMN].isna()
    report["unlabeled_rows_removed"] = int(unlabeled.sum())
    frame = frame.loc[~unlabeled]

    frame[LABEL_COLUMN] = normalize_labels(frame[LABEL_COLUMN])
    unknown = sorted(set(frame[LABEL_COLUMN].unique()) - KNOWN_LABELS)
    if unknown:
        raise SchemaError(f"{name}: unknown labels {unknown}")

    duplicated = frame.duplicated(keep="first")
    report["exact_duplicate_records_removed"] = int(duplicated.sum())
    frame = frame.loc[~duplicated]

    numeric = frame[[*FEATURE_COLUMNS, DUPLICATE_COLUMN]].apply(pd.to_numeric, errors="coerce")
    report["duplicate_column_identical"] = bool(
        numeric["Fwd Header Length"].equals(numeric[DUPLICATE_COLUMN])
    )
    if not report["duplicate_column_identical"]:
        raise SchemaError(f"{name}: {DUPLICATE_COLUMN} differs from Fwd Header Length")
    numeric = numeric[list(FEATURE_COLUMNS)]

    values = numeric.to_numpy(dtype=np.float64)
    report["missing_values"] = {c: int(v) for c, v in zip(numeric.columns, np.isnan(values).sum(axis=0)) if v}
    report["infinite_values"] = {c: int(v) for c, v in zip(numeric.columns, np.isinf(values).sum(axis=0)) if v}
    with np.errstate(invalid="ignore"):
        negative = (values < 0).sum(axis=0)
    report["negative_values_marked_missing"] = {
        c: int(v) for c, v in zip(numeric.columns, negative) if v and c not in NEGATIVE_ALLOWED
    }
    report["negative_sentinel_values_kept"] = {
        c: int(v) for c, v in zip(numeric.columns, negative) if v and c in NEGATIVE_ALLOWED
    }

    event_time = parse_timestamps(frame[TIMESTAMP_COLUMN])
    report["unparsed_timestamps"] = int(event_time.isna().sum())
    if report["unparsed_timestamps"]:
        raise SchemaError(f"{name}: {report['unparsed_timestamps']} timestamps could not be parsed")
    report["event_time_min"] = str(event_time.min())
    report["event_time_max"] = str(event_time.max())

    clean = pd.DataFrame(
        {
            "Source IP": frame["Source IP"].astype(str).to_numpy(),
            "Source Port": _port(frame["Source Port"]),
            "Destination IP": frame["Destination IP"].astype(str).to_numpy(),
            "Destination Port": _port(frame["Destination Port"]),
            EVENT_TIME: event_time.to_numpy(),
            SOURCE_FILE: name,
            LABEL_COLUMN: frame[LABEL_COLUMN].to_numpy(),
        }
    )
    for column in FEATURE_COLUMNS:
        clean[column] = numeric[column].to_numpy(dtype=np.float64)
    report["clean_rows"] = int(len(clean))
    report["labels"] = {str(k): int(v) for k, v in clean[LABEL_COLUMN].value_counts().sort_index().items()}
    return clean, report


def feature_hashes(frame: pd.DataFrame) -> np.ndarray:
    return pd.util.hash_pandas_object(frame[list(FEATURE_COLUMNS)], index=False).to_numpy()


def to_compact(frame: pd.DataFrame) -> pd.DataFrame:
    """Reduce memory use. float32 rounding happens only after duplicates were compared at float64."""
    compact = frame.copy()
    for column in FEATURE_COLUMNS:
        compact[column] = compact[column].astype(np.float32)
    for column in ("Source IP", "Destination IP", SOURCE_FILE, LABEL_COLUMN):
        compact[column] = compact[column].astype("category")
    return compact


def sample_stratified(frame: pd.DataFrame, fraction: float, seed: int) -> pd.DataFrame:
    """Sample each label separately and keep at least one record of every label."""
    rng = np.random.default_rng(seed)
    labels = frame[LABEL_COLUMN].astype(str).to_numpy()
    keep: list[np.ndarray] = []
    for label in sorted(set(labels)):
        positions = np.flatnonzero(labels == label)
        size = max(1, int(np.ceil(len(positions) * fraction)))
        keep.append(rng.choice(positions, size=size, replace=False))
    return frame.iloc[np.sort(np.concatenate(keep))].reset_index(drop=True)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for split, frame in frames.items():
        counts = frame[LABEL_COLUMN].astype(str).value_counts().sort_index()
        rows += [{"split": split, "label": label, "n": int(n)} for label, n in counts.items()]
    return pd.DataFrame(rows, columns=["split", "label", "n"])


def build_splits(
    load_file: Callable[[str], pd.DataFrame],
    sample_fraction: float | None,
    seed: int,
) -> tuple[dict[str, pd.DataFrame], dict]:
    """Assign whole capture days to splits and keep each feature vector in its earliest split only.

    Train uses Monday (benign only). Validation uses Tuesday and Wednesday. Test uses Thursday and
    Friday. Repeats inside one split are real repeated flows and stay. A later split loses any record
    whose feature vector already appeared in an earlier split, whatever its label.
    """
    frames: dict[str, pd.DataFrame] = {}
    quality: dict = {"files": [], "cross_split_duplicates_removed": {}}
    seen: np.ndarray = np.empty(0, dtype=np.uint64)

    for split in SPLIT_ORDER:
        parts, hashes = [], []
        for file_name, day, file_split in FILE_SPLITS:
            if file_split != split:
                continue
            clean, report = clean_frame(load_file(file_name), file_name)
            report.update(split=split, capture_day=day)
            quality["files"].append(report)
            hashes.append(feature_hashes(clean))
            parts.append(to_compact(clean))
            del clean
            gc.collect()
        frame = pd.concat(parts, ignore_index=True)
        split_hash = np.concatenate(hashes)
        del parts, hashes
        order = frame[EVENT_TIME].to_numpy().argsort(kind="stable")
        frame = frame.iloc[order].reset_index(drop=True)
        split_hash = split_hash[order]

        repeated = np.isin(split_hash, seen)
        removed = frame.loc[repeated, LABEL_COLUMN].astype(str).value_counts().sort_index()
        quality["cross_split_duplicates_removed"][split] = {
            "rows": int(repeated.sum()),
            "labels": {str(k): int(v) for k, v in removed.items()},
        }
        frame = frame.loc[~repeated].reset_index(drop=True)
        seen = np.union1d(seen, split_hash[~repeated])
        del order, split_hash

        if split == "train":
            not_benign = frame[LABEL_COLUMN].astype(str) != BENIGN_LABEL
            quality["train_non_benign_removed"] = int(not_benign.sum())
            frame = frame.loc[~not_benign].reset_index(drop=True)
        if sample_fraction is not None:
            frame = sample_stratified(frame, sample_fraction, seed)
        for column in ("Source IP", "Destination IP", SOURCE_FILE, LABEL_COLUMN):
            frame[column] = frame[column].astype(str).astype("category")
        frames[split] = frame
        gc.collect()
    return frames, quality


def prepare_data(zip_path: Path, output_dir: Path, sample_fraction: float | None, seed: int) -> dict:
    """Create the cleaned parquet splits, or reuse them when the inputs are unchanged."""
    manifest_path = output_dir / "manifest.json"
    source_hash = file_sha256(zip_path)
    expected = {"source_sha256": source_hash, "sample_fraction": sample_fraction, "seed": seed}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if {k: manifest.get(k) for k in expected} == expected:
            return manifest

    with zipfile.ZipFile(zip_path) as archive:
        frames, quality = build_splits(lambda name: read_member(archive, name), sample_fraction, seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    for split, frame in frames.items():
        frame.to_parquet(output_dir / f"{split}.parquet", index=False)
    split_summary(frames).to_csv(output_dir / "split_summary.csv", index=False)
    (output_dir / "data_quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        **expected,
        "source_file": zip_path.name,
        "data_mode": "full" if sample_fraction is None else "sample",
        "split_sizes": {split: int(len(frame)) for split, frame in frames.items()},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
