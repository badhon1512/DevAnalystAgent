import Link from "next/link";
import AppShell from "../../components/AppShell";

const cards = [
  { href: "/merchant/products", title: "Products", desc: "Browse products, category/brand filters" },
  { href: "/merchant/warehouses", title: "Branches", desc: "Branch and warehouse master data" },
  { href: "/merchant/inventory", title: "Inventory", desc: "Stock levels, low-stock risk" },
  { href: "/merchant/sales", title: "Sales", desc: "Transactions, channel/region filters" },
  { href: "/merchant/returns", title: "Returns", desc: "Returns, reasons, trends" },
];

export default function Page() {
  return (
    <AppShell title="Merchant Overview">
      <div style={{ padding: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
          {cards.map((c) => (
            <Link
              key={c.href}
              href={c.href}
              style={{
                display: "block",
                padding: 14,
                borderRadius: 12,
                border: "1px solid rgba(255,255,255,0.08)",
                background: "rgba(17,24,39,0.45)",
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <div style={{ fontWeight: 800 }}>{c.title}</div>
              <div style={{ marginTop: 6, color: "#94a3b8", fontSize: 13 }}>{c.desc}</div>
            </Link>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
