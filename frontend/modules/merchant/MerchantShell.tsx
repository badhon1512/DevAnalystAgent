"use client";

import Link from "next/link";
import MerchantSidebar from "./MerchantSidebar";

export default function MerchantShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <MerchantSidebar />
      <main style={{ flex: 1, padding: 20 }}>
        <div className="appShellHeader">
          <div>
            <div style={{ fontSize: 20, fontWeight: 800 }}>{title}</div>
            <div className="appShellSub">Merchant Portal</div>
          </div>
          <div className="viewSwitch">
            <Link href="/storefront">Storefront</Link>
            <Link href="/chat">Full chat</Link>
          </div>
        </div>
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14,
            overflow: "hidden",
            background: "rgba(2,6,23,0.25)",
          }}
        >
          {children}
        </div>
      </main>
    </div>
  );
}
