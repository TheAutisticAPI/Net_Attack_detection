"use client";

interface MockModel {
  id: string;
  name: string;
  version: string;
  stage: "Production" | "Staging" | "Archived" | "None";
  framework: string;
  macroF1: number;
  perClassF1: Record<string, number>;
  trainTime: string;
  inferenceLatency: string;
  createdAt: string;
}

const MOCK_MODELS: MockModel[] = [
  {
    id: "model-001",
    name: "nids-lightgbm",
    version: "1",
    stage: "Staging",
    framework: "LightGBM 4.5.0",
    macroF1: 0.892,
    perClassF1: {
      Benign: 0.98,
      "FTP-BruteForce": 0.95,
      "SSH-BruteForce": 0.93,
      "DoS-GoldenEye": 0.91,
      "DoS-Hulk": 0.96,
      "DoS-SlowHTTPTest": 0.88,
      "DoS-Slowloris": 0.87,
      "DDoS-LOIC-HTTP": 0.94,
      "DDoS-LOIC-UDP": 0.93,
      "Botnet-ARES": 0.85,
      "WebAttack-BruteForce": 0.82,
      "WebAttack-XSS": 0.74,
      "WebAttack-SQLInjection": 0.71,
      Infiltration: 0.76,
    },
    trainTime: "4m 32s",
    inferenceLatency: "0.8ms / 1k flows",
    createdAt: "2026-05-30T12:00:00Z",
  },
  {
    id: "model-002",
    name: "nids-xgboost",
    version: "1",
    stage: "Archived",
    framework: "XGBoost 2.1.0",
    macroF1: 0.878,
    perClassF1: {
      Benign: 0.97,
      "FTP-BruteForce": 0.93,
      "SSH-BruteForce": 0.91,
      "DoS-GoldenEye": 0.89,
      "DoS-Hulk": 0.95,
      "DoS-SlowHTTPTest": 0.85,
      "DoS-Slowloris": 0.84,
      "DDoS-LOIC-HTTP": 0.92,
      "DDoS-LOIC-UDP": 0.91,
      "Botnet-ARES": 0.82,
      "WebAttack-BruteForce": 0.80,
      "WebAttack-XSS": 0.72,
      "WebAttack-SQLInjection": 0.70,
      Infiltration: 0.73,
    },
    trainTime: "7m 15s",
    inferenceLatency: "1.2ms / 1k flows",
    createdAt: "2026-05-30T11:00:00Z",
  },
];

const STAGE_STYLES: Record<string, string> = {
  Production: "badge-critical",
  Staging: "badge-medium",
  Archived: "badge-info",
  None: "badge-low",
};

export default function ModelsPage() {
  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Model Registry</h1>
        <p className="page-subtitle">
          MLflow-tracked model versions with performance metrics
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {MOCK_MODELS.map((model) => (
          <div key={model.id} className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                <div>
                  <h2
                    style={{
                      fontSize: "18px",
                      fontWeight: 700,
                      color: "var(--text-primary)",
                    }}
                  >
                    {model.name}
                  </h2>
                  <div
                    style={{
                      fontSize: "13px",
                      color: "var(--text-muted)",
                      marginTop: "2px",
                    }}
                  >
                    {model.framework} · Version {model.version}
                  </div>
                </div>
              </div>
              <span className={`badge ${STAGE_STYLES[model.stage]}`}>
                {model.stage}
              </span>
            </div>

            {/* Key Metrics */}
            <div className="stats-grid" style={{ marginBottom: "20px" }}>
              <div className="stat-card blue" style={{ padding: "16px" }}>
                <div className="card-title" style={{ fontSize: "11px" }}>
                  Macro F1
                </div>
                <div
                  className="card-value"
                  style={{
                    fontSize: "24px",
                    color:
                      model.macroF1 >= 0.85
                        ? "var(--accent-green)"
                        : "var(--accent-yellow)",
                  }}
                >
                  {model.macroF1.toFixed(3)}
                </div>
              </div>
              <div className="stat-card green" style={{ padding: "16px" }}>
                <div className="card-title" style={{ fontSize: "11px" }}>
                  Training Time
                </div>
                <div className="card-value" style={{ fontSize: "24px" }}>
                  {model.trainTime}
                </div>
              </div>
              <div className="stat-card yellow" style={{ padding: "16px" }}>
                <div className="card-title" style={{ fontSize: "11px" }}>
                  Inference Latency
                </div>
                <div className="card-value" style={{ fontSize: "24px" }}>
                  {model.inferenceLatency}
                </div>
              </div>
            </div>

            {/* Per-class F1 */}
            <div>
              <h3
                style={{
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  marginBottom: "12px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Per-Class F1 Scores
              </h3>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
                  gap: "8px",
                }}
              >
                {Object.entries(model.perClassF1).map(([cls, f1]) => (
                  <div
                    key={cls}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "8px 12px",
                      background: "var(--bg-tertiary)",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  >
                    <span style={{ color: "var(--text-secondary)" }}>{cls}</span>
                    <span
                      style={{
                        fontWeight: 700,
                        fontFamily: "monospace",
                        color:
                          f1 >= 0.9
                            ? "var(--accent-green)"
                            : f1 >= 0.7
                              ? "var(--accent-yellow)"
                              : "var(--accent-red)",
                      }}
                    >
                      {f1.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
