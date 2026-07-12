"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/merchant", label: "Overview" },
  { href: "/merchant/products", label: "Products" },
  { href: "/merchant/warehouses", label: "Branches" },
  { href: "/merchant/inventory", label: "Inventory" },
  { href: "/merchant/sales", label: "Sales" },
  { href: "/merchant/returns", label: "Returns" },
];

export default function MerchantSidebar() {
  const pathname = usePathname();

  return (
    <aside style={{ width: 240, borderRight: "1px solid rgba(255,255,255,0.08)", padding: 16 }}>
      <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 12 }}>StoreWise AI</div>
      <div style={{ color: "#94a3b8", fontSize: 12, marginBottom: 16 }}>Merchant Portal</div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {NAV.map((n) => {
          const active = pathname === n.href || (n.href !== "/merchant" && pathname.startsWith(n.href));
          return (
            <Link
              key={n.href}
              href={n.href}
              style={{
                padding: "10px 10px",
                borderRadius: 10,
                textDecoration: "none",
                color: "inherit",
                background: active ? "rgba(37, 99, 235, 0.20)" : "transparent",
                border: active ? "1px solid rgba(37,99,235,0.35)" : "1px solid transparent",
              }}
            >
              {n.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
