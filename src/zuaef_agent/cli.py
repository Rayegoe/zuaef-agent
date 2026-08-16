from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

from pydantic_ai import (
    DeferredToolRequests,
    DeferredToolResults,
    ToolDenied,
    ToolFailed,
)
from pydantic_ai.exceptions import UserError
from pydantic_ai.messages import ToolCallPart

from .composition import (
    build_profile_agent,
    inspect_plugin,
    installed_plugins,
    resolve_profile,
)
from .config import AgentSettings
from .core import build_agent
from .models import CoreDeps
from .profiles import list_profiles, load_profile
from .receipt_store import ReceiptStore
from .runtime import PausedRun, RuntimeOutcome, execute_run, run_task

# Exit-code contract: completed 0, partial 1, blocked 2, paused 3 (distinct from
# failure), process errors (pre-acceptance config/CLI problems) 64.
EXIT_COMPLETED = 0
EXIT_PARTIAL = 1
EXIT_BLOCKED = 2
EXIT_PAUSED = 3
EXIT_PROCESS_ERROR = 64


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run the ZUAEF outcome-owning PydanticAI agent.",
        exit_on_error=False,
    )
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a task through the shared runtime")
    run.add_argument("task", help="Outcome/task for the agent")
    run.add_argument(
        "--profile",
        help="explicit plugin composition profile under $ZUAEF_CONFIG_ROOT/profiles/",
    )
    run.add_argument("--model")
    run.add_argument("--workspace", type=Path)
    run.add_argument("--request-limit", type=int)
    run.add_argument("--tool-calls-limit", type=int)
    run.add_argument("--total-tokens-limit", type=int)

    resume = sub.add_parser("resume", help="Continue a paused run by approving or denying it")
    resume.add_argument("run_id", help="run_id of the paused run (pause receipt)")
    resume.add_argument("--approve", action="store_true", help="approve pending approvals")
    resume.add_argument("--deny", action="store_true", help="deny pending approvals")
    resume.add_argument("--reason", help="message shown to the model when denying")
    resume.add_argument("--model")
    resume.add_argument("--workspace", type=Path)

    plugin = sub.add_parser(
        "plugin",
        help="inspect installed plugins — installed/discoverable, never enabled",
    )
    plugin_sub = plugin.add_subparsers(dest="plugin_command", required=True)
    plugin_sub.add_parser("list", help="list installed plugin entry points")
    plugin_inspect = plugin_sub.add_parser(
        "inspect", help="show one installed plugin's metadata"
    )
    plugin_inspect.add_argument("plugin_id", help="plugin id (zuaef.plugins entry point name)")

    profile = sub.add_parser("profile", help="manage explicit plugin compositions")
    profile_sub = profile.add_subparsers(dest="profile_command", required=True)
    profile_list = profile_sub.add_parser("list", help="list profiles under the config root")
    profile_list.add_argument("--config-root", type=Path)
    profile_show = profile_sub.add_parser(
        "show", help="show one profile's declared (non-secret) configuration"
    )
    profile_show.add_argument("name")
    profile_check = profile_sub.add_parser(
        "check",
        help="fully resolve one profile (loads factories, validates bundles,"
        " detects conflicts) without any model request",
    )
    profile_check.add_argument("name")
    for command in (profile_show, profile_check):
        command.add_argument("--config-root", type=Path)
    return p


def _settings_from_args(args: argparse.Namespace) -> AgentSettings:
    settings = AgentSettings.from_env()
    changes: dict[str, object] = {}
    if getattr(args, "model", None):
        changes["model"] = args.model
    if getattr(args, "workspace", None):
        changes["workspace_root"] = args.workspace
    for key in ("request_limit", "tool_calls_limit", "total_tokens_limit"):
        value = getattr(args, key, None)
        if value is not None:
            changes[key] = value
    if changes:
        settings = settings.with_overrides(**changes)
    return settings


def _outcome_exit_code(outcome: RuntimeOutcome) -> int:
    if isinstance(outcome, PausedRun):
        return EXIT_PAUSED
    status = outcome.summary.status
    return {"completed": EXIT_COMPLETED, "partial": EXIT_PARTIAL, "blocked": EXIT_BLOCKED}[status]


