import Link from "next/link";

export default function Page() {
  return (
    <main className="welcomePage">
      <section className="welcomePanel" aria-labelledby="welcome-title">
        <div className="welcomeBrandRow">
          <div className="welcomeLogo">AI</div>
          <div>
            <div className="welcomeBrand">StoreWise AI</div>
            <div className="welcomeSub">Agentic commerce demo</div>
          </div>
        </div>

        <div className="welcomeContent">
          <div>
            <p className="welcomeEyebrow">Storefront support + merchant intelligence</p>
            <h1 id="welcome-title">Choose how you want to explore the store</h1>
            <p className="welcomeCopy">
              A compact AI demo for product questions, variant-level inventory, German branches,
              weather-aware demand signals, and operational analytics.
            </p>
          </div>

          <div className="welcomeChoices">
            <Link className="welcomeChoice" href="/storefront">
              <span className="welcomeChoiceTitle">Open Storefront</span>
              <span className="welcomeChoiceText">
                Browse product information and ask support-style questions without seeing internal tools.
              </span>
              <span className="welcomeChoiceAction">Browse products</span>
            </Link>

            <Link className="welcomeChoice welcomeChoiceStrong" href="/merchant">
              <span className="welcomeChoiceTitle">Open Merchant Portal</span>
              <span className="welcomeChoiceText">
                Manage products, branches, inventory, sales, returns, and AI demand research.
              </span>
              <span className="welcomeChoiceAction">Open portal</span>
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
