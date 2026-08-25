"use client";

import Image from "next/image";

import type { ChatMessage as Msg } from "../lib/types";
import MarkdownContent from "./MarkdownContent";
import VoicePlaybackButton from "./VoicePlaybackButton";

function formatTime(ms: number) {
  const d = new Date(ms);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatCost(cost?: number | null) {
  if (cost == null) return "n/a";
  return `$${cost.toFixed(6)}`;
}

function formatSeconds(ms: number) {
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatTraceModel(model?: string | null) {
  return model?.trim() || "N/A";
}

function formatTracePayload(value: unknown) {
  if (value == null || value === "") return "No output captured";
  if (typeof value === "string") {
    try {
      return JSON.stringify(JSON.parse(value), null, 2);
    } catch {
      return value;
    }
  }
  return JSON.stringify(value, null, 2);
}

function toAbsoluteUrl(path?: string | null) {
  if (!path) return null;
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  return `${apiBase}${path}`;
}

export default function ChatMessageView({ message }: { message: Msg }) {
  const isUser = message.role === "user";
  const trace = !isUser ? message.trace : undefined;
  const report = !isUser ? message.report : undefined;
  const chartArtifacts =
    trace?.tool_calls.flatMap((tool) =>
      (tool.artifacts ?? []).map((artifact) => ({
        ...artifact,
        toolName: tool.name,
      }))
    ).filter((artifact) => artifact.type === "chart") ?? [];
  const htmlAsset = report?.assets.find((asset) => asset.type === "html");
  const pdfAsset = report?.assets.find((asset) => asset.type === "pdf");
  const otherAssets =
    report?.assets.filter((asset) => asset.type !== "html" && asset.type !== "pdf") ?? [];
  const htmlViewUrl = toAbsoluteUrl(htmlAsset?.view_url);
  const htmlDownloadUrl = toAbsoluteUrl(htmlAsset?.download_url);
  const pdfDownloadUrl = toAbsoluteUrl(pdfAsset?.download_url);

  return (
    <div className={`msgRow ${isUser ? "msgRowUser" : "msgRowAssistant"}`}>
      <div className={`bubble ${isUser ? "bubbleUser" : "bubbleAssistant"}`}>
        <div className="bubbleContent">
          <MarkdownContent content={message.content} />
        </div>
        {!isUser && (
          <div className="messageActions">
            <VoicePlaybackButton text={message.content} />
          </div>
        )}
        {report && (
          <div className="reportCard">
            <div className="reportCardHeader">
              <div>
                <div className="reportCardEyebrow">Generated Report</div>
                <div className="reportCardTitle">{report.title}</div>
              </div>
              <div className="reportCardMeta">{new Date(report.created_at).toLocaleString()}</div>
            </div>
            <p className="reportCardSummary">{report.summary}</p>
            {htmlViewUrl && (
              <details className="reportPreview">
                <summary>Preview report</summary>
                <div className="reportPreviewFrameWrap">
                  <iframe
                    className="reportPreviewFrame"
                    src={htmlViewUrl}
                    title={`${report.title} preview`}
                  />
                </div>
              </details>
            )}
            <div className="reportLinkRow">
              {htmlAsset && (
                <div className="reportLinkGroup" key={`${report.report_id}-${htmlAsset.filename}`}>
                  <span className="reportLinkLabel">{htmlAsset.label}</span>
                  <div className="reportLinkActions">
                    {htmlViewUrl && (
                      <a href={htmlViewUrl} target="_blank" rel="noreferrer">
                        Open report
                      </a>
                    )}
                    {htmlDownloadUrl && (
                      <a href={htmlDownloadUrl} target="_blank" rel="noreferrer">
                        Download
                      </a>
                    )}
                  </div>
                </div>
              )}
              {pdfAsset && (
                <div className="reportLinkGroup" key={`${report.report_id}-${pdfAsset.filename}`}>
                  <span className="reportLinkLabel">{pdfAsset.label}</span>
                  <div className="reportLinkActions">
                    {pdfDownloadUrl && (
                      <a href={pdfDownloadUrl} target="_blank" rel="noreferrer">
                        Download PDF
                      </a>
                    )}
                  </div>
                </div>
              )}
              {otherAssets.map((asset) => {
                const viewUrl = toAbsoluteUrl(asset.view_url);
                const downloadUrl = toAbsoluteUrl(asset.download_url);
                return (
                  <div className="reportLinkGroup" key={`${report.report_id}-${asset.filename}`}>
                    <span className="reportLinkLabel">{asset.label}</span>
                    <div className="reportLinkActions">
                      {viewUrl && (
                        <a href={viewUrl} target="_blank" rel="noreferrer">
                          View
                        </a>
                      )}
                      {downloadUrl && (
                        <a href={downloadUrl} target="_blank" rel="noreferrer">
                          Download
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {chartArtifacts.length > 0 && (
          <div className="chartCard">
            <div className="chartCardHeader">
              <div>
                <div className="chartCardEyebrow">Generated Charts</div>
                <div className="chartCardTitle">
                  {chartArtifacts.length === 1
                    ? "1 chart created from Python analysis"
                    : `${chartArtifacts.length} charts created from Python analysis`}
                </div>
              </div>
            </div>
            <div className="chartCardGrid">
              {chartArtifacts.map((artifact) => {
                const viewUrl = toAbsoluteUrl(artifact.view_url);
                const downloadUrl = toAbsoluteUrl(artifact.download_url);
                return (
                  <div className="chartArtifactCard" key={`${artifact.toolName}-${artifact.filename}`}>
                    <div className="chartArtifactHeader">
                      <div>
                        <div className="chartArtifactLabel">{artifact.label}</div>
                        <div className="chartArtifactMeta">{artifact.toolName}</div>
                      </div>
                      <div className="chartArtifactActions">
                        {viewUrl && (
                          <a href={viewUrl} target="_blank" rel="noreferrer">
                            View
                          </a>
                        )}
                        {downloadUrl && (
                          <a href={downloadUrl} target="_blank" rel="noreferrer">
                            Download
                          </a>
                        )}
                      </div>
                    </div>
                    {viewUrl && (
                      <Image
                        className="chartArtifactPreview"
                        src={viewUrl}
                        alt={artifact.label}
                        width={960}
                        height={540}
                        unoptimized
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {trace && (
          <details className="tracePanel">
            <summary>
              <span className="traceSummaryTitle">Agent trace</span>
              <span className="traceSummaryMeta">
                {trace.tool_calls.length} {trace.tool_calls.length === 1 ? "step" : "steps"} ·{" "}
                {formatSeconds(trace.latency_ms)}
              </span>
            </summary>
            <div className="traceGrid">
              <div><span>Model</span><strong>{formatTraceModel(trace.model)}</strong></div>
              <div><span>Guardrail</span><strong>{trace.guardrail_status}</strong></div>
              <div><span>Trace ID</span><strong>{trace.trace_id.slice(0, 8)}</strong></div>
              <div><span>Input tokens</span><strong>{trace.token_usage?.input_tokens ?? 0}</strong></div>
              <div><span>Output tokens</span><strong>{trace.token_usage?.output_tokens ?? 0}</strong></div>
              <div><span>Total tokens</span><strong>{trace.token_usage?.total_tokens ?? 0}</strong></div>
              <div><span>Input cost</span><strong>{formatCost(trace.token_usage?.estimated_input_cost_usd)}</strong></div>
              <div><span>Output cost</span><strong>{formatCost(trace.token_usage?.estimated_output_cost_usd)}</strong></div>
              <div><span>Total cost</span><strong>{formatCost(trace.token_usage?.estimated_total_cost_usd)}</strong></div>
            </div>
            {trace.tool_calls.length > 0 && (
              <div className="toolTraceList">
                {trace.tool_calls.map((tool, index) => (
                  <details className="toolTrace" key={`${tool.name}-${index}`} open>
                    <summary className="toolTraceHeader">
                      <span className="toolTraceStep">Step {String(index + 1).padStart(2, "0")}</span>
                      <span className="toolTraceName">{tool.name}</span>
                      <span className="toolTraceStatus">Completed</span>
                    </summary>
                    <div className="toolTraceIo">
                      <section className="toolTraceBlock">
                        <div className="toolTraceLabel">Input</div>
                        <pre>{formatTracePayload(tool.args)}</pre>
                      </section>
                      <section className="toolTraceBlock">
                        <div className="toolTraceLabel">Output</div>
                        <pre>{formatTracePayload(tool.result ?? tool.result_preview)}</pre>
                      </section>
                    </div>
                  </details>
                ))}
              </div>
            )}
          </details>
        )}
        <div className="bubbleMeta">
          {isUser ? "You" : "ProductAI"} - {formatTime(message.createdAt)}
        </div>
      </div>
    </div>
  );
}
