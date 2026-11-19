from __future__ import annotations

import sys
from pathlib import Path

import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evalobs.tracing import JsonlSpanExporter  # noqa: E402

# OpenTelemetry accepts one global provider per process: set it once for the whole session.
MEMORY = InMemorySpanExporter()
JSONL_PATH = Path(__file__).parent / ".spans.test.jsonl"
JSONL_PATH.unlink(missing_ok=True)
_provider = TracerProvider(resource=Resource.create({"service.name": "tests"}))
_provider.add_span_processor(SimpleSpanProcessor(MEMORY))
_provider.add_span_processor(SimpleSpanProcessor(JsonlSpanExporter(JSONL_PATH)))
trace.set_tracer_provider(_provider)


@pytest.fixture
def spans():
    MEMORY.clear()
    yield MEMORY
    MEMORY.clear()
