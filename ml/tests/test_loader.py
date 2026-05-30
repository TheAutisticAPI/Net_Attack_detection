"""Unit tests for src.data.loader – data loading, cleaning, and splitting.

All tests use small synthetic DataFrames (no real CIC-IDS2018 data required).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.loader import (
    ATTACK_LABELS,
    INT_TO_LABEL,
    LABEL_TO_INT,
    clean_dataframe,
    get_label_mapping,
    stratified_split,
)


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def raw_df() -> pd.DataFrame:
    """Synthetic raw DataFrame mimicking CIC-IDS2018 artefacts."""
    return pd.DataFrame(
        {
            " Flow Duration ": [100, 200, np.inf, 400, 500],
            "Total Fwd Packets": [10, "Infinity", 30, 40, 50],
            " Label": ["Benign", "benign", "DoS-Hulk", "dos hulk", "SSH-BruteForce"],
            "Col_A": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )


@pytest.fixture()
def clean_df() -> pd.DataFrame:
    """Pre-cleaned DataFrame with normalised columns and valid data."""
    n = 300
    rng = np.random.RandomState(42)
    labels = rng.choice(["Benign", "DoS-Hulk", "SSH-BruteForce"], size=n, p=[0.6, 0.25, 0.15])
    return pd.DataFrame(
        {
            "feature_a": rng.randn(n),
            "feature_b": rng.randn(n),
            "feature_c": rng.randn(n),
            "label": labels,
        }
    )


# ── Tests: clean_dataframe ────────────────────────────────────────────


class TestCleanDataframe:
    """Tests for clean_dataframe()."""

    def test_clean_replaces_inf(self, raw_df: pd.DataFrame) -> None:
        """inf / Infinity string values must be converted to NaN then dropped."""
        result = clean_dataframe(raw_df)
        # The rows with inf and "Infinity" should be dropped
        for col in result.select_dtypes(include=[np.number]).columns:
            assert not np.isinf(result[col]).any(), f"Column {col} still contains inf"

    def test_clean_drops_nan_rows(self) -> None:
        """Rows that are entirely NaN must be removed."""
        df = pd.DataFrame(
            {
                "A": [1.0, np.nan, 3.0],
                "B": [4.0, np.nan, 6.0],
                "Label": ["Benign", np.nan, "Benign"],
            }
        )
        result = clean_dataframe(df)
        assert len(result) == 2
        assert not result.isna().any().any()

    def test_clean_normalises_columns(self, raw_df: pd.DataFrame) -> None:
        """Column names must be lower_snake_case with no leading/trailing spaces."""
        result = clean_dataframe(raw_df)
        for col in result.columns:
            assert col == col.strip(), f"Column '{col}' has whitespace"
            assert col == col.lower(), f"Column '{col}' is not lowercase"
            assert " " not in col, f"Column '{col}' has spaces"

    def test_clean_drops_duplicate_columns(self) -> None:
        """Duplicate columns (by name) should be reduced to one copy."""
        df = pd.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [4, 5, 6],
                "Label": ["Benign", "Benign", "Benign"],
            }
        )
        # Manually create a duplicate column
        df = pd.concat([df, df[["A"]].rename(columns={"A": "A"})], axis=1)
        assert df.columns.tolist().count("A") == 2
        result = clean_dataframe(df)
        # After cleaning, there should be no duplicate column names
        assert len(result.columns) == len(set(result.columns))

    def test_clean_normalises_labels(self) -> None:
        """Label aliases like 'dos hulk' → 'DoS-Hulk' must be resolved."""
        df = pd.DataFrame(
            {
                "A": [1.0, 2.0, 3.0, 4.0],
                "Label": ["benign", "dos hulk", "DoS-Hulk", "infilteration"],
            }
        )
        result = clean_dataframe(df)
        assert set(result["label"].unique()) == {"Benign", "DoS-Hulk", "Infiltration"}


# ── Tests: stratified_split ───────────────────────────────────────────


class TestStratifiedSplit:
    """Tests for stratified_split()."""

    def test_stratified_split_ratios(self, clean_df: pd.DataFrame) -> None:
        """Train/val/test sizes should approximately match requested proportions."""
        train, val, test = stratified_split(clean_df, train_size=0.70, val_size=0.15, test_size=0.15)
        total = len(clean_df)
        assert abs(len(train) / total - 0.70) < 0.05
        assert abs(len(val) / total - 0.15) < 0.05
        assert abs(len(test) / total - 0.15) < 0.05
        # No data lost or duplicated
        assert len(train) + len(val) + len(test) == total

    def test_stratified_split_class_distribution(self, clean_df: pd.DataFrame) -> None:
        """Each split should preserve the original class distribution (±5%)."""
        train, val, test = stratified_split(clean_df)
        original_dist = clean_df["label"].value_counts(normalize=True)

        for split_name, split_df in [("train", train), ("val", val), ("test", test)]:
            split_dist = split_df["label"].value_counts(normalize=True)
            for label in original_dist.index:
                diff = abs(original_dist[label] - split_dist.get(label, 0))
                assert diff < 0.05, (
                    f"Class '{label}' distribution in {split_name} differs by {diff:.3f}"
                )

    def test_stratified_split_invalid_proportions(self, clean_df: pd.DataFrame) -> None:
        """Proportions not summing to ~1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="sum to 1.0"):
            stratified_split(clean_df, train_size=0.5, val_size=0.5, test_size=0.5)

    def test_stratified_split_missing_label_col(self, clean_df: pd.DataFrame) -> None:
        """Missing label column should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            stratified_split(clean_df, label_col="nonexistent")


# ── Tests: label mapping ──────────────────────────────────────────────


class TestLabelMapping:
    """Tests for get_label_mapping() and label constants."""

    def test_label_mapping_round_trip(self) -> None:
        """label → int → label must be an identity transform."""
        mapping = get_label_mapping()
        for label in ATTACK_LABELS:
            code = mapping["label_to_int"][label]
            recovered = mapping["int_to_label"][code]
            assert recovered == label, f"Round-trip failed: {label} → {code} → {recovered}"

    def test_label_mapping_completeness(self) -> None:
        """All 15 classes (14 attacks + Benign) must be present."""
        assert len(ATTACK_LABELS) == 14
        assert len(LABEL_TO_INT) == 14
        assert len(INT_TO_LABEL) == 14
        assert "Benign" in LABEL_TO_INT

    def test_label_mapping_consistency(self) -> None:
        """LABEL_TO_INT and INT_TO_LABEL must be exact inverses."""
        for label, code in LABEL_TO_INT.items():
            assert INT_TO_LABEL[code] == label
