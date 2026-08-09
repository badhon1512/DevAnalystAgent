"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";

import AppShell from "../../../components/AppShell";
import {
  adminQueueEvaluation,
  adminQueueRagEvaluation,
  getEvaluationDashboard,
  getEvaluationRun,
} from "../../../lib/api";
import type {
  EvaluationDashboard,
  EvaluationRunDetail,
  EvaluationRunRequest,
  EvaluationRunSummary,
  RagEvaluationRunRequest,
} from "../../../lib/types";


const ADMIN_TOKEN_KEY = "productai-admin-token";

const PRESETS = {
  smoke: {
    label: "Critical smoke",
    caseIds: ["rag-return-window-001", "guardrail-destructive-sql-001"],
    categories: [],
    limit: 2,
  },
  guardrail: {
    label: "Guardrails",
    caseIds: [],
    categories: ["guardrail"],
    limit: 8,
  },
  rag: {
    label: "RAG policies",
    caseIds: [],
    categories: ["rag_policy"],
    limit: 8,
  },
  mixed: {
    label: "Mixed regression",
    caseIds: [],
    categories: [],
    limit: 10,
  },
} as const;

type PresetKey = keyof typeof PRESETS;

function readAdminToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(ADMIN_TOKEN_KEY) || "";
}

function subscribeAdminToken(onStoreChange: () => void) {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", onStoreChange);
  return () => window.removeEventListener("storage", onStoreChange);
}

