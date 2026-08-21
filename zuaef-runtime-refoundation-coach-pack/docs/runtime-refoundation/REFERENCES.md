# Reference Anchors

These are design anchors to re-check when implementation questions arise.

## ZUAEF

- `AGENTS.md`
- `Outcome-First PydanticAI Agent Engineering Guide v2.0.md`
- `src/zuaef_agent/core.py`
- `src/zuaef_agent/config.py`
- `src/zuaef_agent/runtime.py`
- `src/zuaef_agent/composition.py`
- `examples/production_writing.py`
- `plugins/zuaef-ace-writing/zuaef_ace_writing/writing_toolset.py`
- `tools/run_writing_eval.py`
- `benchmarks/writing-cases/WCASE-*`

## Pydantic AI Harness concepts

Re-read upstream documentation/source before changing integration semantics:

- repository README: simple agents already have a light harness; capabilities are composable;
- Planning: intended for long agentic runs that drift;
- Skills: deferred instruction loading;
- StepPersistence: execution/persistence substrate, not a full graph checkpoint;
- ToolOutputLimits: bounds oversized persistent tool returns;
- CodeMode: reduces N dependent tool round-trips/context growth.

Do not copy upstream implementation into ZUAEF.

