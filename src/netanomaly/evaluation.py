"""Threshold selection on validation and metric computation on test."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


@dataclass(frozen=True)
class ThresholdChoice:
    threshold: float
    validation_precision: float
    validation_recall: float
    validation_f1: float
    validation_fpr: float
    rule: str = "max_f1_on_validation"

    def to_dict(self) -> dict:
        return asdict(self)


def _f1(precision: np.ndarray, recall: np.ndarray) -> np.ndarray:
    denom = precision + recall
    return np.divide(2 * precision * recall, denom, out=np.zeros_like(denom), where=denom > 0)


def threshold_curve(y_true: np.ndarray, scores: np.ndarray) -> pd.DataFrame:
    """Precision/recall/F1/FPR for every distinct score used as threshold (score >= threshold)."""
    y_true = np.asarray(y_true, dtype=int)
    scores = np.asarray(scores, dtype=np.float64)
    if y_true.min() == y_true.max():
        raise ValueError("validation labels must contain both classes to select a threshold")
    order = np.argsort(-scores, kind="mergesort")
    ordered_scores = scores[order]
    ordered_labels = y_true[order]
    tp = np.cumsum(ordered_labels)
    fp = np.cumsum(1 - ordered_labels)
    # Keep only the last position of each run of equal scores.
    last_of_run = np.r_[np.flatnonzero(np.diff(ordered_scores)), len(scores) - 1]
    tp, fp = tp[last_of_run].astype(np.float64), fp[last_of_run].astype(np.float64)
    precision = tp / (tp + fp)
    recall = tp / y_true.sum()
    return pd.DataFrame(
        {
            "threshold": ordered_scores[last_of_run],
            "precision": precision,
            "recall": recall,
            "f1": _f1(precision, recall),
            "fpr": fp / (len(y_true) - y_true.sum()),
        }
    )


def select_threshold(y_true: np.ndarray, scores: np.ndarray) -> ThresholdChoice:
    """Pick the threshold maximising F1 on validation; ties go to the highest threshold."""
    curve = threshold_curve(y_true, scores)
    best_f1 = curve["f1"].max()
    best = curve[curve["f1"] == best_f1].sort_values("threshold").iloc[-1]
    return ThresholdChoice(
        threshold=float(best["threshold"]),
        validation_precision=float(best["precision"]),
        validation_recall=float(best["recall"]),
        validation_f1=float(best["f1"]),
        validation_fpr=float(best["fpr"]),
    )


def downsample_curve(curve: pd.DataFrame, max_points: int = 1000) -> pd.DataFrame:
    if len(curve) <= max_points:
        return curve.reset_index(drop=True)
    idx = np.unique(np.linspace(0, len(curve) - 1, max_points).astype(int))
    return curve.iloc[idx].reset_index(drop=True)


def compute_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    """Confusion matrix and quality metrics for a fixed threshold."""
    y_true = np.asarray(y_true, dtype=int)
    scores = np.asarray(scores, dtype=np.float64)
    y_pred = (scores >= threshold).astype(int)

    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    two_classes = 0 < int(y_true.sum()) < len(y_true)
    return {
        "n": int(len(y_true)),
        "n_attack": int(y_true.sum()),
        "n_benign": int(len(y_true) - y_true.sum()),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": (tp + tn) / len(y_true) if len(y_true) else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fp / (fp + tn) if fp + tn else 0.0,
        "pr_auc": float(average_precision_score(y_true, scores)) if two_classes else float("nan"),
        "roc_auc": float(roc_auc_score(y_true, scores)) if two_classes else float("nan"),
        "threshold": float(threshold),
    }


def per_attack_recall(labels: pd.Series, scores: np.ndarray, threshold: float) -> pd.DataFrame:
    """Detection rate per original label; for BENIGN the value is the flagged share (FPR)."""
    flagged = np.asarray(scores, dtype=np.float64) >= threshold
    frame = pd.DataFrame({"label": np.asarray(labels, dtype=object), "flagged": flagged})
    out = frame.groupby("label", sort=True)["flagged"].agg(["size", "sum"]).reset_index()
    out.columns = ["label", "n", "flagged"]
    out["flagged_share"] = out["flagged"] / out["n"]
    return out
