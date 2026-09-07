"""zuaef-quant: A-share decision capability for the ZUAEF agent.

This package must stay importable in the quant side environment, which has
no pydantic_ai: submodules like ``freshness`` and ``watchlist`` are
stdlib-only host logic shared with ``tools/quant_trading_monitor.py``.
The plugin capability (``zuaef_quant.plugin``) depends on pydantic_ai and
is therefore imported lazily — never at package import time.
"""

__all__ = ["create_plugin"]


def __getattr__(name):
    if name == "create_plugin":
        from .plugin import create_plugin

        return create_plugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
