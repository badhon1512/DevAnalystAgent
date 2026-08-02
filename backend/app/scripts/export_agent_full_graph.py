from __future__ import annotations

import base64
import html
import urllib.parse
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_GENERATED_DIR = PROJECT_ROOT / "frontend" / "public" / "generated"
MERMAID_INK_IMG_URL = "https://mermaid.ink/img/{payload}?type=png&bgColor=!transparent"


def _build_mermaid() -> str:
    return """%%{init: {"flowchart": {"nodeSpacing": 10, "rankSpacing": 16, "padding": 8}}}%%
flowchart TB
    start(("START")):::startstate
    user[/"User request"/]:::entry
    guardrails{"Guardrail check<br/>approved?"}:::condition
    blocked(["Blocked response<br/>guardrail rejection"]):::guardrail
    end_blocked(("END")):::endstate
    orchestrator(["ProductAI orchestrator<br/>plans, routes, synthesizes"]):::agent
    answer(["Grounded response<br/>answer + artifacts"]):::answer
    end_main(("END")):::endstate

    start --> user --> guardrails
    guardrails -. rejected .-> blocked --> end_blocked
    guardrails -. approved .-> orchestrator

    subgraph orchestration_band[" "]
        direction LR
        subgraph mcp_group["MCP services"]
            direction LR
            mcp_title_gap[" "]:::spacer
            mcp_schema("get_inventory_schema"):::mcp
            mcp_sql("run_readonly_inventory_sql"):::mcp
            mcp_docs("search_company_documents<br/>Agentic RAG"):::mcp
            mcp_weather("get_weather_forecast"):::mcp
            mcp_status("tracestock_mcp_status"):::mcp
        end
        subgraph tool_group["Agent tools"]
            direction LR
            tool_title_gap[" "]:::spacer
            tool_research("researcher_agent"):::analysis
            tool_python("execute_python_code_tool"):::analysis
            tool_chart("save_chart_tool"):::analysis
            tool_report("generate_report_tool"):::analysis
            tool_files("read_file / write_file / list_directory"):::analysis
            tool_dt("datetime_now"):::analysis
        end
        mcp_group <-->|MCP calls| orchestrator
        orchestrator <-->|tool calls| tool_group
    end

    orchestrator --> answer

    subgraph observability_layer["Persistence, tracing and evaluation"]
        direction TB
        postgres[("PostgreSQL + pgvector<br/>application persistence")]:::database
        trace_store["Trace + evaluation store<br/>evidence, decisions, eval IDs"]:::utility
        telemetry["Interpretability + cost<br/>tools, tokens, latency, estimate"]:::observability

        postgres --> trace_store
        trace_store --> telemetry
    end

    answer --> postgres
    telemetry --> end_main

    classDef startstate fill:#2563eb,stroke:#1d4ed8,color:#ffffff,stroke-width:2.5px,font-weight:700
    classDef endstate fill:#0f172a,stroke:#020617,color:#ffffff,stroke-width:2.5px,font-weight:700
    classDef entry fill:#eff6ff,stroke:#0284c7,color:#0f172a,stroke-width:2px,font-weight:600
    classDef condition fill:#fff7ed,stroke:#f97316,color:#431407,stroke-width:2.5px,font-weight:600
    classDef guardrail fill:#fffbeb,stroke:#d97706,color:#451a03,stroke-width:2px,font-weight:600
    classDef agent fill:#eef2ff,stroke:#4f46e5,color:#1e1b4b,stroke-width:2.5px,font-weight:700
    classDef answer fill:#ecfeff,stroke:#0891b2,color:#083344,stroke-width:2.5px,font-weight:700
    classDef router fill:#f1f5f9,stroke:#475569,color:#0f172a,stroke-width:2px,font-weight:600
    classDef result fill:#f0fdfa,stroke:#0f766e,color:#134e4a,stroke-width:2.2px,font-weight:700
    classDef mcp fill:#ecfdf5,stroke:#16a34a,color:#052e16,stroke-width:2px,font-weight:600
    classDef rag fill:#f8fafc,stroke:#0ea5e9,color:#0c4a6e,stroke-width:2px,font-weight:600
    classDef research fill:#faf5ff,stroke:#9333ea,color:#3b0764,stroke-width:2px,font-weight:600
    classDef analysis fill:#fff1f2,stroke:#e11d48,color:#4c0519,stroke-width:2px,font-weight:600
    classDef files fill:#eff6ff,stroke:#0284c7,color:#082f49,stroke-width:2px,font-weight:600
    classDef database fill:#f0fdfa,stroke:#0f766e,color:#134e4a,stroke-width:2.5px,font-weight:600
    classDef utility fill:#fffbeb,stroke:#ca8a04,color:#422006,stroke-width:2px,font-weight:600
    classDef observability fill:#faf5ff,stroke:#8b5cf6,color:#2e1065,stroke-width:2px,font-weight:600
    classDef spacer fill:none,stroke:none,color:#00000000

    style orchestration_band fill:transparent,stroke:transparent,color:transparent
    style mcp_group fill:transparent,stroke:#16a34a,stroke-width:1.5px,color:#052e16
    style tool_group fill:transparent,stroke:#e11d48,stroke-width:1.5px,color:#4c0519
    style observability_layer fill:transparent,stroke:#c4b5fd,stroke-width:1.5px,color:#5b21b6
    linkStyle default stroke:#64748b,stroke-width:2px,color:#475569
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


def _render_png(mermaid: str) -> bytes:
    # mermaid.ink's own client leaves raw base64 unescaped in the URL path; an
    # unlucky "/" byte in the payload is then read as a path separator and 404s.
    # Percent-encoding the payload avoids that.
    encoded = base64.b64encode(mermaid.encode("utf-8")).decode("ascii")
    url = MERMAID_INK_IMG_URL.format(payload=urllib.parse.quote(encoded, safe=""))
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.content


def main() -> None:
    mermaid = _build_mermaid()
    html_page = _build_html(mermaid)

    FRONTEND_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    mmd_path = FRONTEND_GENERATED_DIR / "productai_agent_full_graph.mmd"
    html_path = FRONTEND_GENERATED_DIR / "productai_agent_full_graph.html"
    png_path = FRONTEND_GENERATED_DIR / "productai_agent_full_graph.png"
    mmd_path.write_text(mermaid, encoding="utf-8")
    html_path.write_text(html_page, encoding="utf-8")

    print(f"Wrote {mmd_path}")
    print(f"Wrote {html_path}")

    try:
        png_path.write_bytes(_render_png(mermaid))
        print(f"Wrote {png_path}")
    except Exception as e:
        print(f"[WARN] PNG render skipped: {e}")

    print("Frontend URL: http://localhost:3000/generated/productai_agent_full_graph.html")


if __name__ == "__main__":
    main()
