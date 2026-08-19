from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from pydantic_ai.exceptions import UserError

from .composition import (
    build_profile_agent,
    inspect_plugin,
    installed_plugins,
    resolve_profile,
)
from .config import AgentSettings
from .continuation import resume_paused_run
from .gateway.store import GatewayStore
from .models import CoreDeps
from .profiles import list_profiles, load_profile
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
        help="fully resolve one profile (loads factories, validates bundles)"
        " without any model request",
    )
    profile_check.add_argument("name")
    for command in (profile_show, profile_check):
        command.add_argument("--config-root", type=Path)

    gateway = sub.add_parser(
        "gateway", help="run the interactive business gateway (SPEC v0.3)"
    )
    gateway_sub = gateway.add_subparsers(dest="gateway_command", required=True)
    gateway_start = gateway_sub.add_parser(
        "start", help="foreground blocking gateway process (Stage A: telegram)"
    )
    gateway_start.add_argument("--surface", required=True, choices=["telegram"])
    gateway_start.add_argument("--profile")
    gateway_start.add_argument("--workspace", type=Path)
    gateway_start.add_argument("--model")
    gateway_start.add_argument("--config-root", type=Path)
    gateway_bind = gateway_sub.add_parser(
        "bind-case",
        help="deterministic supervisor operation: bind a channel/thread to "
        "one Case (SPEC v1.0 §5.4). The model can never bind itself.",
    )
    gateway_bind.add_argument("--surface", required=True)
    gateway_bind.add_argument("--tenant", default="default")
    gateway_bind.add_argument("--user", required=True)
    gateway_bind.add_argument("--channel", required=True)
    gateway_bind.add_argument("--thread", default=None)
    gateway_bind.add_argument("--case", default=None, help="case_id to bind")
    gateway_bind.add_argument("--unbind", action="store_true", help="remove the binding")
    gateway_bind.add_argument("--workspace", type=Path)
    gateway_bind.add_argument("--state-root", type=Path)
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
    try:
        # Shared continuation seam: the CLI owns no resume orchestration of
        # its own — the Gateway executes the exact same function.
        outcome = resume_paused_run(
            settings,
            args.run_id,
            decision="approve" if args.approve else "deny",
            reason=args.reason,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_PROCESS_ERROR
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


def _gateway(args: argparse.Namespace) -> int:
    from .gateway import runner

    settings = _settings_from_args(args)
    config = runner.load_gateway_config(args)
    return runner.run_gateway(config=config, settings=settings)


def _gateway_bind_case(args: argparse.Namespace) -> int:
    """Supervisor-only deterministic binding (SPEC v1.0 §5.4).

    Resolves the session through the existing SQLite store and writes
    ``case_id`` into the session binding. Conversation identity, profile and
    run pointers are untouched; ``/new`` keeps the binding. This is the only
    place a channel/thread may acquire a Case — no inbound text can.
    """
    settings = _settings_from_args(args)
    if args.workspace:
        settings = settings.with_overrides(workspace_root=args.workspace)
    if args.state_root:
        settings = settings.with_overrides(runtime_state_root=args.state_root)
    case_id = None if args.unbind else args.case
    if case_id is None and not args.unbind:
        print("process error: --case is required unless --unbind is given", file=sys.stderr)
        return EXIT_PROCESS_ERROR
    store = GatewayStore(settings.state_root / "gateway.sqlite3")
    try:
        session = store.get_or_create_session(
            surface=args.surface,
            tenant_id=args.tenant,
            user_id=args.user,
            channel_id=args.channel,
            thread_id=args.thread,
            default_profile=None,
        )
        bound = store.bind_case(
            session,
            case_id,
        )
    except ValueError as exc:
        print(f"process error: {exc}", file=sys.stderr)
        store.close()
        return EXIT_PROCESS_ERROR
    store.close()
    print(
        json.dumps(
            {
                "surface": bound.surface,
                "tenant_id": bound.tenant_id,
                "channel_id": bound.channel_id,
                "thread_key": bound.thread_key,
                "conversation_id": bound.conversation_id,
                "case_id": bound.case_id,
                "action": "unbound" if args.unbind else "bound",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return EXIT_COMPLETED


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
        elif args.command == "gateway":
            if args.gateway_command == "bind-case":
                code = _gateway_bind_case(args)
            else:
                code = _gateway(args)
        else:
            code = _profile(args)
    except (ValueError, FileNotFoundError, LookupError, UserError, httpx.HTTPError) as exc:
        print(f"process error: {exc}", file=sys.stderr)
        sys.exit(EXIT_PROCESS_ERROR)
    sys.exit(code)


if __name__ == "__main__":
    main()
