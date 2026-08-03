from __future__ import annotations

import html
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_GENERATED_DIR = PROJECT_ROOT / "frontend" / "public" / "generated"


def _build_mermaid() -> str:
    return """%%{init: {"flowchart": {"nodeSpacing": 12, "rankSpacing": 40, "subGraphTitleMargin": {"top": 6, "bottom": 14}}}}%%
flowchart TB
    USER[/User request/] --> GUARD{Guardrail check}
    GUARD -->|rejected| BLOCKED[Blocked response] --> ENDB((End))
    GUARD -->|approved| O[ProductAI Orchestrator]

    O <-->|MCP calls| MCP
    O <-->|tool calls| TOOLS

    subgraph MCP[MCP services]
        M1[get_inventory_schema]
        M2[run_readonly_inventory_sql]
        M3[search_company_documents]
        M4[get_weather_forecast]
        M5[tracestock_mcp_status]
    end

    subgraph TOOLS[Agent tools]
        T1[researcher_agent]
        T2[execute_python_code_tool]
        T3[save_chart_tool]
        T4[generate_report_tool]
        T5[read_file / write_file / list_directory]
        T6[datetime_now]
    end

    O --> ANSWER[Grounded response]
    ANSWER --> ENDM((End))
    O --> DB[(Trace and evaluation store)]

    style GUARD fill:#F97316,color:#ffffff,stroke:#C2410C,stroke-width:3px
    style O fill:#4F46E5,color:#ffffff,stroke:#3730A3,stroke-width:3px
    style ENDB fill:#059669,color:#ffffff,stroke:#047857,stroke-width:3px
    style ENDM fill:#059669,color:#ffffff,stroke:#047857,stroke-width:3px
    style DB fill:#F0FDFA,color:#134E4A,stroke:#0F766E,stroke-width:2px
    style MCP fill:transparent,stroke:#16A34A,stroke-width:2px,color:#052E16
    style TOOLS fill:transparent,stroke:#E11D48,stroke-width:2px,color:#4C0519
"""
def _build_html(mermaid: str) -> str:
    escaped = html.escape(mermaid)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ProductAI Full Agent Graph</title>
  <style>
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #eef2f7;
      color: #0f172a;
      min-height: 100vh;
    }}
    header {{
      padding: 34px 36px 12px;
      color: #0f172a;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(26px, 4vw, 44px);
      letter-spacing: 0;
    }}
    p {{
      max-width: 920px;
      font-size: 17px;
      color: #475569;
      line-height: 1.6;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    .pill {{
      border: 1px solid rgba(148, 163, 184, 0.42);
      border-radius: 999px;
      padding: 8px 12px;
      background: #ffffff;
      color: #334155;
      font-size: 14px;
    }}
    main {{
      margin: 20px 36px 36px;
      padding: 28px;
      border: 1px solid rgba(148, 163, 184, 0.32);
      border-radius: 12px;
      background: #f8fafc;
      box-shadow: 0 18px 50px rgba(15, 23, 42, 0.10);
      overflow-x: auto;
    }}
    section {{
      margin: 20px 36px 36px;
      padding: 28px;
      border: 1px solid rgba(148, 163, 184, 0.32);
      border-radius: 18px;
      background: #ffffff;
      box-shadow: 0 24px 70px rgba(15, 23, 42, 0.10);
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: clamp(22px, 3vw, 32px);
      color: #0f172a;
    }}
    .mermaid {{
      min-width: 1120px;
      font-size: 18px;
    }}
    .compact-graph {{
      display: block;
      width: min(100%, 980px);
      height: auto;
      margin: 22px auto 0;
      border: 1px solid rgba(148, 163, 184, 0.28);
      border-radius: 14px;
      background: #ffffff;
    }}
    @media (max-width: 720px) {{
      header {{
        padding: 24px 18px 8px;
      }}
      main {{
        margin: 14px 14px 24px;
        padding: 16px;
        border-radius: 18px;
      }}
      section {{
        margin: 14px 14px 24px;
        padding: 16px;
        border-radius: 18px;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>ProductAI Full Agent Graph</h1>
    <p>
      Controlled multi-agent workflow from guardrail validation to approved tools,
      grounded outputs, persistence, tracing, cost, and evaluation.
    </p>
    <div class="legend">
      <span class="pill">bidirectional edge = calls + observations</span>
      <span class="pill">dotted edge = conditional edge</span>
      <span class="pill">grouped nodes = capability families, tool names listed inside</span>
    </div>
  </header>
  <main>
    <pre class="mermaid">{escaped}</pre>
  </main>
  <section>
    <h2>Compact Runtime View</h2>
    <p>
      The compact graph shows the actual runtime loop: guardrail validation,
      model reasoning, approved tool execution, and final response.
    </p>
    <img class="compact-graph" src="/generated/agent_graph.png" alt="ProductAI compact runtime graph" />
  </section>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{
      startOnLoad: true,
      securityLevel: "loose",
        theme: "base",
        themeVariables: {{
        background: "transparent",
        mainBkg: "#ffffff",
        primaryColor: "#ffffff",
        secondaryColor: "#ffffff",
        tertiaryColor: "#ffffff",
        fontFamily: "Inter, ui-sans-serif, system-ui",
        fontSize: "20px",
        primaryTextColor: "#111827",
        textColor: "#111827",
        primaryBorderColor: "#334155",
        lineColor: "#475569",
        edgeLabelBackground: "#ffffff",
        clusterBkg: "#f8fafc",
        clusterBorder: "#94a3b8"
      }}
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    mermaid = _build_mermaid()
    html_page = _build_html(mermaid)

    FRONTEND_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    mmd_path = FRONTEND_GENERATED_DIR / "productai_agent_full_graph.mmd"
    html_path = FRONTEND_GENERATED_DIR / "productai_agent_full_graph.html"
    mmd_path.write_text(mermaid, encoding="utf-8")
    html_path.write_text(html_page, encoding="utf-8")

    print(f"Wrote {mmd_path}")
    print(f"Wrote {html_path}")
    print("Paste the .mmd contents into the README mermaid block to keep them in sync.")
    print("Frontend URL: http://localhost:3000/generated/productai_agent_full_graph.html")


if __name__ == "__main__":
    main()
