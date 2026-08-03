from __future__ import annotations

import html
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_GENERATED_DIR = PROJECT_ROOT / "frontend" / "public" / "generated"


def _build_mermaid() -> str:
    return """%%{init: {"flowchart": {"nodeSpacing": 14, "rankSpacing": 42, "subGraphTitleMargin": {"top": 6, "bottom": 16}}}}%%
flowchart TB
    USER[/User request/] --> GUARD{Guardrail check}
    GUARD -->|rejected| BLOCKED[Blocked response]
    GUARD -->|approved| O[ProductAI Orchestrator]

    STATE[/"Graph state<br/>messages, checkpoints"/] <-->|read + write| O
    O <-->|delegated research| RESEARCH
    O <-->|MCP calls| MCP
    O <-->|tool calls| TOOLS

    subgraph RESEARCH["Research sub-agent (bounded loop, max 14 steps)"]
        R1[["get_db_info_tool"]]:::researchNode
        R2[["run_readonly_sql_tool"]]:::researchNode
        R3[["get_weather_forecast"]]:::researchNode
        R4[["datetime_now_for_research"]]:::researchNode
    end

    subgraph MCP[MCP services]
        M1("get_inventory_schema"):::mcpNode
        M2("run_readonly_inventory_sql"):::mcpNode
        M3("search_company_documents"):::mcpNode
        M4("get_weather_forecast"):::mcpNode
        M5("tracestock_mcp_status"):::mcpNode
    end

    subgraph TOOLS[Agent tools]
        T2(["Sandboxed Python data analysis"]):::toolNode
        T3(["save_chart_tool"]):::toolNode
        T4(["generate_report_tool"]):::toolNode
        T5(["read_file / write_file / list_directory"]):::toolNode
        T6(["datetime_now"]):::toolNode
    end

    O --> ANSWER[Grounded response]

    subgraph OBS[Trace, interpretability and cost]
        TRACE("Trace<br/>evidence, decisions, eval IDs"):::obsNode
        INTERP("Interpretability<br/>tool timeline, guardrail status"):::obsNode
        COST("Cost and latency<br/>tokens, latency, estimate"):::obsNode
    end

    ANSWER --> TRACE
    ANSWER --> INTERP
    ANSWER --> COST

    TRACE --> STORE[(PostgreSQL + pgvector)]
    INTERP --> STORE
    COST --> STORE

    BLOCKED --> FINISH((End))
    STORE --> FINISH

    classDef mcpNode fill:#ECFDF5,stroke:#16A34A,stroke-width:1.5px,color:#052E16
    classDef toolNode fill:#FEFCE8,stroke:#CA8A04,stroke-width:1.5px,color:#422006
    classDef researchNode fill:#FDF4FF,stroke:#C026D3,stroke-width:1.5px,color:#4A044E
    classDef obsNode fill:#F5F3FF,stroke:#8B5CF6,stroke-width:1.5px,color:#2E1065

    style GUARD fill:#F97316,color:#ffffff,stroke:#C2410C,stroke-width:3px
    style O fill:#4F46E5,color:#ffffff,stroke:#3730A3,stroke-width:3px
    style STATE fill:#EEF2FF,stroke:#6366F1,stroke-width:2px,color:#1E1B4B
    style ANSWER fill:#ECFEFF,stroke:#0891B2,stroke-width:2.5px,color:#083344
    style BLOCKED fill:#FFF1F2,stroke:#E11D48,stroke-width:2px,color:#4C0519
    style STORE fill:#F0FDFA,stroke:#0F766E,stroke-width:2px,color:#134E4A
    style FINISH fill:#059669,color:#ffffff,stroke:#047857,stroke-width:3px
    style RESEARCH fill:transparent,stroke:#C026D3,stroke-width:2px,color:#C026D3
    style MCP fill:transparent,stroke:#16A34A,stroke-width:2px,color:#16A34A
    style TOOLS fill:transparent,stroke:#CA8A04,stroke-width:2px,color:#CA8A04
    style OBS fill:transparent,stroke:#8B5CF6,stroke-width:2px,color:#8B5CF6
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
