import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from langchain.tools import tool
from mcp.types import LATEST_PROTOCOL_VERSION

from app.rag.constants import DEFAULT_RETRIEVAL_TOP_K

BACKEND_DIR = Path(__file__).resolve().parents[2]
LOG_PREVIEW_LIMIT = 500
MCP_TIMEOUT_SECONDS = 200


def _preview(value: Any, limit: int = LOG_PREVIEW_LIMIT) -> str:
    try:
        text = json.dumps(value, ensure_ascii=True, default=str)
    except TypeError:
        text = str(value)

    return text if len(text) <= limit else f"{text[:limit]}..."


def _normalize_mcp_result(result: dict[str, Any]) -> Any:
    content = result.get("content") or []
    if len(content) == 1 and content[0].get("type") == "text":
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    return [
        item if isinstance(item, dict) else str(item)
        for item in content
    ]


class _MCPStdioClient:
    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self.messages: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self.lock = threading.RLock()
        self.next_request_id = 100
        self.reader_thread: threading.Thread | None = None

    def start(self) -> None:
        with self.lock:
            if self.process and self.process.poll() is None:
                return

            self.close()
            while not self.messages.empty():
                self.messages.get_nowait()

            self.process = subprocess.Popen(
                [sys.executable, "-m", "app.mcp.server"],
                cwd=str(BACKEND_DIR),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
            self.reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
            self.reader_thread.start()

            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": LATEST_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {
                        "name": "tracestock-agent",
                        "version": "0.1.0",
                    },
                },
            }
            self.process.stdin.write(f"{json.dumps(message, ensure_ascii=True)}\n")
            self.process.stdin.flush()

            try:
                response = self.messages.get(timeout=MCP_TIMEOUT_SECONDS)
                while response is not None and response.get("id") != 1:
                    response = self.messages.get(timeout=MCP_TIMEOUT_SECONDS)
            except queue.Empty as exc:
                self.close()
                raise TimeoutError(
                    f"MCP request 1 timed out after {MCP_TIMEOUT_SECONDS}s."
                ) from exc

            if response is None:
                raise RuntimeError("MCP server process exited before responding.")

            if "error" in response:
                raise RuntimeError(f"MCP initialize failed: {response['error']}")

            message = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            self.process.stdin.write(f"{json.dumps(message, ensure_ascii=True)}\n")
            self.process.stdin.flush()

    def close(self) -> None:
        with self.lock:
            process = self.process
            self.process = None
            if not process:
                return

            if process.stdin:
                try:
                    process.stdin.close()
                except OSError:
                    pass

            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        with self.lock:
            self.start()
            request_id = self.next_request_id
            self.next_request_id += 1

            message = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments,
                },
            }
            self.process.stdin.write(f"{json.dumps(message, ensure_ascii=True)}\n")
            self.process.stdin.flush()

            try:
                response = self.messages.get(timeout=MCP_TIMEOUT_SECONDS)
                while response is not None and response.get("id") != request_id:
                    response = self.messages.get(timeout=MCP_TIMEOUT_SECONDS)
            except queue.Empty as exc:
                self.close()
                raise TimeoutError(
                    f"MCP request {request_id} timed out after {MCP_TIMEOUT_SECONDS}s."
                ) from exc

            if response is None:
                raise RuntimeError("MCP server process exited before responding.")

        if "error" in response:
            raise RuntimeError(f"MCP tool {name} failed: {response['error']}")

        return _normalize_mcp_result(response.get("result") or {})

    def _read_stdout(self) -> None:
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            if not line.strip():
                continue
            try:
                self.messages.put(json.loads(line))
            except json.JSONDecodeError:
                continue

        self.messages.put(None)


_mcp_client = _MCPStdioClient()


def start_mcp_server() -> None:
    print("[MCP] Starting persistent MCP server")
    _mcp_client.start()
    print("[MCP] Persistent MCP server is ready")


def close_mcp_server() -> None:
    print("[MCP] Closing persistent MCP server")
    _mcp_client.close()


def _call_mcp_tool(name: str, arguments: dict[str, Any]) -> Any:
    return _mcp_client.call_tool(name, arguments)


def _call_mcp_tool_json(name: str, arguments: dict[str, Any]) -> str:
    started = time.perf_counter()
    print(f"[MCP] Calling tool={name} args={_preview(arguments)}")
    try:
        result = _call_mcp_tool(name, arguments)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        print(f"[MCP] Tool failed tool={name} latency_ms={latency_ms} error={exc!r}")
        raise

    payload = json.dumps(result, ensure_ascii=True)
    latency_ms = int((time.perf_counter() - started) * 1000)
    print(f"[MCP] Tool responded tool={name} latency_ms={latency_ms} preview={_preview(result)}")
    return payload


@tool
def tracestock_mcp_status() -> str:
    """Check that the TraceStock MCP server is reachable and return the exposed MCP tools."""
    return _call_mcp_tool_json("tracestock_mcp_status", {})


@tool
def get_inventory_schema(include_row_counts: bool = False) -> str:
    """
    Inspect TraceStock database tables, columns, foreign keys, indexes, and optional row counts
    through the TraceStock MCP server.
    """
    return _call_mcp_tool_json(
        "get_inventory_schema",
        {"include_row_counts": include_row_counts},
    )


@tool
def run_readonly_inventory_sql(query: str, max_rows: int = 100) -> str:
    """
    Execute one guarded read-only SELECT/WITH query through the TraceStock MCP server.
    Write operations and DDL are blocked by the MCP server.
    """
    return _call_mcp_tool_json(
        "run_readonly_inventory_sql",
        {"query": query, "max_rows": max_rows},
    )


@tool
def search_company_documents(
    query: str,
    top_k: int = DEFAULT_RETRIEVAL_TOP_K,
    retrieval_mode: str = "hybrid",
) -> str:
    """
    Search indexed company policies, SOPs, supplier rules, return policies, and warehouse docs
    through the TraceStock MCP server.
    """
    return _call_mcp_tool_json(
        "search_company_documents",
        {
            "query": query,
            "top_k": top_k,
            "retrieval_mode": retrieval_mode,
        },
    )


@tool
def get_weather_forecast(location: str, days: int = 7, units: str = "metric") -> str:
    """
    Get current and daily weather forecast for a city/location through the MCP server.

    Use this for weather-aware product demand, branch planning, seasonal recommendations,
    and questions about heat, cold, rain, wind, or UV impact.
    """
    return _call_mcp_tool_json(
        "get_weather_forecast",
        {"location": location, "days": days, "units": units},
    )
