"""Bounded, deterministic inspection of the existing web projection.

The pure functions in this module consume ``project_run()`` output.  They do
not read Harness storage, copy projection payloads, or make model decisions.
The ``render_run_*`` helpers only compose the existing reader and projector so
callers can inspect a real run without knowing the Harness storage layout.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any, TypeVar

from ..config import AgentSettings
from .projector import project_run
from .readers import load_run_facts

_DEFAULT_TOP_N = 10
_MAX_TOP_N = 20
_DEFAULT_CHRONOLOGY_LIMIT = 20
_MAX_CHRONOLOGY_LIMIT = 40
_MAX_TOOL_ACTIVITY = 40
_MAX_ARTIFACTS = 40
_MAX_UNKNOWN_REFS = 40
_MAX_DIAGNOSTICS = 20
_MAX_TEXT = 240
_MARKDOWN_BUDGET = 12_000
_SEGMENT_MARKDOWN_BUDGET = 16_000
T = TypeVar("T")


def _bounded_limit(value: int, *, maximum: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return min(value, maximum)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)):
        return ()
    return value if isinstance(value, Sequence) else ()


def _known_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _text(value: Any, *, limit: int = _MAX_TEXT) -> str | None:
    if value is None:
        return None
    rendered = str(value).replace("\r", " ").replace("\n", " ")
    if len(rendered) <= limit:
        return rendered
    return rendered[: max(0, limit - 15)] + "… [truncated]"


def _row_ref(row: Mapping[str, Any], index: int, kind: str) -> str:
    value = row.get("id")
    return str(value) if value is not None else f"{kind}-{index}"


def _usage_value(row: Mapping[str, Any], key: str) -> int | None:
    return _known_int(_mapping(row.get("usage")).get(key))


def _request_fact(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    """Return request facts without copying the projection payload."""
    return {
        "request": _row_ref(row, index, "model-request"),
        "step": row.get("step_index"),
        "latency_ms": _known_int(row.get("duration_ms")),
        "input_tokens": _usage_value(row, "input_tokens"),
        "output_tokens": _usage_value(row, "output_tokens"),
        "status": row.get("status"),
    }


def _rank_requests(
    requests: Sequence[tuple[int, Mapping[str, Any]]],
    *,
    metric: str,
    top_n: int,
) -> tuple[list[dict[str, Any]], int]:
    candidates: list[tuple[int, int, Mapping[str, Any]]] = []
    for index, row in requests:
        value = (
            _known_int(row.get("duration_ms"))
            if metric == "latency_ms"
            else _usage_value(row, metric)
        )
        if value is not None:
            candidates.append((value, index, row))

    # Stable ties retain projection order. Unknown values never enter the
    # ranking and are never replaced with zero.
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = [
        _request_fact(row, index) for _, index, row in candidates[:top_n]
    ]
    return selected, max(0, len(candidates) - len(selected))


def _tool_activity(timeline: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Count tools and mechanically record contiguous groups."""
    activity: dict[str, dict[str, Any]] = {}
    previous_tool: str | None = None
    previous_group: int | None = None

    for row in timeline:
        if row.get("kind") != "tool_call":
            previous_tool = None
            previous_group = None
            continue
        tool = _text(row.get("title"), limit=120) or "Tool call"
        entry = activity.setdefault(
            tool,
            {"tool": tool, "total": 0, "contiguous_groups": []},
        )
        entry["total"] += 1
        groups = entry["contiguous_groups"]
        if tool == previous_tool and previous_group is not None:
            groups[previous_group - 1] += 1
        else:
            groups.append(1)
            previous_tool = tool
            previous_group = len(groups)
    return list(activity.values())


