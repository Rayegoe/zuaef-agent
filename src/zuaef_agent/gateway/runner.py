"""Gateway process runner — SPEC v0.3 §59–§66.

Startup validation (fail closed, in spec order), foreground blocking
Telegram long-polling, cursor persistence, restart recovery and graceful
KeyboardInterrupt shutdown. Stage A: single process, single dispatcher,
serial agent execution — no daemon, no PID manager.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from ..config import AgentSettings
from . import bridge
from .service import GatewayService
from .store import GatewayStore
from .telegram import TelegramAdapter

logger = logging.getLogger(__name__)

DEFAULT_POLL_TIMEOUT = 30
DEFAULT_APPROVAL_TTL = 86400
DEFAULT_MAX_UPLOAD_BYTES = 20971520
DEFAULT_MAX_ARTIFACT_BYTES = 10485760


@dataclass(frozen=True)
class GatewayConfig:
    surface: str = "telegram"
    profile: str | None = None
    config_root: Path | None = None
    telegram_token: str | None = None
    allowed_user_ids: frozenset[str] = field(default_factory=frozenset)
    poll_timeout: int = DEFAULT_POLL_TIMEOUT
    poll_retry_seconds: int = 5
    approval_ttl_seconds: int = DEFAULT_APPROVAL_TTL
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES
    max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


def load_gateway_config(args: Any) -> GatewayConfig:
    """Merge environment and CLI flags; no validation of presence happens
    here — that is the startup sequence's job (fail closed)."""
    allowed = frozenset(
        user.strip()
        for user in os.getenv("ZUAEF_TELEGRAM_ALLOWED_USERS", "").split(",")
        if user.strip()
    )
    return GatewayConfig(
        surface=getattr(args, "surface", "telegram"),
        profile=getattr(args, "profile", None)
        or os.getenv("ZUAEF_GATEWAY_DEFAULT_PROFILE"),
        config_root=getattr(args, "config_root", None),
        telegram_token=os.getenv("ZUAEF_TELEGRAM_BOT_TOKEN")
        or os.getenv("TELEGRAM_BOT_TOKEN"),
        allowed_user_ids=allowed,
        poll_timeout=_env_int("ZUAEF_TELEGRAM_POLL_TIMEOUT", DEFAULT_POLL_TIMEOUT),
        approval_ttl_seconds=_env_int("ZUAEF_GATEWAY_APPROVAL_TTL", DEFAULT_APPROVAL_TTL),
        max_upload_bytes=_env_int(
            "ZUAEF_GATEWAY_MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES
        ),
        max_artifact_bytes=_env_int(
            "ZUAEF_GATEWAY_MAX_ARTIFACT_BYTES", DEFAULT_MAX_ARTIFACT_BYTES
        ),
    )


def default_adapter(config: GatewayConfig, settings: AgentSettings) -> TelegramAdapter:
    assert config.telegram_token is not None
    return TelegramAdapter(
        token=config.telegram_token,
        allowed_user_ids=set(config.allowed_user_ids),
        workspace_root=settings.workspace_root.resolve(),
        poll_timeout=config.poll_timeout,
        max_upload_bytes=config.max_upload_bytes,
    )


def run_gateway(
    *,
    config: GatewayConfig,
    settings: AgentSettings,
    adapter_factory=None,
) -> int:
    """Foreground gateway process. Startup validation order (SPEC §61):

    settings validation → gateway DB init → profile resolve → Telegram token
    present → allowed users present → Telegram getMe probe.

    Any failure raises before polling starts; the CLI turns that into a
    non-zero exit.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # httpx logs full request URLs at INFO — which embed the bot token in
    # /bot<TOKEN>/ paths. The gateway must never log the token (SPEC §17/§71).
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # 1. Settings are validated at AgentSettings construction (limits, roots).

    # 2. Gateway routing-state DB.
    store = GatewayStore(settings.state_root / "gateway.sqlite3")

    # 3. Default profile must resolve before the first user message.
    if config.profile:
        bridge.validate_profile(
            config.profile, settings, config_root=config.config_root
        )

    # 4 + 5. Fail closed: no token, no empty allowlist.
    if not config.telegram_token:
        raise ValueError("ZUAEF_TELEGRAM_BOT_TOKEN is required to start the gateway")
    if not config.allowed_user_ids:
        raise ValueError(
            "ZUAEF_TELEGRAM_ALLOWED_USERS must list at least one user id "
            "(gateway fails closed; there is no allow-all default)"
        )

    # Surface selection (Stage A: Telegram only).
    if config.surface != "telegram":
        raise ValueError(
            f"unsupported surface {config.surface!r}: Stage A supports telegram only"
        )

    adapter = (
        adapter_factory(config, settings)
        if adapter_factory is not None
        else default_adapter(config, settings)
    )

    # 6. Live probe — a dead token must never reach the polling loop.
    adapter.probe()
    logger.info("surface connected: %s", config.surface)

    service = GatewayService(
        settings=settings,
        store=store,
        surface=adapter,
        default_profile=config.profile,
        config_root=config.config_root,
        approval_ttl_seconds=config.approval_ttl_seconds,
        max_artifact_bytes=config.max_artifact_bytes,
        allowed_user_ids=set(config.allowed_user_ids),
    )

    # Restart recovery: reconcile routing state against the ReceiptStore.
    for warning in service.recover_sessions():
        logger.warning("%s", warning)

    cursor = store.get_cursor(config.surface)
    if cursor is not None:
        try:
            adapter.set_offset(int(cursor))
        except ValueError:
            logger.warning("ignoring invalid stored cursor %r", cursor)

    logger.info("gateway started: surface=%s profile=%s", config.surface, config.profile)
    try:
        while True:
            # Transient transport failures (proxy disconnects during long
            # polling, Telegram 5xx) must not kill the gateway: the cursor
            # has not advanced, so the next poll simply re-receives the batch
            # (SPEC §63). KeyboardInterrupt still shuts down cleanly.
            try:
                events = adapter.poll_once(timeout_seconds=config.poll_timeout)
            except httpx.HTTPError as exc:
                logger.warning("surface poll failed (retrying): %s", exc)
                time.sleep(config.poll_retry_seconds)
                continue
            for event in events:
                try:
                    service.handle(event)
                except httpx.HTTPError as exc:
                    logger.warning("gateway event handling failed: %s", exc)
            pending = adapter.pending_cursor()
            if pending is not None:
                store.set_cursor(config.surface, pending)
    except KeyboardInterrupt:
        logger.info("gateway stopped")
        adapter.close()
        return 0
