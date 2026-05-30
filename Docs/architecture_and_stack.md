# Architecture, Scope, and Technology Stack

## Scope and Constraints

### Architectural Integration Principles

This system is designed as a **downstream ML enrichment layer**, not a monolithic IDS. It integrates with existing enterprise security tools at well-defined boundaries:

| Integration Point | Role | Tool Examples |
|---|---|---|
| **Alert input** | Consume signature-based alerts with flow context | Suricata EVE JSON, Snort syslog, syslog aggregator |
| **Packet/flow storage** | Read PCAP and flow metadata for offline analysis | Arkime (formerly Moloch), Suricata PCAP store, CICFlowMeter outputs |
| **Feature extraction** | Parallel flow statistics aggregation (not replacement) | nfstream (primary), Suricata flow records, Zeek logs |
| **API layer** | Structured REST + SSE interface for all consumers | FastAPI backend (primary interface for dashboard, SIEM, external tools) |
| **Output/enrichment** | Structured metadata for downstream SIEM/orchestration | Wazuh ingest, Elasticsearch, structured logging |
| **Live inference** | Streaming anomaly scores and drift signals | SSE streams, kafka, Redis pub/sub, syslog, direct API |

The system does **not** replace Snort/Suricata. It deploys them, integrates their core function (signature-based rule matching). Our role is to:

- Reduce analyst toil through explainability on existing alerts
- Detect when the overall detection system is degrading
- Flag novel or anomalous patterns with statistical confidence
- Provide structured, actionable metadata for orchestration and response
- Surface the highest-uncertainty predictions for human review, closing the active learning loop

### Deployment Scope

| Axis | Decision |
|---|---|
| **Deployment mode** | Passive: consumes .pcap files, Suricata EVE JSON, or Arkime exports. Read-only on network data. No inline interception. |
| **Integration mode** | **Batch + Streaming hybrid.** Batch: offline PCAP analysis (testing, tuning, historical re-scoring). Streaming: live Suricata alert subscriptions (EVE to file/syslog/Redis) consumed via FastAPI backend. |
| **Deployment target** | **Oracle Cloud VPS** with ARM Ampere A1 (4 OCPU, 24 GB RAM, 200 GB block storage, 10 TB/month egress). All Docker images must be ARM64-compatible (`linux/arm64`). Development on x86-64 with multi-arch builds. |
| **Network environment** | Single-segment LAN or pre-captured traces; integrates with centralized SIEM (Wazuh, ELK). Multi-tenant alert isolation supported from Phase 6. |
| **Throughput target** | Batch (pcap): no constraint. Streaming (alert enrichment): ≤ 1000 alerts/sec on the Oracle A1 instance. FastAPI SSE endpoint: ≤ 100 concurrent dashboard connections. |
| **Latency budget** | Offline: no constraint. Streaming: ≤ 10 ms per-flow classification (LightGBM inference, excluding I/O). SHAP explanations computed asynchronously post-hoc (not on the alert ingestion path). Drift detection: ≤ 500 ms per drift-trigger evaluation. API response: ≤ 200 ms p95 for `/predict` endpoint. SSE alert delivery: ≤ 1s from ingestion to dashboard render. |
| **Legal/ethical** | Only traffic on networks you own or have **written authorisation** to monitor. All `.pcap` files must be self-generated in a controlled lab environment, or sourced from publicly licensed research datasets. No raw payload logging. Only IP:port tuples, flow-level statistics, and labels are stored. |

---

## Dataset and Data Sources

### Primary Training: CSE-CIC-IDS2018

Chosen over alternatives for the following explicit reasons:

