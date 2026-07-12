import Link from "next/link";
import AppShell from "../../components/AppShell";

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

export default function Page() {
  return (
    <AppShell title="Merchant Overview">
      <div className="merchantHome">
        <section className="merchantHomeHero">
          <div>
            <p className="merchantHomeEyebrow">Agentic merchant workspace</p>
            <h1>Analyze products, demand, inventory, and actions with ProductAI.</h1>
            <p>
              Use natural language or voice to ask business questions, research market demand,
              inspect catalog data, generate reports, visualize insights, and execute safe tool-backed
              workflows with traces and cost visibility.
            </p>
          </div>
          <div className="merchantHomeAgentCard">
            <span>AI</span>
            <strong>Ready for analysis</strong>
            <small>Ask about sales, stock, demand factors, branch risk, or product performance.</small>
            <Link href="/chat">Open AI Workspace</Link>
          </div>
        </section>

        <section className="merchantHomeStats" aria-label="Merchant Portal AI pillars">
          <div>
            <span>MCP</span>
            <strong>Tool orchestration</strong>
            <small>Weather, database, documents, charts, and safe actions.</small>
          </div>
          <div>
            <span>RAG</span>
            <strong>Knowledge grounding</strong>
            <small>Retrieve trusted product and business context for LLM answers.</small>
          </div>
          <div>
            <span>SAFE</span>
            <strong>Guardrails</strong>
            <small>Policy checks, sandboxed execution, and traceable outputs.</small>
          </div>
          <div>
            <span>TRACE</span>
            <strong>Interpretability</strong>
            <small>Tool calls, token usage, latency, costs, and evidence.</small>
          </div>
        </section>

        <section className="merchantHomeBody">
          <div className="merchantHomeWorkflows">
            <div className="merchantHomeSectionHeader">
              <div>
                <p>Workspace modules</p>
                <h2>Move from question to decision</h2>
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
      </div>
    </AppShell>
  );
}
