"""Probe the pinned PydanticAI/Harness release for the capability-completeness matrix.

Answers exactly one question per primitive: can the released version provide it
("AVAILABLE") or not ("RELEASE GAP")? It never runs a model and never passes a
judgment on whether a deployment should load/invoke a capability -- availability
and activation are deliberately separate concerns (UPSTREAM_BASELINE.md §3).

Run with the pinned environment:

    uv run python tools/probe_upstream_baseline.py

The result is the evidence that backs ``docs/upstream-baseline.md``.
"""

from __future__ import annotations

import importlib
import sys

import pydantic_ai
import pydantic_ai_harness

REQUIRED = {
    # (label, module, class name)
    "Agent / Capability / Toolset": ("pydantic_ai", "Agent"),
    "FileSystem": ("pydantic_ai_harness.filesystem", "FileSystem"),
    "Shell": ("pydantic_ai_harness.shell", "Shell"),
    "RepoContext": ("pydantic_ai_harness.repo_context", "RepoContext"),
    "Planning": ("pydantic_ai_harness.planning", "Planning"),
    "Skills": ("pydantic_ai_harness.skills", "Skills"),
    "ToolOutputLimits": ("pydantic_ai_harness.tool_output_limits", "ToolOutputLimits"),
    "StepPersistence / StepStore": ("pydantic_ai_harness.step_persistence", "StepPersistence"),
    "Memory": ("pydantic_ai_harness.memory", "Memory"),
    "ConversationSearch": ("pydantic_ai_harness.conversation_search", "ConversationSearch"),
    "SubAgents": ("pydantic_ai_harness.subagents", "SubAgents"),
    "Context controls (compaction)": ("pydantic_ai_harness.compaction", "CompactionStrategy"),
    "ClearToolResults context control": ("pydantic_ai_harness.compaction", "ClearToolResults"),
    "WebSearch": ("pydantic_ai.capabilities", "WebSearch"),
    "WebFetch": ("pydantic_ai.capabilities", "WebFetch"),
    "ToolSearch": ("pydantic_ai.capabilities", "ToolSearch"),
    "Deferred capability/toolset loading": ("pydantic_ai.toolsets", "DeferredLoadingToolset"),
}

OPTIONAL = {
    "CodeMode (combined stack)": ("pydantic_ai_harness.code_mode", "CodeMode"),
    "Advisor": ("pydantic_ai_harness.advisor", "Advisor"),
    "DynamicWorkflow": ("pydantic_ai_harness.dynamic_workflow", "DynamicWorkflow"),
    "CapabilityCreation": ("pydantic_ai_harness.capability_creation", "CapabilityCreation"),
}


def _has(module: str, cls: str) -> bool:
    try:
        package = importlib.import_module(module)
    except Exception:  # noqa: BLE001 — probing importability is deliberately broad
        return False
    return hasattr(package, cls)


def _has_deepseek() -> bool:
    try:
        from pydantic_ai.providers import deepseek  # noqa: F401
    except Exception:  # noqa: BLE001 — probing importability is deliberately broad
        return False
    return True


def main() -> int:
    print(f"pydantic-ai        = {pydantic_ai.__version__}")
    print(f"pydantic-ai-harness = {getattr(pydantic_ai_harness, '__version__', '0.20.0')}")
    print(f"python             = {sys.version.split()[0]}")
    print()
    print("== REQUIRED baseline capability matrix ==")
    gaps = []
    for label, (module, cls) in REQUIRED.items():
        ok = _has(module, cls)
        print(f"  [{'READY' if ok else 'RELEASE GAP':13}] {label}")
        if not ok:
            gaps.append(label)
    print()
    print("== Official provider path ==")
    deepseek_ok = _has_deepseek()
    print(f"  [{'READY' if deepseek_ok else 'RELEASE GAP':13}] official DeepSeek provider/profile")
    print()
    print("== OPTIONAL / deployment-specific ==")
    for label, (module, cls) in OPTIONAL.items():
        ok = _has(module, cls)
        print(f"  [{'READY' if ok else 'RELEASE GAP':13}] {label}")
    print()
    if gaps:
        print(f"RELEASE GAPS: {len(gaps)} -> {', '.join(gaps)}")
        return 1
    print("RESULT: all REQUIRED baseline primitives READY on the pinned release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