| Dataset | Verdict | Reason |
|---|---|---|
| NSL-KDD (1999) | ❌ Retired | 1998 traffic. Obsolete protocols. No longer an acceptable benchmark. |
| CICIDS2017 | ⚠️ Supplementary only | Missing several attack classes present in 2018. Acceptable as a secondary validation set. |
| **CSE-CIC-IDS2018** | ✅ Primary | ~16.2 million rows before deduplication and cleaning, 10 days of capture, modern protocols, 14 labelled attack types. AWS-hosted topology with dedicated attacker VMs. Currently the most widely used large-scale IDS benchmark. |
| UNSW-NB15 (2015) | ✅ Cross-validation target | 49 features from Argus/Zeek. Different feature extraction methodology. Use as a cross-dataset generalisation test in later phases, not as primary training data. |

**Attack classes present in CSE-CIC-IDS2018 (and usable in this project):**
Benign · FTP-BruteForce · SSH-BruteForce · DoS-GoldenEye · DoS-Hulk · DoS-SlowHTTPTest · DoS-Slowloris · DDoS-LOIC-HTTP · DDoS-LOIC-UDP · Botnet-ARES · WebAttack-BruteForce · WebAttack-XSS · WebAttack-SQLInjection · Infiltration

**Not present and therefore out of scope:** MitM, ARP Poisoning, DNS Spoofing. These require a separate synthetic lab capture (see Phase 7 extension).

**Class imbalance:** Benign traffic accounts for ~77–83% of flows depending on extraction method. Some attack classes (WebAttack-XSS, WebAttack-SQLInjection) represent <0.001% of total instances. Ignoring this will produce a model that predicts benign for nearly everything and still reports >95% accuracy. This is a well-documented failure mode in IDS literature.

Mandatory mitigations:

- Stratified train/test/validation splits (never shuffle-split on imbalanced data)
- Class-weighted loss in gradient boosted tree training
- For extreme minority classes: SMOTE or class-weight escalation
- **Primary scalar metric: macro-averaged F1**. Accuracy is not used as the primary evaluation metric due to class imbalance

### Streaming Production Data: Suricata EVE Integration

Once deployed in production, the system can ingest live Suricata EVE JSON alerts (via file tail, syslog, or Redis) to:

- Build adaptive benign baseline statistics from live traffic patterns
- Validate that the Phase 1 classifier generalises to production traffic
- Feed ground-truth labels (analyst-reviewed verdicts from the case management UI) into the active learning loop (Phase 5)

**Key advantage:** Suricata EVE provides structured flow context (source/destination IPs, ports, protocols, action, signature metadata) for every alert, enabling quick triage without packet re-processing.

**Note on offline-to-production transition:** Phase 1–3 focus on CSE-CIC-IDS2018. Phase 4 and beyond integrate live Suricata data. The feature schema must be validated for compatibility before production deployment.

---

## Technology Stack

### Ecosystem and Tools Integration

| Component | Tool | Role | Integration Method |
|---|---|---|---|
| **Signature-based detection** | **Suricata** (primary), Snort (supported) | Core threat detection engine. Produces rule-based alerts at network and application layers. | Subscribe to EVE JSON output (file, syslog, or Redis). Replay PCAP from Suricata's store. |
| **PCAP storage & search** | **Arkime** (formerly Moloch) | Centralized PCAP indexing and full-packet investigation tool. Integrates with Suricata and other NIDS. | Query Arkime API for historical PCAP and flow metadata. Export PCAP subsets for offline analysis. |
| **SIEM & host detection** | **Wazuh** (primary) | Centralises logs, alerts, and incident response. Receives Suricata alerts, enriches with endpoint telemetry. | Send enriched flow classifications and drift signals as JSON to Wazuh API or syslog. |
| **Flow extraction (optional offline pipeline)** | **nfstream** (primary) | Fast, Python-native flow aggregation from PCAP. Used in offline batch mode for feature engineering and validation. Validates Suricata flow extraction. | Run on historical PCAP in parallel with Suricata output for cross-validation and feature development. |

### ML/Analytics Stack

