"use client";

import type { ChatMessage as Msg } from "../lib/types";
import MarkdownContent from "./MarkdownContent";

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

export default function ChatMessageView({ message }: { message: Msg }) {
  const isUser = message.role === "user";
  const trace = !isUser ? message.trace : undefined;

  return (
    <div className={`msgRow ${isUser ? "msgRowUser" : "msgRowAssistant"}`}>
      <div className={`bubble ${isUser ? "bubbleUser" : "bubbleAssistant"}`}>
        <div className="bubbleContent">
          <MarkdownContent content={message.content} />
        </div>
        {trace && (
          <details className="tracePanel">
            <summary>
              Agent trace - {trace.tools_used.length || 0} tools -{" "}
              {formatSeconds(trace.latency_ms)}
            </summary>
            <div className="traceGrid">
              <span>Model</span>
              <strong>{trace.model}</strong>
              <span>Guardrail</span>
              <strong>{trace.guardrail_status}</strong>
              <span>Trace ID</span>
              <strong>{trace.trace_id.slice(0, 8)}</strong>
              <span>Input tokens</span>
              <strong>{trace.token_usage?.input_tokens ?? 0}</strong>
              <span>Output tokens</span>
              <strong>{trace.token_usage?.output_tokens ?? 0}</strong>
              <span>Total tokens</span>
              <strong>{trace.token_usage?.total_tokens ?? 0}</strong>
              <span>Input cost</span>
              <strong>{formatCost(trace.token_usage?.estimated_input_cost_usd)}</strong>
              <span>Output cost</span>
              <strong>{formatCost(trace.token_usage?.estimated_output_cost_usd)}</strong>
              <span>Total cost</span>
              <strong>{formatCost(trace.token_usage?.estimated_total_cost_usd)}</strong>
            </div>
            {trace.tool_calls.length > 0 && (
              <div className="toolTraceList">
                {trace.tool_calls.map((tool, index) => (
                  <div className="toolTrace" key={`${tool.name}-${index}`}>
                    <div className="toolTraceName">{tool.name}</div>
                    <pre>{JSON.stringify(tool.args, null, 2)}</pre>
                    {tool.result_preview && <p>{tool.result_preview}</p>}
                  </div>
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
