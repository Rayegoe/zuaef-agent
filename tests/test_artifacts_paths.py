"""P2 unit gates for zuaef-artifacts runtime helpers: path authority
(spec pack 10 section B — security/path gates), bounded process wrapper,
and output placement. Pure-python tests; no system office tools required.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from zuaef_artifacts import paths
from zuaef_artifacts.process import (
    MissingDependency,
    run_bounded,
)


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    (root / "inbox").mkdir(parents=True)
    (root / "artifacts" / "docx").mkdir(parents=True)
    (root / "artifacts" / "pdf").mkdir(parents=True)
    (root / "artifacts" / "slides").mkdir(parents=True)
    (root / "artifacts" / "spreadsheets").mkdir(parents=True)
    (root / "knowledge").mkdir()
    return root


# ── B: security/path gates ────────────────────────────────────────────────


def test_traversal_input_rejected(workspace: Path):
    """B1: ../../ escape is rejected."""
    with pytest.raises(paths.PathRejected, match="outside the workspace"):
        paths.resolve_input_path(workspace, "../../outside.docx", max_bytes=1000)


def test_absolute_input_rejected(workspace: Path):
    with pytest.raises(paths.PathRejected, match="absolute"):
        paths.resolve_input_path(workspace, "/etc/passwd", max_bytes=1000)


def test_symlink_escape_rejected(workspace: Path):
    """resolve() follows links: an in-workspace link pointing outside must
    be rejected."""
    outside = workspace.parent / "secret.txt"
    outside.write_text("x", encoding="utf-8")
    link = workspace / "inbox" / "link.txt"
    link.symlink_to(outside)
    with pytest.raises(paths.PathRejected, match="outside the workspace"):
        paths.resolve_input_path(workspace, "inbox/link.txt", max_bytes=1000)


def test_protected_secret_files_rejected(workspace: Path):
    (workspace / ".env").write_text("K=1", encoding="utf-8")
    (workspace / "server.key").write_text("k", encoding="utf-8")
    secrets_dir = workspace / "docs" / "secrets"
    secrets_dir.mkdir(parents=True)
    (secrets_dir / "notes.md").write_text("n", encoding="utf-8")
    for raw in (".env", "server.key", "docs/secrets/notes.md"):
        with pytest.raises(paths.PathRejected):
            paths.resolve_input_path(workspace, raw, max_bytes=1000)


def test_oversize_input_rejected(workspace: Path):
    big = workspace / "inbox" / "big.docx"
    big.write_bytes(b"x" * 100)
    with pytest.raises(paths.PathRejected, match="byte limit"):
        paths.resolve_input_path(workspace, "inbox/big.docx", max_bytes=10)


def test_existing_artifact_type_enforced(workspace: Path):
    docx = workspace / "artifacts" / "docx" / "a.docx"
    docx.write_bytes(b"x")
    resolved = paths.resolve_existing_artifact(
        workspace, "artifacts/docx/a.docx", "docx", max_bytes=1000
    )
    assert resolved.name == "a.docx"
    with pytest.raises(paths.PathRejected, match="expected a pdf artifact"):
        paths.resolve_existing_artifact(
            workspace, "artifacts/docx/a.docx", "pdf", max_bytes=1000
        )


def test_output_always_under_format_root_and_suffix_enforced(workspace: Path):
    """B3/B4: knowledge/ and inbox/ are never output roots; the suffix is
    enforced; the returned path is workspace-relative and contained."""
    for artifact_type, requested in (
        ("docx", "报价方案.docx"),
        ("pdf", "../escape"),
        ("slides", "deck_without_ext"),
        ("spreadsheet", None),
    ):
        target = paths.allocate_output_path(
            workspace, artifact_type, requested, default_stem="artifact"
        )
        assert target.is_relative_to(workspace / "artifacts")
        assert target.suffix == next(iter(paths.FORMAT_SUFFIXES[artifact_type]))
        rel = target.relative_to(workspace)
        assert rel.parts[0] == "artifacts"
        assert not any(part in {"knowledge", "inbox"} for part in rel.parts[:2])


def test_output_never_overwrites(workspace: Path):
    first = paths.allocate_output_path(workspace, "docx", "plan.docx", default_stem="x")
    first.write_bytes(b"v1")
    second = paths.allocate_output_path(workspace, "docx", "plan.docx", default_stem="x")
    assert second.name == "plan-2.docx"
    assert first.read_bytes() == b"v1"


def test_revision_output_lands_in_format_root(workspace: Path):
    """A docx that previously landed under inbox (upload loop) still revises
    into artifacts/docx/, never back into inbox."""
    source = workspace / "inbox" / "proposal.docx"
    source.write_bytes(b"x")
    target = paths.allocate_revision_path(workspace, "docx", source, None)
    assert target.parent == workspace / "artifacts" / "docx"
    assert target.name == "proposal-rev2.docx"


def test_revision_versioning_increments(workspace: Path):
    source = workspace / "artifacts" / "docx" / "plan.docx"
    source.write_bytes(b"x")
    r2 = paths.allocate_revision_path(workspace, "docx", source, None)
    r2.write_bytes(b"x")
    r3 = paths.allocate_revision_path(workspace, "docx", source, None)
    assert (r2.name, r3.name) == ("plan-rev2.docx", "plan-rev3.docx")


def test_filename_sanitation_preserves_unicode(workspace: Path):
    name = paths.sanitize_filename("../../客户 方案<v2>?.docx")
    assert "/" not in name and ".." not in name
    assert "客户" in name and name.endswith(".docx")


def test_work_and_render_dirs_live_in_state_root(tmp_path: Path):
    state = tmp_path / "state"
    work = paths.allocate_work_dir(state, "call-scope")
    render = paths.allocate_render_dir(state, "call-scope")
    assert work.is_relative_to(state / "artifact-work")
    assert render.is_relative_to(state / "artifact-renders")
    paths.cleanup_dir(work)
    paths.cleanup_dir(render)
    assert not work.exists() and not render.exists()


# ── bounded process wrapper ───────────────────────────────────────────────


def test_run_bounded_uses_argv_list_and_shell_false(monkeypatch, tmp_path):
    """B6: structural guarantee — the child command is an argv list and
    shell=False (no shell string is ever constructed)."""
    seen: dict = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        seen["shell"] = kwargs.get("shell")

        class Done:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Done()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_bounded(
        "/bin/echo", ["hello", "world"], timeout_seconds=5, cwd=tmp_path
    )
    assert result.returncode == 0
    assert seen["argv"] == ["/bin/echo", "hello", "world"]
    assert seen["shell"] is False


def test_run_bounded_timeout_is_bounded(tmp_path):
    result = run_bounded(
        "/bin/sleep", ["5"], timeout_seconds=1, cwd=tmp_path
    )
    assert result.timed_out is True
    assert result.returncode == -1


def test_absent_executable_is_clean_error(tmp_path, monkeypatch):
    from zuaef_artifacts import process

    monkeypatch.setattr(process, "resolve_executable", lambda candidates: None)
    with pytest.raises(MissingDependency, match="LibreOffice"):
        process.office_convert(
            tmp_path / "a.docx",
            "pdf",
            tmp_path,
            timeout_seconds=10,
        )
    with pytest.raises(MissingDependency, match="pdftoppm"):
        process.render_pdf_pages(
            tmp_path / "a.pdf", tmp_path, max_pages=2, timeout_seconds=10
        )


def test_probe_reports_factual_availability():
    from zuaef_artifacts import process

    facts = process.probe_dependencies()
    assert facts["architecture"] in {"x86_64", "aarch64", "armv7l", "x86", "i686"}
    # Python engines are hard dependencies of the plugin — always importable.
    for engine in ("docx", "pypdf", "openpyxl", "pptx"):
        assert not str(facts[engine]).startswith("ERROR"), engine
    # System tools are reported factually, present or absent.
    assert isinstance(facts["libreoffice"], str)
    assert isinstance(facts["pdftoppm"], str)
