"""Architecture subtraction guards (v1.2 T008/T013) — static tests.

These are simple source-level checks, not a framework: they enforce the
documented subtraction boundaries so future changes cannot quietly re-grow
the false-semantics surface the reference architecture removed.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "zuaef_agent"

# The closed compatibility surface (config.py GENERALIST_FLAGS). Adding a new
# entry requires a written architecture decision + spec change (v1.2 SPEC §9),
# not just a new feature flag.
CLOSED_GENERALIST_FLAGS = {
    "enable_web_search",
    "enable_web_fetch",
    "enable_tool_search",
    "enable_memory",
    "enable_conversation_search",
    "enable_context_controls",
    "enable_subagents",
    "enable_shell",
    "enable_repo_context",
}

# Identifiers that must not reappear in the kernel as semantic authority.
FORBIDDEN_KERNEL_IDENTIFIERS = (
    "verified_artifacts",
    "verified_knowledge",
    "verified_tool_effects",
    "settled_evidence",
    "parse_evidence_ref",
    "verify_knowledge",
    "verify_tool_effect",
    "RunSummary",
)


def _kernel_sources() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_generalist_flags_are_a_closed_compatibility_surface():
    """T008: the generalist flag list must not grow without an explicit
    architecture decision. The docstring in config.py states the rule and the
    alternatives; this test pins the current closed set."""
    config_src = (SRC / "config.py").read_text(encoding="utf-8")
    import re

    tuple_match = re.search(r"GENERALIST_FLAGS = \((.*?)\)", config_src, re.DOTALL)
    assert tuple_match, "GENERALIST_FLAGS tuple not found"
    flags = set()
    for line in tuple_match.group(1).splitlines():
        stripped = line.strip()
        m = re.match(r'["' + "'" + r'](.*?)["' + "'" + r']', stripped)
        if m:
            flags.add(m.group(1))
    assert flags == CLOSED_GENERALIST_FLAGS, (
        f"GENERALIST_FLAGS changed from the closed set: {flags ^ CLOSED_GENERALIST_FLAGS}. "
        "New Harness capabilities must arrive via existing packs/profiles, plugin "
        "capabilities, or explicit local composition (v1.2 SPEC §9) — not a new global flag."
    )
    assert "CLOSED (v1.2 SPEC §9)" in config_src, (
        "config.py must carry the closed-surface documentation marker"
    )


def test_kernel_has_no_semantic_verification_identifiers():
    """T013: no verified_*/evidence/summary semantics remain in the kernel
    source. Names may appear in comments/docstrings explaining their removal,
    so this checks the identifier boundary conservatively: no module may define
    or assign them (the only legal mention is in docs/ or a removal note)."""
    for source in _kernel_sources():
        text = source.read_text(encoding="utf-8")
        for ident in FORBIDDEN_KERNEL_IDENTIFIERS:
            # A definition or assignment of the identifier is forbidden;
            # explanatory comments/docstrings are allowed.
            import re

            for match in re.finditer(rf"\b{re.escape(ident)}\b", text):
                line = text[: match.start()].count("\n") + 1
                line_text = text.splitlines()[line - 1].strip()
                if line_text.startswith("#") or '"""' in line_text or "'''" in line_text:
                    continue  # comment/docstring mention (legacy-removal note)
                raise AssertionError(
                    f"{source.relative_to(REPO)}:{line}: forbidden kernel identifier "
                    f"{ident!r} in code: {line_text[:80]}"
                )


def test_kernel_does_not_import_business_plugins():
    """T013: kernel modules must not import business plugins (case, writing,
    budget, client-service, wordpress)."""
    import re

    for source in _kernel_sources():
        text = source.read_text(encoding="utf-8")
        for plugin in ("zuaef_case", "zuaef_ace", "zuaef_budget", "zuaef_client", "zuaef_wordpress"):
            if re.search(rf"(^|\n)\s*(from|import)\s+{plugin}\b", text):
                raise AssertionError(
                    f"{source.relative_to(REPO)}: kernel must not import business "
                    f"plugin {plugin!r}"
                )


def test_no_evidence_registry_or_result_registry_abstractions():
    """A2/I3: the subtraction must not introduce replacement frameworks or a
    universal result schema. Static guard: the forbidden abstraction names
    must not appear as new class definitions in the kernel."""
    forbidden = (
        "EvidenceRegistry",
        "QualityRegistry",
        "ContextRegistry",
        "BindingRegistry",
        "ServiceRegistry",
        "EventBus",
        "BusinessResult",
        "ResultSchema",
        "ResultRegistry",
        "DeliverableType",
    )
    import re

    for source in _kernel_sources():
        if source.name == "receipt_store.py":
            continue  # historical receipt adapter may mention legacy types
        text = source.read_text(encoding="utf-8")
        for name in forbidden:
            if re.search(rf"^class {name}\\b", text, re.MULTILINE):
                raise AssertionError(
                    f"{source.relative_to(REPO)}: forbidden abstraction {name!r} "
                    "(v1.2 DECISIONS forbidden list)"
                )