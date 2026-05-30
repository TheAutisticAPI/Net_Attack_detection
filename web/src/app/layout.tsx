import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "TheAutisticNIDS — Network Intrusion Detection",
  description:
    "ML-powered network intrusion detection system with explainability, anomaly detection, and concept drift awareness.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app-layout">
          <Sidebar />
          <Header />
          <main className="main-content">{children}</main>
        </div>
      </body>
    </html>
  );
}
