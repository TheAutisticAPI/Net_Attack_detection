# Project Roadmap & Implementation Status

This document tracks the engineering progress of **TheAutisticNIDS** (Network Intrusion Detection System) across all 7 development phases. Each phase is a fully testable, functional system increment containing parallel **ML (🔬)** and **Web (🌐)** tracks.

---

## 📊 Executive Summary

| Phase | Description | Track | Status | Progress | Est. Completion |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Phase 1** | **Baseline Pipeline + Platform Foundation** | 🔬 & 🌐 | **In Progress** | `██████████░` 90% | Q2 2026 (Active) |
| **Phase 2** | **Anomaly Detection + Dashboard Foundation** | 🔬 & 🌐 | **Planned** | `░░░░░░░░░░░` 0% | Q2 2026 |
| **Phase 3** | **Explainability + Alert Visualisation** | 🔬 & 🌐 | **Planned** | `░░░░░░░░░░░` 0% | Q3 2026 |
| **Phase 4** | **Live Ingestion + Concept Drift Detection** | 🔬 & 🌐 | **Planned** | `░░░░░░░░░░░` 0% | Q3 2026 |
| **Phase 5** | **Analyst Triage & Active Learning Loop** | 🔬 & 🌐 | **Planned** | `░░░░░░░░░░░` 0% | Q4 2026 |
| **Phase 6** | **Multi-Tenant Isolation + Hardening** | 🔬 & 🌐 | **Planned** | `░░░░░░░░░░░` 0% | Q4 2026 |
| **Phase 7** | **Research Extensions (Scope Permitting)** | 🔬 & 🌐 | **Planned** | `░░░░░░░░░░░` 0% | Ongoing |

---

## 🎯 Current Focus: Phase 1 Integration & Training
We have built all modular components for Phase 1. The immediate next steps are:
1. **Step 9**: Load the trained ML model from MLflow inside the FastAPI lifespan and wire it into the `/predict` endpoint.
2. **Step 10**: Place the raw `CSE-CIC-IDS2018` dataset into the raw directory, execute the training pipeline, and populate `ml/EVALUATION.md`.

---

## 🗓️ Phase-by-Phase Checklist

### Phase 1: Baseline Pipeline + Platform Foundation
**Goal:** Establish clean data pipelines, baseline ML models, APIs, relational database schema, and an analyst interface.
- [x] **Project Scaffolding & Shared Configs**
  - [x] Docker Compose developer setup (`postgres`, `api`, `web`, `mlflow`)
  - [x] Root configuration (`.gitignore`, `.env.example`, `README.md`)
  - [x] Dockerfiles for API (ARM64-ready) and Web (Standalone-ready)
- [x] **🔬 ML Track: Baseline Classifier**
  - [x] Data loading, cleaning, infinite value replacement, and train/val/test splits (`loader.py`)
  - [x] Feature deduplication (prevent train-test leakage across time windows)
  - [x] Skewness-aware log-transforms and 12 custom derived features (`engineering.py`)
  - [x] Feature selection via Random Forest permutation importance (`selection.py`)
  - [x] Suricata EVE schema alignment & mapping validator
  - [x] LightGBM stratified 5-fold cross-validation with MLflow logging
  - [x] XGBoost stratified 5-fold cross-validation comparison model
  - [x] Model evaluator & per-class precision/recall/F1 metrics (`metrics.py`)
  - [x] ML unit testing suite (31 tests passing)
- [x] **🌐 Web Track: Platform Scaffolding**
  - [x] Forward-compatible PostgreSQL schema (`flows`, `predictions`, `alerts`, `shap_explanations`, `model_versions`)
  - [x] Asynchronous database engine & connection pool setup (`asyncpg` + `SQLAlchemy`)
  - [x] Async migrations structure using Alembic
  - [x] Asynchronous FastAPI core skeleton
  - [x] Schemas for predictions, health check, alert lists, and ML models
  - [x] `/health` connectivity and uptime health checks
  - [x] `/alerts` & `/alerts/{id}` paginated query endpoints
  - [x] `/models` registry browser query API
  - [x] Next.js 15 App router dashboard framework in dark mode
  - [x] UI Card/Grid dashboards with chart overlays using `Recharts`
  - [x] Filterable and paginated alerts tabular page with status badges
  - [x] Model registry management page displaying historical metrics
  - [x] Local browser-based mock data engine representing all 14 attack classes
  - [x] API unit testing suite using async SQLite mock (30 tests passing)
