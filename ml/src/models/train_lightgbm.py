"""LightGBM training pipeline with MLflow experiment tracking.

Trains a multi-class LightGBM classifier with:
- Stratified 5-fold cross-validation for robust evaluation
- Class-weighted loss (``is_unbalance: true``) for imbalanced data
- Full MLflow logging: hyperparams, per-fold metrics, final model artifact
- Automatic model registration to MLflow Model Registry as 'Staging'
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import numpy as np
import yaml
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

__all__ = [
    "train_lightgbm",
    "load_production_model",
    "get_default_config",
]

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "lightgbm.yaml"


def get_default_config() -> dict[str, Any]:
    """Load default hyperparameters from ``configs/lightgbm.yaml``.

    Returns
    -------
    dict
        Hyperparameter dictionary.
    """
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)
    # Fallback defaults
    return {
        "objective": "multiclass",
        "metric": "multi_logloss",
        "num_class": 15,
        "learning_rate": 0.05,
        "num_leaves": 127,
        "max_depth": -1,
        "min_child_samples": 50,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "n_estimators": 500,
        "is_unbalance": True,
        "verbosity": -1,
        "random_state": 42,
    }


def train_lightgbm(
    X_train: np.ndarray | Any,
    y_train: np.ndarray | Any,
    X_val: np.ndarray | Any,
    y_val: np.ndarray | Any,
    config: dict[str, Any] | None = None,
    experiment_name: str = "nids-lightgbm",
) -> lgb.Booster:
    """Train a LightGBM multi-class classifier with MLflow tracking.

    Parameters
    ----------
    X_train, y_train:
        Training features and integer-encoded labels.
    X_val, y_val:
        Validation features and labels (used for early stopping and
        final metric reporting).
    config:
        Hyperparameter dict.  Merged on top of defaults from
        ``configs/lightgbm.yaml``.
    experiment_name:
        MLflow experiment name.

    Returns
    -------
    lgb.Booster
        Trained LightGBM Booster (best iteration selected by early
        stopping on validation multi_logloss).
    """
    params = get_default_config()
    if config:
        params.update(config)

    n_estimators = params.pop("n_estimators", 500)
    random_state = params.get("random_state", 42)

    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="lightgbm-train") as run:
        mlflow.log_params(params)
        mlflow.log_param("n_estimators", n_estimators)

        # ── Stratified 5-fold CV for robust metric estimates ───────
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
        fold_f1s: list[float] = []

        X_train_np = np.asarray(X_train)
        y_train_np = np.asarray(y_train)

        for fold, (trn_idx, oof_idx) in enumerate(skf.split(X_train_np, y_train_np)):
            X_trn, y_trn = X_train_np[trn_idx], y_train_np[trn_idx]
            X_oof, y_oof = X_train_np[oof_idx], y_train_np[oof_idx]

            ds_trn = lgb.Dataset(X_trn, label=y_trn)
            ds_oof = lgb.Dataset(X_oof, label=y_oof, reference=ds_trn)

            booster = lgb.train(
                params,
                ds_trn,
                num_boost_round=n_estimators,
                valid_sets=[ds_trn, ds_oof],
                valid_names=["train", "valid"],
                callbacks=[
                    lgb.early_stopping(stopping_rounds=30, verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )

            y_oof_pred = booster.predict(X_oof).argmax(axis=1)
            fold_macro_f1 = float(f1_score(y_oof, y_oof_pred, average="macro", zero_division=0))
            fold_f1s.append(fold_macro_f1)
            mlflow.log_metric(f"fold_{fold}_macro_f1", fold_macro_f1, step=fold)
            logger.info("Fold %d macro-F1: %.4f", fold, fold_macro_f1)

        cv_mean_f1 = float(np.mean(fold_f1s))
        cv_std_f1 = float(np.std(fold_f1s))
        mlflow.log_metric("cv_mean_macro_f1", cv_mean_f1)
        mlflow.log_metric("cv_std_macro_f1", cv_std_f1)
        logger.info("CV macro-F1: %.4f ± %.4f", cv_mean_f1, cv_std_f1)

        # ── Final model on full training set ───────────────────────
        ds_train_full = lgb.Dataset(np.asarray(X_train), label=np.asarray(y_train))
        ds_val = lgb.Dataset(
            np.asarray(X_val), label=np.asarray(y_val), reference=ds_train_full
        )

        final_booster = lgb.train(
            params,
            ds_train_full,
            num_boost_round=n_estimators,
            valid_sets=[ds_train_full, ds_val],
            valid_names=["train", "valid"],
            callbacks=[
                lgb.early_stopping(stopping_rounds=30, verbose=False),
                lgb.log_evaluation(period=50),
            ],
        )

        # Validation metrics
        y_val_pred = final_booster.predict(np.asarray(X_val)).argmax(axis=1)
        val_macro_f1 = float(f1_score(y_val, y_val_pred, average="macro", zero_division=0))
        mlflow.log_metric("val_macro_f1", val_macro_f1)
        logger.info("Final validation macro-F1: %.4f", val_macro_f1)

        # Log model
        mlflow.lightgbm.log_model(
            final_booster,
            artifact_path="model",
            registered_model_name="nids-lightgbm",
        )

        # Transition to Staging
        client = mlflow.tracking.MlflowClient()
        latest_versions = client.get_latest_versions("nids-lightgbm")
        if latest_versions:
            latest = latest_versions[-1]
            client.transition_model_version_stage(
                name="nids-lightgbm",
                version=latest.version,
                stage="Staging",
            )
            logger.info(
                "Registered model version %s as Staging (run %s)",
                latest.version,
                run.info.run_id,
            )

    return final_booster


def load_production_model(model_name: str = "nids-lightgbm") -> lgb.Booster:
    """Load the Production (or Staging) model from MLflow Model Registry.

    Tries ``Production`` stage first, then falls back to ``Staging``.

    Parameters
    ----------
    model_name:
        Registered model name in MLflow.

    Returns
    -------
    lgb.Booster
        Loaded LightGBM Booster ready for inference.

    Raises
    ------
    mlflow.exceptions.MlflowException
        If no model version is found in Production or Staging.
    """
    for stage in ("Production", "Staging"):
        try:
            model_uri = f"models:/{model_name}/{stage}"
            model = mlflow.lightgbm.load_model(model_uri)
            logger.info("Loaded %s model '%s' from %s", stage, model_name, model_uri)
            return model
        except Exception:
            logger.debug("No %s version found for '%s'", stage, model_name)
            continue

    raise mlflow.exceptions.MlflowException(
        f"No Production or Staging version found for model '{model_name}'"
    )