| Layer | Tool | Why |
|---|---|---|
| **Supervised classifier** | **LightGBM** (primary), XGBoost (baseline comparison) | LightGBM matches XGBoost accuracy on tabular security data while training faster and using less memory, making it better suited for iterative experimentation and eventual live inference. Both are appropriate; train both, compare, justify the final choice. |
| **Anomaly detector** | **Isolation Forest** (Phase 2) → **shallow Autoencoder** (Phase 7D, optional) | Start with Isolation Forest: fast, low-memory, minimal hyperparameters, interpretable anomaly score threshold. Add an Autoencoder only in Phase 7D if IF false-positive rate is unacceptable at the target threshold. These are not equivalent alternatives. They have different inductive biases and failure modes. |
| **Explainability** | **SHAP** (TreeExplainer for LightGBM/XGBoost) | TreeExplainer computes Shapley values efficiently for tree ensembles (exact for individual trees, polynomial-time path-dependent estimation for ensembles), making it fast enough for post-hoc per-alert explanations. LIME is model-agnostic and slower; use it only as a comparison in the evaluation phase to validate SHAP stability (the IEEE Access 2024 benchmark evaluated both across six metrics, including stability and robustness, where SHAP outperformed on most). |
| **Concept drift detection** | **River** (`drift` module: ADWIN, Page-Hinkley) | River is the consolidated successor to scikit-multiflow and creme, actively maintained (2026). Use ADWIN on the rolling F1 score stream to detect when the classifier is degrading. This is not a model update mechanism; it is a detection trigger. |

### Application & Infrastructure Stack

| Layer | Tool | Why |
|---|---|---|
| **API backend** | **FastAPI** (Gunicorn + Uvicorn workers) | Async Python backend serving ML inference endpoints, alert enrichment, case management CRUD, and SSE streams. Pydantic validation on all request/response models. OpenAPI docs auto-generated. In production, run behind Gunicorn with Uvicorn workers for multi-process fault isolation. |
| **Analyst dashboard** | **Next.js 15+** (App Router, TypeScript) | Multi-user, production-grade analyst dashboard. React Server Components for initial data load; client components with SSE for real-time alert feed. **Recharts** for visualization (React-native, declarative API). Migrate to Apache ECharts if performance requires it for views exceeding 10k data points. |
| **Database** | **PostgreSQL** | Used from Phase 1 onward. Stores alerts, predictions, SHAP explanations, drift events, case management state, analyst verdicts, and model metadata. PostgreSQL provides MVCC concurrency for multi-process writes (API + EVE subscriber + dashboard), `LISTEN/NOTIFY` for real-time event push, and Row-Level Security (RLS) for multi-tenant isolation in Phase 6. |
| **MLOps / Model Registry** | **MLflow** (self-hosted) | PostgreSQL metadata backend + local artifact store on VPS. Model lifecycle stages: `None` → `Staging` → `Production` → `Archived`. Experiment tracking for all training runs (Phase 1–3). Enables reproducible model comparison and rollback. The MLflow tracking server is itself a lightweight FastAPI service. |
| **Prototyping dashboard** | **Streamlit** | Used in Phase 1–3 **only** as a local prototyping tool for the ML developer. Quick visualisation of training results, feature distributions, and model comparisons during development. Not deployed to production; it is replaced by the Next.js dashboard from Phase 4B onward. |
| **Monitoring & observability** | **Prometheus + Grafana** | Industry-standard open source observability stack. Expose detection metrics (flow classification rate, alert rate, anomaly score distribution, drift detector state) as Prometheus metrics; visualise in Grafana with Alertmanager for threshold-based notifications. Grafana panels embedded in the Next.js dashboard where needed; extend with custom Recharts components as requirements emerge. |
| **Alerting/logging** | **PostgreSQL** + console/syslog | Append-only detection log with structured schema in PostgreSQL. Infrastructure alerting via Grafana Alertmanager. SIEM forwarding via Wazuh API/syslog. |
| **Containerisation** | **Docker Compose** | One `docker-compose.yml` that brings up the full stack. Multi-stage builds with ARM64-compatible base images for Oracle A1 deployment. Development uses the same Compose file with override profiles. |
