from __future__ import annotations

import os

from pydantic_ai.models import Model

from .config import AgentSettings


def _http_proxy() -> str | None:
    """Resolve an http(s) proxy from the environment, ignoring socks:// entries.

    Local setups run a TUN/transparent proxy whose `all_proxy` points at
    socks://127.0.0.1:port — httpx rejects that scheme without the socksio
    extra, and a broken system resolver (SERVFAIL) makes plain direct connects
    fail too. The http(s) proxy variables carry a working path in that setup;
    anything non-http is deliberately ignored so the client stays deterministic.
    """
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        value = os.environ.get(name)
        if value and value.startswith(("http://", "https://")):
            return value
    return None


def resolve_model(settings: AgentSettings) -> str | Model:
    """Resolve either a normal PydanticAI model id or an OpenAI-compatible endpoint.

    The OpenAI-specific modules are imported lazily: a normal model id must not
    pay (or fail on) the ``openai`` import.
    """
    if not settings.openai_base_url:
        return settings.model

    import httpx
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import (
        OpenAIChatModel,
        OpenAIChatModelSettings,
        OpenAIResponsesModel,
    )
    from pydantic_ai.profiles.openai import OpenAIModelProfile
    from pydantic_ai.providers.openai import OpenAIProvider

    assert settings.compat_model is not None
    proxy = _http_proxy()
    http_client = (
        httpx.AsyncClient(trust_env=False, proxy=proxy)
        if proxy
        else httpx.AsyncClient(trust_env=False)
    )
    client = AsyncOpenAI(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key or "not-required",
        timeout=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
        http_client=http_client,
    )
    provider = OpenAIProvider(openai_client=client)
    if settings.openai_api_mode == "responses":
        return OpenAIResponsesModel(settings.compat_model, provider=provider)
    profile = OpenAIModelProfile(
        openai_supports_strict_tool_definition=settings.openai_strict_tool_definitions,
        openai_chat_supports_multiple_system_messages=settings.openai_multiple_system_messages,
        openai_chat_supports_max_completion_tokens=settings.openai_supports_max_completion_tokens,
    )
    model_settings = None
    if settings.openai_enable_thinking is not None:
        # DeepSeek's OpenAI-compatible API defaults V4 models to thinking mode.
        # Forced tool selection is rejected in that mode, so forward the explicit
        # toggle from the copied provider configuration through `extra_body`.
        thinking_type = "enabled" if settings.openai_enable_thinking else "disabled"
        model_settings = OpenAIChatModelSettings(
            extra_body={"thinking": {"type": thinking_type}}
        )
    return OpenAIChatModel(
        settings.compat_model,
        provider=provider,
        profile=profile,
        settings=model_settings,
    )
