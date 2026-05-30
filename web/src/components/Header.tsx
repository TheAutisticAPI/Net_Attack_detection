"use client";

import { usePathname } from "next/navigation";

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/alerts": "Alert Management",
  "/models": "Model Registry",
};

export function Header() {
  const pathname = usePathname();
  const title = PAGE_TITLES[pathname] ?? "TheAutisticNIDS";

  return (
    <header className="header">
      <h1 className="header-title">{title}</h1>
      <div className="header-actions">
        <button className="btn btn-secondary" style={{ fontSize: "12px" }}>
          <span className="status-dot online"></span>
          v0.1.0 · Phase 1
        </button>
      </div>
    </header>
  );
}
