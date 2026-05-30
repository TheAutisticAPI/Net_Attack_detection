# Project Governance, Evaluation, and References

## Team Composition & Ownership

This is a project with clear responsibilities and parallel execution.

| Role | Scope |
|---|---|
| **ML / DevOps Engineer** | Model training, feature engineering, drift detection, MLOps pipeline (MLflow), containerisation, Oracle VPS deployment, Suricata/Wazuh integration, Prometheus metrics |
| **Web Developer** | FastAPI backend API, Next.js dashboard, case management UI, real-time alert streaming (SSE), frontend observability, Grafana integration |

**Parallel execution model:** Each phase has an **ML track** and a **Web track** that run concurrently. The Web track builds the API layer, database schema, and frontend foundation *while* the ML track develops the models and pipeline. They converge at Phase 4 integration points and are fully interdependent from Phase 5 onward.

**Handoff contract:** The ML track produces Python modules with defined interfaces (predict functions, SHAP output schemas, drift event structures). The Web track consumes these via FastAPI service endpoints. The contract is the API schema; both sides develop against it from Phase 1.

---

## Evaluation Criteria

The project is complete and successful when:

1. **Phase 1 (ML):** Classifier achieves macro-F1 ≥ 0.85 on the CSE-CIC-IDS2018 held-out test set, with no single attack class F1 < 0.70. Feature schema is documented for Suricata EVE compatibility. All training runs tracked in MLflow.
2. **Phase 1 (Web):** FastAPI serves `/predict`, `/alerts`, `/health` endpoints with Pydantic-validated responses. PostgreSQL schema supports all planned phases. Docker Compose starts the full dev stack in one command.
3. **Phase 2 (ML):** Anomaly detector's FPR on a clean benign validation set is ≤ 5% at the calibrated operating threshold.
4. **Phase 2 (Web):** Dashboard renders alert list with anomaly scores. Overview charts display attack distribution and anomaly score histogram with real Phase 1–2 data.
5. **Phase 3 (ML):** SHAP attributions are stored for 100% of flagged alerts; global SHAP summary plots are validated against domain expectations (documented in writing).
6. **Phase 3 (Web):** SHAP waterfall chart renders on every alert detail page. Global feature importance view works. End-to-end alert investigation flow (list → detail → explanation) is usable.
7. **Phase 4:** Live pipeline sustains ≤ 1000 alerts/sec and correctly enriches Suricata EVE alerts with classifier confidence and anomaly scores without data loss. SSE endpoint delivers alerts to connected dashboard clients within 1s of ingestion. ADWIN correctly fires a `DRIFT_DETECTED` event when artificially injected distribution shift is applied to the input stream (documented test case). Wazuh integration endpoint works (alerts are successfully forwarded with metadata). Grafana dashboard displays live Prometheus metrics.
8. **Phase 5:** Case lifecycle works end-to-end (New → Under Review → Confirmed/FP → Closed). Analyst verdicts successfully feed incremental model updates. MTTR is tracked and displayed. Uncertainty sampling surfaces low-confidence alerts first.
9. **Phase 6:** Multi-tenant isolation verified (tenant A cannot see tenant B's alerts via API or dashboard). JWT auth enforced on all API endpoints. System deploys and runs on Oracle VPS ARM64 instance via Docker Compose.
10. **Phase 6 (Deployment):** Docker Compose brings up the complete production stack (FastAPI, Next.js, PostgreSQL, EVE subscriber, Prometheus, Grafana, and MLflow) on the Oracle VPS in a single command.
11. A written evaluation section addresses: imbalance strategy and its measured effect on per-class metrics; false positive budget and how the FPR threshold was chosen; integration gaps (which features from Phase 1 are missing from Suricata EVE?); one documented failure mode per detection layer (what does the classifier miss? what does the anomaly detector false-positive on? when does SHAP produce unstable attributions?).

---

## Reference Anchors

For literature grounding and comparison baselines:

- **Dataset paper (CIC-IDS2018):** Sharafaldin et al., *Toward Generating a New Intrusion Detection Dataset*, ICISSP 2018
- **Dataset paper (UNSW-NB15):** Moustafa & Slay, *UNSW-NB15: A Comprehensive Data Set for Network Intrusion Detection Systems*, MilCIS 2015
- **CICFlowMeter critique and nfstream:** Documented in Luxemburk et al. 2021 (NetFlow vs CICFlowMeter comparison), where nfstream addresses CICFlowMeter's known TCP flow construction and attribute extraction errors
- **LightGBM:** Ke et al., *LightGBM: A Highly Efficient Gradient Boosting Decision Tree*, NeurIPS 2017
- **Isolation Forest:** Liu et al., *Isolation Forest*, ICDM 2008
- **SHAP:** Lundberg & Lee, *A Unified Approach to Interpreting Model Predictions*, NeurIPS 2017
- **SHAP vs LIME in IDS:** IEEE Access 2024 benchmark (six evaluation metrics including stability, robustness, completeness across three IDS datasets and seven models); SHAP outperformed LIME on stability and global coherence, though LIME remains useful for local sanity checks
- **Concept drift in IDS:** ICISSP 2026 (Rehman et al.), which focuses on incremental federated learning under an evolving threat landscape and demonstrates ADWIN and Page-Hinkley as practical drift detectors for IDS contexts. *Note: verify publication status; if in-press or preprint, cite accordingly.*
- **River library:** Montiel et al., *River: Machine Learning for Streaming Data in Python*, JMLR 2021, which is the consolidated successor to creme and scikit-multiflow and is still actively maintained as of 2026
- **FastAPI:** Ramírez, *FastAPI framework*, 2018+, an async Python web framework with native Pydantic validation, automatic OpenAPI documentation, and ASGI support
- **MLflow:** Zaharia et al., *Accelerating the Machine Learning Lifecycle with MLflow*, IEEE Data Eng. Bull. 2018, an open-source platform for experiment tracking, model registry, and deployment