def _timeline_fact(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    usage = _mapping(row.get("usage"))
    compact_usage = {
        key: _known_int(usage.get(key))
        for key in ("input_tokens", "output_tokens")
        if _known_int(usage.get(key)) is not None
    }
    return {
        "id": _row_ref(row, index, str(row.get("kind") or "event")),
        "step": row.get("step_index"),
        "kind": row.get("kind"),
        "title": _text(row.get("title"), limit=120),
        "status": row.get("status"),
        "duration_ms": _known_int(row.get("duration_ms")),
        "usage": compact_usage or None,
    }


def _artifact_fact(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": _text(item.get("path"), limit=400),
        "size": _known_int(item.get("size")),
        "sha256": _text(item.get("sha256"), limit=96),
        "change": _text(item.get("change"), limit=80),
        "label": _text(item.get("label"), limit=120),
    }


def _bounded_list(items: Sequence[T], limit: int) -> tuple[list[T], int]:
    selected = list(items[:limit])
    return selected, max(0, len(items) - len(selected))


def inspect_run(
    projection: Mapping[str, Any],
    *,
    top_n: int = _DEFAULT_TOP_N,
    chronology_limit: int = _DEFAULT_CHRONOLOGY_LIMIT,
) -> dict[str, Any]:
    """Build a bounded inspection mapping from one ``project_run`` result.

    Only fact fields are selected. In particular, timeline ``payload`` values
    are intentionally never traversed, so prompt/response parts, tool args
    and tool result bodies cannot enter the inspection output.
    """
    top_n = _bounded_limit(top_n, maximum=_MAX_TOP_N, name="top_n")
    chronology_limit = _bounded_limit(
        chronology_limit,
        maximum=_MAX_CHRONOLOGY_LIMIT,
        name="chronology_limit",
    )
    run = _mapping(projection.get("run"))
    usage = _mapping(projection.get("usage"))
    timeline = [
        item for item in _sequence(projection.get("timeline"))
        if isinstance(item, Mapping)
    ]
    model_requests = [
        (index, row)
        for index, row in enumerate(timeline)
        if row.get("kind") == "model_request"
    ]

    slowest, slowest_omitted = _rank_requests(
        model_requests, metric="latency_ms", top_n=top_n
    )
    largest_input, largest_input_omitted = _rank_requests(
        model_requests, metric="input_tokens", top_n=top_n
    )
    largest_output, largest_output_omitted = _rank_requests(
        model_requests, metric="output_tokens", top_n=top_n
    )

    chronology_source = timeline[-chronology_limit:] if chronology_limit else []
    chronology_start = len(timeline) - len(chronology_source)
    chronology = [
        _timeline_fact(row, index)
        for index, row in zip(
            range(chronology_start, len(timeline)), chronology_source
        )
    ]

    all_tools = _tool_activity(timeline)
    tool_activity, tool_omitted = _bounded_list(all_tools, _MAX_TOOL_ACTIVITY)

    artifacts_source = [
        item
        for item in _sequence(projection.get("artifacts"))
        if isinstance(item, Mapping)
    ]
    artifacts, artifacts_omitted = _bounded_list(
        [_artifact_fact(item) for item in artifacts_source], _MAX_ARTIFACTS
    )

    incomplete_requests = [
        {
            "request": _row_ref(row, index, "model-request"),
            "step": row.get("step_index"),
        }
        for index, row in model_requests
        if row.get("status") == "incomplete"
    ]
    unresolved_tools = [
        {
            "tool_call": _row_ref(row, index, "tool-call"),
            "tool": _text(row.get("title"), limit=120) or "Tool call",
            "step": row.get("step_index"),
        }
        for index, row in enumerate(timeline)
        if row.get("kind") == "tool_call" and row.get("status") == "unresolved"
    ]
    started_tools = [
        {
            "tool_call": _row_ref(row, index, "tool-call"),
            "tool": _text(row.get("title"), limit=120) or "Tool call",
            "step": row.get("step_index"),
        }
        for index, row in enumerate(timeline)
        if row.get("kind") == "tool_call" and row.get("status") == "started"
    ]

    # A receipt can retain an unresolved effect even when its event is absent
    # from the selected timeline. Keep only safe reference/name facts.
    known_unresolved = {
        item["tool_call"]
        for item in unresolved_tools
        if item.get("tool_call") is not None
    }
    for item in _sequence(projection.get("unresolved_effects")):
        if not isinstance(item, Mapping):
            continue
        tool_call_id = item.get("tool_call_id")
        if tool_call_id is None or str(tool_call_id) in known_unresolved:
            continue
        unresolved_tools.append(
            {
                "tool_call": _text(tool_call_id, limit=160),
                "tool": _text(item.get("tool_name"), limit=120) or "Tool call",
                "step": None,
            }
        )
        known_unresolved.add(str(tool_call_id))

    request_count = _known_int(run.get("request_count"))
    if request_count is None and "request_count" not in run:
        request_count = len(model_requests)
    usage_input = _known_int(usage.get("input_tokens"))
    usage_output = _known_int(usage.get("output_tokens"))
    usage_source = _text(usage.get("source"), limit=80)

    unavailable_usage: list[str] = []
    if usage_input is None:
        unavailable_usage.append("run input tokens")
    if usage_output is None:
        unavailable_usage.append("run output tokens")
    if model_requests and any(
        _usage_value(row, "input_tokens") is None for _, row in model_requests
    ):
        unavailable_usage.append("per-request input tokens")
    if model_requests and any(
        _usage_value(row, "output_tokens") is None for _, row in model_requests
    ):
        unavailable_usage.append("per-request output tokens")

    diagnostics_source = [
        _text(item, limit=300) or "Unknown diagnostic"
        for item in _sequence(projection.get("diagnostics"))
    ]
    diagnostics, diagnostics_omitted = _bounded_list(
        diagnostics_source, _MAX_DIAGNOSTICS
    )
    incomplete_requests, incomplete_omitted = _bounded_list(
        incomplete_requests, _MAX_UNKNOWN_REFS
    )
    unresolved_tools, unresolved_omitted = _bounded_list(
        unresolved_tools, _MAX_UNKNOWN_REFS
    )
    started_tools, started_omitted = _bounded_list(started_tools, _MAX_UNKNOWN_REFS)
    unavailable_usage, unavailable_usage_omitted = _bounded_list(
        unavailable_usage, _MAX_UNKNOWN_REFS
    )

    wall_clock_ms = _known_int(run.get("duration_ms"))
    summary = {
        "run_id": _text(run.get("run_id"), limit=160),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "wall_clock_ms": wall_clock_ms,
        "duration_ms": wall_clock_ms,
        "model": _text(run.get("model"), limit=160),
        "profile": _text(run.get("profile"), limit=160),
        "requests": request_count,
        "tool_calls": _known_int(run.get("tool_call_count")),
        "input_tokens": usage_input,
        "output_tokens": usage_output,
        "usage_source": usage_source,
    }

    return {
        "run_id": summary["run_id"],
        "summary": summary,
        "rankings": {
            "slowest_requests": slowest,
            "largest_input_requests": largest_input,
            "largest_output_requests": largest_output,
        },
        "tool_activity": tool_activity,
        "timeline": chronology,
        "artifacts": artifacts,
        "unknown_facts": {
            "incomplete_requests": incomplete_requests,
            "unresolved_tool_calls": unresolved_tools,
            "started_tool_calls": started_tools,
            "unavailable_usage": unavailable_usage,
            "diagnostics": diagnostics,
        },
        "bounds": {
            "top_n": top_n,
            "chronology_limit": chronology_limit,
            "chronology_omitted": max(0, len(timeline) - len(chronology)),
            "slowest_requests_omitted": slowest_omitted,
            "largest_input_requests_omitted": largest_input_omitted,
            "largest_output_requests_omitted": largest_output_omitted,
            "tool_activity_limit": _MAX_TOOL_ACTIVITY,
            "tool_activity_omitted": tool_omitted,
            "artifacts_limit": _MAX_ARTIFACTS,
            "artifacts_omitted": artifacts_omitted,
            "unknown_refs_limit": _MAX_UNKNOWN_REFS,
            "incomplete_requests_omitted": incomplete_omitted,
            "unresolved_tool_calls_omitted": unresolved_omitted,
            "started_tool_calls_omitted": started_omitted,
            "unavailable_usage_omitted": unavailable_usage_omitted,
            "diagnostics_limit": _MAX_DIAGNOSTICS,
            "diagnostics_omitted": diagnostics_omitted,
        },
    }


def inspect_run_segment(
    projection: Mapping[str, Any],
    start_step: int,
    end_step: int,
    *,
    top_n: int = _DEFAULT_TOP_N,
    chronology_limit: int = _DEFAULT_CHRONOLOGY_LIMIT,
) -> dict[str, Any]:
    """Inspect a bounded projected step range without model/tool content."""
    if not isinstance(start_step, int) or isinstance(start_step, bool):
        raise TypeError("start_step must be an integer")
    if not isinstance(end_step, int) or isinstance(end_step, bool):
        raise TypeError("end_step must be an integer")
    if start_step > end_step:
        raise ValueError("start_step must be <= end_step")
    selected = [
        row
        for row in _sequence(projection.get("timeline"))
        if isinstance(row, Mapping)
        and isinstance(row.get("step_index"), int)
        and not isinstance(row.get("step_index"), bool)
        and start_step <= row["step_index"] <= end_step
    ]
    scoped = dict(projection)
    scoped["timeline"] = selected
    result = inspect_run(
        scoped, top_n=top_n, chronology_limit=chronology_limit
    )
    result["scope"] = {"start_step": start_step, "end_step": end_step}
    return result


def _load_projection(run_id: str, settings: AgentSettings | None) -> dict[str, Any]:
    effective_settings = settings or AgentSettings.from_env()
    facts = asyncio.run(load_run_facts(effective_settings, run_id))
    if facts is None:
        raise LookupError(f"Run {run_id!r} not found")
    return project_run(facts)


def _projection_or_run(
    run_or_projection: str | Mapping[str, Any], settings: AgentSettings | None
) -> Mapping[str, Any]:
    if isinstance(run_or_projection, str):
        return _load_projection(run_or_projection, settings)
    if isinstance(run_or_projection, Mapping):
        return run_or_projection
    raise TypeError("run_id must be a string or a projected mapping")


def render_run_json(
    run_id: str | Mapping[str, Any],
    *,
    settings: AgentSettings | None = None,
    top_n: int = _DEFAULT_TOP_N,
    chronology_limit: int = _DEFAULT_CHRONOLOGY_LIMIT,
) -> dict[str, Any]:
    """Return the bounded JSON-compatible inspection for a run or projection."""
    return inspect_run(
        _projection_or_run(run_id, settings),
        top_n=top_n,
        chronology_limit=chronology_limit,
    )


def render_inspection_markdown(
    inspection: Mapping[str, Any], *, max_chars: int = _MARKDOWN_BUDGET
) -> str:
    """Render one inspection without slicing a table or JSON object."""
    if not isinstance(max_chars, int) or isinstance(max_chars, bool):
        raise TypeError("max_chars must be an integer")
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    budget = min(max_chars, _MARKDOWN_BUDGET)
    data = dict(inspection)
    rankings = _mapping(data.get("rankings"))
    tools = list(data.get("tool_activity") or [])
    timeline = list(data.get("timeline") or [])
    artifacts = list(data.get("artifacts") or [])
    unknown = _mapping(data.get("unknown_facts"))

    def render(
        *,
        ranking_limit: int,
        tool_limit: int,
        timeline_limit: int,
        artifact_limit: int,
        unknown_limit: int,
    ) -> str:
        summary = _mapping(data.get("summary"))
        run_id = _markdown_cell(
            data.get("run_id") or summary.get("run_id") or "Unknown"
        )
        lines = [f"# Run {run_id}", "", "## Summary", ""]
        summary_rows = (
            ("Status", summary.get("status")),
            ("Started", summary.get("started_at")),
            ("Finished", summary.get("finished_at")),
            ("Wall clock", _format_duration(summary.get("wall_clock_ms"))),
            ("Model", summary.get("model")),
            ("Profile", summary.get("profile")),
            ("Requests", summary.get("requests")),
            ("Tool calls", summary.get("tool_calls")),
            ("Input tokens", summary.get("input_tokens")),
            ("Output tokens", summary.get("output_tokens")),
            ("Usage source", summary.get("usage_source")),
        )
        lines.extend(
            f"{label}: {_markdown_value(value)}" for label, value in summary_rows
        )

        lines.extend(("", "## Slowest model requests", ""))
        lines.extend(
            _ranking_table(
                rankings.get("slowest_requests") or [],
                metric="latency",
                limit=ranking_limit,
                omitted=_ranking_omitted(
                    data, "slowest_requests", "slowest_requests_omitted", ranking_limit
                ),
            )
        )
        lines.extend(("", "## Largest input requests", ""))
        lines.extend(
            _ranking_table(
                rankings.get("largest_input_requests") or [],
                metric="input",
                limit=ranking_limit,
                omitted=_ranking_omitted(
                    data,
                    "largest_input_requests",
                    "largest_input_requests_omitted",
                    ranking_limit,
                ),
            )
        )
        lines.extend(("", "## Largest output requests", ""))
        lines.extend(
            _ranking_table(
                rankings.get("largest_output_requests") or [],
                metric="output",
                limit=ranking_limit,
                omitted=_ranking_omitted(
                    data,
                    "largest_output_requests",
                    "largest_output_requests_omitted",
                    ranking_limit,
                ),
            )
        )

        visible_tools = tools[:tool_limit]
        lines.extend(("", "## Tool activity", ""))
        if visible_tools:
            lines.extend(
                ("| tool | total | contiguous groups |", "|---|---:|---|")
            )
            lines.extend(
                f"| {_markdown_cell(item.get('tool'))} | "
                f"{_markdown_value(item.get('total'))} | "
                f"{_markdown_cell(', '.join(str(group) for group in item.get('contiguous_groups', [])) or 'Unknown')} |"
                for item in visible_tools
            )
            omitted = max(0, len(tools) - len(visible_tools)) + int(
                _mapping(data.get("bounds")).get("tool_activity_omitted") or 0
            )
            if omitted:
                lines.append(f"- {omitted} tool entries omitted")
        else:
            lines.append("- none")

        visible_timeline = timeline[-timeline_limit:] if timeline_limit else []
        omitted = max(0, len(timeline) - len(visible_timeline)) + int(
            _mapping(data.get("bounds")).get("chronology_omitted") or 0
        )
        lines.extend(("", "## Timeline", ""))
        if visible_timeline:
            lines.extend(
                (
                    "| step | kind | title | status | duration | usage |",
                    "|---:|---|---|---|---:|---|",
                )
            )
            lines.extend(
                f"| {_markdown_value(item.get('step'))} | "
                f"{_markdown_cell(item.get('kind'))} | "
                f"{_markdown_cell(item.get('title'))} | "
                f"{_markdown_cell(item.get('status'))} | "
                f"{_markdown_value(_format_duration(item.get('duration_ms')))} | "
                f"{_markdown_cell(_format_usage(item.get('usage')))} |"
                for item in visible_timeline
            )
            if omitted:
                lines.append(f"- {omitted} chronology rows omitted")
        else:
            lines.append("- none")

        visible_artifacts = artifacts[:artifact_limit]
        omitted = max(0, len(artifacts) - len(visible_artifacts)) + int(
            _mapping(data.get("bounds")).get("artifacts_omitted") or 0
        )
        lines.extend(("", "## Artifacts", ""))
        if visible_artifacts:
            lines.extend(
                (
                    "| path | size | change | sha256 |",
                    "|---|---:|---|---|",
                )
            )
            lines.extend(
                f"| {_markdown_cell(item.get('path'))} | "
                f"{_markdown_value(item.get('size'))} | "
                f"{_markdown_cell(item.get('change'))} | "
                f"{_markdown_cell(item.get('sha256'))} |"
                for item in visible_artifacts
            )
            if omitted:
                lines.append(f"- {omitted} artifacts omitted")
        else:
            lines.append("- none")

        lines.extend(("", "## Unknown / unresolved facts", ""))
        unknown_rows = (
            ("incomplete requests", unknown.get("incomplete_requests") or []),
            ("unresolved tool calls", unknown.get("unresolved_tool_calls") or []),
            ("started tool calls", unknown.get("started_tool_calls") or []),
            ("unavailable usage", unknown.get("unavailable_usage") or []),
            ("diagnostics", unknown.get("diagnostics") or []),
        )
        any_unknown = False
        for label, values in unknown_rows:
            visible = values[:unknown_limit]
            bound_key = _unknown_bound_key(label)
            omitted = max(0, len(values) - len(visible)) + int(
                _mapping(data.get("bounds")).get(bound_key) or 0
            )
            if not visible and not omitted:
                continue
            any_unknown = True
            rendered = ", ".join(_unknown_value(value) for value in visible)
            lines.append(f"- {label}: {rendered or 'Unknown'}")
            if omitted:
                lines.append(f"  - {omitted} entries omitted")
        if not any_unknown:
            lines.append("- none")
        return "\n".join(lines) + "\n"

    limits = {
        "ranking_limit": 10,
        "tool_limit": len(tools),
        "timeline_limit": len(timeline),
        "artifact_limit": len(artifacts),
        "unknown_limit": _MAX_UNKNOWN_REFS,
    }
    result = render(**limits)
    while len(result) > budget and any(value > 0 for value in limits.values()):
        for key in (
            "timeline_limit",
            "ranking_limit",
            "tool_limit",
            "artifact_limit",
            "unknown_limit",
        ):
            if limits[key] > 0:
                limits[key] = max(0, limits[key] // 2)
                break
        result = render(**limits)
    if len(result) > budget:
        raise ValueError("inspection summary cannot fit the requested budget")
    return result


def render_run_markdown(
    run_id: str | Mapping[str, Any],
    *,
    settings: AgentSettings | None = None,
    top_n: int = _DEFAULT_TOP_N,
    chronology_limit: int = _DEFAULT_CHRONOLOGY_LIMIT,
) -> str:
    """Load through the authoritative projection and render Markdown."""
    inspection = inspect_run(
        _projection_or_run(run_id, settings),
        top_n=top_n,
        chronology_limit=chronology_limit,
    )
    return render_inspection_markdown(inspection)


def render_run_segment_markdown(
    run_id: str | Mapping[str, Any],
    start_step: int,
    end_step: int,
    *,
    settings: AgentSettings | None = None,
    top_n: int = _DEFAULT_TOP_N,
    chronology_limit: int = _DEFAULT_CHRONOLOGY_LIMIT,
) -> str:
    """Render one bounded projected step range for an analysis Agent.

    The segment uses the same projection and fact-only renderer as the full
    inspection.  It deliberately does not expose prompt, response, tool
    arguments or tool-result bodies; a future content-bearing path must be an
    explicit, separately audited policy decision.
    """
    inspection = inspect_run_segment(
        _projection_or_run(run_id, settings),
        start_step,
        end_step,
        top_n=top_n,
        chronology_limit=chronology_limit,
    )
    rendered = render_inspection_markdown(
        inspection, max_chars=_SEGMENT_MARKDOWN_BUDGET
    )
    return (
        rendered.rstrip()
        + "\n\n## Scope\n\n"
        + f"- Steps: {start_step}–{end_step}\n"
        + "- Content: unavailable in this fact-only inspection\n"
    )


def _format_duration(value: Any) -> str | None:
    value = _known_int(value)
    if value is None:
        return None
    if value < 1_000:
        return f"{value}ms"
    if value < 60_000:
        return f"{value / 1_000:.3f}s"
    minutes, remainder = divmod(value, 60_000)
    return f"{minutes}m {remainder / 1_000:.3f}s"


def _format_usage(value: Any) -> str | None:
    usage = _mapping(value)
    input_tokens = _known_int(usage.get("input_tokens"))
    output_tokens = _known_int(usage.get("output_tokens"))
    if input_tokens is None and output_tokens is None:
        return None
    return f"in={_format_number(input_tokens)} out={_format_number(output_tokens)}"


def _format_number(value: Any) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return "Unknown"


def _markdown_value(value: Any) -> str:
    if value is None:
        return "Unknown"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return _markdown_cell(_text(value) or "Unknown")


def _markdown_cell(value: Any) -> str:
    rendered = _text(value) or "Unknown"
    return rendered.replace("|", "\\|")


def _ranking_table(
    rows: Sequence[Mapping[str, Any]],
    *,
    metric: str,
    omitted: int,
    limit: int,
) -> list[str]:
    visible = list(rows[:limit])
    if not visible:
        reason = {
            "latency": "no authoritative request duration",
            "input": "no authoritative per-request input usage",
            "output": "no authoritative per-request output usage",
        }[metric]
        return [f"- Unavailable: {reason}."]
    lines = [
        "| request | latency | input | output | status |",
        "|---|---:|---:|---:|---|",
    ]
    lines.extend(
        f"| {_markdown_cell(row.get('request'))} | "
        f"{_markdown_value(_format_duration(row.get('latency_ms')))} | "
        f"{_markdown_value(row.get('input_tokens'))} | "
        f"{_markdown_value(row.get('output_tokens'))} | "
        f"{_markdown_cell(row.get('status'))} |"
        for row in visible
    )
    if omitted:
        lines.append(f"- {omitted} requests omitted")
    return lines


def _ranking_omitted(
    data: Mapping[str, Any],
    key: str,
    bound_key: str,
    limit: int,
) -> int:
    rankings = _mapping(data.get("rankings"))
    visible = rankings.get(key) or []
    bounds = _mapping(data.get("bounds"))
    return max(0, len(visible) - limit) + int(bounds.get(bound_key) or 0)


def _unknown_bound_key(label: str) -> str:
    return {
        "incomplete requests": "incomplete_requests_omitted",
        "unresolved tool calls": "unresolved_tool_calls_omitted",
        "started tool calls": "started_tool_calls_omitted",
        "unavailable usage": "unavailable_usage_omitted",
        "diagnostics": "diagnostics_omitted",
    }[label]


def _unknown_value(value: Any) -> str:
    if isinstance(value, Mapping):
        reference = value.get("request") or value.get("tool_call")
        tool = value.get("tool")
        if reference is not None and tool is not None:
            return f"{_markdown_cell(reference)} ({_markdown_cell(tool)})"
        if reference is not None:
            return _markdown_cell(reference)
    return _markdown_cell(value)


__all__ = [
    "inspect_run",
    "inspect_run_segment",
    "render_inspection_markdown",
    "render_run_json",
    "render_run_markdown",
    "render_run_segment_markdown",
]
