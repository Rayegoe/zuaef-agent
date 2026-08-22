"""HTTP API for the ZUAEF Agent Console — thin JSON adapters over readers/actions.

Route surface (API-CONTRACT §2–§7): two read endpoints, two action
endpoints, one health check, one SSE invalidation stream (T008C — thin
``run_changed`` notices only; the HTTP projection stays the UI's single
truth). No fragmenting one run into many endpoints;
no new business domain; errors use one small stable code set.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from importlib.metadata import PackageNotFoundError, version

from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from ..config import AgentSettings
from . import actions, readers, sse
from .projector import project_run, run_view


def _package_version() -> str:
    try:
        return version("zuaef-agent")
    except PackageNotFoundError:
        return "0.0.0"


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _error_response(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message}}, status_code=status
    )


def _settings(request: Request) -> AgentSettings:
    return request.app.state.settings


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "version": _package_version()})


async def list_runs(request: Request) -> JSONResponse:
    settings = _settings(request)
    params = request.query_params
    limit_raw = params.get("limit")
    limit = None
    if limit_raw is not None:
        try:
            limit = int(limit_raw)
        except ValueError:
            return _error_response("INVALID_ACTION", "limit must be an integer", 400)
    try:
        page, next_cursor = await readers.list_run_facts(
            settings,
            limit=limit,
            cursor=params.get("cursor"),
            status=params.get("status"),
        )
    except ValueError as exc:
        return _error_response("INVALID_ACTION", str(exc), 400)
    return JSONResponse(
        {
            "runs": [run_view(facts) for facts in page],
            "next_cursor": next_cursor,
        }
    )


async def get_run(request: Request) -> JSONResponse:
    settings = _settings(request)
    run_id = request.path_params["run_id"]
    try:
        facts = await readers.load_run_facts(settings, run_id)
    except ValueError:
        return _error_response("INVALID_RUN_ID", f"invalid run id: {run_id!r}", 400)
    if facts is None:
        return _error_response("RUN_NOT_FOUND", f"Run {run_id} not found", 404)
    return JSONResponse(
        project_run(facts, action_in_flight=actions.is_in_flight(run_id))
    )


async def _parse_body(request: Request) -> dict:
    body = await request.body()
    if not body:
        return {}
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise ApiError("INVALID_ACTION", "request body must be JSON", 400)
    if not isinstance(data, dict):
        raise ApiError("INVALID_ACTION", "request body must be a JSON object", 400)
    return data


async def run_events(request: Request) -> Response:
    """SSE invalidation for one run (T008C): ``run_changed`` frames only."""
    settings = _settings(request)
    run_id = request.path_params["run_id"]
    try:
        facts = await readers.load_run_facts(settings, run_id)
    except ValueError:
        return _error_response("INVALID_RUN_ID", f"invalid run id: {run_id!r}", 400)
    if facts is None:
        return _error_response("RUN_NOT_FOUND", f"Run {run_id} not found", 404)
    poll_interval = float(getattr(request.app.state, "sse_poll_seconds", 1.0))

    async def stream() -> AsyncIterator[str]:
        async for chunk in sse.run_changed_stream(
            settings,
            run_id,
            poll_interval=poll_interval,
            is_disconnected=request.is_disconnected,
        ):
            yield chunk

    return StreamingResponse(
        stream(),
        media_type=sse.SSE_MEDIA_TYPE,
        headers={"Cache-Control": "no-cache"},
    )


async def approve(request: Request) -> JSONResponse:
    return await _act(request, "approve")


async def deny(request: Request) -> JSONResponse:
    return await _act(request, "deny")


async def _act(request: Request, decision: str) -> JSONResponse:
    settings = _settings(request)
    run_id = request.path_params["run_id"]
    try:
        body = await _parse_body(request)
        receipt = actions.require_paused(settings, run_id)
        actions.validate_target(receipt, body.get("tool_call_id"))
        reason = body.get("reason")
        if reason is not None and not isinstance(reason, str):
            raise ApiError("INVALID_ACTION", "reason must be a string", 400)
        actions.start_resume(settings, run_id, decision=decision, reason=reason)
    except actions.ActionError as exc:
        status = {
            "RUN_NOT_FOUND": 404,
            "RUN_NOT_PAUSED": 409,
            "INVALID_ACTION": 400,
            "FORBIDDEN": 403,
        }.get(exc.code, 400)
        return _error_response(exc.code, exc.message, status)
    except ApiError as exc:
        return _error_response(exc.code, exc.message, exc.status)
    return JSONResponse(
        {"accepted": True, "run_id": run_id, "decision": decision},
        status_code=202,
    )


def api_routes() -> list[Route]:
    return [
        Route("/api/health", health, methods=["GET"]),
        Route("/api/runs", list_runs, methods=["GET"]),
        Route("/api/runs/{run_id}", get_run, methods=["GET"]),
        Route("/api/runs/{run_id}/events", run_events, methods=["GET"]),
        Route("/api/runs/{run_id}/approve", approve, methods=["POST"]),
        Route("/api/runs/{run_id}/deny", deny, methods=["POST"]),
    ]
