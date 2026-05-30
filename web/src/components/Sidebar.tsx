"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  {
    section: "Detection",
    items: [
      { href: "/", label: "Dashboard", icon: "📊" },
      { href: "/alerts", label: "Alerts", icon: "🚨" },
    ],
  },
  {
    section: "Analysis",
    items: [
      { href: "/models", label: "Models", icon: "🧠" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">N</div>
        <div>
          <div className="sidebar-brand-text">TheAutisticNIDS</div>
          <div className="sidebar-brand-sub">Intrusion Detection</div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((section) => (
          <div key={section.section}>
            <div className="sidebar-section-label">{section.section}</div>
            {section.items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`sidebar-link ${pathname === item.href ? "active" : ""}`}
              >
                <span className="sidebar-icon">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </div>
        ))}
      </nav>
      <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border-color)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
          <span className="status-dot online"></span>
          <span style={{ color: "var(--text-secondary)" }}>System Online</span>
        </div>
      </div>
    </aside>
  );
}
