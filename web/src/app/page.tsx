"use client";

import { useMemo } from "react";
import {
  generateMockAlerts,
  getAttackDistribution,
  getAlertTimeSeries,
  getAnomalyHistogram,
  getSeverityDistribution,
  SEVERITY_COLORS,
  ATTACK_COLORS,
} from "@/lib/mockData";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from "recharts";

export default function DashboardPage() {
  const alerts = useMemo(() => generateMockAlerts(200), []);

  const attackDistribution = useMemo(() => getAttackDistribution(alerts), [alerts]);
  const timeSeries = useMemo(() => getAlertTimeSeries(alerts), [alerts]);
  const anomalyHistogram = useMemo(() => getAnomalyHistogram(alerts), [alerts]);
  const severityDist = useMemo(() => getSeverityDistribution(alerts), [alerts]);

  const totalAlerts = alerts.length;
  const attackCount = alerts.filter((a) => a.label !== "Benign").length;
  const criticalCount = alerts.filter((a) => a.severity === "critical").length;
  const avgConfidence = (
    alerts.reduce((s, a) => s + a.confidence, 0) / totalAlerts
  ).toFixed(3);

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Detection Overview</h1>
        <p className="page-subtitle">
          Real-time network intrusion detection metrics — Phase 1 mock data
        </p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card blue">
          <div className="card-title">Total Flows</div>
          <div className="card-value">{totalAlerts.toLocaleString()}</div>
          <div className="card-change positive">↑ Live monitoring</div>
        </div>
        <div className="stat-card red">
          <div className="card-title">Attack Detections</div>
          <div className="card-value">{attackCount}</div>
          <div className="card-change negative">
            {((attackCount / totalAlerts) * 100).toFixed(1)}% of traffic
          </div>
        </div>
        <div className="stat-card yellow">
          <div className="card-title">Critical Alerts</div>
          <div className="card-value">{criticalCount}</div>
          <div className="card-change negative">Requires attention</div>
        </div>
        <div className="stat-card green">
          <div className="card-title">Avg Confidence</div>
          <div className="card-value">{avgConfidence}</div>
          <div className="card-change positive">Model accuracy</div>
        </div>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        {/* Alert Volume Time Series */}
        <div className="chart-container">
          <div className="chart-header">
            <div>
              <div className="chart-title">Alert Volume</div>
              <div className="chart-subtitle">Flows classified over time</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={timeSeries}>
              <defs>
                <linearGradient id="gradientTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradientAttacks" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f87171" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#f87171" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip
                contentStyle={{
                  background: "#1a2332",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  color: "#f1f5f9",
                  fontSize: "12px",
                }}
              />
              <Area
                type="monotone"
                dataKey="total"
                stroke="#38bdf8"
                fill="url(#gradientTotal)"
                strokeWidth={2}
                name="Total Flows"
              />
              <Area
                type="monotone"
                dataKey="attacks"
                stroke="#f87171"
                fill="url(#gradientAttacks)"
                strokeWidth={2}
                name="Attacks"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Attack Distribution */}
        <div className="chart-container">
          <div className="chart-header">
            <div>
              <div className="chart-title">Attack Distribution</div>
              <div className="chart-subtitle">Breakdown by attack class</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={attackDistribution}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
              >
                {attackDistribution.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={ATTACK_COLORS[entry.name] || "#64748b"}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#1a2332",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  color: "#f1f5f9",
                  fontSize: "12px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="charts-grid">
        {/* Anomaly Score Distribution */}
        <div className="chart-container">
          <div className="chart-header">
            <div>
              <div className="chart-title">Anomaly Score Distribution</div>
              <div className="chart-subtitle">
                Histogram of anomaly detector scores
              </div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={anomalyHistogram}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="range" stroke="#64748b" fontSize={10} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip
                contentStyle={{
                  background: "#1a2332",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  color: "#f1f5f9",
                  fontSize: "12px",
                }}
              />
              <Bar dataKey="count" fill="#a78bfa" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Severity Breakdown */}
        <div className="chart-container">
          <div className="chart-header">
            <div>
              <div className="chart-title">Severity Breakdown</div>
              <div className="chart-subtitle">Alert distribution by severity level</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={severityDist} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" stroke="#64748b" fontSize={11} />
              <YAxis
                dataKey="name"
                type="category"
                stroke="#64748b"
                fontSize={12}
                width={70}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a2332",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  color: "#f1f5f9",
                  fontSize: "12px",
                }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {severityDist.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={SEVERITY_COLORS[entry.name] || "#64748b"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