def _print_outcome(outcome: RuntimeOutcome) -> None:
    if isinstance(outcome, PausedRun):
        payload = outcome.pause_receipt.model_dump()
    else:
        payload = outcome.receipt.model_dump()
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _run(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    profile = getattr(args, "profile", None)
    if profile is None:
        outcome = run_task(args.task, settings)
    else:
        run_id = uuid4().hex
        agent, snapshot = build_profile_agent(
            settings, run_id=run_id, profile=profile
        )
        deps = CoreDeps(
            workspace_root=settings.workspace_root.resolve(), run_id=run_id
        )
        outcome = execute_run(
            agent,
            deps,
            prompt=args.task,
            settings=settings,
            run_id=run_id,
            composition=snapshot,
        )
    _print_outcome(outcome)
    return _outcome_exit_code(outcome)


def _resume(args: argparse.Namespace) -> int:
    if bool(args.approve) == bool(args.deny):
        print("exactly one of --approve / --deny is required", file=sys.stderr)
        return EXIT_PROCESS_ERROR
    settings = _settings_from_args(args)

    receipt = ReceiptStore(settings.state_root).read(args.run_id)
    if getattr(receipt, "state", "terminal") != "paused":
        print(f"run {args.run_id} is not paused; resume needs a pause receipt", file=sys.stderr)
        return EXIT_PROCESS_ERROR

    from pydantic_ai_harness.step_persistence import FileStepStore, continue_run

    store = FileStepStore(settings.step_store_dir)
    history = asyncio.run(continue_run(store, run_id=args.run_id))

    requests = DeferredToolRequests(
        approvals=[
            ToolCallPart(
                tool_name=entry.get("tool_name") or "",
                args=entry.get("args") or {},
                tool_call_id=entry.get("tool_call_id") or "",
            )
            for entry in receipt.pending_approvals
        ]
    )
    results = DeferredToolResults()
    for call in requests.approvals:
        results.approvals[call.tool_call_id] = True if args.approve else ToolDenied(args.reason or "denied by operator")
    for entry in receipt.pending_calls:
        results.calls[entry["tool_call_id"]] = ToolFailed("no external executor configured")

    run_id = uuid4().hex
    composition = getattr(receipt, "composition", None)
    if composition is not None:
        # The pause receipt is the composition authority; the mutable
        # current profile is ignored, and an installed version/entry point
        # that drifted from the frozen snapshot fails here (process error).
        agent, _ = build_profile_agent(
            settings, run_id=run_id, snapshot=composition
        )
    else:
        agent = build_agent(settings, run_id=run_id)
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)
    outcome = execute_run(
        agent,
        deps,
        settings=settings,
        run_id=run_id,
        conversation_id=receipt.conversation_id,
        message_history=history,
        deferred_tool_results=results,
        prior_pause_receipt=receipt,
        composition=composition,
    )
    _print_outcome(outcome)
    return _outcome_exit_code(outcome)


def _plugin(args: argparse.Namespace) -> int:
    if args.plugin_command == "list":
        rows = installed_plugins()
        if not rows:
            print("(no plugins installed)")
            return 0
        for plugin_id, version in rows:
            print(f"{plugin_id:<20}{version}")
        return 0
    plugin_id, version, entry_point = inspect_plugin(args.plugin_id)
    print(f"id: {plugin_id}")
    print(f"version: {version}")
    print(f"entry_point: {entry_point}")
    return 0


def _profile(args: argparse.Namespace) -> int:
    if args.profile_command == "list":
        names = list_profiles(args.config_root)
        if not names:
            print("(no profiles)")
            return 0
        for name in names:
            print(name)
        return 0
    config_root = args.config_root
    if args.profile_command == "show":
        profile = load_profile(args.name, config_root)
        print(
            json.dumps(profile.model_dump(), ensure_ascii=False, indent=2)
        )
        return 0
    settings = AgentSettings.from_env()
    snapshot = resolve_profile(args.name, settings, config_root=config_root)
    print(
        json.dumps(snapshot.model_dump(), ensure_ascii=False, indent=2)
    )
    return 0


def main() -> None:
    parser = _parser()
    try:
        args = parser.parse_args()
        _settings_from_args(args)  # validates limits pre-acceptance: process error, no receipt
    except (ValueError, argparse.ArgumentError) as exc:
        print(f"process error: {exc}", file=sys.stderr)
        sys.exit(EXIT_PROCESS_ERROR)

    try:
        if args.command == "run":
            code = _run(args)
        elif args.command == "resume":
            code = _resume(args)
        elif args.command == "plugin":
            code = _plugin(args)
        else:
            code = _profile(args)
    except (ValueError, FileNotFoundError, LookupError, UserError) as exc:
        print(f"process error: {exc}", file=sys.stderr)
        sys.exit(EXIT_PROCESS_ERROR)
    sys.exit(code)


if __name__ == "__main__":
    main()
