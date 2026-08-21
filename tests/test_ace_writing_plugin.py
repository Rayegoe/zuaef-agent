"""Production contract tests for the small ``ace-writing`` environment."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from pydantic_ai import RunContext, RunUsage
from zuaef_ace_writing import create_plugin
from zuaef_ace_writing.plugin import _resolve_ace_root
from zuaef_ace_writing.writing_toolset import build_writing_toolset as plugin_toolset

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

EXPECTED_TOOLS = {
    "pull_context",
    "save_article",
}
MODEL_TECHNIQUE_TOOLS = EXPECTED_TOOLS | {"pull_techniques"}


def _env(tmp_path: Path) -> PluginEnv:
    return PluginEnv(
        plugin_id="ace-writing",
        plugin_version="0.1.0",
        workspace_root=tmp_path / "workspace",
        state_root=tmp_path / "state",
    )


def _fake_ace_root(tmp_path: Path) -> Path:
    ace = tmp_path / "ace"
    (ace / "tools").mkdir(parents=True, exist_ok=True)
    (ace / "tools" / "ctx.py").write_text("", encoding="utf-8")
    return ace


def _fake_technique_index(ace: Path) -> None:
    (ace / "corpus" / "runtime").mkdir(parents=True, exist_ok=True)
    for technique_id, body in (
        ("ex-b", "B first paragraph.\n\nB second paragraph."),
        ("ex-a", "A first paragraph.\n\nA second paragraph."),
    ):
        (ace / "corpus" / "runtime" / f"{technique_id}.md").write_text(
            body, encoding="utf-8"
        )
    rows = [
        {
            "exemplar_id": "ex-b",
            "source_ref": "src-b",
            "text_ref": "corpus/runtime/ex-b.md",
            "primary_function": "DETAIL",
            "effect_tags": ["ordinary_prose"],
            "use_when": ["product_copy"],
            "interpretation_distance": "none",
            "author_intrusion": "none",
            "status": "active",
            "rights": {"runtime_allowed": True},
        },
        {
            "exemplar_id": "ex-a",
            "source_ref": "src-a",
            "text_ref": "corpus/runtime/ex-a.md",
            "primary_function": "NARRATE",
            "effect_tags": ["scene_preserving"],
            "use_when": ["opening"],
            "interpretation_distance": "near",
            "author_intrusion": "low",
            "status": "active",
            "rights": {"runtime_allowed": True},
        },
    ]
    (ace / "corpus" / "exemplar_index.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )


def _tool_names(bundle: PluginBundle, tmp_path: Path) -> set[str]:
    deps = CoreDeps(workspace_root=tmp_path, run_id="r1")
    ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
    return set(asyncio.run(bundle.toolsets[0].get_tools(ctx)))


class TestPluginContract:
    def test_bundle_is_one_toolset_only(self, tmp_path: Path) -> None:
        bundle = create_plugin(_env(tmp_path), {"ace_root": str(_fake_ace_root(tmp_path))})
        assert isinstance(bundle, PluginBundle)
        assert len(bundle.toolsets) == 1
        assert bundle.skill_dirs == ()
        assert bundle.capabilities == ()

    def test_expected_tool_names(self, tmp_path: Path) -> None:
        bundle = create_plugin(_env(tmp_path), {"ace_root": str(_fake_ace_root(tmp_path))})
        assert _tool_names(bundle, tmp_path) == EXPECTED_TOOLS

    def test_technique_guidance_is_explicitly_configurable(self, tmp_path: Path) -> None:
        root = _fake_ace_root(tmp_path)
        default = create_plugin(_env(tmp_path), {"ace_root": str(root)})
        candidate = create_plugin(
            _env(tmp_path),
            {"ace_root": str(root), "include_technique_guidance": False},
        )

        assert default.toolsets[0].include_technique_guidance is True
        assert candidate.toolsets[0].include_technique_guidance is False
        assert _tool_names(candidate, tmp_path) == EXPECTED_TOOLS

    def test_technique_guidance_config_must_be_boolean(self, tmp_path: Path) -> None:
        with pytest.raises(CompositionError, match="must be a boolean"):
            create_plugin(
                _env(tmp_path),
                {
                    "ace_root": str(_fake_ace_root(tmp_path)),
                    "include_technique_guidance": "false",
                },
            )

    def test_model_owned_technique_mode_exposes_only_id_retrieval_extra(
        self, tmp_path: Path
    ) -> None:
        root = _fake_ace_root(tmp_path)
        _fake_technique_index(root)
        candidate = create_plugin(
            _env(tmp_path),
            {"ace_root": str(root), "technique_selection_mode": "model"},
        )

        toolset = candidate.toolsets[0]
        assert toolset.technique_selection_mode == "model"
        assert _tool_names(candidate, tmp_path) == MODEL_TECHNIQUE_TOOLS

    def test_technique_selection_mode_must_be_known(self, tmp_path: Path) -> None:
        with pytest.raises(CompositionError, match="technique_selection_mode"):
            create_plugin(
                _env(tmp_path),
                {
                    "ace_root": str(_fake_ace_root(tmp_path)),
                    "technique_selection_mode": "ranked",
                },
            )

    def test_model_catalog_is_neutral_and_selection_retrieval_is_exact(
        self, tmp_path: Path
    ) -> None:
        from zuaef_ace_writing import writing_toolset

        root = _fake_ace_root(tmp_path)
        _fake_technique_index(root)

        catalog = writing_toolset.build_technique_catalog(root)
        assert "ex-b | function=DETAIL" in catalog
        assert "ex-a | function=NARRATE" in catalog
        assert "B first paragraph" not in catalog
        assert "A first paragraph" not in catalog

        selected = writing_toolset.retrieve_selected_techniques_impl(
            ["ex-a", "ex-b"], ace_root=root
        )
        assert selected.index("### ex-a") < selected.index("### ex-b")
        assert "A first paragraph" in selected
        assert "B first paragraph" in selected
        assert "TECHNIQUE_SELECTION: ex-a, ex-b" in selected

        assert "unknown technique id" in writing_toolset.retrieve_selected_techniques_impl(
            ["missing"], ace_root=root
        )
        assert "at most 3" in writing_toolset.retrieve_selected_techniques_impl(
            ["ex-a", "ex-b", "ex-a", "ex-b"], ace_root=root
        )

    def test_context_switch_only_removes_technique_projection(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from zuaef_ace_writing import writing_toolset

        monkeypatch.setattr(
            writing_toolset,
            "list_materials_impl",
            lambda *args, **kwargs: '{"id":"M001","filename":"source.md"}\n',
        )
        monkeypatch.setattr(
            writing_toolset,
            "read_material_impl",
            lambda *args, **kwargs: "source body",
        )
        monkeypatch.setattr(
            writing_toolset, "_experience_section", lambda *args, **kwargs: "EXPERIENCE"
        )
        monkeypatch.setattr(
            writing_toolset, "_technique_section", lambda *args, **kwargs: "TECHNIQUE"
        )

        common = {
            "article_id": "article",
            "query": "query",
            "ace_root": _fake_ace_root(tmp_path),
            "learning_root": tmp_path / "learning",
        }
        control = writing_toolset.build_writer_context(
            **common, include_technique_guidance=True
        )
        candidate = writing_toolset.build_writer_context(
            **common, include_technique_guidance=False
        )

        assert "[M001] source.md" in control
        assert "[M001] source.md" in candidate
        assert "EXPERIENCE" in control
        assert "EXPERIENCE" in candidate
        assert "TECHNIQUE" in control
        assert "TECHNIQUE" not in candidate

    def test_model_owned_context_has_catalog_not_selected_bodies(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from zuaef_ace_writing import writing_toolset

        root = _fake_ace_root(tmp_path)
        _fake_technique_index(root)
        monkeypatch.setattr(
            writing_toolset,
            "list_materials_impl",
            lambda *args, **kwargs: '{"id":"M001","filename":"source.md"}\n',
        )
        monkeypatch.setattr(
            writing_toolset, "read_material_impl", lambda *args, **kwargs: "source body"
        )
        monkeypatch.setattr(
            writing_toolset, "_experience_section", lambda *args, **kwargs: "EXPERIENCE"
        )

        context = writing_toolset.build_writer_context(
            "article",
            "query",
            ace_root=root,
            learning_root=tmp_path / "learning",
            technique_selection_mode="model",
        )
        assert "## 可按需选择的 technique catalog" in context
        assert "ex-a | function=NARRATE" in context
        assert "ex-b | function=DETAIL" in context
        assert "A first paragraph" not in context
        assert "B first paragraph" not in context
        assert "EXPERIENCE" in context

    def test_ace_root_from_config_wins_over_env(self, tmp_path: Path, monkeypatch) -> None:
        fake = _fake_ace_root(tmp_path)
        monkeypatch.setenv("ACE_ROOT", "/nonexistent/env/ace")
        assert _resolve_ace_root({"ace_root": str(fake)}) == fake.resolve()

    def test_ace_root_from_env_when_config_absent(self, tmp_path: Path, monkeypatch) -> None:
        fake = _fake_ace_root(tmp_path)
        monkeypatch.setenv("ACE_ROOT", str(fake))
        assert _resolve_ace_root({}) == fake.resolve()

    def test_corpus_root_is_bound_to_writing_toolset(self, tmp_path: Path) -> None:
        ace = _fake_ace_root(tmp_path)
        corpus = tmp_path / "writing-corpus"
        bundle = create_plugin(
            _env(tmp_path),
            {"ace_root": str(ace), "corpus_root": str(corpus)},
        )

        assert bundle.toolsets[0].corpus_root == corpus.resolve()

    def test_missing_ctx_py_fails_loud(self, tmp_path: Path) -> None:
        bad = tmp_path / "not-ace"
        bad.mkdir()
        with pytest.raises(CompositionError, match="tools/ctx.py"):
            create_plugin(_env(tmp_path), {"ace_root": str(bad)})

    def test_plugin_surface_is_not_the_legacy_proof_surface(self, tmp_path: Path) -> None:
        plugin = plugin_toolset(_fake_ace_root(tmp_path))
        deps = CoreDeps(workspace_root=tmp_path, run_id="r1")
        ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
        names = set(asyncio.run(plugin.get_tools(ctx)))
        assert names == EXPECTED_TOOLS
        assert names.isdisjoint({"list_materials", "check_claim", "save_artifact"})
