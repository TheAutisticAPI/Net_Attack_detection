"""Unit tests for model training pipelines and evaluation metrics.

Uses tiny synthetic datasets to smoke-test LightGBM and XGBoost training,
plus full coverage of the evaluation metrics module.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from sklearn.datasets import make_classification

from src.evaluation.metrics import (
    benchmark_inference_latency,
    compute_classification_report,
    compute_confusion_matrix,
    compute_roc_auc,
    generate_evaluation_report,
)


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def synthetic_multiclass() -> dict:
    """Tiny 4-class classification dataset for smoke tests."""
    X, y = make_classification(
        n_samples=400,
        n_features=10,
        n_informative=6,
        n_classes=4,
        n_clusters_per_class=1,
        random_state=42,
    )
    # Split manually: 300 train, 50 val, 50 test
    return {
        "X_train": X[:300],
        "y_train": y[:300],
        "X_val": X[300:350],
        "y_val": y[300:350],
        "X_test": X[350:],
        "y_test": y[350:],
        "n_classes": 4,
    }


@pytest.fixture()
def prediction_data() -> dict:
    """Pre-canned predictions for metrics testing."""
    rng = np.random.RandomState(42)
    n = 100
    n_classes = 4
    y_true = rng.randint(0, n_classes, n)
    y_pred = y_true.copy()
    # Introduce some errors
    flip_idx = rng.choice(n, size=15, replace=False)
    y_pred[flip_idx] = (y_pred[flip_idx] + 1) % n_classes

    # Probability scores
    y_score = np.zeros((n, n_classes))
    for i in range(n):
        y_score[i, y_pred[i]] = 0.7
        remaining = 0.3 / (n_classes - 1)
        for j in range(n_classes):
            if j != y_pred[i]:
                y_score[i, j] = remaining

    labels = list(range(n_classes))
    label_names = [f"class_{i}" for i in range(n_classes)]

    return {
        "y_true": y_true,
        "y_pred": y_pred,
        "y_score": y_score,
        "labels": labels,
        "label_names": label_names,
        "n_classes": n_classes,
    }


# ── Tests: LightGBM smoke test ────────────────────────────────────────


class TestLightGBMSmoke:
    """Smoke tests for the LightGBM training pipeline."""

    def test_lightgbm_smoke(self, synthetic_multiclass: dict) -> None:
        """LightGBM should train and produce predictions of the right shape."""
        # Import here so the test is skipped if lightgbm is not installed
        lgb = pytest.importorskip("lightgbm")
        from src.models.train_lightgbm import get_default_config

        data = synthetic_multiclass
        config = get_default_config()
        config["num_class"] = data["n_classes"]
        config["n_estimators"] = 10  # fast
        config["verbosity"] = -1
        n_estimators = config.pop("n_estimators")

        ds_train = lgb.Dataset(data["X_train"], label=data["y_train"])
        ds_val = lgb.Dataset(data["X_val"], label=data["y_val"], reference=ds_train)

        booster = lgb.train(
            config,
            ds_train,
            num_boost_round=n_estimators,
            valid_sets=[ds_val],
            valid_names=["valid"],
            callbacks=[lgb.log_evaluation(period=0)],
        )

        preds = booster.predict(data["X_test"])
        assert preds.shape == (len(data["X_test"]), data["n_classes"])
        assert np.allclose(preds.sum(axis=1), 1.0, atol=1e-5)


# ── Tests: XGBoost smoke test ─────────────────────────────────────────


class TestXGBoostSmoke:
    """Smoke tests for the XGBoost training pipeline."""

    def test_xgboost_smoke(self, synthetic_multiclass: dict) -> None:
        """XGBoost should train and produce predictions of the right shape."""
        xgb = pytest.importorskip("xgboost")
        from src.models.train_xgboost import get_default_config

        data = synthetic_multiclass
        config = get_default_config()
        config["num_class"] = data["n_classes"]
        config["n_estimators"] = 10
        n_estimators = config.pop("n_estimators")

        dtrain = xgb.DMatrix(data["X_train"], label=data["y_train"])
        dval = xgb.DMatrix(data["X_val"], label=data["y_val"])

        booster = xgb.train(
            config,
            dtrain,
            num_boost_round=n_estimators,
            evals=[(dval, "valid")],
            verbose_eval=False,
        )

        dtest = xgb.DMatrix(data["X_test"])
        preds = booster.predict(dtest)
        assert preds.shape == (len(data["X_test"]), data["n_classes"])
        assert np.allclose(preds.sum(axis=1), 1.0, atol=1e-5)


# ── Tests: Classification metrics ─────────────────────────────────────


class TestMetrics:
    """Tests for compute_classification_report()."""

    def test_metrics_computation(self, prediction_data: dict) -> None:
        """Classification report should contain macro_f1 and per-class stats."""
        report = compute_classification_report(
            prediction_data["y_true"],
            prediction_data["y_pred"],
            prediction_data["labels"],
            prediction_data["label_names"],
        )
        assert "macro_f1" in report
        assert 0.0 <= report["macro_f1"] <= 1.0
        # Per-class entries
        for name in prediction_data["label_names"]:
            assert name in report
            assert "precision" in report[name]
            assert "recall" in report[name]
            assert "f1-score" in report[name]

    def test_metrics_perfect_predictions(self) -> None:
        """Perfect predictions should yield macro_f1 = 1.0."""
        y = np.array([0, 1, 2, 0, 1, 2])
        report = compute_classification_report(
            y, y, labels=[0, 1, 2], label_names=["a", "b", "c"]
        )
        assert report["macro_f1"] == pytest.approx(1.0)


# ── Tests: Confusion matrix ───────────────────────────────────────────


class TestConfusionMatrix:
    """Tests for compute_confusion_matrix()."""

    def test_confusion_matrix_shape(self, prediction_data: dict) -> None:
        """Confusion matrix must be (n_classes × n_classes)."""
        cm = compute_confusion_matrix(
            prediction_data["y_true"],
            prediction_data["y_pred"],
            prediction_data["label_names"],
        )
        n = prediction_data["n_classes"]
        assert cm.shape == (n, n)

    def test_confusion_matrix_diagonal_dominant(self, prediction_data: dict) -> None:
        """With 85% accuracy, diagonal should dominate."""
        cm = compute_confusion_matrix(
            prediction_data["y_true"],
            prediction_data["y_pred"],
            prediction_data["label_names"],
        )
        assert cm.trace() > cm.sum() * 0.5  # diagonal > 50% of total


# ── Tests: ROC-AUC ────────────────────────────────────────────────────


class TestRocAuc:
    """Tests for compute_roc_auc()."""

    def test_roc_auc_values(self, prediction_data: dict) -> None:
        """ROC-AUC values should be between 0 and 1."""
        auc = compute_roc_auc(
            prediction_data["y_true"],
            prediction_data["y_score"],
            prediction_data["label_names"],
        )
        assert "macro_auc" in auc
        assert 0.0 <= auc["macro_auc"] <= 1.0
        for name in prediction_data["label_names"]:
            assert name in auc
            if not np.isnan(auc[name]):
                assert 0.0 <= auc[name] <= 1.0


# ── Tests: Inference latency ──────────────────────────────────────────


class TestInferenceLatency:
    """Tests for benchmark_inference_latency()."""

    def test_inference_latency_benchmark(self) -> None:
        """Latency benchmark should return expected keys with sensible values."""
        # Mock model with a predict method
        mock_model = MagicMock()
        mock_model.predict = MagicMock(return_value=np.zeros(50))
        X = np.random.randn(50, 5)

        result = benchmark_inference_latency(mock_model, X, n_iterations=3)

        assert "median_ms_per_1000" in result
        assert "mean_ms_per_1000" in result
        assert "std_ms_per_1000" in result
        assert result["n_samples"] == 50
        assert result["n_iterations"] == 3
        assert result["median_ms_per_1000"] >= 0
        assert mock_model.predict.call_count == 3


# ── Tests: Evaluation report ──────────────────────────────────────────


class TestEvaluationReport:
    """Tests for generate_evaluation_report()."""

    def test_report_generation(self, prediction_data: dict) -> None:
        """Report should be written as a valid Markdown file."""
        report = compute_classification_report(
            prediction_data["y_true"],
            prediction_data["y_pred"],
            prediction_data["labels"],
            prediction_data["label_names"],
        )
        metrics = {"classification_report": report}

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "report.md"
            generate_evaluation_report(metrics, out_path)

            assert out_path.exists()
            content = out_path.read_text(encoding="utf-8")
            assert "# NIDS Model Evaluation Report" in content
            assert "Macro-F1" in content
