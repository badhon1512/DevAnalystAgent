"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/merchant", label: "BI Dashboard", icon: "BI" },
  { href: "/merchant/ai-dashboard", label: "AI Dashboard", icon: "AD" },
  { href: "/chat", label: "AI Analysis", icon: "AI" },
  { href: "/merchant/products", label: "Products", icon: "PR" },
  { href: "/merchant/warehouses", label: "Branches", icon: "BR" },
  { href: "/merchant/inventory", label: "Inventory", icon: "IN" },
  { href: "/merchant/sales", label: "Sales", icon: "SA" },
  { href: "/merchant/returns", label: "Returns", icon: "RT" },
];

export default function MerchantSidebar() {
  const pathname = usePathname();

  return (
    <aside className="merchantSidebar">
      <Link className="merchantBrand" href="/">
        <span>AI</span>
        <div>
          <strong>ProductAI</strong>
          <small>Merchant Portal</small>
        </div>
      </Link>

      <nav className="merchantNav">
        {NAV.map((n) => {
          const active =
            pathname === n.href ||
            (n.href !== "/merchant" && n.href !== "/chat" && pathname.startsWith(n.href));
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`merchantNavItem${active ? " merchantNavItemActive" : ""}`}
            >
              <span>{n.icon}</span>
              <strong>{n.label}</strong>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
