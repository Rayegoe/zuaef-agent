"""Thin zuaef-agent adapter for the external ZUAEF Writing Intelligence Pack."""

from .plugin import build_plugin
from .toolset import SanlianCorpusToolset, build_sanlian_toolset

__all__ = ["SanlianCorpusToolset", "build_plugin", "build_sanlian_toolset"]
