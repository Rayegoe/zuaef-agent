from __future__ import annotations

import os

from pydantic_ai.models import Model

from .config import AgentSettings

_DEEPSEEK_MODEL_PREFIX = "deepseek-"


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


def _openai_client(settings: AgentSettings):
    """Deployment-specific OpenAI-compatible client glue.

    Only transport/configuration lives here (base URL, api key, proxy, timeouts,
    retries). Model capability flags belong to the official provider profiles.
    """
    import httpx
    from openai import AsyncOpenAI

    proxy = _http_proxy()
    http_client = (
        httpx.AsyncClient(trust_env=False, proxy=proxy)
        if proxy
        else httpx.AsyncClient(trust_env=False)
    )
    base_url = settings.openai_base_url
    if base_url:
        # Deployment transport glue: operators often paste a full endpoint
        # (…/chat/completions) into LLM_API_BASE, but the OpenAI SDK appends
        # the chat path itself — normalize to the API root so the request is
        # not double-suffixed.
        base_url = base_url.rstrip("/")
        base_url = base_url.removesuffix("/chat/completions")
    return AsyncOpenAI(
        base_url=base_url,
        api_key=settings.openai_api_key or "not-required",
        timeout=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
        http_client=http_client,
    )


def _is_deepseek_model(model_name: str | None) -> bool:
    """DeepSeek models served through the official ``DeepSeekProvider``.

    The official provider/profile owns their capability flags
    (``deepseek_model_profile``), so ZUAEF no longer copies them.
    """
    return bool(model_name) and model_name.startswith(_DEEPSEEK_MODEL_PREFIX)


def _thinking_settings(settings: AgentSettings):
    """Deployment toggle: DeepSeek OpenAI-compatible APIs default to thinking;
    forward the explicit enable/disable through ``extra_body``. This is
    transport/configuration, not a capability profile."""
    if settings.openai_enable_thinking is None:
        return None
    from pydantic_ai.models.openai import OpenAIChatModelSettings

    thinking_type = "enabled" if settings.openai_enable_thinking else "disabled"
    return OpenAIChatModelSettings(extra_body={"thinking": {"type": thinking_type}})


def resolve_model(settings: AgentSettings) -> str | Model:
    """Resolve either a normal PydanticAI model id or an OpenAI-compatible endpoint.

    The OpenAI-specific modules are imported lazily: a normal model id must not
    pay (or fail on) the ``openai`` import. Model capability flags come from
    the official provider profiles (T005): DeepSeek models use the official
    ``DeepSeekProvider``/``deepseek_model_profile``; generic compatible
    endpoints use ``OpenAIProvider`` with its official default profile.
    """
    if not settings.openai_base_url:
        return settings.model

    assert settings.compat_model is not None
    from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    client = _openai_client(settings)

    if settings.openai_api_mode == "responses":
        return OpenAIResponsesModel(
            settings.compat_model, provider=OpenAIProvider(openai_client=client)
        )

    if _is_deepseek_model(settings.compat_model):
        from pydantic_ai.providers.deepseek import DeepSeekProvider

        provider = DeepSeekProvider(openai_client=client)
    else:
        provider = OpenAIProvider(openai_client=client)

    return OpenAIChatModel(
        settings.compat_model,
        provider=provider,
        settings=_thinking_settings(settings),
    )
