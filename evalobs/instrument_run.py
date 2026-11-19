"""Run another project's eval script with tracing switched on, without changing that project.

    python -m evalobs.instrument_run --service sec-mcp-agent --jsonl reports/spans.jsonl --otlp \
        -- ../sec-mcp-agent/scripts/run_eval.py --model qwen2.5:3b

Like opentelemetry-instrument, it patches entry points before the script imports them:
    sec_mcp_agent.agent.llm.OllamaChat.chat       -> one span per LLM call (GenAI attributes)
    mcp.client.Client.call_tool                   -> one span per MCP tool call
    sec_mcp_agent.agent.agent.Agent.ask           -> one root span per question
    fraud_agents.graph.Investigator.investigate   -> one root span per investigation
    fraud_agents.graph.single_agent               -> one root span per single-agent baseline
"""

from __future__ import annotations

import argparse
import functools
import runpy
import sys
from pathlib import Path
from typing import Any

from evalobs.tracing import TracedChatModel, instrument_mcp, run_span, setup_tracing


def patch_llm() -> None:
    from sec_mcp_agent.agent.llm import OllamaChat

    original = OllamaChat.chat

    def chat(
        self: Any, messages: list, tools: list | None = None, schema: dict | None = None
    ) -> Any:
        class _Inner:
            name = self.name

            @staticmethod
            def chat(m: list, tools: list | None = None, schema: dict | None = None) -> Any:
                return original(self, m, tools=tools, schema=schema)

        return TracedChatModel(_Inner()).chat(messages, tools=tools, schema=schema)

    OllamaChat.chat = chat  # type: ignore[method-assign]


def patch_roots() -> None:
    try:
        from sec_mcp_agent.agent.agent import Agent

        ask = Agent.ask

        @functools.wraps(ask)
        async def traced_ask(self: Any, question: str) -> Any:
            with run_span("agent.ask", question=question[:300]) as span:
                answer = await ask(self, question)
                span.set_attributes(
                    {
                        "agent.grounded": answer.grounded,
                        "agent.citations": len(answer.citations),
                        "agent.tool_calls": len(answer.tool_calls),
                    }
                )
                return answer

        Agent.ask = traced_ask  # type: ignore[method-assign]
    except ImportError:
        pass
    try:
        import fraud_agents.graph as graph

        investigate = graph.Investigator.investigate

        @functools.wraps(investigate)
        async def traced_investigate(self: Any, transaction_id: str) -> Any:
            with run_span("graph.investigate", transaction_id=transaction_id) as span:
                result = await investigate(self, transaction_id)
                span.set_attributes(
                    {
                        "graph.rounds": result.rounds,
                        "graph.approved": result.approved,
                        "graph.verdict": result.report.verdict,
                        "graph.fraud_type": result.report.fraud_type,
                    }
                )
                return result

        graph.Investigator.investigate = traced_investigate  # type: ignore[method-assign]
        single = graph.single_agent

        @functools.wraps(single)
        async def traced_single(*args: Any, **kwargs: Any) -> Any:
            with run_span("single_agent.investigate"):
                return await single(*args, **kwargs)

        graph.single_agent = traced_single
    except ImportError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", required=True)
    parser.add_argument("--jsonl", type=Path)
    parser.add_argument("--otlp", action="store_true", help="Also export to OTEL_EXPORTER_OTLP_*")
    parser.add_argument("script", type=Path)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()
    provider = setup_tracing(ns.service, jsonl=ns.jsonl, otlp=ns.otlp)
    instrument_mcp()
    patch_llm()
    patch_roots()
    script = ns.script.resolve()
    sys.path.insert(0, str(script.parent.parent))  # the project root, as the script expects
    sys.argv = [str(script), *[a for a in ns.args if a != "--"]]
    try:
        runpy.run_path(str(script), run_name="__main__")
    finally:
        provider.force_flush()
        provider.shutdown()


if __name__ == "__main__":
    main()
