# Phased Implementation Roadmap

Each phase is a working, testable system. Phase N does not need Phase N+1 to be functional. Build forward, not backward.

**Each phase has two parallel tracks:**
- **ML Track (🔬)**: model development, feature engineering, pipeline work
- **Web Track (🌐)**: API, database, dashboard, frontend

The tracks run concurrently. Dependencies between tracks are called out explicitly.

---

### Phase 1: Baseline Pipeline + Platform Foundation

**Goal:** ML track gets a working classifier on CSE-CIC-IDS2018. Web track builds the API skeleton, database schema, and project scaffolding so both tracks converge cleanly at integration.

#### 🔬 ML Track: Baseline Classifier

- Data loading and cleaning script for CSE-CIC-IDS2018 CSVs (handle known artefacts: infinite values, NaN rows, duplicate flows from multi-day merges). Deduplication strategy: deduplicate by flow 5-tuple + timestamp window to prevent the same flow appearing in both train and test splits.
- Feature selection: use Random Forest permutation importance to identify the top 30–40 features from the 80-feature space; document which features were dropped and why.
- **Feature engineering**: apply log-transforms to heavily skewed features (e.g., flow byte counts, packet counts). Evaluate derived features (inter-arrival time statistics, flow duration ratios) if they improve discriminative power. Document all transformations applied.
- **Feature schema validation**: document which features are extractable from Suricata EVE JSON output (or derivable from EVE + PCAP) for eventual production use. Flag any features that are only available in the CIC dataset (e.g., synthetic attack labels) vs. observable in live traffic.
- LightGBM multiclass classifier trained with stratified k-fold cross-validation (k=5) and class-weighted loss.
- XGBoost baseline trained under identical conditions.
- Evaluation report: per-class precision/recall/F1, macro-F1, confusion matrix, ROC-AUC curves (one-vs-rest), inference latency per 1000 flows.
- **MLflow experiment tracking**: all training runs logged with hyperparameters, metrics, and model artifacts. Best model registered in the Model Registry as `Staging`.
- **Minimum bar:** Macro-F1 ≥ 0.85 on held-out test split. No single attack class F1 < 0.70.

#### 🌐 Web Track: Platform Scaffolding

- **PostgreSQL schema design**: tables for `flows`, `predictions`, `alerts`, `shap_explanations`, `model_versions`. Schema must accommodate Phase 2 (anomaly scores), Phase 3 (SHAP), and Phase 5 (case management) without breaking migrations.
- **FastAPI project skeleton**: project structure, Pydantic models for request/response validation, health check endpoint (`/health`), OpenAPI docs. Use SQLAlchemy + Alembic for database migrations.
- **Core API endpoints (serving static/batch results)**:
  - `POST /predict`: accept a flow feature vector, return classifier label + confidence (initially returns mock responses until ML track delivers the model)
  - `GET /alerts`: paginated alert list with filtering (by class, confidence threshold, time range)
  - `GET /alerts/{id}`: single alert detail
  - `GET /models`: list registered MLflow model versions and their stages
- **Next.js project initialisation**: App Router, TypeScript, Recharts installed. Basic layout shell with navigation (Alerts, Dashboard, Models). Dark mode default. No real data is present yet; the dashboard uses seeded mock data from the CSE-CIC-IDS2018 schema.
- **Docker Compose (dev profile)**: PostgreSQL + FastAPI + Next.js + MLflow tracking server. One `docker-compose up` to start the full dev environment.

**Handoff:** ML track delivers a trained LightGBM model artifact via MLflow. Web track loads it from the registry for live inference in the `/predict` endpoint.

**Out of scope this phase:** live traffic, Suricata integration, anomaly detection, SHAP, drift detection.

---

### Phase 2: Anomaly Detection + Dashboard Foundation

**Goal:** ML track adds the anomaly detection layer. Web track builds the dashboard foundation with real data from Phase 1 and visualisation components.

#### 🔬 ML Track: Anomaly Detection Layer

