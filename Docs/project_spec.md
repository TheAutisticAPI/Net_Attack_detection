# ML-Based Network Intrusion Detection System

## TheAutisticNIDS

---

## Problem Statement

Signature-based network intrusion detection is a solved problem: Snort and Suricata are mature, production-proven, and free. They excel at detecting known attack patterns through rule matching. But the real-world security problem is not whether signatures work, but how to operationalise the data they already produce.

The unsolved problems are one layer above:

1. **Behavioural anomaly detection**: flagging traffic deviations that no static signature captures (unusual flow volumes, timing, protocol patterns, user behaviour shifts).
2. **Alert explainability at scale**: Suricata/Snort generate high-fidelity alerts, but analysts drown in alert volume without clear attribution: *which traffic features made this decision*? Existing tools provide labels but not explanation.
3. **Adaptive detection under concept drift**: production IDS systems degrade as traffic patterns and attacker tactics evolve, but most deployed systems never detect this degradation, let alone respond to it.

This project builds an **ML enrichment layer** that integrates with Suricata/Snort as a complementary downstream consumer. It consumes their structured alert streams (EVE JSON, syslog) and PCAP data, and adds:

1. **Explainability as a first-class output**: every alert (both signature-based and anomaly-based) produces human-readable feature attribution, enabling analysts to act, not just triage.
2. **Concept drift detection**: the system actively monitors classifier degradation due to distribution shift and surfaces that signal to analysts with structured evidence.
3. **Dual-layer triage**: a supervised classifier (learns from known-attack labels) and parallel unsupervised anomaly detector operate together with clearly defined roles, creating a holistic risk assessment.
4. **Tool integration**: designed as a platform layer that reads from existing tools' outputs (Suricata EVE, PCAP stores like Arkime) and writes structured metadata (SHAP explanations, drift signals) back to SIEM/Wazuh for unified orchestration.
5. **Analyst-facing platform**: a production-grade web dashboard with case management, real-time alert streaming, and a human-in-the-loop active learning cycle that continuously improves detection quality.

The system operates in **passive mode only**: consumes PCAP files (batch) or Suricata alerts (streaming). No inline blocking, no packet injection, no firewall rule generation. It is an analyst-assist platform, not a standalone appliance.

---

## What This Is and Is Not

### What This IS

- A **downstream ML enrichment layer** that integrates with Suricata/Snort to extend their capabilities with explainability, anomaly detection, and drift awareness.
- A **two-person team project** with clear ML/DevOps and Web Dev ownership boundaries and parallel execution tracks.
- A **production-deployable platform** on Oracle Cloud VPS with a proper API layer (FastAPI), multi-user dashboard (Next.js), authentication (JWT), and multi-tenant isolation (PostgreSQL RLS).
- A **platform for alert triage and case management** that consumes signature-based alerts and adds statistical and behavioural context, with a human-in-the-loop active learning cycle.
- A **research testbed** for adaptive IDS concepts (concept drift, multimodal detection, explainable security, active learning).
- A **reference implementation** for integrating open-source tools (Suricata, Arkime, Wazuh, MLflow, Grafana) into a cohesive ML-aware pipeline.

### What This Is NOT

- A replacement for Snort/Suricata: signature-based detection remains the foundation.
- A firewall or packet-blocking system.
- A substitute for Arkime or full-packet PCAP search (we integrate with it).
- A commercial SaaS product: multi-tenant isolation is for separated environments/network segments, not public-facing customer onboarding.
- An encrypted-traffic classifier: TLS payload inspection is out of scope; we use observable metadata only.
- A zero-day detection system: the anomaly layer detects statistical outliers, which is distinct from and weaker than detecting novel attack logic.
- Attempting to solve TLS interception, encrypted DNS tunneling detection, or advanced evasion; these are orthogonal problems best solved by complementary tools (threat intelligence feeds, DNS sinkhole integration, etc.).

---

## Exploration Index

Welcome to **TheAutisticNIDS** project documentation. The complete project specification is partitioned into logical components below for simple navigation and maintenance:

### 🗺️ Architecture, Scope, & Technology Stack

[Architecture, Scope, & Technology Stack](architecture_and_stack.md)

Defines how the ML enrichment layer integrates with Suricata, Arkime, and Wazuh. Outlines the passive operational scope, performance constraints (Oracle VPS target, latency budget), legal guidelines, data sources (CSE-CIC-IDS2018), and the complete technical ecosystem (LightGBM, SHAP, FastAPI, Next.js, and PostgreSQL).

### 🚀 Phased Implementation Roadmap

[Phased Implementation Roadmap](phased_deliverables.md)

Contains the highly structured 7-phase delivery roadmap. Each phase operates concurrently across parallel **ML Tracks (🔬)** and **Web Tracks (🌐)** to build and test progressive milestones—from static baseline classifiers and SHAP explanations to live streaming ingestion, active learning loops, and multi-tenant RLS production deployment.

### Project Governance & Evaluation

[Project Governance & Evaluation](governance_and_evaluation.md)

Details the project ownership splits (ML/DevOps vs. Web Developer tracks) and the clear handoff API contract. Lists the exact completion metrics for all phases, validation targets, and the academic references anchoring our literature foundation.

### Original PS

[Original PS](original_ps.md)