- [/] **🔌 Integration & Training**
  - [x] API router `/predict` structure
  - [ ] Connect MLflow model loading into FastAPI service lifecycle
  - [ ] E2E integration test verification (`predict` -> DB -> API -> Dashboard)
  - [ ] Local training run with complete `CSE-CIC-IDS2018` dataset (~6 GB raw)
  - [ ] Save metrics & register best classifier to `Staging` stage
  - [ ] Populate model verification metrics into `ml/EVALUATION.md`

---

### Phase 2: Anomaly Detection + Dashboard Foundation
**Goal:** Add a zero-day/statistical anomaly detection layer running in parallel to the signature classifier, and upgrade the dashboard to support dual-layer indicators.
- [ ] **🔬 ML Track: Anomaly Detection Layer**
  - [ ] Train Isolation Forest exclusively on benign flows from the training split
  - [ ] Calibrate decision threshold on validation set to achieve **FPR ≤ 5%**
  - [ ] Parallel inference engine (return both classifier labels and anomaly scores)
  - [ ] Generate PR curves for Isolation Forest thresholds
  - [ ] Document difference between Isolation Forest `contamination` and calibration threshold
  - [ ] Write analysis on outlier vs. classifier performance
  - [ ] Log and register Isolation Forest in MLflow alongside classifier
- [ ] **🌐 Web Track: Dashboard Foundation**
  - [ ] Update `/predict` to return dual-layer outputs (`label`, `confidence`, `anomaly_score`, `anomaly_flag`)
  - [ ] Update `/alerts` to support filtering by anomaly flag and sorting by anomaly score
  - [ ] Alert list UI: render severity color-coding, anomaly scores, and flags
  - [ ] Alert detail UI: prepare layouts for SHAP explainability cards
  - [ ] Visualizations: Recharts histogram of anomaly scores, scatter plots for anomalous clusterings

---

### Phase 3: Explainability + Alert Visualisation
**Goal:** Implement local model explanations via SHAP and design interactive breakdown charts for security analysts.
- [ ] **🔬 ML Track: Explainability Module**
  - [ ] Integrate SHAP `TreeExplainer` for per-alert explanations (top-5 feature contributions)
  - [ ] Generate global feature importance plots (SHAP beeswarm)
  - [ ] Design async worker pattern to save SHAP attributions in PostgreSQL without blocking `/predict`
  - [ ] Verify feature attributions against network domain rules (e.g., DoS must exhibit high flow rate)
  - [ ] Perform stability checks: compare SHAP vs. LIME feature allocations on sample alerts
- [ ] **🌐 Web Track: Explainability Visualisation**
  - [ ] Implement `GET /alerts/{id}/explanation` returning SHAP JSON payload
  - [ ] Implement `GET /models/{id}/global-importance` returning beeswarm aggregates
  - [ ] Analyst Dashboard: Render real-time SHAP waterfall charts with push/pull attribution bars
  - [ ] Model Registry: Render global beeswarm charts filterable by attack class
  - [ ] Compare page: Render LightGBM vs. XGBoost training times, latency, and drift metrics

---

### Phase 4: Live Ingestion + Concept Drift Detection
**Goal:** Connect the system to live Suricata infrastructure, establish real-time socket/SSE feeds, and flag concept drift.
- [ ] **🔬 ML Track: Ingestion & Drift**
  - [ ] EVE JSON pipeline: Tail, parse, and transform Suricata events to Phase 1 feature format
  - [ ] River ADWIN integration: Monitor rolling metrics (F1 proxy, signature-classifier agreement rate)
  - [ ] Drift exporter: Emit structured `DRIFT_DETECTED` events when ADWIN triggers
  - [ ] Prometheus exporter: Instrument custom metrics (latency, alerts, drift states, p95 anomaly scores)
  - [ ] Live hot-reloads: Pull MLflow model versions marked `Production` without API downtime
