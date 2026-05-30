"""Evaluation metrics, reporting, and latency benchmarking for NIDS models.

Primary metric: **macro-averaged F1** (treats every attack class equally,
regardless of prevalence).  Target thresholds:

- Overall macro-F1 ≥ 0.85
- Per-class F1 ≥ 0.70 for every attack type
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize

__all__ = [
    "compute_classification_report",
    "compute_confusion_matrix",
    "compute_roc_auc",
    "benchmark_inference_latency",
    "generate_evaluation_report",
]

logger = logging.getLogger(__name__)


def compute_classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: list[int],
    label_names: list[str],
) -> dict[str, Any]:
    """Compute per-class precision / recall / F1 and macro-F1.

    Parameters
    ----------
    y_true:
        Ground-truth integer-encoded labels.
    y_pred:
        Predicted integer-encoded labels.
    labels:
        Ordered list of integer label codes.
    label_names:
        Human-readable names corresponding to *labels*.

    Returns
    -------
    dict
        Nested dict identical to ``sklearn.metrics.classification_report``
        output with ``output_dict=True``, plus a top-level ``"macro_f1"``
        convenience key.
    """
    report: dict[str, Any] = classification_report(
        y_true,
        y_pred,
        labels=labels,
        target_names=label_names,
        output_dict=True,
        zero_division=0,
    )
    report["macro_f1"] = report["macro avg"]["f1-score"]
    return report


def compute_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label_names: list[str],
) -> np.ndarray:
    """Compute a confusion matrix.

    Parameters
    ----------
    y_true:
        Ground-truth labels.
    y_pred:
        Predicted labels.
    label_names:
        Ordered label names (used to infer ``labels`` integer range).

    Returns
    -------
    np.ndarray
        Shape ``(n_classes, n_classes)`` confusion matrix.
    """
    labels = list(range(len(label_names)))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    return cm


def compute_roc_auc(
    y_true: np.ndarray,
    y_score: np.ndarray,
    label_names: list[str],
) -> dict[str, float]:
    """Compute one-vs-rest ROC-AUC per class.

    Parameters
    ----------
    y_true:
        Ground-truth integer-encoded labels.
    y_score:
        Predicted probability matrix of shape ``(n_samples, n_classes)``.
    label_names:
        Ordered label names.

    Returns
    -------
    dict[str, float]
        ``{label_name: auc_score}`` plus ``"macro_auc"`` averaging over
        all classes.
    """
    labels = list(range(len(label_names)))
    y_true_bin = label_binarize(y_true, classes=labels)

    auc_scores: dict[str, float] = {}
    valid_aucs: list[float] = []

    for idx, name in enumerate(label_names):
        # Skip classes with no positive samples (AUC is undefined)
        if y_true_bin[:, idx].sum() == 0:
            logger.warning("Class '%s' has no true positives – skipping AUC", name)
            auc_scores[name] = float("nan")
            continue
        try:
            score = float(roc_auc_score(y_true_bin[:, idx], y_score[:, idx]))
        except ValueError:
            score = float("nan")
        auc_scores[name] = score
        if not np.isnan(score):
            valid_aucs.append(score)

    auc_scores["macro_auc"] = float(np.mean(valid_aucs)) if valid_aucs else float("nan")
    return auc_scores


def benchmark_inference_latency(
    model: Any,
    X_sample: np.ndarray,
    n_iterations: int = 10,
) -> dict[str, float]:
    """Measure inference latency in milliseconds per 1 000 flows.

    Parameters
    ----------
    model:
        A trained model with a ``.predict()`` method.
    X_sample:
        Feature matrix to run predictions on.
    n_iterations:
        Number of times to repeat; final result is the median.

    Returns
    -------
    dict[str, float]
        ``{"median_ms_per_1000": …, "mean_ms_per_1000": …, "std_ms_per_1000": …,
          "n_samples": …, "n_iterations": …}``
    """
    n_samples = X_sample.shape[0]
    timings: list[float] = []

    for _ in range(n_iterations):
        start = time.perf_counter()
        model.predict(X_sample)
        elapsed = time.perf_counter() - start
        # Normalise to ms per 1 000 flows
        ms_per_1000 = (elapsed / n_samples) * 1_000 * 1_000  # seconds→ms, then ×1000 flows
        timings.append(ms_per_1000)

    result = {
        "median_ms_per_1000": float(np.median(timings)),
        "mean_ms_per_1000": float(np.mean(timings)),
        "std_ms_per_1000": float(np.std(timings)),
        "n_samples": n_samples,
        "n_iterations": n_iterations,
    }
    logger.info(
        "Inference latency: %.2f ms / 1000 flows (median over %d iterations)",
        result["median_ms_per_1000"],
        n_iterations,
    )
    return result


def generate_evaluation_report(metrics: dict[str, Any], output_path: Path) -> None:
    """Write a Markdown evaluation report to disk.

    Parameters
    ----------
    metrics:
        Dictionary containing at least ``"classification_report"``,
        optionally ``"roc_auc"`` and ``"latency"``.
    output_path:
        Path for the output ``.md`` file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# NIDS Model Evaluation Report",
        "",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    # ── Classification report ──────────────────────────────────────
    cr = metrics.get("classification_report", {})
    macro_f1 = cr.get("macro_f1", cr.get("macro avg", {}).get("f1-score", "N/A"))
    lines.append(f"## Overall Macro-F1: {macro_f1:.4f}" if isinstance(macro_f1, float) else f"## Overall Macro-F1: {macro_f1}")
    lines.append("")

    target_met = isinstance(macro_f1, float) and macro_f1 >= 0.85
    lines.append(f"> Target ≥ 0.85: **{'✅ MET' if target_met else '❌ NOT MET'}**")
    lines.append("")

    # Per-class table
    lines.append("### Per-Class Metrics")
    lines.append("")
    lines.append("| Class | Precision | Recall | F1-Score | Support |")
    lines.append("|-------|-----------|--------|----------|---------|")
    for key, vals in cr.items():
        if isinstance(vals, dict) and "precision" in vals:
            flag = ""
            f1 = vals.get("f1-score", 0)
            if isinstance(f1, float) and f1 < 0.70 and key not in ("macro avg", "weighted avg", "micro avg"):
                flag = " ⚠️"
            lines.append(
                f"| {key}{flag} | {vals.get('precision', 0):.4f} | "
                f"{vals.get('recall', 0):.4f} | {vals.get('f1-score', 0):.4f} | "
                f"{int(vals.get('support', 0))} |"
            )
    lines.append("")

    # ── ROC-AUC ────────────────────────────────────────────────────
    roc = metrics.get("roc_auc")
    if roc:
        lines.append("### ROC-AUC (One-vs-Rest)")
        lines.append("")
        lines.append(f"**Macro AUC**: {roc.get('macro_auc', 'N/A'):.4f}" if isinstance(roc.get("macro_auc"), float) else f"**Macro AUC**: {roc.get('macro_auc', 'N/A')}")
        lines.append("")
        lines.append("| Class | AUC |")
        lines.append("|-------|-----|")
        for k, v in roc.items():
            if k != "macro_auc":
                lines.append(f"| {k} | {v:.4f} |" if isinstance(v, float) and not np.isnan(v) else f"| {k} | N/A |")
        lines.append("")

    # ── Latency ────────────────────────────────────────────────────
    latency = metrics.get("latency")
    if latency:
        lines.append("### Inference Latency")
        lines.append("")
        lines.append(f"- **Median**: {latency['median_ms_per_1000']:.2f} ms / 1 000 flows")
        lines.append(f"- **Mean ± Std**: {latency['mean_ms_per_1000']:.2f} ± {latency['std_ms_per_1000']:.2f} ms")
        lines.append(f"- **Samples**: {latency['n_samples']}, **Iterations**: {latency['n_iterations']}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Evaluation report written to %s", output_path)