function formatDate(value?: string | null) {
  if (!value) return "Pending";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatCost(value?: number | null) {
  if (value === null || value === undefined) return "N/A";
  return `$${value.toFixed(value < 0.01 ? 4 : 2)}`;
}

function formatCategory(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function runTone(run: EvaluationRunSummary) {
  if (run.status === "queued" || run.status === "running") return "running";
  if (run.status === "failed" || run.error_case_count > 0) return "error";
  if ((run.pass_rate_percent ?? 0) >= 90) return "pass";
  return "warn";
}

export default function EvaluationDashboardPage() {
  const adminToken = useSyncExternalStore(subscribeAdminToken, readAdminToken, () => "");
  const [dashboard, setDashboard] = useState<EvaluationDashboard | null>(null);
  const [selectedRun, setSelectedRun] = useState<EvaluationRunDetail | null>(null);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [preset, setPreset] = useState<PresetKey>("smoke");
  const [model, setModel] = useState<EvaluationRunRequest["model"]>("gpt-5.4-nano");
  const [budget, setBudget] = useState(0.5);
  const [loading, setLoading] = useState(true);
  const [queueing, setQueueing] = useState(false);
  const [ragQueueing, setRagQueueing] = useState(false);
  const [ragMode, setRagMode] = useState<
    RagEvaluationRunRequest["retrieval_mode"]
  >("hybrid");
  const [ragEmbeddingModel, setRagEmbeddingModel] = useState<
    RagEvaluationRunRequest["embedding_model"]
  >("BAAI/bge-small-en-v1.5");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadDashboard = useCallback(async () => {
    setError("");
    try {
      const next = await getEvaluationDashboard();
      setDashboard(next);
      const preferredId = selectedRunId || next.latest_run?.run_id || "";
      if (preferredId) {
        setSelectedRunId(preferredId);
        setSelectedRun(await getEvaluationRun(preferredId));
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Evaluation data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [selectedRunId]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const hasActiveRun =
    dashboard?.runs.some(
      (run) => run.status === "queued" || run.status === "running",
    ) ||
    dashboard?.rag_latest?.status === "queued" ||
    dashboard?.rag_latest?.status === "running";

  useEffect(() => {
    if (!hasActiveRun) return;
    const timer = window.setInterval(() => void loadDashboard(), 4000);
    return () => window.clearInterval(timer);
  }, [hasActiveRun, loadDashboard]);

  const trendRuns = useMemo(
    () =>
      [...(dashboard?.runs ?? [])]
        .filter((run) => run.pass_rate_percent !== null && run.pass_rate_percent !== undefined)
        .slice(0, 8)
        .reverse(),
    [dashboard],
  );

  async function selectRun(runId: string) {
    setSelectedRunId(runId);
    setError("");
    try {
      setSelectedRun(await getEvaluationRun(runId));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Run detail could not be loaded.");
    }
  }

  async function queueRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!adminToken) return;
    const selectedPreset = PRESETS[preset];
    const estimatedCost = selectedPreset.limit * 0.1;
    if (!window.confirm(`Run ${selectedPreset.label} with an estimated cost of $${estimatedCost.toFixed(2)}?`)) {
      return;
    }

    setQueueing(true);
    setError("");
    setNotice("");
    try {
      const queued = await adminQueueEvaluation(adminToken, {
        categories: [...selectedPreset.categories],
        case_ids: [...selectedPreset.caseIds],
        limit: selectedPreset.limit,
        model,
        analysis_depth: "quick",
        answer_detail: "concise",
        budget_usd: budget,
        estimated_cost_per_case: 0.1,
        fail_fast: false,
      });
      setNotice(`Run ${queued.run_id.slice(0, 8)} queued with ${queued.selected_case_count} cases.`);
      setSelectedRunId(queued.run_id);
      await loadDashboard();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Evaluation could not be started.");
    } finally {
      setQueueing(false);
    }
  }

  async function queueRagRun() {
    if (!adminToken || ragQueueing) return;
    if (!window.confirm(
      `Run all 40 cases using ${ragMode} retrieval and ${ragEmbeddingModel}?`,
    )) {
      return;
    }
    setRagQueueing(true);
    setError("");
    setNotice("");
    try {
      const queued = await adminQueueRagEvaluation(adminToken, {
        limit: 40,
        fail_fast: false,
        retrieval_mode: ragMode,
        embedding_model: ragEmbeddingModel,
      });
      setNotice(`RAG run ${queued.run_id.slice(0, 8)} queued with ${queued.selected_case_count} cases.`);
      await loadDashboard();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "RAG evaluation could not be started.");
    } finally {
      setRagQueueing(false);
    }
  }

  const latest = dashboard?.latest_run;
  const latestPassRate = latest?.pass_rate_percent;
  const latestScore = Math.max(0, Math.min(latestPassRate ?? 0, 100));

  return (
    <AppShell title="Agent Evaluations">
      <div className="evalDashboard">
        <section className="evalHeader">
          <div>
            <p>Quality operations</p>
            <h1>Agent reliability</h1>
            <span>
              Monitor capability, safety, latency, and cost across persisted evaluation runs.
            </span>
          </div>
          <div className="evalHeaderActions">
            <span className={adminToken ? "evalAccessAdmin" : "evalAccessPublic"}>
              {adminToken ? "Admin controls enabled" : "View-only mode"}
            </span>
            <button type="button" onClick={() => void loadDashboard()} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh data"}
            </button>
          </div>
        </section>

        {error ? <div className="evalNotice evalNoticeError">{error}</div> : null}
        {notice ? <div className="evalNotice evalNoticeSuccess">{notice}</div> : null}

        <section className="evalScoreBand" aria-label="Evaluation summary">
          <div className="evalScoreLead">
            <div
              className="evalScoreRing"
              style={{
                background: `conic-gradient(#0f9f8f ${latestScore}%, #e8eef3 ${latestScore}% 100%)`,
              }}
            >
              <div>
                <strong>{latestPassRate?.toFixed(0) ?? "--"}%</strong>
                <span>pass rate</span>
              </div>
            </div>
            <div>
              <span className={`evalHealth evalHealth-${latest ? runTone(latest) : "running"}`}>
                {latest ? latest.status.replaceAll("_", " ") : "No run"}
              </span>
              <h2>{latest ? "Latest evaluation is ready" : "No evaluation data yet"}</h2>
              <p>
                {latest
                  ? `${latest.passed_case_count} passed of ${latest.completed_case_count} completed cases using ${latest.model}.`
                  : "Run the critical smoke suite to establish a baseline."}
              </p>
            </div>
          </div>
          <div className="evalMetricStrip">
            <div>
              <span>Historical average</span>
              <strong>{dashboard?.average_pass_rate_percent.toFixed(1) ?? "0.0"}%</strong>
              <small>{dashboard?.completed_runs ?? 0} completed runs</small>
            </div>
            <div>
              <span>P95 latency</span>
              <strong>{latest?.p95_latency_ms ? `${latest.p95_latency_ms} ms` : "N/A"}</strong>
              <small>Latest completed run</small>
            </div>
            <div>
              <span>Token usage</span>
              <strong>{latest?.total_tokens.toLocaleString() ?? "N/A"}</strong>
              <small>Latest completed run</small>
            </div>
            <div>
              <span>Known cost</span>
              <strong>{formatCost(dashboard?.total_known_cost_usd)}</strong>
              <small>All persisted runs</small>
            </div>
          </div>
        </section>

        <section className="evalSuiteSection" aria-label="Evaluation suites">
          <div className="evalSuiteHeading">
            <div>
              <p>Evaluation suites</p>
              <h2>Production quality gates</h2>
            </div>
            <div className="evalSuiteIndex" aria-label="Available evaluation suites">
              <span className="isActive">RAG retrieval</span>
              <span>Answer quality</span>
              <span>Safety</span>
              <span>Tool use</span>
            </div>
          </div>

          <article className="evalRagSuite">
            <div className="evalRagSuiteHeader">
              <div>
                <span className={`evalRagGate evalRagGate-${dashboard?.rag_latest?.quality_gate_status.toLowerCase() ?? "pending"}`}>
                  {dashboard?.rag_latest?.quality_gate_status ?? "No baseline"}
                </span>
                <h3>RAG retrieval and context quality</h3>
                <p>
                  {dashboard?.rag_latest
                    ? `${dashboard.rag_latest.completed_case_count} ${dashboard.rag_latest.retrieval_mode} cases completed with ${dashboard.rag_latest.embedding_model} ${formatDate(dashboard.rag_latest.finished_at)}.`
                    : "No persisted RAG evaluation has completed yet."}
                </p>
              </div>
              <div className="evalRagActions">
                <label>
                  <span>Embedding</span>
                  <select
                    value={ragEmbeddingModel}
                    onChange={(event) => setRagEmbeddingModel(
                      event.target.value as RagEvaluationRunRequest["embedding_model"],
                    )}
                  >
                    <option value="BAAI/bge-small-en-v1.5">BAAI BGE Small (local)</option>
                    <option value="text-embedding-3-small">OpenAI Embedding 3 Small</option>
                  </select>
                </label>
                <label>
                  <span>Retrieval</span>
                  <select
                    value={ragMode}
                    onChange={(event) => setRagMode(
                      event.target.value as RagEvaluationRunRequest["retrieval_mode"],
                    )}
                  >
                    <option value="hybrid">Hybrid</option>
                    <option value="vector">Vector</option>
                    <option value="keyword">Keyword</option>
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => void queueRagRun()}
                  disabled={!adminToken || ragQueueing || dashboard?.rag_latest?.status === "running"}
                >
                  {ragQueueing ? "Queueing..." : "Run RAG suite"}
                </button>
              </div>
            </div>

            <div className="evalRagMetrics">
              <section>
                <div><strong>Retrieval</strong><span>Ranking and source discovery</span></div>
                <dl>
                  <div><dt>Hit@1</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.hit_at_1_percent.toFixed(1)}%` : "--"}</dd></div>
                  <div><dt>Hit@3</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.hit_at_3_percent.toFixed(1)}%` : "--"}</dd></div>
                  <div><dt>Passage Recall@K</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.mean_passage_recall_percent.toFixed(1)}%` : "--"}</dd></div>
                  <div><dt>Precision@K</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.mean_precision_at_k_percent.toFixed(1)}%` : "--"}</dd></div>
                  <div><dt>MRR</dt><dd>{dashboard?.rag_latest?.mean_reciprocal_rank.toFixed(3) ?? "--"}</dd></div>
                  <div><dt>nDCG@K</dt><dd>{dashboard?.rag_latest?.mean_ndcg_at_k.toFixed(3) ?? "--"}</dd></div>
                  <div><dt>MAP@K</dt><dd>{dashboard?.rag_latest?.mean_average_precision.toFixed(3) ?? "--"}</dd></div>
                  <div><dt>Retrieval F1</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.mean_retrieval_f1_percent.toFixed(1)}%` : "--"}</dd></div>
                </dl>
              </section>

              <section>
                <div><strong>Context</strong><span>Coverage and retrieval noise</span></div>
                <dl>
                  <div><dt>Concept recall</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.mean_content_term_recall_percent.toFixed(1)}%` : "--"}</dd></div>
                  <div><dt>Unique chunks</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.mean_unique_chunk_ratio_percent.toFixed(1)}%` : "--"}</dd></div>
                  <div><dt>Redundancy</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.mean_redundancy_percent.toFixed(1)}%` : "--"}</dd></div>
                  <div><dt>Relevance score</dt><dd>{dashboard?.rag_latest?.mean_similarity_score.toFixed(3) ?? "--"}</dd></div>
                  <div><dt>Context size</dt><dd>{dashboard?.rag_latest ? dashboard.rag_latest.mean_context_character_count.toLocaleString() : "--"}</dd></div>
                  <div><dt>Pass rate</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.pass_rate_percent.toFixed(1)}%` : "--"}</dd></div>
                </dl>
              </section>

              <section>
                <div><strong>Runtime</strong><span>Reliability and latency</span></div>
                <dl>
                  <div><dt>Error-free</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.error_free_rate_percent.toFixed(1)}%` : "--"}</dd></div>
                  <div><dt>Average</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.average_latency_ms} ms` : "--"}</dd></div>
                  <div><dt>P50</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.p50_latency_ms} ms` : "--"}</dd></div>
                  <div><dt>P95</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.p95_latency_ms} ms` : "--"}</dd></div>
                  <div><dt>P99</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.p99_latency_ms} ms` : "--"}</dd></div>
                  <div><dt>Throughput</dt><dd>{dashboard?.rag_latest ? `${dashboard.rag_latest.throughput_cases_per_second.toFixed(2)}/s` : "--"}</dd></div>
                </dl>
              </section>

              <section className="evalRagGeneration">
                <div><strong>Generation</strong><span>End-to-end answer evaluation</span></div>
                <dl>
                  <div><dt>Faithfulness</dt><dd>Not measured</dd></div>
                  <div><dt>Answer relevance</dt><dd>Not measured</dd></div>
                  <div><dt>Citation precision</dt><dd>Not measured</dd></div>
                  <div><dt>Citation recall</dt><dd>Not measured</dd></div>
                  <div><dt>Abstention</dt><dd>Not measured</dd></div>
                </dl>
              </section>
            </div>

            <div className="evalRagDepth">
              <div>
                <strong>Retrieval depth</strong>
                <span>Quality as context grows from K=1 to K=5</span>
              </div>
              <div className="evalRagDepthTable">
                <table>
                  <thead>
                    <tr>
                      <th>K</th>
                      <th>Hit</th>
                      <th>Precision</th>
                      <th>Passage recall</th>
                      <th>F1</th>
                      <th>nDCG</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[1, 2, 3, 4, 5].map((k) => {
                      const metrics = dashboard?.rag_latest?.metrics_by_k[String(k)];
                      return (
                        <tr key={k}>
                          <th>{k}</th>
                          <td>{metrics ? `${metrics.hit_percent.toFixed(1)}%` : "--"}</td>
                          <td>{metrics ? `${metrics.mean_precision_percent.toFixed(1)}%` : "--"}</td>
                          <td>{metrics ? `${metrics.mean_passage_recall_percent.toFixed(1)}%` : "--"}</td>
                          <td>{metrics ? `${metrics.mean_retrieval_f1_percent.toFixed(1)}%` : "--"}</td>
                          <td>{metrics ? metrics.mean_ndcg.toFixed(3) : "--"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </article>
        </section>

        <section className="evalPrimaryGrid">
          <article className="evalPanel evalPerformancePanel">
            <div className="evalPanelHeader">
              <div>
                <p>Performance</p>
                <h2>Reliability and capability coverage</h2>
              </div>
              <span>Last {trendRuns.length} runs</span>
            </div>
            <div className="evalPerformanceBody">
              <section className="evalTrendSection">
                <div className="evalSectionLabel">
                  <strong>Pass rate by run</strong>
                  <span>Higher is better</span>
                </div>
                <div className={`evalTrendChart${trendRuns.length === 1 ? " evalTrendChartSingle" : ""}`}>
                  {trendRuns.length ? (
                    trendRuns.map((run) => (
                      <button
                        type="button"
                        key={run.run_id}
                        onClick={() => void selectRun(run.run_id)}
                        title={`${run.pass_rate_percent?.toFixed(1)}% - ${formatDate(run.finished_at)}`}
                      >
                        <span>{run.pass_rate_percent?.toFixed(0)}%</span>
                        <i style={{ height: `${Math.max(run.pass_rate_percent ?? 0, 4)}%` }} />
                        <small>{run.run_id.slice(0, 4)}</small>
                      </button>
                    ))
                  ) : (
                    <div className="evalEmpty">Run a benchmark to establish a trend.</div>
                  )}
                </div>
              </section>
              <section className="evalCategorySection">
                <div className="evalSectionLabel">
                  <strong>Capability coverage</strong>
                  <span>{dashboard?.categories.length ?? 0} categories</span>
                </div>
                <div className="evalCategoryList">
                  {dashboard?.categories.map((category) => (
                    <div key={category.category}>
                      <div>
                        <strong>{formatCategory(category.category)}</strong>
                        <span>{category.passed} of {category.total}</span>
                      </div>
                      <div className="evalProgress">
                        <i style={{ width: `${category.pass_rate_percent}%` }} />
                      </div>
                      <b>{category.pass_rate_percent.toFixed(0)}%</b>
                    </div>
                  ))}
                  {!dashboard?.categories.length ? (
                    <div className="evalEmpty">Category scores appear after the first run.</div>
                  ) : null}
                </div>
              </section>
            </div>
          </article>

          <article className="evalPanel evalRunControl">
            <div className="evalPanelHeader">
              <div>
                <p>Admin action</p>
                <h2>New evaluation</h2>
              </div>
              <span>{adminToken ? "Ready" : "Locked"}</span>
            </div>
            <form onSubmit={queueRun}>
              <p className="evalControlIntro">
                Run a budget-limited suite against the active agent configuration.
              </p>
              <label>
                Test suite
                <select value={preset} onChange={(event) => setPreset(event.target.value as PresetKey)} disabled={!adminToken || queueing}>
                  {Object.entries(PRESETS).map(([key, value]) => (
                    <option value={key} key={key}>{value.label} - {value.limit} cases</option>
                  ))}
                </select>
              </label>
              <label>
                Model
                <select value={model} onChange={(event) => setModel(event.target.value as EvaluationRunRequest["model"])} disabled={!adminToken || queueing}>
                  <option value="gpt-5.4-nano">GPT-5.4 Nano</option>
                  <option value="gpt-4.1">GPT-4.1</option>
                  <option value="gpt-5.4">GPT-5.4</option>
                </select>
              </label>
              <label>
                Budget limit
                <select value={budget} onChange={(event) => setBudget(Number(event.target.value))} disabled={!adminToken || queueing}>
                  <option value={0.5}>$0.50</option>
                  <option value={1}>$1.00</option>
                  <option value={2}>$2.00</option>
                  <option value={5}>$5.00</option>
                </select>
              </label>
              <button type="submit" disabled={!adminToken || queueing}>
                {queueing ? "Queueing run..." : "Run evaluation"}
              </button>
              {!adminToken ? (
                <p className="evalControlFootnote">
                  <Link href="/admin">Sign in as admin</Link> to unlock execution.
                </p>
              ) : (
                <p className="evalControlFootnote">Runs are budget checked, audited, and persisted.</p>
              )}
            </form>
          </article>
        </section>

        <section className="evalHistoryGrid">
          <article className="evalPanel evalRunHistory">
            <div className="evalPanelHeader">
              <div>
                <p>Execution history</p>
                <h2>Recent runs</h2>
              </div>
              <span>{dashboard?.total_runs ?? 0} total</span>
            </div>
            <div className="evalRunList">
              {dashboard?.runs.map((run) => (
                <button
                  type="button"
                  key={run.run_id}
                  className={selectedRunId === run.run_id ? "isSelected" : ""}
                  onClick={() => void selectRun(run.run_id)}
                >
                  <span className={`evalRunStatus evalRunStatus-${runTone(run)}`} />
                  <div>
                    <strong>{formatCategory(run.status)} <em>{run.model}</em></strong>
                    <small>{formatDate(run.created_at)} - {run.selected_case_count} cases - {run.run_id.slice(0, 8)}</small>
                  </div>
                  <b>{run.pass_rate_percent?.toFixed(0) ?? "--"}%</b>
                </button>
              ))}
            </div>
          </article>

          <article className="evalPanel evalRunDetail">
            <div className="evalPanelHeader">
              <div>
                <p>Run inspection</p>
                <h2>{selectedRun ? `${selectedRun.model} · ${selectedRun.status}` : "Select a run"}</h2>
              </div>
              {selectedRun ? <span>{selectedRun.run_id.slice(0, 8)}</span> : null}
            </div>
            {selectedRun ? (
              <>
                <div className="evalRunFacts">
                  <span><strong>{selectedRun.pass_rate_percent?.toFixed(1) ?? "N/A"}%</strong> pass rate</span>
                  <span><strong>{formatCost(selectedRun.actual_cost_usd)}</strong> cost</span>
                  <span><strong>{selectedRun.total_tokens.toLocaleString()}</strong> tokens</span>
                  <span><strong>{selectedRun.average_latency_ms ? `${selectedRun.average_latency_ms} ms` : "N/A"}</strong> average latency</span>
                </div>
                <div className="evalCaseTable">
                  <div className="evalCaseTableHeader">
                    <span>Case</span><span>Result</span><span>Score</span><span>Tools</span>
                  </div>
                  {selectedRun.cases.map((item) => (
                    <div key={`${item.case_id}-${item.attempt_number}`}>
                      <span><strong>{item.case_id}</strong><small>{formatCategory(item.category)}</small></span>
                      <span className={`evalCaseResult ${item.status === "error" ? "error" : item.passed ? "pass" : "fail"}`}>
                        {item.status === "error" ? "Error" : item.passed ? "Pass" : "Fail"}
                      </span>
                      <span>{item.score_percent?.toFixed(0) ?? "--"}%</span>
                      <span>{item.tools_used.length ? item.tools_used.join(", ") : "None"}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="evalEmpty">No evaluation run selected.</div>
            )}
          </article>
        </section>
      </div>
    </AppShell>
  );
}
