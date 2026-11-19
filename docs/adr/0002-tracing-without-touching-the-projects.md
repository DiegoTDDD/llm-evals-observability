# ADR 0002: Trace the projects without changing them

**Status:** accepted

## Context
Both agent projects should stay free of observability code, and their eval scripts already exist.

## Decision
`evalobs.instrument_run` works like `opentelemetry-instrument`: it sets up a tracer provider,
patches the entry points (the Ollama chat call, `mcp.client.Client.call_tool`, `Agent.ask`,
`Investigator.investigate`, `single_agent`) and runs the project's eval script unchanged.
- LLM spans use the OpenTelemetry GenAI attributes (`gen_ai.request.model`,
  `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`), which Langfuse maps to generations.
- Tool spans record the arguments the model sent and mark tool errors as span errors.
- The MCP SDK 2.x propagates trace context through `_meta` and opens its own server spans, so
  the server's work nests under the client's tool span: one trace from question to tool to answer.

## Consequences
- No dependency from the projects on this repository.
- The patch points are part of the contract: a rename in a project breaks tracing, which the
  live workflow notices (the Langfuse check expects traces).
