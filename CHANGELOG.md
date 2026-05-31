# Changelog

All notable changes to **TheAutisticNIDS** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0-alpha] - 2026-05-30

This initial pre-release implements the foundation for **Phase 1: Baseline Pipeline + Platform Foundation** of the Network Intrusion Detection System. It delivers fully testable foundations across both the **ML Track (🔬)** and the **Web Track (🌐)**.

### Added

#### ML Track (🔬)
- **Data Loading & Cleaning (`ml/src/data/loader.py`)**: Built a data processing engine for the CSE-CIC-IDS2018 dataset. Implements handling of infinite/NaN values, stratified 70/15/15 train/val/test splits, bidirectional class mapping, and a robust flow deduplication strategy (deduplicating by flow 5-tuple and timestamp window to prevent data leakage).
- **Feature Engineering & Selection (`ml/src/features/`)**:
  - `engineering.py`: Automated log-transformations for highly skewed features, custom feature extraction (12 derived features including byte/packet ratios, flag ratios, IAT coefficient of variation, and active/idle ratios) with safe division handling.
  - `selection.py`: Feature selection using Random Forest permutation importance and a schema validator that maps CSE-CIC-IDS2018 features against Suricata EVE JSON fields.
- **Model Training & Evaluation (`ml/src/models/`, `ml/src/evaluation/`)**:
  - `train_lightgbm.py`: Stratified 5-fold cross-validation, class-weighted loss, early stopping, and automatic MLflow logging/model registration in the `Staging` stage.
  - `train_xgboost.py`: Baseline training pipeline mirroring the LightGBM setup.
  - `metrics.py`: Evaluator compiling per-class precision/recall/F1 metrics, one-vs-rest ROC-AUC curves, and inference latency benchmarking (ms per 1k flows).
- **ML Testing Suites**: 31 comprehensive test cases validating loader, feature, and model scripts using synthetic data.

#### Web Track (🌐)
- **FastAPI Core Service (`api/app/`)**: Established the asynchronous backend server with routers for health, model registry, alert queries, and predictions. Features lifespan-managed startup/shutdown and CORS validation.
- **Database Architecture & Migrations (`api/app/db/`)**:
  - `models.py`: Implemented 5 forward-compatible PostgreSQL tables (`flows`, `predictions`, `alerts`, `shap_explanations`, `model_versions`) designed to accommodate SHAP values (Phase 3), anomaly indicators (Phase 2), case statuses (Phase 5), and row-level security tenant IDs (Phase 6).
  - `session.py`: Database engine instantiation using asyncpg and async sessions.
  - Alembic migrations setup for database evolutionary versioning.
- **Analyst Dashboard (`web/`)**:
  - A Next.js 15 (App Router, TypeScript) dashboard featuring a custom, responsive dark-mode design system with micro-animations.
  - Alerts explorer with multi-parameter filtering (attack type, confidence, date range) and visual indicator widgets.
  - Model registry browser rendering hyperparameter configurations and per-class performance tables.
  - In-browser mock data generator simulating CSE-CIC-IDS2018 distributions across all 14 attack classes.
- **API Testing Suites**: 30 integration test cases executing against an asynchronous, in-memory SQLite backend.

#### Infrastructure
- **Docker Compose (`docker-compose.yml`)**: Designed a single-command local orchestration file provisioning PostgreSQL 16, MLflow tracking server, FastAPI backend, and Next.js frontend.
- **Multi-Stage Dockerfiles**: Formulated optimized multi-stage build recipes for `api/Dockerfile` (ARM64-ready) and `web/Dockerfile` (next-standalone output mode).
- **Environment and Scaffolding**: Setup root `.env.example`, `.gitignore`, and detailed architecture README with system workflows.

---

### Commits in this Release

- `db1a91a` - chore: initial project scaffolding with Docker Compose
- `a2e99de` - feat(ml): add baseline classifier pipeline for CSE-CIC-IDS2018
- `69d8a18` - feat(api): add FastAPI backend with PostgreSQL schema and Alembic
- `c4cc8ed` - feat(web): add Next.js 15 analyst dashboard with dark mode
- `83d571a` - docs(ml): evaluation report placeholder

[0.1.0-alpha]: https://github.com/TheAutisticAPI/Net_Attack_detection/releases/tag/v0.1.0-alpha
