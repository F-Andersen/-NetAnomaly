import numpy as np
import pandas as pd
import pytest

from conftest import raw_frame
from netanomaly.data import (
    SchemaError,
    build_splits,
    clean_frame,
    normalize_labels,
    parse_timestamps,
    sample_stratified,
)
from netanomaly.schema import EXPECTED_COLUMNS, FEATURE_COLUMNS, FILE_SPLITS, LABEL_COLUMN


def test_schema_rejects_missing_column():
    frame = raw_frame(1, 5).drop(columns=["Flow Duration"])
    with pytest.raises(SchemaError, match="Flow Duration"):
        clean_frame(frame, "bad.csv")


def test_schema_rejects_unexpected_order():
    frame = raw_frame(1, 5)
    frame = frame[list(reversed(EXPECTED_COLUMNS))]
    with pytest.raises(SchemaError):
        clean_frame(frame, "bad.csv")


def test_rejects_differing_duplicate_column():
    frame = raw_frame(1, 5)
    frame.loc[0, "Fwd Header Length.1"] = -5
    with pytest.raises(SchemaError, match="differs"):
        clean_frame(frame, "bad.csv")


def test_unknown_label_is_an_error():
    frame = raw_frame(1, 5)
    frame.loc[0, LABEL_COLUMN] = "Alien Attack"
    with pytest.raises(SchemaError, match="Alien"):
        clean_frame(frame, "bad.csv")


def test_blank_rows_and_exact_duplicates_are_removed_and_counted():
    base = raw_frame(1, 5)
    blank = pd.DataFrame(np.nan, index=[0, 1, 2], columns=base.columns)
    frame = pd.concat([base, base.iloc[[0]], blank], ignore_index=True)
    clean, report = clean_frame(frame, "f.csv")
    assert report["blank_rows_removed"] == 3
    assert report["exact_duplicate_records_removed"] == 1
    assert len(clean) == 5 == report["clean_rows"]


def test_quality_report_counts_nonfinite_and_negative_values():
    frame = raw_frame(1, 5)
    frame["Flow Bytes/s"] = frame["Flow Bytes/s"].astype(float)
    frame.loc[0, "Flow Bytes/s"] = np.inf
    frame.loc[1, "Flow Bytes/s"] = np.nan
    frame.loc[2, "Flow Duration"] = -3
    frame.loc[3, "Init_Win_bytes_forward"] = -1
    _, report = clean_frame(frame, "f.csv")
    assert report["infinite_values"] == {"Flow Bytes/s": 1}
    assert report["missing_values"] == {"Flow Bytes/s": 1}
    assert report["negative_values_marked_missing"] == {"Flow Duration": 1}
    assert report["negative_sentinel_values_kept"] == {"Init_Win_bytes_forward": 1}


def test_web_attack_label_dash_is_normalized():
    result = normalize_labels(pd.Series(["Web Attack \x96 XSS", "Web Attack – Sql Injection", " BENIGN "]))
    assert result.tolist() == ["Web Attack - XSS", "Web Attack - Sql Injection", "BENIGN"]


def test_timestamps_are_day_first_and_12_hour_afternoons_are_restored():
    parsed = parse_timestamps(pd.Series(["7/7/2017 3:30", "03/07/2017 08:55:58", "6/7/2017 12:59"]))
    assert parsed.tolist() == [
        pd.Timestamp("2017-07-07 15:30"), pd.Timestamp("2017-07-03 08:55:58"), pd.Timestamp("2017-07-06 12:59"),
    ]


def _loader(extra: dict[str, pd.DataFrame] | None = None):
    frames = {}
    for i, (name, day, _) in enumerate(FILE_SPLITS):
        y, m, d = day.split("-")
        attacks = {} if i == 0 else {"DDoS": 4}
        frames[name] = raw_frame(100 + i, 40, attacks, day=f"{int(d)}/{int(m)}/{y}")
    frames.update(extra or {})
    return frames.__getitem__


def test_splits_are_whole_days_in_capture_order():
    frames, _ = build_splits(_loader(), None, 1)
    assert set(frames["train"]["source_file"].astype(str)) == {"Monday-WorkingHours.pcap_ISCX.csv"}
    assert frames["train"]["event_time"].max() < frames["validation"]["event_time"].min()
    assert frames["validation"]["event_time"].max() < frames["test"]["event_time"].min()


def test_train_is_benign_only():
    frames, _ = build_splits(_loader(), None, 1)
    assert set(frames["train"][LABEL_COLUMN].astype(str)) == {"BENIGN"}


def test_feature_vector_stays_only_in_its_earliest_split():
    monday_name = FILE_SPLITS[0][0]
    tuesday_name = FILE_SPLITS[1][0]
    monday = raw_frame(100, 40, day="3/7/2017")
    tuesday = raw_frame(101, 40, {"FTP-Patator": 4}, day="4/7/2017")
    # Row 5 of Tuesday repeats Monday's features, with a different flow id, time and label.
    columns = list(FEATURE_COLUMNS)
    tuesday.loc[tuesday.index[-1], columns] = monday.loc[5, columns].to_numpy()
    tuesday.loc[tuesday.index[-1], "Fwd Header Length.1"] = monday.loc[5, "Fwd Header Length"]
    frames, quality = build_splits(_loader({monday_name: monday, tuesday_name: tuesday}), None, 1)
    assert quality["cross_split_duplicates_removed"]["validation"] == {"rows": 1, "labels": {"FTP-Patator": 1}}
    train_duration = frames["train"]["Flow Duration"].to_numpy()
    val_duration = frames["validation"]["Flow Duration"].to_numpy()
    assert np.isclose(float(monday.loc[5, "Flow Duration"]), train_duration).any()
    assert not np.isclose(float(monday.loc[5, "Flow Duration"]), val_duration).any()
    assert (frames["validation"]["Label"].astype(str) == "FTP-Patator").sum() == 3


def test_removed_duplicate_is_the_matching_row_after_time_sort():
    """Regression: hashes must stay aligned with rows when a split is sorted by time."""
    monday_name, tuesday_name = FILE_SPLITS[0][0], FILE_SPLITS[1][0]
    monday = raw_frame(100, 40, day="3/7/2017")
    tuesday = raw_frame(101, 40, day="4/7/2017")
    columns = list(FEATURE_COLUMNS)
    tuesday.loc[0, columns] = monday.loc[9, columns].to_numpy()
    tuesday.loc[0, "Fwd Header Length.1"] = monday.loc[9, "Fwd Header Length"]
    # Make the repeated flow the latest of the day so sorting moves it.
    tuesday.loc[0, "Timestamp"] = "4/7/2017 16:59"
    frames, _ = build_splits(_loader({monday_name: monday, tuesday_name: tuesday}), None, 1)
    assert not np.isclose(float(monday.loc[9, "Flow Duration"]), frames["validation"]["Flow Duration"].to_numpy()).any()


def test_sampling_is_reproducible_and_keeps_rare_labels():
    frame = raw_frame(1, 1000, {"Heartbleed": 2, "DDoS": 500})
    first = sample_stratified(frame, 0.05, seed=3)
    assert first["Flow ID"].tolist() == sample_stratified(frame, 0.05, seed=3)["Flow ID"].tolist()
    assert first["Flow ID"].tolist() != sample_stratified(frame, 0.05, seed=4)["Flow ID"].tolist()
    counts = first[LABEL_COLUMN].value_counts()
    assert counts["Heartbleed"] == 1 and counts["BENIGN"] == 50 and counts["DDoS"] == 25
