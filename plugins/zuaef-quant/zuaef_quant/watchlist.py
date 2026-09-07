"""Analysis watchlist — user attention facts (three-tier stock universe).

The candidate pool is algorithm-owned (READY/NEAR evidence comes only from
frozen selection); positions are monitor-owned. The analysis watchlist is
the missing third tier: user-curated attention for on-demand diagnosis and
monitoring. It is a business fact, not a strategy input:

- watchlist symbols NEVER enter the opportunity lifecycle (READY/NEAR);
- watchlist edits never mutate the candidate universe or the frozen spec;
- scope is an opaque host binding (bound case id, else the chat channel
  id) so multiple groups/clients never see each other's lists — Quant
  Core never learns what a customer is;
- state lives under workspace/artifacts/quant/watchlist/<scope>.json,
  written only by this module (host tool), never committed to Git.

``legacy_watchlist.toml`` stays a repo-side seed/compat baseline; Feishu
edits must not touch it.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

WATCHLIST_DIRNAME = Path("artifacts") / "quant" / "watchlist"
MAX_SYMBOLS = 64
_CODE_RE = re.compile(r"^\d{6}$")
_SCOPE_RE = re.compile(r"[^A-Za-z0-9._-]")


class WatchlistError(ValueError):
    """Raised for invalid scope/action/symbol input — user-facing message."""


def scope_dir(workspace_root: Path) -> Path:
    return Path(workspace_root) / WATCHLIST_DIRNAME


def scope_filename(scope: str) -> str:
    """Filesystem-safe scope name; opaque bindings stay opaque."""
    if not scope or not scope.strip():
        raise WatchlistError("analysis watchlist scope is empty")
    name = _SCOPE_RE.sub("_", scope.strip())[:80].strip("._-") or "default"
    return name + ".json"


def normalize_symbol(symbol: str) -> str:
    code = str(symbol or "").strip()
    if not _CODE_RE.match(code):
        raise WatchlistError(
            f"{symbol!r} is not a valid A-share code (expected 6 digits, e.g. 600460)"
        )
    return code


def _path(directory: Path, scope: str) -> Path:
    return Path(directory) / scope_filename(scope)


def read_symbols_in(directory: Path, scope: str) -> list[str]:
    """Current watchlist symbols for one scope; missing file is empty."""
    data = _read(_path(directory, scope))
    symbols = data.get("symbols") or []
    return [str(s) for s in symbols]


def read_symbols(workspace_root: Path, scope: str) -> list[str]:
    return read_symbols_in(scope_dir(workspace_root), scope)


def all_symbols_in(directory: Path) -> list[str]:
    """Union across every scope file in one watchlist directory — the
    monitor's observation-plane feed. Scope isolation stays intact at read
    time (per-scope files); this union is for quoting/monitoring only,
    never for cross-scope display."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    seen: dict[str, None] = {}
    for path in sorted(directory.glob("*.json")):
        for symbol in _read(path).get("symbols") or []:
            seen.setdefault(str(symbol), None)
    return list(seen)


def all_symbols(workspace_root: Path) -> list[str]:
    return all_symbols_in(scope_dir(workspace_root))


def update_symbols_in(
    directory: Path,
    scope: str,
    action: str,
    symbols: list[str],
    *,
    run_id: str | None = None,
) -> dict:
    """Add/remove symbols for one scope. Local, reversible, approval-free:
    no orders, no strategy change, no candidate-pool mutation."""
    if action not in ("add", "remove"):
        raise WatchlistError(f"unknown watchlist action {action!r} (use add/remove)")
    codes = [normalize_symbol(s) for s in symbols]
    if not codes:
        raise WatchlistError("no symbols given")
    deduped = list(dict.fromkeys(codes))

    current = read_symbols_in(directory, scope)
    if action == "add":
        merged = list(dict.fromkeys(current + deduped))
        if len(merged) > MAX_SYMBOLS:
            raise WatchlistError(
                f"analysis watchlist is capped at {MAX_SYMBOLS} symbols"
            )
        changed = [s for s in merged if s not in current]
    else:
        merged = [s for s in current if s not in set(deduped)]
        changed = [s for s in deduped if s in current]

    path = _path(directory, scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scope": scope,
        "symbols": merged,
        "updated_at": _dt.datetime.now(_dt.UTC).isoformat(),
        "updated_by_run": run_id,
        "note": "user attention facts; analysis-only, never READY/NEAR",
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)
    return {
        "scope": scope,
        "action": action,
        "changed": changed,
        "symbols": merged,
        "count": len(merged),
    }


def update_symbols(
    workspace_root: Path,
    scope: str,
    action: str,
    symbols: list[str],
    *,
    run_id: str | None = None,
) -> dict:
    return update_symbols_in(scope_dir(workspace_root), scope, action, symbols, run_id=run_id)


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
