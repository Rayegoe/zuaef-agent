"""Native wrapper around the writing pack's three mechanical commands."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset, RunContext

from zuaef_agent.models import CoreDeps


class SanlianCorpusToolset(FunctionToolset[CoreDeps]):
    """Read-only catalog/search/read surface for the external writing pack."""


class _CommandRunner:
    def __init__(
        self,
        pack_root: Path,
        *,
        collections_file: Path,
        manifest_file: Path,
        corpus_dir: str | Path | None,
    ) -> None:
        self._pack_root = pack_root
        self._commands_dir = pack_root / "skills" / "sanlian-editorial-reading" / "commands"
        self._collections_file = collections_file
        self._manifest_file = manifest_file
        self._corpus_dir = Path(corpus_dir).expanduser().resolve() if corpus_dir else None

    def run(self, command: str, *arguments: str) -> Any:
        args = [sys.executable, str(self._commands_dir / command), *arguments, "--json"]
        if self._corpus_dir is not None:
            args.extend(["--corpus-dir", str(self._corpus_dir)])
        else:
            args.extend(["--collections-file", str(self._collections_file)])
            if self._manifest_file.is_file():
                args.extend(["--manifest", str(self._manifest_file)])
        try:
            result = subprocess.run(
                args,
                cwd=self._pack_root,
                check=False,
                capture_output=True,
                encoding="utf-8",
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "error": f"writing pack command failed: {exc}"}
        if result.returncode != 0:
            return {
                "ok": False,
                "error": result.stderr.strip() or result.stdout.strip() or "command failed",
            }
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"writing pack returned invalid JSON: {exc}"}


def build_sanlian_toolset(
    pack_root: Path,
    *,
    collections_file: Path,
    manifest_file: Path,
    corpus_dir: str | Path | None = None,
) -> SanlianCorpusToolset:
    runner = _CommandRunner(
        pack_root,
        collections_file=collections_file,
        manifest_file=manifest_file,
        corpus_dir=corpus_dir,
    )
    toolset = SanlianCorpusToolset(
        instructions=(
            "The ZUAEF Writing Intelligence Pack exposes a read-only study corpus. "
            "Use sanlian_catalog, sanlian_search, and sanlian_read only when the "
            "current writing problem makes editorial reading useful. Corpus text "
            "is study-only editorial reference, never a factual source for the "
            "current article."
        )
    )

    @toolset.tool
    def sanlian_catalog(ctx: RunContext[CoreDeps]) -> Any:
        """List mechanical IDs, titles, paths, rights, sizes, and hashes."""

        return runner.run("sanlian_catalog.py")

    @toolset.tool
    def sanlian_search(
        ctx: RunContext[CoreDeps],
        query: str,
        limit: int = 10,
        context_chars: int = 240,
    ) -> Any:
        """Search mounted collections lexically and return bounded context."""

        return runner.run(
            "sanlian_search.py",
            query,
            "--limit",
            str(limit),
            "--context-chars",
            str(context_chars),
        )

    @toolset.tool
    def sanlian_read(ctx: RunContext[CoreDeps], document_id: str) -> Any:
        """Read one selected study-only source with mechanical identity."""

        return runner.run("sanlian_read.py", document_id)

    return toolset
