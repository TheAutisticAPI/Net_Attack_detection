"""XGBoost training pipeline with MLflow experiment tracking.

Mirror of the LightGBM pipeline but using XGBoost.  Same interface so
the two models can be compared in a single experiment dashboard.

- Stratified 5-fold cross-validation
- ``scale_pos_weight`` / sample weights for class imbalance
- Full MLflow logging: hyperparams, per-fold metrics, model artifact
- Automatic model registration as 'Staging'
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import mlflow
import mlflow.xgboost
import numpy as np
import xgboost as xgb
import yaml
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.utils.class_weight import compute_sample_weight

__all__ = [
    "train_xgboost",
    "load_production_model",
    "get_default_config",
]

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "xgboost.yaml"


def get_default_config() -> dict[str, Any]:
    """Load default hyperparameters from ``configs/xgboost.yaml``.

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
        "objective": "multi:softprob",
        "eval_metric": "mlogloss",
        "num_class": 15,
        "learning_rate": 0.05,
        "max_depth": 8,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "n_estimators": 500,
        "tree_method": "hist",
        "verbosity": 0,
        "random_state": 42,
    }


def train_xgboost(
    X_train: np.ndarray | Any,
    y_train: np.ndarray | Any,
    X_val: np.ndarray | Any,
    y_val: np.ndarray | Any,
    config: dict[str, Any] | None = None,
    experiment_name: str = "nids-xgboost",
) -> xgb.Booster:
    """Train an XGBoost multi-class classifier with MLflow tracking.

    Parameters
    ----------
    X_train, y_train:
        Training features and integer-encoded labels.
    X_val, y_val:
        Validation features and labels.
    config:
        Hyperparameter dict, merged on top of defaults.
    experiment_name:
        MLflow experiment name.

    Returns
    -------
    xgb.Booster
        Trained XGBoost Booster.
    """
    params = get_default_config()
    if config:
        params.update(config)

    n_estimators = params.pop("n_estimators", 500)
    random_state = params.get("random_state", 42)

    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="xgboost-train") as run:
        mlflow.log_params(params)
        mlflow.log_param("n_estimators", n_estimators)

        X_train_np = np.asarray(X_train)
        y_train_np = np.asarray(y_train)

        # Class-weighted sample weights
        sample_weights = compute_sample_weight("balanced", y_train_np)

        # ── Stratified 5-fold CV ───────────────────────────────────
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
        fold_f1s: list[float] = []

        for fold, (trn_idx, oof_idx) in enumerate(skf.split(X_train_np, y_train_np)):
            X_trn, y_trn = X_train_np[trn_idx], y_train_np[trn_idx]
            X_oof, y_oof = X_train_np[oof_idx], y_train_np[oof_idx]
            w_trn = sample_weights[trn_idx]

            dtrain = xgb.DMatrix(X_trn, label=y_trn, weight=w_trn)
            doof = xgb.DMatrix(X_oof, label=y_oof)

            booster = xgb.train(
                params,
                dtrain,
                num_boost_round=n_estimators,
                evals=[(dtrain, "train"), (doof, "valid")],
                early_stopping_rounds=30,
                verbose_eval=False,
            )

            y_oof_prob = booster.predict(doof)
            y_oof_pred = y_oof_prob.argmax(axis=1)
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
        dtrain_full = xgb.DMatrix(X_train_np, label=y_train_np, weight=sample_weights)
        dval = xgb.DMatrix(np.asarray(X_val), label=np.asarray(y_val))

        final_booster = xgb.train(
            params,
            dtrain_full,
            num_boost_round=n_estimators,
            evals=[(dtrain_full, "train"), (dval, "valid")],
            early_stopping_rounds=30,
            verbose_eval=50,
        )

        # Validation metrics
        y_val_prob = final_booster.predict(dval)
        y_val_pred = y_val_prob.argmax(axis=1)
        val_macro_f1 = float(f1_score(y_val, y_val_pred, average="macro", zero_division=0))
        mlflow.log_metric("val_macro_f1", val_macro_f1)
        logger.info("Final validation macro-F1: %.4f", val_macro_f1)

        # Log model
        mlflow.xgboost.log_model(
            final_booster,
            artifact_path="model",
            registered_model_name="nids-xgboost",
        )

        # Transition to Staging
        client = mlflow.tracking.MlflowClient()
        latest_versions = client.get_latest_versions("nids-xgboost")
        if latest_versions:
            latest = latest_versions[-1]
            client.transition_model_version_stage(
                name="nids-xgboost",
                version=latest.version,
                stage="Staging",
            )
            logger.info(
                "Registered model version %s as Staging (run %s)",
                latest.version,
                run.info.run_id,
            )

    return final_booster


def load_production_model(model_name: str = "nids-xgboost") -> xgb.Booster:
    """Load the Production (or Staging) XGBoost model from MLflow.

    Parameters
    ----------
    model_name:
        Registered model name.

    Returns
    -------
    xgb.Booster
        Loaded XGBoost Booster ready for inference.

    Raises
    ------
    mlflow.exceptions.MlflowException
        If no model version is found.
    """
    for stage in ("Production", "Staging"):
        try:
            model_uri = f"models:/{model_name}/{stage}"
            model = mlflow.xgboost.load_model(model_uri)
            logger.info("Loaded %s model '%s'", stage, model_name)
            return model
        except Exception:
            logger.debug("No %s version found for '%s'", stage, model_name)
            continue

    raise mlflow.exceptions.MlflowException(
        f"No Production or Staging version found for model '{model_name}'"
    )
