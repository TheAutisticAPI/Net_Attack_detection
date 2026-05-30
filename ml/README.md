# TheAutisticNIDS – Machine Learning Track

> Phase 1: Supervised classification of network intrusion attacks using the
> CSE-CIC-IDS2018 dataset.

## Project Structure

```
ml/
├── pyproject.toml              # Dependencies & project metadata
├── configs/
│   ├── lightgbm.yaml           # LightGBM default hyperparameters
│   └── xgboost.yaml            # XGBoost default hyperparameters
├── src/
│   ├── data/
│   │   └── loader.py           # Data loading, cleaning, splitting
│   ├── features/
│   │   ├── engineering.py      # Log transforms, derived features
│   │   └── selection.py        # Importance-based selection, schema validation
│   ├── models/
│   │   ├── train_lightgbm.py   # LightGBM training + MLflow
│   │   └── train_xgboost.py    # XGBoost training + MLflow
│   ├── evaluation/
│   │   └── metrics.py          # Metrics, confusion matrix, ROC-AUC, reports
│   └── explainability/         # Phase 3 (SHAP – placeholder)
└── tests/
    ├── test_loader.py           # Data loader tests
    ├── test_features.py         # Feature engineering tests
    └── test_models.py           # Model & metrics tests
```

## Quick Start

### 1. Install dependencies

```bash
cd ml
pip install -e ".[dev]"
```

### 2. Run tests

```bash
cd ml
pytest tests/ -v --tb=short
```

### 3. Train a model

```python
from pathlib import Path
from src.data.loader import load_cicids2018, clean_dataframe, stratified_split, LABEL_TO_INT
from src.features.engineering import apply_log_transforms, compute_derived_features
from src.models.train_lightgbm import train_lightgbm

# Load & clean
df = load_cicids2018(Path("path/to/csv/dir"))
df = clean_dataframe(df)

# Feature engineering
df = apply_log_transforms(df)
df = compute_derived_features(df)

# Encode labels
df["label_int"] = df["label"].map(LABEL_TO_INT)

# Split
train, val, test = stratified_split(df)

# Prepare features
feature_cols = [c for c in train.columns if c not in ("label", "label_int")]
X_train, y_train = train[feature_cols], train["label_int"]
X_val, y_val = val[feature_cols], val["label_int"]

# Train with MLflow tracking
model = train_lightgbm(X_train, y_train, X_val, y_val)
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **macro-F1** as primary metric | Treats rare attack classes equally; accuracy hides class imbalance |
| **`is_unbalance: true`** | LightGBM internally re-weights classes; no manual SMOTE needed |
| **Stratified splits** | Preserves class distribution across train/val/test |
| **log1p transforms** | Reduces impact of extreme outliers in flow statistics |
| **Permutation importance** | Avoids bias of Gini importance toward high-cardinality features |
| **Feature schema validation** | Flags features unavailable at inference time (Suricata pipeline) |

## Targets

- Overall macro-F1 ≥ **0.85**
- Per-class F1 ≥ **0.70** for every attack type

## Dataset

**CSE-CIC-IDS2018** – ~16.2 M rows, 80 features, 14 attack types + Benign.

Known artefacts handled by `loader.py`:
- Leading/trailing whitespace in column names
- `'Infinity'` / `'inf'` string values in numeric columns
- Entirely-NaN rows
- Inconsistent label capitalisation (e.g., `'dos hulk'` → `DoS-Hulk`)
- Varying timestamp formats across CSV files
