"use client";

import Link from "next/link";
import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";
import AppShell from "../../components/AppShell";
import { api } from "../../lib/api";
import type { BranchRisk, DashboardAnalytics } from "../../lib/types";

const workflowCards = [
  {
    href: "/merchant/products",
    icon: "PR",
    title: "Catalog Intelligence",
    desc: "Inspect product records, categories, brands, variants, pricing, and AI-ready product context.",
  },
  {
    href: "/merchant/inventory",
    icon: "IN",
    title: "Inventory Risk",
    desc: "Track stock, branch availability, reorder pressure, and low-stock signals for operational decisions.",
  },
  {
    href: "/merchant/sales",
    icon: "SA",
    title: "Sales Insights",
    desc: "Ask natural-language questions about sales patterns, channels, branches, and product demand.",
  },
  {
    href: "/merchant/warehouses",
    icon: "BR",
    title: "Branch Network",
    desc: "Review branch and warehouse context for city-level demand analysis and local fulfillment.",
  },
  {
    href: "/merchant/returns",
    icon: "RT",
    title: "Returns Analysis",
    desc: "Explore return reasons, product friction, quality signals, and customer experience patterns.",
  },
];

const aiCapabilities = [
  "Voice or natural-language analysis",
  "MCP tools and RAG grounding",
  "Guardrailed Python execution",
  "Reports, charts, and action summaries",
];