- [ ] **🌐 Web Track: Live Dashboard**
  - [ ] Add Server-Sent Events (SSE) router: `GET /alerts/stream`
  - [ ] Analyst Dashboard: Live-streaming alert feed with animations, scroll-locks, and connection status
  - [ ] Real-time updates: Update stat counters and charts dynamically on incoming SSE events
  - [ ] Grafana: Stand up Prometheus and Grafana dashboards, embedding panels into the analyst UI
  - [ ] Alerting: Configure Alertmanager rules triggering on drift triggers or performance degradation
  - [ ] SIEM: Configure Wazuh forwarders pushing enriched alert records

---

### Phase 5: Analyst Triage & Active Learning Loop
**Goal:** Close the human-in-the-loop lifecycle. Enable security analysts to review flagged alerts, submit ground-truth corrections, and incrementally update models.
- [ ] **🌐 Web Track: Case Management UI**
  - [ ] Build Case state machine (`New` -> `Under Review` -> `Confirmed Attack` / `False Positive` -> `Closed`)
  - [ ] Triage Dashboard: Prioritize alerts using **uncertainty sampling** (lowest confidence first)
  - [ ] Verification Form: Submit analyst verdict, notes, and metadata
  - [ ] Audit Trail: Track and display historic logs of transitions (who, when, what, why)
  - [ ] MTTR Dashboard: Monitor Mean Time to Respond and Mean Time to Resolve
- [ ] **🔬 ML Track: Active Learning Pipeline**
  - [ ] Verdict Consumer: Read analyst-labelled records from DB
  - [ ] Incremental Trainer: Trigger River Hoeffding Trees or Incremental Random Forests updates in background
  - [ ] Safety Evaluator: Benchmark incremental model against parent before promoting to `Production`
  - [ ] Feedback metric tracking: Monitor the proportion of high-uncertainty predictions over time

---

### Phase 6: Multi-Tenant Isolation + Production Hardening
**Goal:** Deploy the multi-tenant SaaS application on Oracle VPS infrastructure with hardened access control.
- [ ] **🔬 ML Track: Production Hardening**
  - [ ] VPS provisioning: Orchestrate stack on ARM Ampere A1 (ARM64 Docker support)
  - [ ] Reverse Proxy: Configure Caddy/Nginx with TLS termination (Let's Encrypt)
  - [ ] Cron Backup: Schedule `pg_dump` and MLflow artifact replication tasks
- [ ] **🌐 Web Track: Enterprise & Isolation**
  - [ ] Authenticated routing: Integrate JWT authentication and tenant verification
  - [ ] DB Row-Level Security (RLS): Implement `tenant_id` scopes on PostgreSQL tables
  - [ ] Filtered views: Filter dashboards, metrics, Grafana panels, and alerts based on tenant session
  - [ ] Security Headers: Apply strict CORS configurations, CSP rules, and cookie hardening

---

### Phase 7: Research Extensions
**Goal:** Extend system capabilities through specialized network security ML experiments.
- [ ] **7A: Cross-Dataset Generalization Test**
  - [ ] Train on CSE-CIC-IDS2018, align features, and evaluate on UNSW-NB15
- [ ] **7B: Layer-2 Mitigation (Synthetic ARP Poisoning)**
  - [ ] Capture controlled LAN ARP poisoning logs, label flows, and train layer-2 detection features
- [ ] **7C: Autoencoder Anomaly Detector**
  - [ ] Train a 3-layer deep autoencoder on benign flows, compare performance metrics against Isolation Forest
- [ ] **7D: Suricata Signature Tuning Feedback**
  - [ ] Analyze classifier predictions against Suricata rules to suggest tuning and prevent false positives
