# ML Evaluation Report — Phase 1

> **Status**: Placeholder — to be populated after training on CSE-CIC-IDS2018 dataset.

## Target Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Macro-F1 (held-out test) | ≥ 0.85 | — |
| Min per-class F1 | ≥ 0.70 | — |
| Anomaly FPR (Phase 2) | ≤ 5% | — |
| Inference latency (/1k flows) | ≤ 10ms | — |

## Per-Class Classification Report

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------| 
| Benign | — | — | — | — |
| FTP-BruteForce | — | — | — | — |
| SSH-BruteForce | — | — | — | — |
| DoS-GoldenEye | — | — | — | — |
| DoS-Hulk | — | — | — | — |
| DoS-SlowHTTPTest | — | — | — | — |
| DoS-Slowloris | — | — | — | — |
| DDoS-LOIC-HTTP | — | — | — | — |
| DDoS-LOIC-UDP | — | — | — | — |
| Botnet-ARES | — | — | — | — |
| WebAttack-BruteForce | — | — | — | — |
| WebAttack-XSS | — | — | — | — |
| WebAttack-SQLInjection | — | — | — | — |
| Infiltration | — | — | — | — |

## Confusion Matrix

*To be generated after training.*

## ROC-AUC Curves (One-vs-Rest)

*To be generated after training.*

## Feature Schema Validation

| Feature Source | Count | Notes |
|----------------|-------|-------|
| Suricata EVE (available in production) | — | — |
| PCAP-derived (requires nfstream) | — | — |
| Dataset-only (not in production) | — | — |

## Class Imbalance Strategy

- Stratified train/val/test splits (70/15/15)
- Class-weighted loss (`is_unbalance: true` for LightGBM)
- SMOTE / class-weight escalation for extreme minority classes (WebAttack-XSS, SQLInjection)
- Primary metric: macro-averaged F1 (not accuracy)

## Model Comparison: LightGBM vs XGBoost

| Metric | LightGBM | XGBoost |
|--------|----------|---------|
| Macro-F1 | — | — |
| Training time | — | — |
| Inference latency | — | — |
| Model size | — | — |

## Known Limitations & Failure Modes

*To be documented after evaluation:*
1. What does the classifier miss?
2. Which attack classes are hardest to distinguish?
3. Is there any evidence of data leakage?
4. Feature importance sanity check (do top features match domain knowledge?)
