## Project 8: Network Traffic Mining & Anomaly-Based Attack Detection

### Problem Statement

Cyberattacks like Denial of Service (DoS), Man-in-the-Middle (MitM), IP Spoofing, and ARP Poisoning are among the most damaging and frequently occurring threats on modern networks — yet most small and mid-scale organisations lack intelligent intrusion detection beyond basic firewalls. Traditional signature-based systems miss novel or mutated attack patterns entirely.

This project involves building an **AI-powered network intrusion detection system** that mines live or captured network traffic, extracts behavioural features, and uses machine learning to detect known and unknown attack patterns in real time — classifying the attack type and triggering immediate alerts.

### Tech Stack Keywords

**Python** · **Scapy / PyShark** · **Scikit-learn / XGBoost** (classification) · **Isolation Forest / Autoencoder** (anomaly detection) · **NSL-KDD / CICIDS2017 Dataset** · **Feature Engineering** (flow-level features) · **SHAP** (explainability) · **FastAPI** · **Streamlit** · **Docker**

### Deliverables

* **Traffic Feature Engineering Pipeline** A module that processes raw packet captures and extracts flow-level features (packet inter-arrival time, flow duration, byte ratios, flag counts, connection state) matching the feature space used in benchmark intrusion detection datasets.

* **Attack Classification Model** A supervised ML model (XGBoost / Random Forest) trained on NSL-KDD or CICIDS2017 to classify traffic flows into categories: *normal, DoS, MitM, spoofing, port scan, and brute force* — complete with per-class confidence scores.

* **Zero-Day Anomaly Detection Layer** An unsupervised model (Isolation Forest or Autoencoder) running in parallel to flag statistically anomalous traffic patterns that do not match any known attack signature, effectively catching novel threats the classifier hasn't seen.

* **Explainability Module** SHAP-based feature importance outputs that explain *why* a particular flow was flagged as an attack — highlighting which features (e.g., abnormally high SYN count, spoofed TTL values) contributed most to the model's decision.

* **Real-Time Detection Interface** A live traffic ingestion dashboard displaying per-flow classification results in real time, showing attack type, confidence metrics, source/destination IPs, and flagged feature anomalies.

* **Incident Log & Alert System** A structured log of all detected attacks capturing timestamps, attack type, severity score, and affected IPs — equipped with configurable alerts (dashboard notifications/emails) for high-severity detections.
