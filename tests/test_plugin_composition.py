"""Plugin Composition Layer tests — SPEC v0.2 §39–§43.

The fixture plugins under ``tests/fixture_plugins/`` are real importable
modules whose ``zuaef.plugins`` entry points are constructed here (hermetic:
nothing is pip-installed). ``discover``/``version_for`` inject the fixture
registry into the composition layer's resolution seams.
"""

from __future__ import annotations

import asyncio
import json
import sys
from importlib.metadata import EntryPoint
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai import RunContext, RunUsage
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from zuaef_agent.composition import (
    build_agent_from_snapshot,
    build_profile_agent,
    resolve_profile,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import (
    CompositionError,
    CompositionSnapshot,
    PluginBundle,
)
from zuaef_agent.profiles import load_profile
from zuaef_agent.runtime import (
    PausedRun,
    TerminalRun,
    decide,
    execute_run,
)

WRITING_PROFILE = """\
schema = 1
name = "writing"

[[plugins]]
id = "fixture-ace-writing"
allow_capabilities = false

[plugins.config]
ace_root = "/v1"
"""


def _ep(module: str, name: str, factory: str = "create_plugin") -> EntryPoint:
    return EntryPoint(
        name=name,
        value=f"fixture_plugins.{module}:{factory}",
        group="zuaef.plugins",
    )


DISCOVER = {
    "fixture-ace-writing": _ep("writing", "fixture-ace-writing"),
    "hardware-scout": _ep("hardware", "hardware-scout"),
    "capability-plugin": _ep("capability", "capability-plugin"),
    "conflict-plugin": _ep("conflict", "conflict-plugin"),
    "broken-plugin": _ep("broken", "broken-plugin"),
    "invalid-bundle": _ep("broken", "invalid-bundle", "create_invalid"),
    "never-enabled": _ep("never_enabled", "never-enabled"),
}

VERSIONS = {
    "fixture-ace-writing": "0.2.1",
    "hardware-scout": "0.1.0",
    "capability-plugin": "0.3.0",
    "conflict-plugin": "0.0.1",
    "broken-plugin": "0.0.1",
    "invalid-bundle": "0.0.1",
    "never-enabled": "0.0.1",
}


def _vf(ep: EntryPoint) -> str:
    return VERSIONS[ep.name]


def _settings(tmp_path: Path, *, enable_skills: bool = False) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=enable_skills,
    )


def _write_profile(
    tmp_path: Path,
    name: str,
    text: str = WRITING_PROFILE,
) -> Path:
    config_root = tmp_path / "config"
    directory = config_root / "profiles"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.toml").write_text(text, encoding="utf-8")
    return config_root


def _deps(settings: AgentSettings, run_id: str) -> CoreDeps:
    return CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)


def _tool_names(toolset) -> set[str]:
    ctx = RunContext(deps=CoreDeps(workspace_root=Path("/tmp"), run_id=""), usage=RunUsage(), prompt="", model=None)
    return set(asyncio.run(toolset.get_tools(ctx)))


def _user_tool_names(agent) -> set[str]:
    """Tool names from user-supplied toolsets only (plugin toolsets are plain
    FunctionToolset members; capability-owned and internal ones are not)."""
    from pydantic_ai import FunctionToolset

    return {
        name
        for toolset in agent.toolsets
        if type(toolset) is FunctionToolset
        for name in _tool_names(toolset)
    }


def _final(text: str = "done") -> ModelResponse:
    return ModelResponse(parts=[TextPart(content=text)])


def _has_tool_return(messages) -> bool:
    return any(
        getattr(part, "part_kind", None) in ("tool-return", "tool-retry")
        for message in messages
        for part in getattr(message, "parts", [])
    )


def _publish_fn(messages, info):
    if not _has_tool_return(messages):
        return ModelResponse(
            parts=[ToolCallPart("publish_article", {"article_id": "a1"})]
        )
    return _final("published")


# ── §39 Static ───────────────────────────────────────────────────────────────


def test_plugin_bundle_fields_are_the_only_primitives():
    """Architecture invariant: no hook/middleware/event/service fields exist."""
    assert set(PluginBundle.__dataclass_fields__) == {
        "toolsets",
        "skill_dirs",
        "capabilities",
    }
    assert set(CompositionSnapshot.model_fields) == {
        "schema_version",
        "profile",
        "plugins",
        "generalist",
        "composition_id",
    }


