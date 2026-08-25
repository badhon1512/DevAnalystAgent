import Link from "next/link";
import type { CSSProperties } from "react";
import AppShell from "../../../components/AppShell";

const executiveBrief = [
  "Revenue momentum is healthy, but branch-level stock coverage needs attention before the next demand spike.",
  "Weather-sensitive categories and laptop accessories show the strongest near-term opportunity.",
  "Returns are concentrated around a small group of products, so review intelligence should guide merchandising fixes.",
  "Recommended focus: protect availability, reduce avoidable returns, and promote high-confidence growth categories.",
];

const priorityActions = [
  "Rebalance low-stock products into Berlin and Munich before the weekend demand window.",
  "Review product pages for high-return items and clarify sizing, compatibility, and included accessories.",
  "Create a bundle campaign around top laptop SKUs and slow-moving accessories.",
  "Ask AI Analysis to generate a weekly demand report with branch-level reorder suggestions.",
];

const reviewIntel = [
  {
    product: "NovaWorks Pro Laptop 14",
    rating: 4.6,
    volume: 184,
    sentiment: "Mostly positive",
    praise: "Performance, display quality, lightweight design",
    complaints: "Battery expectations and charger heat",
    action: "Improve battery guidance and add accessory bundle recommendations.",
  },
  {
    product: "RainShell Commuter Jacket",
    rating: 4.1,
    volume: 96,
    sentiment: "Mixed positive",
    praise: "Waterproofing, packable design",
    complaints: "Sizing uncertainty",
    action: "Add clearer sizing advice and branch stock visibility.",
  },
  {
    product: "Breeze Portable Air Cooler",
    rating: 4.4,
    volume: 121,
    sentiment: "Positive seasonal",
    praise: "Fast cooling and low noise",
    complaints: "Room-size expectations",
    action: "Add room-size fit notes and target warm-weather branches.",
  },
];

const risks = [
  "Branch stock risk may block demand capture in weather-sensitive categories.",
  "Return reasons indicate avoidable product-page clarity issues.",
  "Demand signals are stronger than current replenishment confidence for selected SKUs.",
];

const opportunities = [
  "Use review sentiment to improve product pages and reduce support load.",
  "Promote high-demand categories by branch and season.",
  "Turn BI dashboard anomalies into scheduled AI action reports.",
];

const evidence = ["BI dashboard metrics", "Sales and revenue trend", "Inventory coverage", "Product reviews", "Return reasons"];

export default function Page() {
  return (
    <AppShell title="AI Dashboard">
      <div className="merchantAiDashboard merchantAiDashboardCompact">
        <section className="aiDashboardTopBar">
          <div>
            <p className="merchantHomeEyebrow">AI decision layer</p>
            <h1>Compact merchant briefing generated from live business context.</h1>
            <span>Frontend design preview. Backend sync will be connected later.</span>
          </div>
          <div className="aiDashboardActions">
            <button type="button" disabled>
              <span aria-hidden="true">&#10022;</span> Sync AI Insights
            </button>
            <Link href="/chat"><span aria-hidden="true">&#10022;</span> Open AI Analysis</Link>
          </div>
        </section>

        <section className="aiDashboardGrid">
          <article className="aiBriefPanel">
            <div className="aiPanelHeader">
              <span>01</span>
              <div>
                <p>Executive brief</p>
                <h2>What matters now</h2>
              </div>
            </div>
            <ul>
              {executiveBrief.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className="aiActionsPanel">
            <div className="aiPanelHeader">
              <span>02</span>
              <div>
                <p>Priority actions</p>
                <h2>Recommended next steps</h2>
              </div>
            </div>
            <ol>
              {priorityActions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          </article>

          <article className="aiReviewPanel">
            <div className="aiPanelHeader">
              <span>03</span>
              <div>
                <p>Product review intelligence</p>
                <h2>Ratings, sentiment, and product-page actions</h2>
              </div>
            </div>
            <div className="aiReviewList">
              {reviewIntel.map((item) => (
                <div className="aiReviewCard" key={item.product}>
                  <div className="aiReviewCardTop">
                    <div
                      className="aiReviewScore"
                      style={{ "--score": item.rating * 20 } as CSSProperties}
                      aria-label={`${item.rating} out of 5 review rating`}
                    >
                      <strong>{item.rating.toFixed(1)}</strong>
                      <span>/5</span>
                    </div>
                    <div className="aiReviewTitleBlock">
                      <strong>{item.product}</strong>
                      <span>{item.sentiment}</span>
                      <small>{item.volume} reviews analyzed</small>
                    </div>
                  </div>
                  <dl>
                    <dt>Praise</dt>
                    <dd>{item.praise}</dd>
                    <dt>Complaint</dt>
                    <dd>{item.complaints}</dd>
                    <dt>Action</dt>
                    <dd>{item.action}</dd>
                  </dl>
                </div>
              ))}
            </div>
          </article>

          <article className="aiRiskOpportunityPanel">
            <div className="aiPanelHeader">
              <span>04</span>
              <div>
                <p>Risks and opportunities</p>
                <h2>Decision summary</h2>
              </div>
            </div>
            <div className="aiRiskOpportunityGrid">
              <div>
                <strong>Risks</strong>
                <ul>
                  {risks.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <strong>Opportunities</strong>
                <ul>
                  {opportunities.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </article>
        </section>

        <section className="aiDashboardFooterPanel">
          <div>
            <p>Evidence planned for sync</p>
            <div>
              {evidence.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </div>
          <div>
            <p>Trace preview</p>
            <span>Guardrails: required</span>
            <span>Cost: calculated after sync</span>
            <span>Model: N/A</span>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
