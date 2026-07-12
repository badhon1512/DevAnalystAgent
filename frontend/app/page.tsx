import Link from "next/link";

const capabilities = [
  { code: "ORC", label: "Agent orchestrator", value: "Routes tasks across tools and workflows" },
  { code: "RAG", label: "RAG knowledge layer", value: "Retrieves knowledge for LLMs to answer with trusted context" },
  { code: "MCP", label: "MCP tool layer", value: "Connects weather, data, docs, and actions" },
  { code: "SAFE", label: "Safety guardrails", value: "Policy guardrails, sandboxing, and guarded execution" },
  { code: "TRACE", label: "Interpretability", value: "Tool calls, reasoning path, latency, and usage" },
  { code: "$", label: "Cost visibility", value: "Token tracking and estimated run cost" },
];

export default function Page() {
  return (
    <main className="landingPage">
      <nav className="landingNav" aria-label="Primary">
        <Link className="landingBrand" href="/">
          <span>AI</span>
          <div>
            <strong>ProductAI</strong>
            <small>COSS platform for self-hosted agentic commerce</small>
          </div>
        </Link>
        <div className="landingNavLinks">
          <Link href="/storefront">Storefront</Link>
          <Link href="/merchant">Merchant Portal</Link>
        </div>
      </nav>

      <section className="landingHero" aria-labelledby="landing-title">
        <div className="landingCopy">
          <div className="landingBadge">
            <span aria-hidden="true">✨</span>
            Multi-agent AI product system
          </div>
          <h1 id="landing-title">Multi-agent AI for product intelligence and business action</h1>
          <p>
            ProductAI coordinates specialized agents for product support, merchant analytics,
            market research, demand forecasting, safe tool execution, and business reporting.
            It can orchestrate MCP tools, retrieve knowledge for LLMs, generate reports, visualize
            insight charts, create webpages, explain reasoning, and show cost and guardrail status.
          </p>

          <div className="landingAiTasks" aria-label="What the multi-agent system can do">
            <span>Product Q&A</span>
            <span>Market research</span>
            <span>Demand forecasting</span>
            <span>Business reports</span>
            <span>Insight charts</span>
            <span>Webpage creation</span>
            <span>RAG answers</span>
            <span>MCP tools</span>
            <span>Safe actions</span>
          </div>

          <div className="landingPathOverview" aria-label="ProductAI experience overview">
            <Link href="/merchant">
              <span className="landingPathKicker">Agentic business workspace</span>
              <strong>Merchant Portal</strong>
              <span>Ask in natural language or voice to get sales insights, demand research, reports, charts, inventory risks, and safe actions.</span>
              <em>Enter Merchant Portal</em>
            </Link>
            <div className="landingPathDisabled" aria-disabled="true">
              <span className="landingPathKicker">AI buyer experience</span>
              <strong>Storefront</strong>
              <span>Agentic customer support for product queries, comparisons, recommendations, policy answers, and issue resolution.</span>
              <em>Under development - coming soon</em>
            </div>
          </div>

          <dl className="landingStats" aria-label="Demo coverage">
            <div>
              <dt>MCP</dt>
              <dd>Tool orchestration</dd>
            </div>
            <div>
              <dt>Safe</dt>
              <dd>Sandboxed execution</dd>
            </div>
            <div>
              <dt>Trace</dt>
              <dd>Cost + explainability</dd>
            </div>
          </dl>
        </div>

        <div className="landingPreview" aria-label="AI commerce workflow preview">
          <div className="landingPreviewTop">
            <span className="landingStatusDot" />
            <span>Agent orchestration layer</span>
            <strong>Guardrailed + observable</strong>
          </div>

          <div className="landingAgentMap">
            <div className="landingAgentNode landingAgentNodeMain">
              <span>AI</span>
              <strong>Product Intelligence Orchestrator</strong>
              <small>Plans, selects MCP tools, follows guardrails, and explains outcomes</small>
            </div>
            <div className="landingTrace landingTraceOne" />
            <div className="landingTrace landingTraceTwo" />
            <div className="landingTrace landingTraceThree" />
          </div>

          <div className="landingCapabilityGrid">
            {capabilities.map((item) => (
              <div className="landingCapability" key={item.code}>
                <span>{item.code}</span>
                <div>
                  <strong>{item.label}</strong>
                  <small>{item.value}</small>
                </div>
              </div>
            ))}
          </div>

          <div className="landingInsight">
            <div>
              <span>Detailed action layer</span>
              <strong>Every answer can show tools used, guardrail status, cost estimate, evidence, and next action.</strong>
            </div>
            <small>Built for support answers, product discovery, operational insight, and trustworthy agentic automation.</small>
          </div>
        </div>
      </section>

      <footer className="landingFooter">
        <div>
          <strong>ProductAI</strong>
          <span>Copyright (c) 2026 ProductAI. Open-source agentic commerce demo.</span>
        </div>
        <div className="landingFooterLinks">
          <a href="https://github.com/badhon1512/DevAnalystAgent" target="_blank" rel="noreferrer">
            GitHub
          </a>
          <a href="https://github.com/badhon1512" target="_blank" rel="noreferrer">
            Contact
          </a>
        </div>
      </footer>
    </main>
  );
}