def test_invalid_bundle_type_fails(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(
        tmp_path,
        "broken",
        text='schema = 1\nname = "broken"\n\n[[plugins]]\nid = "invalid-bundle"\n',
    )
    with pytest.raises(CompositionError, match="must return a PluginBundle"):
        resolve_profile(
            "broken", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
        )


def test_capability_fail_closed(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(
        tmp_path,
        "cap",
        text='schema = 1\nname = "cap"\n\n[[plugins]]\nid = "capability-plugin"\n',
    )
    with pytest.raises(CompositionError, match="does not allow them"):
        resolve_profile(
            "cap", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
        )


def test_capability_allowed_reaches_agent(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(
        tmp_path,
        "cap",
        text='schema = 1\nname = "cap"\n\n[[plugins]]\nid = "capability-plugin"\nallow_capabilities = true\n',
    )
    agent, snapshot = build_profile_agent(
        settings,
        run_id=uuid4().hex,
        profile="cap",
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    capability_types = [type(capability).__name__ for capability in agent.root_capability.capabilities]
    assert "FixtureCapability" in capability_types
    assert snapshot.plugins[0].capabilities_allowed is True


def test_profile_unknown_field_fails(tmp_path):
    config_root = _write_profile(
        tmp_path,
        "bad",
        text='schema = 1\nname = "bad"\nbogus = true\n',
    )
    with pytest.raises(CompositionError, match="schema validation"):
        load_profile("bad", config_root)


def test_profile_name_mismatch_fails(tmp_path):
    config_root = _write_profile(
        tmp_path,
        "writing",
        text='schema = 1\nname = "other"\n',
    )
    with pytest.raises(CompositionError, match="does not match the file name"):
        load_profile("writing", config_root)


def test_secret_config_rejected(tmp_path):
    config_root = _write_profile(
        tmp_path,
        "leaky",
        text='schema = 1\nname = "leaky"\n\n[[plugins]]\nid = "fixture-ace-writing"\n\n[plugins.config]\napi_key = "sk-leak"\n',
    )
    with pytest.raises(CompositionError, match="secret-named"):
        load_profile("leaky", config_root)


def test_snapshot_json_contains_no_secret(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    snapshot = resolve_profile(
        "writing", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    dumped = snapshot.model_dump_json()
    for secret_word in ("api_key", "password", "token", "secret"):
        assert secret_word not in dumped.lower()


# ── §40 Resolver ─────────────────────────────────────────────────────────────


def test_one_id_resolves_to_exactly_one_entry_point(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    snapshot = resolve_profile(
        "writing", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    assert snapshot.profile == "writing"
    assert [ref.id for ref in snapshot.plugins] == ["fixture-ace-writing"]
    ref = snapshot.plugins[0]
    assert ref.version == "0.2.1"
    assert ref.entry_point == "fixture_plugins.writing:create_plugin"
    assert ref.config == {"ace_root": "/v1"}
    assert ref.capabilities_allowed is False
    assert len(snapshot.composition_id) == 64


def test_zero_match_fails(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(
        tmp_path,
        "ghost",
        text='schema = 1\nname = "ghost"\n\n[[plugins]]\nid = "not-installed"\n',
    )
    with pytest.raises(CompositionError, match="not installed"):
        resolve_profile(
            "ghost", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
        )


def test_duplicate_plugin_id_fails(tmp_path):
    config_root = _write_profile(
        tmp_path,
        "dup",
        text='schema = 1\nname = "dup"\n\n[[plugins]]\nid = "fixture-ace-writing"\n\n[[plugins]]\nid = "fixture-ace-writing"\n',
    )
    with pytest.raises(CompositionError, match="duplicate plugin id"):
        load_profile("dup", config_root)


def test_disabled_installed_plugin_not_imported(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    assert "fixture_plugins.never_enabled" not in sys.modules
    resolve_profile(
        "writing", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    assert "fixture_plugins.never_enabled" not in sys.modules, (
        "an installed-but-unlisted plugin must never be imported"
    )


def test_deterministic_ordering_and_hash_sensitivity(tmp_path):
    settings = _settings(tmp_path)
    two_plugins = (
        'schema = 1\nname = "mix"\n\n'
        '[[plugins]]\nid = "hardware-scout"\n\n'
        '[[plugins]]\nid = "fixture-ace-writing"\n'
    )
    config_root = _write_profile(tmp_path, "mix", text=two_plugins)
    snapshot = resolve_profile(
        "mix", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    assert [ref.id for ref in snapshot.plugins] == ["hardware-scout", "fixture-ace-writing"]
    reverted = _write_profile(
        tmp_path,
        "mix",
        text='schema = 1\nname = "mix"\n\n[[plugins]]\nid = "fixture-ace-writing"\n\n[[plugins]]\nid = "hardware-scout"\n',
    )
    snapshot_reverted = resolve_profile(
        "mix", settings, config_root=reverted, discover=lambda: DISCOVER, version_for=_vf
    )
    assert snapshot_reverted.composition_id != snapshot.composition_id
    again = resolve_profile(
        "mix", settings, config_root=reverted, discover=lambda: DISCOVER, version_for=_vf
    )
    assert again.composition_id == snapshot_reverted.composition_id


def test_factory_exception_fails_before_run(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(
        tmp_path,
        "boom",
        text='schema = 1\nname = "boom"\n\n[[plugins]]\nid = "broken-plugin"\n',
    )
    with pytest.raises(CompositionError, match="factory failed"):
        resolve_profile(
            "boom", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
        )


# ── §41 Composition ──────────────────────────────────────────────────────────


def test_no_profile_behavior_unchanged(tmp_path):
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    agent, snapshot = build_profile_agent(settings, run_id=run_id)
    assert snapshot is None
    plain = build_agent(settings, run_id=run_id)
    assert _user_tool_names(agent) == _user_tool_names(plain) == set()


def test_plugin_toolsets_reach_agent(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    agent, snapshot = build_profile_agent(
        settings,
        run_id=uuid4().hex,
        profile="writing",
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    names = _user_tool_names(agent)
    assert {"list_materials", "save_artifact", "publish_article"} <= names
    assert snapshot.plugins[0].id == "fixture-ace-writing"


def test_plugin_skill_dirs_reach_skills_capability(tmp_path):
    settings = _settings(tmp_path, enable_skills=True).with_overrides(
        skills_dir=tmp_path / "no-base-skills"
    )
    config_root = _write_profile(tmp_path, "writing")
    agent, _ = build_profile_agent(
        settings,
        run_id=uuid4().hex,
        profile="writing",
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    skills = [
        capability
        for capability in agent.root_capability.capabilities
        if type(capability).__name__ == "Skills"
    ]
    assert len(skills) == 1
    directories = [Path(directory) for directory in skills[0].directories]
    plugin_skill = Path("tests/fixture_plugins/fixture_plugins/skills").resolve()
    assert plugin_skill in directories


def test_duplicate_tool_fails_no_silent_override(tmp_path):
    """Collision regression: upstream composition owns tool-name conflicts.

    ZUAEF no longer runs its own tool-conflict preflight (T003 DELETE) — the
    combined upstream toolset refuses duplicate names. Proof that a conflict
    still cannot silently override: resolution succeeds, but materializing
    the composed agent's tool schema raises PydanticAI's own ``UserError``.
    """
    from pydantic_ai.exceptions import UserError
    from pydantic_ai.messages import ModelResponse, TextPart
    from pydantic_ai.models.function import FunctionModel

    settings = _settings(tmp_path)
    config_root = _write_profile(
        tmp_path,
        "clash",
        text='schema = 1\nname = "clash"\n\n[[plugins]]\nid = "fixture-ace-writing"\n\n[[plugins]]\nid = "conflict-plugin"\n',
    )
    # Resolution no longer performs the conflict check; it must not raise.
    snapshot = resolve_profile(
        "clash", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    agent = build_agent_from_snapshot(
        settings,
        snapshot=snapshot,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )

    async def handler(messages, info):
        return ModelResponse(parts=[TextPart("x")])

    with agent.override(model=FunctionModel(handler)), pytest.raises(
        UserError, match="conflicts"
    ):
        asyncio.run(agent.run("go"))


# ── §42 Receipt ──────────────────────────────────────────────────────────────


def test_composition_id_sensitive_to_all_identity_facts(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")

    def resolve_with(vf, discover=None):
        return resolve_profile(
            "writing",
            settings,
            config_root=config_root,
            discover=discover or (lambda: DISCOVER),
            version_for=vf,
        )

    baseline = resolve_with(_vf)
    assert resolve_with(_vf).composition_id == baseline.composition_id

    _write_profile(
        tmp_path,
        "writing",
        text='schema = 1\nname = "writing"\n\n[[plugins]]\nid = "fixture-ace-writing"\n\n[plugins.config]\nace_root = "/v2"\n',
    )
    assert resolve_with(_vf).composition_id != baseline.composition_id
    _write_profile(tmp_path, "writing")

    bumped = lambda ep: "0.2.2" if ep.name == "fixture-ace-writing" else _vf(ep)
    assert resolve_with(bumped).composition_id != baseline.composition_id

    alias_ep = dict(DISCOVER)
    alias_ep["fixture-ace-writing"] = _ep("writing", "fixture-ace-writing", "create_plugin_alias")
    assert resolve_with(_vf, discover=lambda: alias_ep).composition_id != baseline.composition_id


def test_terminal_receipt_carries_composition(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    run_id = uuid4().hex
    agent, snapshot = build_profile_agent(
        settings,
        run_id=run_id,
        profile="writing",
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    deps = _deps(settings, run_id)

    def fn(messages, info):
        return _final("done")

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(
            agent, deps, prompt="go", settings=settings, run_id=run_id, composition=snapshot
        )

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.schema_version == "1.2"
    assert outcome.receipt.composition == snapshot
    stored = outcome.receipt.summary.receipt
    on_disk = json.loads(Path(stored).read_text(encoding="utf-8"))
    assert on_disk["composition"]["composition_id"] == snapshot.composition_id
    assert on_disk["composition"]["plugins"][0]["config"] == {"ace_root": "/v1"}


def test_pause_receipt_roundtrip_with_composition(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    snapshot = resolve_profile(
        "writing", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    from datetime import UTC, datetime

    from zuaef_agent.models import PauseReceipt
    from zuaef_agent.receipt_store import ReceiptStore

    now = datetime.now(UTC)
    pause = PauseReceipt(
        run_id="p1",
        conversation_id="c1",
        model="test",
        started_at=now,
        finished_at=now,
        composition=snapshot,
    )
    path = ReceiptStore(settings.state_root).write(pause)
    stored = ReceiptStore(settings.state_root).read("p1")
    assert stored.schema_version == "1.2"
    assert stored.composition.composition_id == snapshot.composition_id
    assert Path(path).is_file()


# ── §43 Resume P0 ────────────────────────────────────────────────────────────


def test_resume_uses_frozen_composition_ignoring_mutable_profile(tmp_path):
    from fixture_plugins import writing as writing_fixture

    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    snapshot = resolve_profile(
        "writing", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )

    run_id = uuid4().hex
    agent, _ = build_profile_agent(
        settings, run_id=run_id, snapshot=snapshot, discover=lambda: DISCOVER, version_for=_vf
    )
    deps = _deps(settings, run_id)
    with agent.override(model=FunctionModel(_publish_fn)):
        paused = execute_run(
            agent, deps, prompt="publish", settings=settings, run_id=run_id, composition=snapshot
        )
    assert isinstance(paused, PausedRun)
    assert paused.pause_receipt.composition == snapshot

    # The profile mutates after the pause; resume must ignore it.
    _write_profile(
        tmp_path,
        "writing",
        text='schema = 1\nname = "writing"\n\n[[plugins]]\nid = "fixture-ace-writing"\n\n[plugins.config]\nace_root = "/mutated"\n',
    )

    run_id2 = uuid4().hex
    resume_agent, _ = build_profile_agent(
        settings, run_id=run_id2, snapshot=snapshot, discover=lambda: DISCOVER, version_for=_vf
    )
    assert writing_fixture.last_config == {"ace_root": "/v1"}, (
        "resume must feed the factory the frozen config, not the mutated profile"
    )
    deps2 = _deps(settings, run_id2)
    with resume_agent.override(model=FunctionModel(_publish_fn)):
        continued = execute_run(
            resume_agent,
            deps2,
            settings=settings,
            run_id=run_id2,
            conversation_id=paused.conversation_id,
            message_history=paused.message_history,
            deferred_tool_results=decide(paused, approve=True),
            prior_pause_receipt=paused.pause_receipt,
            composition=snapshot,
        )

    assert isinstance(continued, TerminalRun)
    assert continued.receipt.continued_from_run_id == paused.pause_receipt.run_id
    assert continued.receipt.conversation_id == paused.pause_receipt.conversation_id
    assert continued.receipt.composition == snapshot


def test_resume_version_mismatch_fails_before_model_request(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    snapshot = resolve_profile(
        "writing", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    bumped = lambda ep: "0.2.2" if ep.name == "fixture-ace-writing" else _vf(ep)
    with pytest.raises(CompositionError, match="composition requires version"):
        build_agent_from_snapshot(
            settings,
            run_id=uuid4().hex,
            snapshot=snapshot,
            discover=lambda: DISCOVER,
            version_for=bumped,
        )


def test_resume_entry_point_mismatch_fails_before_model_request(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    snapshot = resolve_profile(
        "writing", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    moved = dict(DISCOVER)
    moved["fixture-ace-writing"] = _ep("writing", "fixture-ace-writing", "create_plugin_alias")
    with pytest.raises(CompositionError, match="requires entry point"):
        build_agent_from_snapshot(
            settings,
            run_id=uuid4().hex,
            snapshot=snapshot,
            discover=lambda: moved,
            version_for=_vf,
        )


def test_missing_plugin_at_resume_fails_before_model_request(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    snapshot = resolve_profile(
        "writing", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    with pytest.raises(CompositionError, match="not installed"):
        build_agent_from_snapshot(
            settings,
            run_id=uuid4().hex,
            snapshot=snapshot,
            discover=dict,
            version_for=_vf,
        )


def test_profile_and_snapshot_together_fail(tmp_path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    snapshot = resolve_profile(
        "writing", settings, config_root=config_root, discover=lambda: DISCOVER, version_for=_vf
    )
    with pytest.raises(CompositionError, match="not both"):
        build_profile_agent(
            settings,
            run_id=uuid4().hex,
            profile="writing",
            snapshot=snapshot,
            config_root=config_root,
            discover=lambda: DISCOVER,
            version_for=_vf,
        )
