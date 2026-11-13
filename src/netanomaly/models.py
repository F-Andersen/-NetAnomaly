"""Anomaly detectors with one convention: a higher score means more anomalous."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor


@dataclass
class IsolationForestDetector:
    """Main model. Its score is s(x) = 2^(-E(h(x)) / c(psi)), in (0, 1]."""

    n_estimators: int = 200
    max_samples: int = 256
    max_features: float = 1.0
    bootstrap: bool = False
    random_state: int = 42
    n_jobs: int = -1
    name: str = "isolation_forest"
    model_: IsolationForest | None = field(default=None, repr=False)

    def fit(self, X: np.ndarray) -> "IsolationForestDetector":
        self.model_ = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples=min(self.max_samples, len(X)),
            max_features=self.max_features,
            bootstrap=self.bootstrap,
            contamination="auto",
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        ).fit(X)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        # score_samples is the negated paper score, so negating restores s(x).
        return -self.model_.score_samples(X)

    def params(self) -> dict:
        return {
            "n_estimators": self.n_estimators,
            "max_samples": self.max_samples,
            "max_features": self.max_features,
            "bootstrap": self.bootstrap,
            "random_state": self.random_state,
            "n_jobs": self.n_jobs,
        }


@dataclass
class LOFDetector:
    """Comparison model. Uses novelty=True: fitted on train, scores only previously unseen records."""

    n_neighbors: int = 20
    metric: str = "minkowski"
    p: int = 2
    n_jobs: int = -1
    name: str = "lof_novelty"
    model_: LocalOutlierFactor | None = field(default=None, repr=False)

    def fit(self, X: np.ndarray) -> "LOFDetector":
        self.model_ = LocalOutlierFactor(
            n_neighbors=self.n_neighbors,
            novelty=True,
            metric=self.metric,
            p=self.p,
            contamination="auto",
            n_jobs=self.n_jobs,
        ).fit(X)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        return -self.model_.score_samples(X)

    def params(self) -> dict:
        return {
            "n_neighbors": self.n_neighbors,
            "novelty": True,
            "metric": self.metric,
            "p": self.p,
            "n_jobs": self.n_jobs,
        }


@dataclass
class RobustZScoreDetector:
    """Statistical baseline: the largest absolute per-feature value after robust scaling.

    The preprocessing step already centres each feature on its train median and divides by its
    train IQR, so this equals the rule "alert if any single feature deviates by more than T IQRs".
    """

    name: str = "robust_zscore_baseline"
    fitted_: bool = False

    def fit(self, X: np.ndarray) -> "RobustZScoreDetector":
        self.fitted_ = True
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        if not self.fitted_:
            raise RuntimeError("detector is not fitted")
        return np.abs(X).max(axis=1).astype(np.float64)

    def params(self) -> dict:
        return {"aggregation": "max_abs_over_features", "center": "train_median", "scale": "train_iqr"}