- Isolation Forest trained **exclusively on benign flows** from the training split (no attack labels used — this is the point).
- Anomaly score decision threshold calibrated on a held-out benign validation set to achieve **FPR ≤ 5%** at the operating point; document this threshold explicitly (note: this is distinct from Isolation Forest's `contamination` parameter, which controls the expected outlier proportion in training data and should be set near 0 for benign-only training).
- Parallel inference: every flow receives both a classifier label and an anomaly score.
- Precision-recall curve for the anomaly detector at multiple decision thresholds.
- Written analysis: what does the anomaly detector catch that the classifier misses? What does it false-positive on? This is more valuable than just the metrics.
- **MLflow**: Isolation Forest model registered alongside the classifier. Both models loadable from a single MLflow registry query.

**Do not describe Isolation Forest as "zero-day detection."** It is a statistical outlier detector. It flags unusual flows relative to what benign traffic looks like. It will also flag unusual-but-legitimate traffic (e.g., a backup job running at 3am). This is a triage layer, not a ground truth.

#### 🌐 Web Track: Dashboard Foundation

- **API endpoints for anomaly data**:
  - `POST /predict` updated to return classifier label, confidence, and anomaly score (dual-layer response)
  - `GET /alerts` updated to be filterable by anomaly flag and sortable by anomaly score
- **Dashboard views (Next.js)**:
  - **Alert list view**: paginated, sortable table of classified flows. Columns: timestamp, source IP:port, dest IP:port, classifier label, confidence, anomaly score, anomaly flag. Colour-coded severity.
  - **Alert detail view**: expanded single-alert page (contains a placeholder for the SHAP waterfall, to be populated in Phase 3).
  - **Overview dashboard**: attack class distribution (pie/bar chart), alert volume time series (line chart), anomaly score distribution (histogram). All built with Recharts.
- **Component library**: reusable chart wrappers, data table, status badges, loading skeletons. These components will be reused across all subsequent phases.

**Handoff:** ML track delivers the Isolation Forest model and anomaly scoring function. Web track integrates it into the `/predict` response and renders anomaly scores in the dashboard.

---

### Phase 3: Explainability + Alert Visualisation

**Goal:** ML track integrates SHAP explainability. Web track builds the SHAP visualisation components and completes the alert investigation experience.

#### 🔬 ML Track: Explainability Module

- SHAP TreeExplainer integrated for per-alert explanation generation (top-5 feature contributions with direction and magnitude).
- SHAP summary plot (beeswarm) over the full test set for global model validation, showing which features matter most and in what direction for each attack class.
- SHAP explanations stored in PostgreSQL alongside each alert (asynchronous, so they are never on the detection hot path).
- **API schema for SHAP output**: define the JSON structure for per-alert SHAP values (feature name, SHAP value, base value, direction) so the web track can render it.
- Written validation: do the SHAP top features match domain knowledge? For example, DoS attacks should rank high on flow rate, packet size variance, and SYN flag counts. If they don't, investigate whether there is data leakage (e.g., IP/port columns left in the feature set), which is a common pitfall in published IDS work.
- Optional comparison: run LIME on 100 randomly sampled flagged alerts and compare feature attribution stability against SHAP (quantitative, not just visual).

#### 🌐 Web Track: Explainability Visualisation

- **API endpoints for SHAP data**:
  - `GET /alerts/{id}/explanation`: returns SHAP values for a specific alert
  - `GET /models/{id}/global-importance`: returns global SHAP summary data (for beeswarm/bar charts)
- **Dashboard views (Next.js)**:
  - **SHAP waterfall chart** on alert detail page: horizontal bar chart showing top-5 feature contributions with direction (pushing toward attack vs. pushing toward benign). Built with Recharts.
  - **Global feature importance view**: beeswarm-style or bar chart showing aggregate SHAP values per feature across the test set, filterable by attack class.
  - **Model comparison view**: side-by-side LightGBM vs. XGBoost metrics pulled from MLflow API (macro-F1, per-class F1, training time, inference latency).
  - **End-to-end alert investigation flow**: analyst clicks alert → sees classification + anomaly score + SHAP explanation + raw flow metadata on a single page. This is the core analyst experience.

**Handoff:** ML track defines the SHAP JSON schema and writes explanations to PostgreSQL. Web track reads them via the API and renders visual explanations.

---

### Phase 4: Live Ingestion + Concept Drift Detection

**Goal:** Connect the system to live Suricata infrastructure. Both tracks converge on the real-time pipeline.

#### 🔬 ML Track (4A): Live Pipeline + Drift Detection

- **Suricata EVE subscriber**: read alert and flow events from Suricata's EVE output (file tail, syslog, or Redis) and map them to the Phase 1 feature schema in real-time.
- **Optional parallel flow extraction**: nfstream live capture (for environments where Suricata is not yet deployed, or to cross-validate Suricata's flow stats).
- **River ADWIN drift detector** applied to the rolling per-class F1 stream: when ADWIN signals drift, log a structured `DRIFT_DETECTED` event with timestamp, affected class, and the metric trajectory that triggered it.
- **Ground-truth labelling strategy for production drift detection**: in production, ground-truth labels are not freely available. ADWIN monitors model–Suricata agreement rate (classifier prediction vs. Suricata signature verdict) as a proxy metric. When agreement degrades, ADWIN fires. This measures *model consistency with the signature engine*, not true detection quality, which is an important distinction that must be documented. True F1 monitoring requires a manually labelled holdout window, which is feasible only during periodic analyst review cycles.
- **Prometheus exporter** exposing: `ids_flows_classified_total`, `ids_alerts_total`, `ids_anomaly_score_p95`, `ids_drift_events_total`, `ids_inference_latency_ms`.
- **MLflow model promotion**: move the best-performing model from `Staging` to `Production`. FastAPI loads the `Production` model from MLflow on startup and supports hot-reload on model version change.

#### 🌐 Web Track (4B): Real-Time Dashboard + Monitoring

- **SSE streaming endpoint** (`GET /alerts/stream`): Server-Sent Events stream that pushes new alerts to connected dashboard clients as they are classified. SSE chosen over WebSocket because alert flow is unidirectional (server → client) and SSE provides automatic reconnection, works through standard HTTP infrastructure, and is simpler to secure.
- **Real-time alert feed in Next.js**: live-updating alert list driven by SSE. New alerts animate in at the top. Auto-scroll with manual override. Connection status indicator.
- **Dashboard updates**:
  - Attack rate time series (live-updating, rolling window)
  - Anomaly score distribution (live histogram)
  - Drift detector state indicator (green/yellow/red based on ADWIN state)
  - Source/destination IP, timestamp, rule name, classifier confidence, top-3 SHAP features per alert
- **Grafana integration**: embed Grafana panels (infrastructure metrics: CPU, memory, ingestion rate, inference latency) into the Next.js dashboard via iframe or API-driven rendering. Grafana remains the source of truth for Prometheus metrics.
- **Grafana dashboard** (import via JSON) with Alertmanager rule: fire alert if `ids_drift_events_total` exceeds threshold or per-class F1 drops more than X% in a 5-minute window.
- **Wazuh/SIEM integration**: send enriched alert metadata (model confidence, anomaly score, drift signal) to Wazuh API or syslog for centralised log aggregation and incident response orchestration.
- **Docker Compose (production profile)**: EVE subscriber + FastAPI + Next.js + PostgreSQL + Prometheus + Grafana + MLflow. One command to bring up the full system (assumes Suricata and Wazuh are pre-deployed).

**On concept drift:** detecting drift is Phase 4. *Responding to drift* (retraining, active learning, model versioning) is Phase 5. Do not conflate them. A system that detects it has degraded and surfaces that clearly to an analyst is already more honest and useful than 95% of published academic IDS systems.

---

### Phase 5: Analyst Triage & Active Learning Loop

**Goal:** Close the human-in-the-loop feedback cycle. Analyst verdicts improve detection quality over time.

This phase is architecturally significant because it transforms the system from a static classifier into an adaptive one. The web developer builds the triage workflow; the ML engineer wires analyst verdicts into incremental model updates.

#### 🌐 Web Track: Case Management UI

- **Case lifecycle workflow**: every flagged alert (classifier or anomaly) can be promoted to a case. Cases move through a defined state machine:
  - `New` → `Under Review` → `Confirmed Attack` | `False Positive` | `Escalated` → `Closed`
- **Triage interface**: priority-sorted alert queue. Sorting strategy is **uncertainty sampling**, where alerts with the lowest classifier confidence are surfaced first because they are the most informative for active learning and the most likely to need human judgement.
- **Verdict submission**: analyst marks each case with a ground-truth label (attack class or false positive), optional free-text notes, and timestamp. Stored in PostgreSQL with analyst ID.
- **Audit trail**: immutable log of all verdict decisions. Every state transition recorded with who, when, and why. Compliance-ready for SOC 2 / internal audit requirements.
- **MTTR tracking**: Mean Time to Respond (New → first analyst action) and Mean Time to Resolve (New → Closed) computed and displayed on the dashboard.

#### 🔬 ML Track: Active Learning Pipeline

- **Verdict ingestion**: consume analyst verdicts from PostgreSQL as labelled training samples.
- **Incremental model update**: when a sufficient window of analyst-labelled flows accumulates (configurable threshold, e.g., 100 new labels), trigger an incremental update using River's Hoeffding Tree or incremental Random Forest. This runs *alongside* the primary LightGBM model, not as a replacement.
- **Model comparison**: compare the incrementally-updated model against the static Phase 1 model on the same holdout set. Track both in MLflow. Only promote to `Production` if the updated model improves or maintains macro-F1.
- **Uncertainty sampling feedback**: the active learning loop should reduce the number of uncertain predictions over time as more analyst verdicts are collected. Track and report this metric (% of predictions above/below confidence threshold over time).
- **Drift response**: when ADWIN fires (Phase 4), automatically increase the priority of uncertain alerts in the triage queue to accelerate analyst labelling in the drifted region.

---

### Phase 6: Multi-Tenant Isolation + Production Hardening

**Goal:** Deploy the system on Oracle VPS with multi-tenant support and production-grade security.

#### 🔬 ML Track: Infrastructure & Deployment

- **Oracle VPS deployment**: full Docker Compose stack running on ARM Ampere A1 (4 OCPU, 24 GB RAM). Multi-stage Docker builds with `linux/arm64` base images. Validate all dependencies compile on ARM64.
- **Reverse proxy and TLS**: deployment method kept open (Nginx, Traefik, or Caddy, to be chosen based on operational complexity preference at deployment time). TLS termination with Let's Encrypt or equivalent. All internal services communicate over Docker's bridge network; only the reverse proxy is exposed.
- **Backup and recovery**: PostgreSQL pg_dump scheduled backup. MLflow artifact store backup. Docker volume backup strategy documented.
- **Resource monitoring**: cAdvisor or Prometheus node exporter for container-level CPU/memory/disk metrics on the VPS.

#### 🌐 Web Track: Multi-Tenant & Auth

- **JWT authentication**: all API endpoints require a valid JWT. Token includes tenant ID claim. Issued by a lightweight auth service or external IdP (e.g., Keycloak, or simple JWT issuer for prototype).
- **PostgreSQL Row-Level Security (RLS)**: tenant isolation at the database level. Every row in the `alerts`, `predictions`, `cases`, and `verdicts` tables carries a `tenant_id`. RLS policies enforce that queries only return rows matching the authenticated tenant's ID. This is the strongest isolation model short of separate databases.
- **Per-tenant dashboard views**: Next.js dashboard scoped by tenant. Alert lists, case management, SHAP views, and drift indicators all filtered by the authenticated tenant.
- **Per-tenant Grafana**: Grafana organisation-level isolation. Each tenant gets a separate Grafana org with its own dashboards and data source filters.
- **Rate limiting and CORS**: FastAPI middleware for per-tenant rate limiting. Strict CORS policy allowing only the deployed frontend origin.
- **Security hardening checklist**: `httpOnly` session cookies, CSP headers, input sanitisation, no secrets in frontend code, dependency audit against CVE databases.

---

### Phase 7: Research Extensions (Scope Permitting)

These are independent, additive extensions. Pick based on interest and deployment context.

**7A: Cross-Dataset Generalisation Test**

Train exclusively on CSE-CIC-IDS2018. Evaluate cross-dataset transfer on UNSW-NB15 (after feature alignment with Suricata EVE fields). Report macro-F1 drop. Investigate which attack classes transfer and which collapse, which represents a publishable finding if the analysis is rigorous.

**7B: Synthetic ARP Poisoning Data**

Generate a controlled ARP poisoning trace: Kali Linux VM + Ettercap targeting a victim VM on an isolated virtual LAN. Extract flows with nfstream or Suricata EVE. Label manually. Add as a new class to the classifier. Evaluate whether the existing feature space is discriminative enough to separate ARP poisoning from other attacks, or whether new features (ARP-specific: request/reply ratio, MAC-IP binding changes) are required. This is an honest answer to the question of signature-less layer 2 attacks.

**7C: Autoencoder Anomaly Detector (Parallel Experiment)**

Train a shallow 3-layer autoencoder (encoder: N→32→16, decoder: 16→32→N, where N = number of selected features from Phase 1) on benign flows. **Prerequisite**: apply min-max or standard normalisation to the feature space before training; unlike tree-based models, autoencoders are not scale-invariant. Reconstruct test flows; flag those exceeding a reconstruction error threshold calibrated to the same FPR ≤ 5% target as Phase 2. Compare: does the autoencoder detect more attack types with fewer false positives than Isolation Forest? Under what conditions does each outperform? Use UNSW-NB15 as a blind test set to assess cross-dataset robustness. This is a **parallel experiment**, not a replacement of the Phase 2/4 production pipeline, and both detectors should be evaluable independently.

**7D: Suricata Rule Tuning via ML Feedback**

Analyse which Suricata rules generate false positives or false negatives relative to ground truth in the training dataset. Use model feature importance and alert correlation to recommend rule thresholds or priorities. Could manifest as a Suricata dashboard showing per-rule precision/recall in the production environment (requires ground-truth tagging, so may be limited to research phase). This is not a rule generation system, but rather serves as informed feedback for human SOC tuning.
