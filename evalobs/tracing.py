"""OpenTelemetry tracing for the agents: one span per LLM call and per MCP tool call.

    setup_tracing("sec-mcp-agent", jsonl="reports/spans.jsonl", otlp=True)
    llm = TracedChatModel(OllamaChat("qwen2.5:3b"))
    instrument_mcp()        # every mcp.client.Client.call_tool becomes a span
    with run_span("agent.ask", question_id="f01"):
        ...

Spans use the OpenTelemetry GenAI attribute names (gen_ai.*), which Langfuse maps to
generations, tokens and models. The same spans go to a JSONL file that the static dashboard
reads, so the report does not depend on a running Langfuse.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.trace import Status, StatusCode

TRACER_NAME = "evalobs"
_patched = False


class JsonlSpanExporter(SpanExporter):
    """Writes finished spans as one JSON object per line."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            for s in spans:
                f.write(json.dumps(span_to_dict(s), default=str) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:  # nothing to release
        return None


def span_to_dict(s: ReadableSpan) -> dict[str, Any]:
    ctx = s.get_span_context()
    return {
        "name": s.name,
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
        "parent_id": format(s.parent.span_id, "016x") if s.parent else None,
        "start": s.start_time / 1e9,
        "seconds": (s.end_time - s.start_time) / 1e9 if s.end_time else None,
        "status": s.status.status_code.name,
        "error": s.status.description,
        "attributes": dict(s.attributes or {}),
        "service": (s.resource.attributes or {}).get("service.name"),
    }


def setup_tracing(
    service: str, jsonl: str | Path | None = None, otlp: bool = False
) -> TracerProvider:
    """Configure a provider. OTLP goes to OTEL_EXPORTER_OTLP_ENDPOINT with
    OTEL_EXPORTER_OTLP_HEADERS (for Langfuse: its /api/public/otel endpoint and Basic auth)."""
    provider = TracerProvider(resource=Resource.create({"service.name": service}))
    if jsonl:
        provider.add_span_processor(SimpleSpanProcessor(JsonlSpanExporter(jsonl)))
    if otlp:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


def tracer() -> trace.Tracer:
    return trace.get_tracer(TRACER_NAME)


@contextmanager
def run_span(name: str, **attributes: Any) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(name, attributes=_clean(attributes)) as span:
        yield span


class TracedChatModel:
    """Wraps any ChatModel (sec_mcp_agent.agent.llm) and records each call as a span."""

    def __init__(self, inner: Any, system: str = "ollama") -> None:
        self.inner = inner
        self.name = inner.name
        self.system = system

    def chat(
        self, messages: list[dict], tools: list[dict] | None = None, schema: dict | None = None
    ) -> Any:
        attrs = {
            "gen_ai.operation.name": "chat",
            "gen_ai.system": self.system,
            "gen_ai.request.model": self.name,
            "llm.messages": len(messages),
            "llm.tools_offered": len(tools or []),
            "llm.output_schema": (schema or {}).get("title", ""),
        }
        with tracer().start_as_current_span(f"chat {self.name}", attributes=attrs) as span:
            t0 = time.perf_counter()
            try:
                reply = self.inner.chat(messages, tools=tools, schema=schema)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, f"{type(exc).__name__}: {exc}"[:300]))
                raise
            span.set_attributes(
                {
                    "gen_ai.usage.input_tokens": reply.prompt_tokens,
                    "gen_ai.usage.output_tokens": reply.completion_tokens,
                    "llm.tool_calls": len(reply.tool_calls),
                    "llm.seconds": round(time.perf_counter() - t0, 3),
                }
            )
            return reply


def instrument_mcp() -> None:
    """Patch mcp.client.Client.call_tool so every tool call becomes a span (idempotent)."""
    global _patched
    if _patched:
        return
    from mcp.client import Client

    original = Client.call_tool

    async def call_tool(
        self: Any, name: str, arguments: dict | None = None, *args: Any, **kwargs: Any
    ) -> Any:
        attrs = {"mcp.tool": name, "mcp.arguments": json.dumps(arguments or {}, default=str)[:500]}
        with tracer().start_as_current_span(f"tool {name}", attributes=attrs) as span:
            try:
                result = await original(self, name, arguments, *args, **kwargs)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, f"{type(exc).__name__}: {exc}"[:300]))
                raise
            if result.is_error:
                text = " ".join(getattr(c, "text", "") for c in result.content)
                span.set_status(Status(StatusCode.ERROR, text[:300]))
            span.set_attribute("mcp.is_error", bool(result.is_error))
            return result

    Client.call_tool = call_tool  # type: ignore[method-assign]
    _patched = True


def langfuse_env(host: str, public_key: str, secret_key: str) -> dict[str, str]:
    """Environment for the OTLP exporter to send spans to a Langfuse project."""
    import base64

    token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    return {
        "OTEL_EXPORTER_OTLP_ENDPOINT": f"{host.rstrip('/')}/api/public/otel",
        "OTEL_EXPORTER_OTLP_HEADERS": f"Authorization=Basic {token}",
    }


def _clean(attributes: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in attributes.items():
        if v is None:
            continue
        out[k] = v if isinstance(v, str | bool | int | float) else json.dumps(v, default=str)
    return out


def apply_env(env: dict[str, str]) -> None:
    os.environ.update(env)
