"""Plugin factory tests (SPEC v0.1 §20-22, Gate D surface)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from zuaef_client_service import build_plugin
from zuaef_client_service.plugin import DEFAULT_SLICE_ROOT, _resolve_slice_root

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_client_service"


def _env(tmp_path: Path) -> PluginEnv:
    return PluginEnv(
        plugin_id="client-service",
        plugin_version="0.1.0",
        workspace_root=tmp_path / "workspace",
        state_root=tmp_path / "state",
    )


@pytest.fixture()
def slice_root(tmp_path: Path) -> Path:
    root = tmp_path / "slice"
    shutil.copytree(FIXTURE, root)
    return root


class TestFactory:
    def test_bundle_shape(self, slice_root: Path, tmp_path: Path) -> None:
        bundle = build_plugin(_env(tmp_path), {"slice_root": str(slice_root)})
        assert isinstance(bundle, PluginBundle)
        assert len(bundle.toolsets) == 1
        assert bundle.capabilities == ()
        assert len(bundle.skill_dirs) == 1
        skills = bundle.skill_dirs[0]
        for skill in (
            "client-service",
            "semantic-preference",
            "sales-disclosure-boundary",
            "beauty-content-domain",
        ):
            assert (skills / skill / "SKILL.md").is_file()

    def test_config_slice_root_wins(self, slice_root: Path, tmp_path: Path) -> None:
        resolved = _resolve_slice_root({"slice_root": str(slice_root)})
        assert resolved == slice_root.resolve()

    def test_missing_slice_root_fails_loud(self, tmp_path: Path) -> None:
        with pytest.raises(CompositionError, match="slice_root missing"):
            build_plugin(_env(tmp_path), {"slice_root": str(tmp_path / "nope")})

    def test_missing_evidence_fails_loud(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        with pytest.raises(CompositionError, match="evidence_ledger"):
            build_plugin(_env(tmp_path), {"slice_root": str(root)})

    def test_default_slice_root_is_local_share(self) -> None:
        assert "client-service" in str(DEFAULT_SLICE_ROOT)
