"""Preprocessing pipeline. Every learned statistic is estimated on the train split only."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, RobustScaler

from .schema import FEATURE_COLUMNS, NEGATIVE_ALLOWED, PROTOCOL_COLUMN

TCP = 6
UDP = 17


class FlowSanitizer(TransformerMixin, BaseEstimator):
    """Encode the protocol and mark physically impossible values as missing."""

    def fit(self, X: pd.DataFrame, y=None) -> "FlowSanitizer":
        self._check(X)
        self.output_names_ = np.array(
            ["protocol_tcp", "protocol_udp", *(c for c in FEATURE_COLUMNS if c != PROTOCOL_COLUMN)],
            dtype=object,
        )
        return self

    @staticmethod
    def _check(X: pd.DataFrame) -> None:
        missing = [c for c in FEATURE_COLUMNS if c not in X.columns]
        if missing:
            raise ValueError(f"missing feature columns: {missing}")

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        self._check(X)
        protocol = X[PROTOCOL_COLUMN].to_numpy(dtype=np.float64)
        columns = [c for c in FEATURE_COLUMNS if c != PROTOCOL_COLUMN]
        values = X[columns].to_numpy(dtype=np.float32, copy=True)
        with np.errstate(invalid="ignore"):
            values[~np.isfinite(values)] = np.nan
            for index, name in enumerate(columns):
                if name not in NEGATIVE_ALLOWED:
                    column = values[:, index]
                    column[column < 0] = np.nan
        encoded = np.column_stack([protocol == TCP, protocol == UDP]).astype(np.float32)
        return np.hstack([encoded, values])

    def get_feature_names_out(self, input_features=None) -> np.ndarray:
        return self.output_names_


def signed_log1p(X: np.ndarray) -> np.ndarray:
    return np.sign(X) * np.log1p(np.abs(X))


def build_preprocessor() -> Pipeline:
    return Pipeline(
        [
            ("sanitize", FlowSanitizer()),
            ("impute", SimpleImputer(strategy="median")),
            ("drop_constant", VarianceThreshold(threshold=0.0)),
            ("signed_log", FunctionTransformer(signed_log1p, feature_names_out="one-to-one")),
            ("scale", RobustScaler(quantile_range=(25.0, 75.0))),
        ]
    )


def model_feature_names(preprocessor: Pipeline) -> list[str]:
    return [str(n) for n in preprocessor.get_feature_names_out()]


def dropped_constant_features(preprocessor: Pipeline) -> list[str]:
    sanitized = preprocessor.named_steps["sanitize"].get_feature_names_out()
    keep = preprocessor.named_steps["drop_constant"].get_support()
    return [str(name) for name, kept in zip(sanitized, keep) if not kept]
