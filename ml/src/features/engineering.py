"""Feature engineering transforms for CIC-IDS2018 network flow data.

Every transform is a pure function ``DataFrame → DataFrame``, making
transforms composable and testable in isolation.

**Log transforms** – applied to columns with skewness > 2 (or a
caller-specified list).  Uses ``np.log1p`` so zero values are safe.

**Derived features** – ratios and statistics computed from existing CIC
columns that capture aspects of network behaviour that raw counters
miss (e.g., byte-per-packet ratios, flag-count ratios, duration
fractions).
"""

from __future__ import annotations

import logging
from typing import Final

import numpy as np
import pandas as pd

__all__ = [
    "apply_log_transforms",
    "compute_derived_features",
    "SKEWED_COLUMNS",
]

logger = logging.getLogger(__name__)

# ── Known heavily-skewed columns in CIC-IDS2018 ───────────────────────
SKEWED_COLUMNS: Final[list[str]] = [
    "flow_duration",
    "total_fwd_packets",
    "total_backward_packets",
    "total_length_of_fwd_packets",
    "total_length_of_bwd_packets",
    "fwd_packet_length_max",
    "fwd_packet_length_mean",
    "bwd_packet_length_max",
    "bwd_packet_length_mean",
    "flow_bytes/s",
    "flow_packets/s",
    "flow_iat_max",
    "flow_iat_mean",
    "fwd_iat_total",
    "fwd_iat_max",
    "fwd_iat_mean",
    "bwd_iat_total",
    "bwd_iat_max",
    "bwd_iat_mean",
    "fwd_header_length",
    "bwd_header_length",
    "subflow_fwd_bytes",
    "subflow_bwd_bytes",
    "init_win_bytes_forward",
    "init_win_bytes_backward",
    "active_mean",
    "active_max",
    "idle_mean",
    "idle_max",
]


def apply_log_transforms(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Apply ``log1p`` to skewed numeric columns.

    Parameters
    ----------
    df:
        Input DataFrame.
    columns:
        Explicit list of column names to transform.  If ``None``, columns
        with absolute skewness > 2 are selected automatically.

    Returns
    -------
    pd.DataFrame
        DataFrame with transformed columns (original columns are replaced
        in-place with their ``log1p`` values; column names are unchanged).

    Notes
    -----
    ``np.log1p(x) = log(1 + x)`` so ``x = 0`` is handled safely.
    Negative values are left untouched and a warning is emitted.
    """
    df = df.copy()

    if columns is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        skew_vals = df[numeric_cols].skew()
        columns = skew_vals[skew_vals.abs() > 2].index.tolist()
        logger.info("Auto-detected %d skewed columns for log transform", len(columns))

    for col in columns:
        if col not in df.columns:
            logger.debug("Skipping missing column: %s", col)
            continue

        series = df[col]
        if not np.issubdtype(series.dtype, np.number):
            logger.debug("Skipping non-numeric column: %s", col)
            continue

        if (series < 0).any():
            logger.warning(
                "Column '%s' has negative values – applying log1p only to non-negative rows",
                col,
            )
            mask = series >= 0
            df.loc[mask, col] = np.log1p(series[mask])
        else:
            df[col] = np.log1p(series)

    return df


def compute_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived features from raw CIC-IDS2018 columns.

    All new columns are prefixed with ``derived_`` for easy identification.

    Derived features created
    ~~~~~~~~~~~~~~~~~~~~~~~~
    - ``derived_fwd_bwd_packet_ratio`` – ratio of forward to backward packets
    - ``derived_fwd_bwd_byte_ratio`` – ratio of forward to backward bytes
    - ``derived_bytes_per_packet`` – total bytes divided by total packets
    - ``derived_fwd_bytes_per_packet`` – forward bytes / forward packets
    - ``derived_bwd_bytes_per_packet`` – backward bytes / backward packets
    - ``derived_down_up_ratio_bytes`` – backward bytes / forward bytes
    - ``derived_psh_flag_ratio`` – PSH flag count / total packets
    - ``derived_urg_flag_ratio`` – URG flag count / total packets
    - ``derived_syn_flag_ratio`` – SYN flag count / total packets
    - ``derived_ack_flag_ratio`` – ACK flag count / total packets
    - ``derived_flow_iat_cv`` – coefficient of variation of flow IAT
    - ``derived_active_idle_ratio`` – active mean / idle mean

    Parameters
    ----------
    df:
        Cleaned DataFrame from the data loader.

    Returns
    -------
    pd.DataFrame
        DataFrame with additional ``derived_*`` columns appended.
    """
    df = df.copy()

    # ── helper: safe divide (returns 0 where denominator is 0) ─────
    def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
        return numerator / denominator.replace(0, np.nan).fillna(0)

    # ── Packet ratios ──────────────────────────────────────────────
    if {"total_fwd_packets", "total_backward_packets"}.issubset(df.columns):
        total_pkts = df["total_fwd_packets"] + df["total_backward_packets"]
        df["derived_fwd_bwd_packet_ratio"] = _safe_ratio(
            df["total_fwd_packets"], df["total_backward_packets"]
        )

        # Flag ratios (normalised by total packets)
        for flag_col, derived_name in [
            ("psh_flag_count", "derived_psh_flag_ratio"),
            ("urg_flag_count", "derived_urg_flag_ratio"),
            ("syn_flag_count", "derived_syn_flag_ratio"),
            ("ack_flag_count", "derived_ack_flag_ratio"),
        ]:
            if flag_col in df.columns:
                df[derived_name] = _safe_ratio(df[flag_col], total_pkts)
    else:
        total_pkts = pd.Series(0, index=df.index)

    # ── Byte ratios ────────────────────────────────────────────────
    fwd_bytes_col = "total_length_of_fwd_packets"
    bwd_bytes_col = "total_length_of_bwd_packets"

    if {fwd_bytes_col, bwd_bytes_col}.issubset(df.columns):
        total_bytes = df[fwd_bytes_col] + df[bwd_bytes_col]
        df["derived_fwd_bwd_byte_ratio"] = _safe_ratio(df[fwd_bytes_col], df[bwd_bytes_col])
        df["derived_down_up_ratio_bytes"] = _safe_ratio(df[bwd_bytes_col], df[fwd_bytes_col])

        if total_pkts.any():
            df["derived_bytes_per_packet"] = _safe_ratio(total_bytes, total_pkts)

        if "total_fwd_packets" in df.columns:
            df["derived_fwd_bytes_per_packet"] = _safe_ratio(
                df[fwd_bytes_col], df["total_fwd_packets"]
            )
        if "total_backward_packets" in df.columns:
            df["derived_bwd_bytes_per_packet"] = _safe_ratio(
                df[bwd_bytes_col], df["total_backward_packets"]
            )

    # ── Inter-arrival time statistics ──────────────────────────────
    if {"flow_iat_mean", "flow_iat_std"}.issubset(df.columns):
        df["derived_flow_iat_cv"] = _safe_ratio(df["flow_iat_std"], df["flow_iat_mean"])

    # ── Active / idle ratio ────────────────────────────────────────
    if {"active_mean", "idle_mean"}.issubset(df.columns):
        df["derived_active_idle_ratio"] = _safe_ratio(df["active_mean"], df["idle_mean"])

    n_derived = len([c for c in df.columns if c.startswith("derived_")])
    logger.info("Computed %d derived features", n_derived)
    return df
