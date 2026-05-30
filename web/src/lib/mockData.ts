/**
 * Mock data seeded from CSE-CIC-IDS2018 schema.
 * Used for development until the ML pipeline delivers real predictions.
 */

export interface MockAlert {
  id: string;
  timestamp: string;
  src_ip: string;
  src_port: number;
  dst_ip: string;
  dst_port: number;
  protocol: string;
  label: string;
  confidence: number;
  anomaly_score: number | null;
  severity: "critical" | "high" | "medium" | "low";
}

const ATTACK_TYPES = [
  "Benign",
  "FTP-BruteForce",
  "SSH-BruteForce",
  "DoS-GoldenEye",
  "DoS-Hulk",
  "DoS-SlowHTTPTest",
  "DoS-Slowloris",
  "DDoS-LOIC-HTTP",
  "DDoS-LOIC-UDP",
  "Botnet-ARES",
  "WebAttack-BruteForce",
  "WebAttack-XSS",
  "WebAttack-SQLInjection",
  "Infiltration",
];

function randomIP(): string {
  return `${10 + Math.floor(Math.random() * 20)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 254) + 1}`;
}

function randomPort(): number {
  return Math.floor(Math.random() * 65535) + 1;
}

function getSeverity(label: string, confidence: number): MockAlert["severity"] {
  if (label === "Benign") return "low";
  if (label.startsWith("DDoS") || label.startsWith("DoS")) {
    return confidence > 0.9 ? "critical" : "high";
  }
  if (label.includes("BruteForce") || label.includes("SQLInjection")) {
    return confidence > 0.85 ? "high" : "medium";
  }
  return "medium";
}

export function generateMockAlerts(count: number = 50): MockAlert[] {
  const now = new Date();
  return Array.from({ length: count }, (_, i) => {
    const label = ATTACK_TYPES[Math.floor(Math.random() * ATTACK_TYPES.length)];
    const confidence = label === "Benign"
      ? 0.85 + Math.random() * 0.14
      : 0.55 + Math.random() * 0.44;
    const anomalyScore = label === "Benign"
      ? Math.random() * 0.3
      : 0.4 + Math.random() * 0.6;

    return {
      id: `alert-${String(i + 1).padStart(4, "0")}`,
      timestamp: new Date(now.getTime() - i * 30000 - Math.random() * 10000).toISOString(),
      src_ip: randomIP(),
      src_port: randomPort(),
      dst_ip: randomIP(),
      dst_port: [80, 443, 22, 21, 8080, 3306][Math.floor(Math.random() * 6)],
      protocol: ["TCP", "UDP", "TCP", "TCP"][Math.floor(Math.random() * 4)],
      label,
      confidence: parseFloat(confidence.toFixed(3)),
      anomaly_score: parseFloat(anomalyScore.toFixed(3)),
      severity: getSeverity(label, confidence),
    };
  });
}

/** Attack distribution for pie/bar chart */
export function getAttackDistribution(alerts: MockAlert[]) {
  const counts: Record<string, number> = {};
  alerts.forEach((a) => {
    counts[a.label] = (counts[a.label] || 0) + 1;
  });
  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

/** Time-series data for alert volume */
export function getAlertTimeSeries(alerts: MockAlert[]) {
  const buckets: Record<string, { total: number; attacks: number }> = {};
  alerts.forEach((a) => {
    const hour = a.timestamp.substring(0, 13) + ":00";
    if (!buckets[hour]) buckets[hour] = { total: 0, attacks: 0 };
    buckets[hour].total++;
    if (a.label !== "Benign") buckets[hour].attacks++;
  });
  return Object.entries(buckets)
    .map(([time, data]) => ({ time: time.substring(11), ...data }))
    .sort((a, b) => a.time.localeCompare(b.time));
}

/** Anomaly score histogram */
export function getAnomalyHistogram(alerts: MockAlert[]) {
  const bins = Array.from({ length: 10 }, (_, i) => ({
    range: `${(i * 0.1).toFixed(1)}-${((i + 1) * 0.1).toFixed(1)}`,
    count: 0,
  }));
  alerts.forEach((a) => {
    if (a.anomaly_score !== null) {
      const idx = Math.min(Math.floor(a.anomaly_score * 10), 9);
      bins[idx].count++;
    }
  });
  return bins;
}

/** Severity distribution */
export function getSeverityDistribution(alerts: MockAlert[]) {
  const counts = { critical: 0, high: 0, medium: 0, low: 0 };
  alerts.forEach((a) => {
    if (a.label !== "Benign") counts[a.severity]++;
  });
  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

export const ATTACK_COLORS: Record<string, string> = {
  "Benign": "#22c55e",
  "FTP-BruteForce": "#f87171",
  "SSH-BruteForce": "#fb923c",
  "DoS-GoldenEye": "#fbbf24",
  "DoS-Hulk": "#a78bfa",
  "DoS-SlowHTTPTest": "#f472b6",
  "DoS-Slowloris": "#38bdf8",
  "DDoS-LOIC-HTTP": "#ef4444",
  "DDoS-LOIC-UDP": "#dc2626",
  "Botnet-ARES": "#8b5cf6",
  "WebAttack-BruteForce": "#ec4899",
  "WebAttack-XSS": "#e879f9",
  "WebAttack-SQLInjection": "#c084fc",
  "Infiltration": "#64748b",
};