function formatMoney(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

function riskTone(risk: BranchRisk["risk"]) {
  if (risk === "High") return "danger";
  if (risk === "Medium") return "warn";
  return "good";
}

export default function Page() {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const analytics = await api.dashboard();
        if (alive) setData(analytics);
      } catch (e: unknown) {
        if (alive) setError(e instanceof Error ? e.message : "Failed to load dashboard analytics");
      } finally {
        if (alive) setLoading(false);
      }
    }

    void load();
    return () => {
      alive = false;
    };
  }, []);

  const maxRevenue = useMemo(
    () => Math.max(...(data?.revenue_trend.map((point) => point.revenue) ?? [0]), 1),
    [data]
  );

  const topChannel = data?.channel_mix[0];
  const avgBranchCoverage = data?.branch_risk.length
    ? data.branch_risk.reduce((sum, branch) => sum + Math.min(branch.coverage, 200), 0) /
      data.branch_risk.length
    : 0;

  return (
    <AppShell title="Merchant Dashboard">
      <div className="merchantDashboard">
        <section className="merchantDashboardHero">
          <div>
            <p className="merchantHomeEyebrow">Live BI dashboard</p>
            <h1>Monitor demand, revenue, inventory risk, and branch signals.</h1>
            <p>
              ProductAI reads your commerce database directly and turns sales, revenue, inventory,
              product, branch, channel, and return data into fast operational insight.
            </p>
          </div>
          <div className="merchantDashboardAction">
            <span>AI</span>
            <strong>Need deeper analysis?</strong>
            <small>Ask in natural language or voice for demand research, branch risk, or a business report.</small>
            <Link href="/chat">Open AI Analysis</Link>
          </div>
        </section>

        {loading && <div className="merchantDashboardNotice">Loading live database insights...</div>}
        {error && <div className="merchantDashboardNotice merchantDashboardError">{error}</div>}

        {data && (
          <>
            <section className="merchantInsightStats" aria-label="Merchant dashboard signals">
              {data.metrics.map((card) => (
                <div className={`merchantInsightStat merchantInsightStat-${card.tone}`} key={card.label}>
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                  <small>{card.detail}</small>
                </div>
              ))}
            </section>

            <section className="merchantGraphGrid" aria-label="Important insight graphs">
              <div className="merchantGraphCard merchantGraphCardLarge">
                <div className="merchantGraphHeader">
                  <div>
                    <p>Demand index</p>
                    <h2>High-demand product categories</h2>
                  </div>
                  <span>By units sold</span>
                </div>
                <div className="merchantBarChart">
                  {data.category_demand.map((bar) => (
                    <div className="merchantBarRow" key={bar.label}>
                      <span>{bar.label}</span>
                      <div>
                        <i style={{ width: `${Math.max(bar.share, 4)}%` }} />
                      </div>
                      <strong>{bar.units}</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div className="merchantGraphCard">
                <div className="merchantGraphHeader">
                  <div>
                    <p>Revenue</p>
                    <h2>6-month trend</h2>
                  </div>
                  <span>Live</span>
                </div>
                <div className="merchantLineChart" aria-label="Revenue trend chart">
                  {data.revenue_trend.map((point, index) => (
                    <span
                      key={`${point.label}-${index}`}
                      title={`${point.label}: ${formatMoney(point.revenue)}`}
                      style={{
                        height: `${Math.max((point.revenue / maxRevenue) * 88, 8)}%`,
                        left: `${index * (88 / Math.max(data.revenue_trend.length - 1, 1)) + 4}%`,
                      }}
                    />
                  ))}
                </div>
                <div className="merchantChartAxis">
                  {data.revenue_trend.map((point, index) => (
                    <span key={`${point.label}-${index}`}>{point.label}</span>
                  ))}
                </div>
              </div>

              <div className="merchantGraphCard">
                <div className="merchantGraphHeader">
                  <div>
                    <p>Round indicators</p>
                    <h2>Operational health</h2>
                  </div>
                  <span>Database</span>
                </div>
                <div className="merchantCircleGrid">
                  <div className="merchantCircleMeter" style={{ "--value": data.returns.return_rate } as CSSProperties}>
                    <strong>{data.returns.return_rate.toFixed(1)}%</strong>
                    <span>Return rate</span>
                  </div>
                  <div className="merchantCircleMeter" style={{ "--value": Math.min(avgBranchCoverage / 2, 100) } as CSSProperties}>
                    <strong>{Math.round(avgBranchCoverage)}%</strong>
                    <span>Stock coverage</span>
                  </div>
                  <div className="merchantCircleMeter" style={{ "--value": topChannel?.share ?? 0 } as CSSProperties}>
                    <strong>{Math.round(topChannel?.share ?? 0)}%</strong>
                    <span>{topChannel?.channel ?? "Channel"}</span>
                  </div>
                </div>
              </div>

              <div className="merchantGraphCard">
                <div className="merchantGraphHeader">
                  <div>
                    <p>Branches</p>
                    <h2>Inventory risk</h2>
                  </div>
                  <span>Coverage</span>
                </div>
                <div className="merchantRiskList">
                  {data.branch_risk.slice(0, 4).map((item) => (
                    <div className="merchantRiskItem" key={item.branch}>
                      <div>
                        <strong>{item.branch}</strong>
                        <small>
                          {item.city ? `${item.city} - ` : ""}
                          {Math.round(item.coverage)}% coverage, {item.low_stock_skus} low-stock SKUs
                        </small>
                      </div>
                      <span className={`merchantRiskBadge merchantRiskBadge-${riskTone(item.risk)}`}>
                        {item.risk}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="merchantGraphCard">
                <div className="merchantGraphHeader">
                  <div>
                    <p>Products</p>
                    <h2>Top revenue drivers</h2>
                  </div>
                  <span>Top 5</span>
                </div>
                <div className="merchantProductInsightList">
                  {data.top_products.map((product, index) => (
                    <div className="merchantProductInsight" key={product.product_id}>
                      <span>{index + 1}</span>
                      <div>
                        <strong>{product.name}</strong>
                        <small>
                          {product.category || "Catalog"} - {product.units} units - {formatMoney(product.revenue)}
                        </small>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="merchantHomeBody">
              <div className="merchantHomeWorkflows">
                <div className="merchantHomeSectionHeader">
                  <div>
                    <p>Merchant modules</p>
                    <h2>Move from insight to decision</h2>
                  </div>
                </div>
                <div className="merchantHomeGrid">
                  {workflowCards.map((card) => (
                    <Link className="merchantHomeTile" href={card.href} key={card.href}>
                      <span>{card.icon}</span>
                      <strong>{card.title}</strong>
                      <small>{card.desc}</small>
                    </Link>
                  ))}
                </div>
              </div>

              <aside className="merchantHomeAside">
                <p>What ProductAI can do</p>
                <h2>Agentic workflows</h2>
                <ul>
                  {aiCapabilities.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </aside>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
