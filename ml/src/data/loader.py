"""Data loading, cleaning, and splitting for CSE-CIC-IDS2018.

This module handles every known CSV artefact in the CIC-IDS2018 dataset:
- Leading / trailing whitespace in column names
- ``'Infinity'`` and ``'inf'`` string values in numeric columns
- Rows that are entirely NaN
- Inconsistent capitalisation in the ``Label`` column
- Varying timestamp formats across CSV files

All public helpers are stateless, pure-function transforms on DataFrames so
they compose cleanly in a pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

__all__ = [
    "load_cicids2018",
    "clean_dataframe",
    "deduplicate_flows",
    "stratified_split",
    "get_label_mapping",
    "ATTACK_LABELS",
    "LABEL_TO_INT",
    "INT_TO_LABEL",
]

logger = logging.getLogger(__name__)

# ── Canonical attack labels ────────────────────────────────────────────
ATTACK_LABELS: Final[list[str]] = [
    "Benign",
    "FTP-BruteForce",
    "SSH-BruteForce",
    "DoS-GoldenEye",
    "DoS-Hulk",
    "DoS-SlowHTTPTest",
    "DoS-Slowloris",
    "DDoS-LOIC-HTTP",
    "DDoS-LOIC-UDP",
    "Botnet-ARES",
    "WebAttack-BruteForce",
    "WebAttack-XSS",
    "WebAttack-SQLInjection",
    "Infiltration",
]

LABEL_TO_INT: Final[dict[str, int]] = {label: idx for idx, label in enumerate(ATTACK_LABELS)}
INT_TO_LABEL: Final[dict[int, str]] = {idx: label for idx, label in enumerate(ATTACK_LABELS)}

# Normalised aliases → canonical label (covers common CIC-IDS2018 quirks)
_LABEL_ALIASES: Final[dict[str, str]] = {
    alias.strip().lower(): canonical
    for canonical in ATTACK_LABELS
    for alias in [
        canonical,
        canonical.replace("-", " "),
        canonical.replace("-", "_"),
        canonical.lower(),
    ]
}
# Extra aliases for known dataset variations
_LABEL_ALIASES.update(
    {
        "benign": "Benign",
        "ftp-bruteforce": "FTP-BruteForce",
        "ssh-bruteforce": "SSH-BruteForce",
        "dos-goldeneye": "DoS-GoldenEye",
        "dos goldeneye": "DoS-GoldenEye",
        "dos-hulk": "DoS-Hulk",
        "dos hulk": "DoS-Hulk",
        "dos-slowhttptest": "DoS-SlowHTTPTest",
        "dos slowhttptest": "DoS-SlowHTTPTest",
        "dos-slowloris": "DoS-Slowloris",
        "dos slowloris": "DoS-Slowloris",
        "ddos-loic-http": "DDoS-LOIC-HTTP",
        "ddos loic http": "DDoS-LOIC-HTTP",
        "ddos-loic-udp": "DDoS-LOIC-UDP",
        "ddos loic udp": "DDoS-LOIC-UDP",
        "botnet-ares": "Botnet-ARES",
        "bot": "Botnet-ARES",
        "brute force -web": "WebAttack-BruteForce",
        "brute force-web": "WebAttack-BruteForce",
        "webattack-bruteforce": "WebAttack-BruteForce",
        "webattack-xss": "WebAttack-XSS",
        "xss": "WebAttack-XSS",
        "webattack-sqlinjection": "WebAttack-SQLInjection",
        "sql injection": "WebAttack-SQLInjection",
        "infiltration": "Infiltration",
        "infilteration": "Infiltration",  # common typo in dataset
    }
)


# ── Public API ─────────────────────────────────────────────────────────


def load_cicids2018(data_dir: Path) -> pd.DataFrame:
    """Load and concatenate all CSE-CIC-IDS2018 CSV files from *data_dir*.

    Parameters
    ----------
    data_dir:
        Directory containing one or more ``*.csv`` files.

    Returns
    -------
    pd.DataFrame
        Concatenated raw DataFrame (not yet cleaned).

    Raises
    ------
    FileNotFoundError
        If *data_dir* does not exist or contains no CSV files.
    """
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    frames: list[pd.DataFrame] = []
    for csv_path in csv_files:
        logger.info("Loading %s …", csv_path.name)
        df = pd.read_csv(csv_path, low_memory=False)
        frames.append(df)
        logger.info("  → %d rows, %d columns", len(df), len(df.columns))

    combined = pd.concat(frames, ignore_index=True)
    logger.info("Combined dataset: %d rows, %d columns", len(combined), len(combined.columns))
    return combined


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all defensive cleaning steps to a raw CIC-IDS2018 DataFrame.

    Steps performed (in order):
    1. Strip whitespace from column names.
    2. Normalise column names to ``lower_snake_case``.
    3. Drop exact-duplicate columns (keeps first occurrence).
    4. Replace ``inf`` / ``-inf`` string and numeric values with ``NaN``.
    5. Drop rows that are entirely ``NaN``.
    6. Drop remaining rows containing any ``NaN``.
    7. Normalise the ``label`` column to canonical attack names.

    Parameters
    ----------
    df:
        Raw DataFrame from :func:`load_cicids2018`.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with consistent dtypes and no missing values.
    """
    df = df.copy()
    n_before = len(df)

    # 1-2. Normalise column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    # 3. Drop duplicate columns (by name)
    df = df.loc[:, ~df.columns.duplicated()]

    # 4. Replace inf / -inf (both string and numeric forms)
    df = df.replace(["Infinity", "infinity", "inf", "-inf", "-Infinity"], np.nan)
    df = df.replace([np.inf, -np.inf], np.nan)

    # Coerce object columns that should be numeric
    for col in df.columns:
        if df[col].dtype == object and col != "label":
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            except (ValueError, TypeError):
                pass

    # 5. Drop rows that are entirely NaN
    df = df.dropna(how="all")

    # 6. Drop remaining rows with any NaN
    df = df.dropna(how="any")

    # 7. Normalise labels
    if "label" in df.columns:
        df["label"] = df["label"].astype(str).str.strip().str.lower().map(_LABEL_ALIASES)
        unknown = df["label"].isna().sum()
        if unknown > 0:
            logger.warning("Dropped %d rows with unmapped labels", unknown)
            df = df.dropna(subset=["label"])

    n_after = len(df)
    logger.info("Cleaning: %d → %d rows (dropped %d)", n_before, n_after, n_before - n_after)
    return df.reset_index(drop=True)


