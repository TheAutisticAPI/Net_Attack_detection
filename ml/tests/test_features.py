"""Unit tests for feature engineering and selection modules.

All tests use small synthetic DataFrames – no real dataset needed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.engineering import (
    SKEWED_COLUMNS,
    apply_log_transforms,
    compute_derived_features,
)
from src.features.selection import (
    SURICATA_EVE_FEATURES,
    select_features_by_importance,
    validate_feature_schema,
)


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def numeric_df() -> pd.DataFrame:
    """DataFrame with known distributions for log-transform testing."""
    rng = np.random.RandomState(42)
    n = 200
    return pd.DataFrame(
        {
            # Highly right-skewed (exponential)
            "skewed_col": rng.exponential(scale=100, size=n),
            # Already roughly normal
            "normal_col": rng.randn(n) * 10 + 50,
            # Contains zeros
            "zero_heavy_col": np.where(rng.rand(n) < 0.5, 0, rng.exponential(50, n)),
            # Contains negative values
            "mixed_sign_col": rng.randn(n) * 100,
        }
    )


@pytest.fixture()
def flow_df() -> pd.DataFrame:
    """DataFrame with CIC-IDS2018-like flow columns for derived features."""
    rng = np.random.RandomState(42)
    n = 100
    return pd.DataFrame(
        {
            "total_fwd_packets": rng.randint(1, 1000, n),
            "total_backward_packets": rng.randint(0, 500, n),
            "total_length_of_fwd_packets": rng.randint(100, 100000, n),
            "total_length_of_bwd_packets": rng.randint(0, 50000, n),
            "psh_flag_count": rng.randint(0, 10, n),
            "urg_flag_count": rng.randint(0, 3, n),
            "syn_flag_count": rng.randint(0, 5, n),
            "ack_flag_count": rng.randint(0, 20, n),
            "flow_iat_mean": rng.exponential(1000, n),
            "flow_iat_std": rng.exponential(500, n),
            "active_mean": rng.exponential(100, n),
            "idle_mean": rng.exponential(200, n),
        }
    )


@pytest.fixture()
def classification_data() -> tuple[pd.DataFrame, pd.Series]:
    """Small classification dataset for feature selection tests."""
    rng = np.random.RandomState(42)
    n = 200
    # 3 informative features + 2 noise features
    X = pd.DataFrame(
        {
            "informative_1": rng.randn(n) * 10,
            "informative_2": rng.randn(n) * 5,
            "informative_3": rng.randn(n) * 3,
            "noise_1": rng.randn(n),
            "noise_2": rng.randn(n),
        }
    )
    # Label depends on informative features
    score = X["informative_1"] + X["informative_2"] * 2 + X["informative_3"]
    y = pd.Series(np.digitize(score, bins=[-10, 0, 10]), name="label")
    return X, y


# ── Tests: apply_log_transforms ───────────────────────────────────────


class TestLogTransforms:
    """Tests for apply_log_transforms()."""

    def test_log_transform_positive_values(self, numeric_df: pd.DataFrame) -> None:
        """log1p should reduce the magnitude of large positive values."""
        result = apply_log_transforms(numeric_df, columns=["skewed_col"])
        # log1p(x) < x for x > 1.72...
        assert result["skewed_col"].max() < numeric_df["skewed_col"].max()
        # All values should still be finite
        assert np.isfinite(result["skewed_col"]).all()

    def test_log_transform_handles_zeros(self, numeric_df: pd.DataFrame) -> None:
        """log1p(0) = 0, so zero values must remain zero."""
        result = apply_log_transforms(numeric_df, columns=["zero_heavy_col"])
        # Where original was 0, result should also be 0 (log1p(0) = 0)
        zero_mask = numeric_df["zero_heavy_col"] == 0
        np.testing.assert_array_almost_equal(
            result.loc[zero_mask, "zero_heavy_col"].values,
            np.zeros(zero_mask.sum()),
        )

    def test_log_transform_auto_detect(self, numeric_df: pd.DataFrame) -> None:
        """When columns=None, auto-detection should pick the skewed ones."""
        result = apply_log_transforms(numeric_df, columns=None)
        # The skewed column should have been transformed (reduced max)
        assert result["skewed_col"].max() < numeric_df["skewed_col"].max()

    def test_log_transform_preserves_shape(self, numeric_df: pd.DataFrame) -> None:
        """Output DataFrame should have the same shape as input."""
        result = apply_log_transforms(numeric_df, columns=["skewed_col"])
        assert result.shape == numeric_df.shape

    def test_log_transform_handles_missing_columns(self, numeric_df: pd.DataFrame) -> None:
        """Missing column names in the list should be silently skipped."""
        result = apply_log_transforms(numeric_df, columns=["nonexistent_col"])
        pd.testing.assert_frame_equal(result, numeric_df)


# ── Tests: compute_derived_features ───────────────────────────────────


class TestDerivedFeatures:
    """Tests for compute_derived_features()."""

    def test_derived_features_output_columns(self, flow_df: pd.DataFrame) -> None:
        """Derived features must all start with 'derived_'."""
        result = compute_derived_features(flow_df)
        derived_cols = [c for c in result.columns if c.startswith("derived_")]
        assert len(derived_cols) >= 5, f"Expected ≥5 derived features, got {len(derived_cols)}"

    def test_derived_features_expected_names(self, flow_df: pd.DataFrame) -> None:
        """Key derived features should be present."""
        result = compute_derived_features(flow_df)
        expected = {
            "derived_fwd_bwd_packet_ratio",
            "derived_fwd_bwd_byte_ratio",
            "derived_bytes_per_packet",
            "derived_psh_flag_ratio",
            "derived_flow_iat_cv",
            "derived_active_idle_ratio",
        }
        assert expected.issubset(set(result.columns)), (
            f"Missing columns: {expected - set(result.columns)}"
        )

    def test_derived_features_no_nans(self, flow_df: pd.DataFrame) -> None:
        """Derived features should not introduce NaN (safe division)."""
        result = compute_derived_features(flow_df)
        derived_cols = [c for c in result.columns if c.startswith("derived_")]
        for col in derived_cols:
            assert result[col].isna().sum() == 0, f"NaN found in derived column '{col}'"

    def test_derived_features_preserves_original(self, flow_df: pd.DataFrame) -> None:
        """Original columns must remain unchanged."""
        result = compute_derived_features(flow_df)
        for col in flow_df.columns:
            pd.testing.assert_series_equal(result[col], flow_df[col], check_names=True)

    def test_derived_features_empty_df(self) -> None:
        """Should handle DataFrames with no matching columns gracefully."""
        df = pd.DataFrame({"unrelated_col": [1, 2, 3]})
        result = compute_derived_features(df)
        assert len(result) == 3
        assert list(result.columns) == ["unrelated_col"]


# ── Tests: select_features_by_importance ──────────────────────────────


class TestFeatureSelection:
    """Tests for select_features_by_importance()."""

    def test_feature_selection_returns_correct_count(
        self, classification_data: tuple[pd.DataFrame, pd.Series]
    ) -> None:
        """Must return exactly n_features names."""
        X, y = classification_data
        selected = select_features_by_importance(X, y, n_features=3)
        assert len(selected) == 3
        assert all(isinstance(f, str) for f in selected)
        assert all(f in X.columns for f in selected)

    def test_feature_selection_respects_max(
        self, classification_data: tuple[pd.DataFrame, pd.Series]
    ) -> None:
        """Requesting more features than available should return all."""
        X, y = classification_data
        selected = select_features_by_importance(X, y, n_features=100)
        assert len(selected) == X.shape[1]


# ── Tests: validate_feature_schema ────────────────────────────────────


class TestFeatureSchema:
    """Tests for validate_feature_schema()."""

    def test_feature_schema_validation(self) -> None:
        """Known features should be classified correctly."""
        features = ["protocol", "fwd_packet_length_max", "some_unknown_feature"]
        schema = validate_feature_schema(features)
        assert schema["protocol"] == "suricata_eve"
        assert schema["fwd_packet_length_max"] == "pcap_derived"
        assert schema["some_unknown_feature"] == "dataset_only"

    def test_feature_schema_all_suricata(self) -> None:
        """All SURICATA_EVE_FEATURES should map to 'suricata_eve'."""
        features = list(SURICATA_EVE_FEATURES)
        schema = validate_feature_schema(features)
        for feat in features:
            assert schema[feat] == "suricata_eve", f"'{feat}' should be suricata_eve"

    def test_feature_schema_empty(self) -> None:
        """Empty feature list should return empty dict."""
        schema = validate_feature_schema([])
        assert schema == {}
