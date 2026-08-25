"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/merchant", label: "BI Dashboard", icon: "BI" },
  { href: "/merchant/ai-dashboard", label: "AI Dashboard", icon: "AD" },
  { href: "/merchant/evaluations", label: "Agent Evals", icon: "EV" },
  { href: "/chat", label: "AI Analysis", icon: "\u2726" },
  { href: "/merchant/products", label: "Products", icon: "PR" },
  { href: "/merchant/warehouses", label: "Branches", icon: "BR" },
  { href: "/merchant/inventory", label: "Inventory", icon: "IN" },
  { href: "/merchant/sales", label: "Sales", icon: "SA" },
  { href: "/merchant/returns", label: "Returns", icon: "RT" },
];

export default function MerchantSidebar({
  open = false,
  onNavigate,
}: {
  /** Drawer state. Only affects small screens; the sidebar is always visible on desktop. */
  open?: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();

  return (
    <aside
      className={`merchantSidebar${open ? " merchantSidebarOpen" : ""}`}
      // Hidden from assistive tech on mobile until opened; on desktop CSS keeps
      // it visible and this attribute is ignored because it is never set there.
      aria-label="Merchant portal navigation"
    >
      <Link className="merchantBrand" href="/" onClick={onNavigate}>
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
              aria-current={active ? "page" : undefined}
              onClick={onNavigate}
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
