"""Feature selection and schema validation for CIC-IDS2018 → Suricata pipeline.

This module answers two questions:

1. **Which features matter most?**  Uses Random Forest permutation importance
   to rank features and select the top-*N*.
2. **Which features are available at inference time?**  Validates each selected
   feature against known Suricata EVE JSON fields and PCAP-derivable metrics.

The distinction matters because the CIC-IDS2018 dataset contains features that
are only available offline (e.g., labels computed by CICFlowMeter) while
production inference relies on what Suricata and PCAP processing can provide.
"""

from __future__ import annotations

import logging
from typing import Final

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

__all__ = [
    "select_features_by_importance",
    "validate_feature_schema",
    "SURICATA_EVE_FEATURES",
]

logger = logging.getLogger(__name__)

# ── Features extractable from Suricata EVE JSON ───────────────────────
SURICATA_EVE_FEATURES: Final[set[str]] = {
    # Flow-level fields from EVE flow records
    "protocol",
    "src_port",
    "dst_port",
    "flow_duration",
    "flow_bytes/s",
    "flow_packets/s",
    # TCP flags (Suricata logs TCP flag summaries)
    "syn_flag_count",
    "ack_flag_count",
    "fin_flag_count",
    "rst_flag_count",
    "psh_flag_count",
    "urg_flag_count",
    "ece_flag_count",
    "cwe_flag_count",
    # Byte/packet counters from flow records
    "total_fwd_packets",
    "total_backward_packets",
    "total_length_of_fwd_packets",
    "total_length_of_bwd_packets",
    # Window sizes (initial window from TCP handshake)
    "init_win_bytes_forward",
    "init_win_bytes_backward",
    # Subflow counters
    "subflow_fwd_bytes",
    "subflow_bwd_bytes",
    "subflow_fwd_packets",
    "subflow_bwd_packets",
    # Derived features computable from EVE flow data
    "derived_fwd_bwd_packet_ratio",
    "derived_fwd_bwd_byte_ratio",
    "derived_bytes_per_packet",
    "derived_psh_flag_ratio",
    "derived_syn_flag_ratio",
    "derived_ack_flag_ratio",
}

# Features derivable from raw PCAP (via CICFlowMeter or similar)
_PCAP_DERIVED_FEATURES: Final[set[str]] = {
    "fwd_packet_length_max",
    "fwd_packet_length_min",
    "fwd_packet_length_mean",
    "fwd_packet_length_std",
    "bwd_packet_length_max",
    "bwd_packet_length_min",
    "bwd_packet_length_mean",
    "bwd_packet_length_std",
    "flow_iat_mean",
    "flow_iat_std",
    "flow_iat_max",
    "flow_iat_min",
    "fwd_iat_total",
    "fwd_iat_mean",
    "fwd_iat_std",
    "fwd_iat_max",
    "fwd_iat_min",
    "bwd_iat_total",
    "bwd_iat_mean",
    "bwd_iat_std",
    "bwd_iat_max",
    "bwd_iat_min",
    "fwd_header_length",
    "bwd_header_length",
    "packet_length_mean",
    "packet_length_std",
    "packet_length_variance",
    "average_packet_size",
    "avg_fwd_segment_size",
    "avg_bwd_segment_size",
    "active_mean",
    "active_std",
    "active_max",
    "active_min",
    "idle_mean",
    "idle_std",
    "idle_max",
    "idle_min",
    "down/up_ratio",
    "fwd_packets/s",
    "bwd_packets/s",
    "min_packet_length",
    "max_packet_length",
    "fwd_act_data_pkts",
    "min_seg_size_forward",
    "derived_flow_iat_cv",
    "derived_active_idle_ratio",
    "derived_fwd_bytes_per_packet",
    "derived_bwd_bytes_per_packet",
    "derived_down_up_ratio_bytes",
    "derived_urg_flag_ratio",
}


def select_features_by_importance(
    X: pd.DataFrame,
    y: pd.Series,
    n_features: int = 40,
    random_state: int = 42,
) -> list[str]:
    """Select top-*n_features* by Random Forest permutation importance.

    A lightweight Random Forest (100 trees, max_depth 10) is trained and
    ``sklearn.inspection.permutation_importance`` is used to rank features.
    This avoids the bias of Gini importance towards high-cardinality features.

    Parameters
    ----------
    X:
        Feature matrix (numeric columns only).
    y:
        Target labels (integer-encoded).
    n_features:
        Number of features to keep.
    random_state:
        Seed for reproducibility.

    Returns
    -------
    list[str]
        Ordered list of the top feature names (most important first).
    """
    if n_features > X.shape[1]:
        logger.warning(
            "Requested %d features but only %d available – returning all",
            n_features,
            X.shape[1],
        )
        n_features = X.shape[1]

    logger.info("Training lightweight RF for feature selection (%d features) …", X.shape[1])
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        n_jobs=-1,
        random_state=random_state,
        class_weight="balanced",
    )
    rf.fit(X, y)

    logger.info("Computing permutation importance …")
    result = permutation_importance(
        rf,
        X,
        y,
        n_repeats=5,
        n_jobs=-1,
        random_state=random_state,
        scoring="f1_macro",
    )

    importances = pd.Series(result.importances_mean, index=X.columns)
    importances = importances.sort_values(ascending=False)

    selected = importances.head(n_features).index.tolist()
    logger.info(
        "Selected %d features. Top-5: %s",
        len(selected),
        selected[:5],
    )
    return selected


def validate_feature_schema(selected_features: list[str]) -> dict[str, str]:
    """Classify each feature by its runtime availability.

    Categories
    ----------
    ``suricata_eve``
        Directly available from Suricata EVE JSON logs.
    ``pcap_derived``
        Derivable from PCAP files (e.g., via CICFlowMeter).
    ``dataset_only``
        Only present in the CIC-IDS2018 dataset; not available at inference.

    Parameters
    ----------
    selected_features:
        List of feature names (e.g., output of :func:`select_features_by_importance`).

    Returns
    -------
    dict[str, str]
        Mapping ``{feature_name: category}``.
    """
    schema: dict[str, str] = {}
    for feat in selected_features:
        feat_lower = feat.lower().strip()
        if feat_lower in {f.lower() for f in SURICATA_EVE_FEATURES}:
            schema[feat] = "suricata_eve"
        elif feat_lower in {f.lower() for f in _PCAP_DERIVED_FEATURES}:
            schema[feat] = "pcap_derived"
        else:
            schema[feat] = "dataset_only"

    counts = {}
    for v in schema.values():
        counts[v] = counts.get(v, 0) + 1
    logger.info("Feature schema: %s", counts)
    return schema