def deduplicate_flows(
    df: pd.DataFrame,
    time_window_seconds: float = 0.001,
) -> pd.DataFrame:
    """Remove near-duplicate flows based on the 5-tuple and timestamp.

    Two flows are considered duplicates when they share the same
    ``(src_ip, dst_ip, src_port, dst_port, protocol)`` **and** their
    timestamps differ by less than *time_window_seconds*.

    Parameters
    ----------
    df:
        Cleaned DataFrame (post :func:`clean_dataframe`).
    time_window_seconds:
        Maximum seconds between timestamps to consider flows as duplicates.

    Returns
    -------
    pd.DataFrame
        DataFrame with near-duplicate flows removed.

    Notes
    -----
    If any of the 5-tuple columns are missing the DataFrame is returned
    unchanged with a warning logged.
    """
    five_tuple = ["src_ip", "dst_ip", "src_port", "dst_port", "protocol"]
    missing = [col for col in five_tuple if col not in df.columns]
    if missing:
        logger.warning(
            "Cannot deduplicate – missing columns: %s. Returning unchanged.", missing
        )
        return df

    df = df.copy()

    # Try to parse timestamp column
    ts_col: str | None = None
    for candidate in ("timestamp", "flow_start_time", "tstamp"):
        if candidate in df.columns:
            ts_col = candidate
            break

    if ts_col is not None:
        df["_ts_parsed"] = pd.to_datetime(df[ts_col], errors="coerce", dayfirst=True)
        df = df.sort_values(five_tuple + ["_ts_parsed"])

        # Mark rows that are too close in time within each 5-tuple group
        grouped = df.groupby(five_tuple, sort=False)
        time_diff = grouped["_ts_parsed"].diff().dt.total_seconds().abs()
        is_duplicate = time_diff < time_window_seconds
        n_dupes = int(is_duplicate.sum())
        df = df[~is_duplicate]
        df = df.drop(columns=["_ts_parsed"])
        logger.info("Deduplication removed %d near-duplicate flows", n_dupes)
    else:
        # Fallback: exact duplicate on 5-tuple
        n_before = len(df)
        df = df.drop_duplicates(subset=five_tuple)
        logger.info(
            "Deduplication (exact, no timestamp): %d → %d rows", n_before, len(df)
        )

    return df.reset_index(drop=True)


def stratified_split(
    df: pd.DataFrame,
    label_col: str = "label",
    train_size: float = 0.70,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Stratified train / validation / test split preserving class distribution.

    Parameters
    ----------
    df:
        Cleaned DataFrame.
    label_col:
        Name of the column containing class labels.
    train_size, val_size, test_size:
        Desired proportions (must sum to 1.0 ± 0.01).
    random_state:
        Seed for reproducibility.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        ``(train_df, val_df, test_df)``

    Raises
    ------
    ValueError
        If proportions do not sum to ~1.0 or *label_col* is missing.
    """
    total = train_size + val_size + test_size
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"Split proportions must sum to 1.0, got {total:.3f}")
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' not found in DataFrame")

    # First split: train vs (val+test)
    val_test_size = val_size + test_size
    train_df, temp_df = train_test_split(
        df,
        test_size=val_test_size,
        stratify=df[label_col],
        random_state=random_state,
    )

    # Second split: val vs test (relative proportions within the remainder)
    relative_test = test_size / val_test_size
    val_df, test_df = train_test_split(
        temp_df,
        test_size=relative_test,
        stratify=temp_df[label_col],
        random_state=random_state,
    )

    logger.info(
        "Split: train=%d (%.1f%%), val=%d (%.1f%%), test=%d (%.1f%%)",
        len(train_df),
        100 * len(train_df) / len(df),
        len(val_df),
        100 * len(val_df) / len(df),
        len(test_df),
        100 * len(test_df) / len(df),
    )
    return (
        train_df.reset_index(drop=True),
        val_df.reset_index(drop=True),
        test_df.reset_index(drop=True),
    )


def get_label_mapping() -> dict[str, dict[str, int] | dict[int, str]]:
    """Return bidirectional label ↔ integer mappings.

    Returns
    -------
    dict
        ``{"label_to_int": {…}, "int_to_label": {…}}``

    Examples
    --------
    >>> m = get_label_mapping()
    >>> m["label_to_int"]["Benign"]
    0
    >>> m["int_to_label"][0]
    'Benign'
    """
    return {
        "label_to_int": dict(LABEL_TO_INT),
        "int_to_label": dict(INT_TO_LABEL),
    }
