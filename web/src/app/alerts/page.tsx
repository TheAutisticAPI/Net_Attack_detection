"use client";

import { useMemo, useState } from "react";
import { generateMockAlerts, type MockAlert } from "@/lib/mockData";
import Link from "next/link";

const SEVERITY_BADGE: Record<string, string> = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
};

export default function AlertsPage() {
  const allAlerts = useMemo(() => generateMockAlerts(100), []);
  const [filter, setFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const filtered = useMemo(() => {
    if (filter === "all") return allAlerts;
    if (filter === "attacks") return allAlerts.filter((a) => a.label !== "Benign");
    return allAlerts.filter((a) => a.label === filter);
  }, [allAlerts, filter]);

  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);
  const totalPages = Math.ceil(filtered.length / pageSize);

  const uniqueLabels = useMemo(
    () => [...new Set(allAlerts.map((a) => a.label))].sort(),
    [allAlerts]
  );

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Alert Management</h1>
        <p className="page-subtitle">
          {filtered.length} alerts · Classified by LightGBM + Isolation Forest
        </p>
      </div>

      {/* Filter Bar */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          marginBottom: "20px",
          flexWrap: "wrap",
        }}
      >
        <button
          className={`btn ${filter === "all" ? "btn-primary" : "btn-secondary"}`}
          onClick={() => { setFilter("all"); setPage(1); }}
        >
          All ({allAlerts.length})
        </button>
        <button
          className={`btn ${filter === "attacks" ? "btn-primary" : "btn-secondary"}`}
          onClick={() => { setFilter("attacks"); setPage(1); }}
        >
          Attacks Only
        </button>
        {uniqueLabels.map((label) => (
          <button
            key={label}
            className={`btn ${filter === label ? "btn-primary" : "btn-secondary"}`}
            onClick={() => { setFilter(label); setPage(1); }}
            style={{ fontSize: "11px" }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Alerts Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Source</th>
              <th>Destination</th>
              <th>Protocol</th>
              <th>Classification</th>
              <th>Confidence</th>
              <th>Anomaly Score</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((alert) => (
              <tr key={alert.id}>
                <td style={{ fontFamily: "monospace", fontSize: "12px" }}>
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </td>
                <td style={{ fontFamily: "monospace", fontSize: "12px" }}>
                  {alert.src_ip}:{alert.src_port}
                </td>
                <td style={{ fontFamily: "monospace", fontSize: "12px" }}>
                  {alert.dst_ip}:{alert.dst_port}
                </td>
                <td>
                  <span className="badge badge-info">{alert.protocol}</span>
                </td>
                <td>
                  <span
                    className={`badge ${alert.label === "Benign" ? "badge-benign" : "badge-attack"}`}
                  >
                    {alert.label}
                  </span>
                </td>
                <td>
                  <span
                    style={{
                      color:
                        alert.confidence > 0.9
                          ? "var(--accent-green)"
                          : alert.confidence > 0.7
                            ? "var(--accent-yellow)"
                            : "var(--accent-red)",
                      fontWeight: 600,
                      fontFamily: "monospace",
                    }}
                  >
                    {(alert.confidence * 100).toFixed(1)}%
                  </span>
                </td>
                <td>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <div
                      style={{
                        width: "60px",
                        height: "6px",
                        background: "var(--bg-tertiary)",
                        borderRadius: "3px",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${(alert.anomaly_score ?? 0) * 100}%`,
                          height: "100%",
                          background:
                            (alert.anomaly_score ?? 0) > 0.7
                              ? "var(--accent-red)"
                              : (alert.anomaly_score ?? 0) > 0.4
                                ? "var(--accent-yellow)"
                                : "var(--accent-green)",
                          borderRadius: "3px",
                          transition: "width 0.3s ease",
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontFamily: "monospace",
                        fontSize: "12px",
                        color: "var(--text-muted)",
                      }}
                    >
                      {alert.anomaly_score?.toFixed(2) ?? "—"}
                    </span>
                  </div>
                </td>
                <td>
                  <span className={`badge ${SEVERITY_BADGE[alert.severity]}`}>
                    {alert.severity}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: "12px",
          marginTop: "20px",
        }}
      >
        <button
          className="btn btn-secondary"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
        >
          ← Previous
        </button>
        <span style={{ color: "var(--text-muted)", fontSize: "13px" }}>
          Page {page} of {totalPages}
        </span>
        <button
          className="btn btn-secondary"
          disabled={page >= totalPages}
          onClick={() => setPage((p) => p + 1)}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
