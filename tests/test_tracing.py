"""Spans for LLM calls, MCP tool calls and runs; JSONL export; the launcher's patches."""

import json

import pytest
from mcp.client import Client
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from sec_mcp_agent.agent.llm import ChatReply, ScriptedChat, ToolCallRequest

from evalobs.tracing import TracedChatModel, instrument_mcp, langfuse_env, run_span, span_to_dict

pytestmark = pytest.mark.anyio


def toy_server() -> MCPServer:
    server = MCPServer("toy")

    @server.tool()
    def double(x: int) -> int:
        """Double a number."""
        if x < 0:
            raise ToolError("negative")
        return 2 * x

    return server


def test_llm_call_span_has_genai_attributes(spans):
    llm = TracedChatModel(
        ScriptedChat(
            [
                ChatReply(
                    content="{}",
                    prompt_tokens=120,
                    completion_tokens=30,
                    tool_calls=[ToolCallRequest("x", {})],
                )
            ]
        )
    )
    llm.chat([{"role": "user", "content": "hi"}], tools=[{}, {}], schema={"title": "Report"})
    [s] = spans.get_finished_spans()
    a = s.attributes
    assert s.name == "chat scripted"
    assert a["gen_ai.usage.input_tokens"] == 120 and a["gen_ai.usage.output_tokens"] == 30
    assert a["gen_ai.request.model"] == "scripted" and a["llm.output_schema"] == "Report"
    assert a["llm.tools_offered"] == 2 and a["llm.tool_calls"] == 1


def test_llm_error_is_recorded_and_reraised(spans):
    llm = TracedChatModel(ScriptedChat([]))  # raises: no replies left
    with pytest.raises(AssertionError):
        llm.chat([{"role": "user", "content": "hi"}])
    [s] = spans.get_finished_spans()
    assert s.status.status_code.name == "ERROR" and "AssertionError" in s.status.description


async def test_mcp_tool_calls_become_spans_including_tool_errors(spans):
    instrument_mcp()
    instrument_mcp()  # idempotent
    async with Client(toy_server()) as client:
        with run_span("agent.ask", question="q1"):
            assert (await client.call_tool("double", {"x": 2})).structured_content["result"] == 4
            assert (await client.call_tool("double", {"x": -1})).is_error
    finished = spans.get_finished_spans()
    ours = [s for s in finished if s.name.startswith(("tool ", "agent."))]
    assert [s.name for s in ours] == ["tool double", "tool double", "agent.ask"]
    ok, bad, root = ours
    assert ok.attributes["mcp.is_error"] is False
    assert json.loads(ok.attributes["mcp.arguments"]) == {"x": 2}
    assert bad.status.status_code.name == "ERROR" and "negative" in bad.status.description
    assert ok.parent.span_id == root.context.span_id  # tool spans nest under the run
    # The MCP SDK propagates the trace context, so the server's own span nests under ours.
    server = [s for s in finished if s.name == "tools/call double"]
    assert server and server[0].parent.span_id == ok.context.span_id


def test_span_to_dict_and_jsonl_export(spans):
    from conftest import JSONL_PATH

    with run_span("graph.investigate", transaction_id="t-1", ignored=None, nested={"a": 1}):
        pass
    [s] = spans.get_finished_spans()
    d = span_to_dict(s)
    assert d["name"] == "graph.investigate" and d["service"] == "tests" and d["parent_id"] is None
    assert d["attributes"] == {"transaction_id": "t-1", "nested": '{"a": 1}'}
    last = json.loads(JSONL_PATH.read_text().splitlines()[-1])
    assert last["span_id"] == d["span_id"]


def test_langfuse_env_uses_basic_auth_on_the_otel_endpoint():
    env = langfuse_env("http://localhost:3000/", "pk-lf-1", "sk-lf-1")
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://localhost:3000/api/public/otel"
    assert env["OTEL_EXPORTER_OTLP_HEADERS"] == "Authorization=Basic cGstbGYtMTpzay1sZi0x"


def test_launcher_patches_ollama_chat_without_calling_ollama(spans, monkeypatch):
    from sec_mcp_agent.agent.llm import OllamaChat

    from evalobs import instrument_run

    def fake_chat(self, messages, tools=None, schema=None):
        return ChatReply(content="ok", prompt_tokens=7, completion_tokens=3)

    monkeypatch.setattr(OllamaChat, "chat", fake_chat)
    instrument_run.patch_llm()
    model = OllamaChat.__new__(OllamaChat)  # skip __init__: no Ollama client needed
    model.name = "qwen2.5:3b"
    assert model.chat([{"role": "user", "content": "x"}]).content == "ok"
    [s] = spans.get_finished_spans()
    assert s.attributes["gen_ai.request.model"] == "qwen2.5:3b"
    assert s.attributes["gen_ai.usage.input_tokens"] == 7
