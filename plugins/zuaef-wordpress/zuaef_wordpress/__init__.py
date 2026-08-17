"""zuaef-wordpress plugin factory — SPEC v0.3 §47, §56.

Profile config carries non-secret settings only (``site_url``,
``site_label``); credentials come from the environment
(``ZUAEF_WORDPRESS_USERNAME`` / ``ZUAEF_WORDPRESS_APP_PASSWORD``) and never
enter a profile, a CompositionSnapshot or a receipt. Missing credentials are
a loud composition error — the profile fails to resolve instead of running
half-configured.
"""

from __future__ import annotations

import os
from typing import Any

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .client import WordPressClient
from .toolset import make_toolset


def create_plugin(env: PluginEnv, config: dict[str, Any]) -> PluginBundle:
    site_url = str(config.get("site_url") or "").strip()
    if not site_url:
        raise CompositionError(
            "wordpress plugin requires non-secret profile config 'site_url'"
        )
    username = os.getenv("ZUAEF_WORDPRESS_USERNAME")
    app_password = os.getenv("ZUAEF_WORDPRESS_APP_PASSWORD")
    if not username or not app_password:
        raise CompositionError(
            "wordpress credentials missing: set ZUAEF_WORDPRESS_USERNAME and "
            "ZUAEF_WORDPRESS_APP_PASSWORD"
        )
    client = WordPressClient(
        site_url=site_url,
        username=username,
        app_password=app_password,
    )
    return PluginBundle(toolsets=[make_toolset(client)])
