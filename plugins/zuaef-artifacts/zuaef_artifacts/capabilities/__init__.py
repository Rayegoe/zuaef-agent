"""Capability assembly for the four artifact formats.

Each format is one declarative PydanticAI ``Capability`` with a
business-semantic id/description, deferred loading (tools and instructions
stay hidden until the model loads the capability via ``load_capability``),
and plugin-local guidance injected as capability instructions. The model
never needs a format command: discovery is driven by the description text.
"""

from __future__ import annotations

from ..contracts import ArtifactBounds
from .docx import build_capability as build_docx_capability
from .pdf import build_capability as build_pdf_capability
from .slides import build_capability as build_slides_capability
from .spreadsheet import build_capability as build_spreadsheet_capability

__all__ = [
    "ArtifactBounds",
    "build_docx_capability",
    "build_pdf_capability",
    "build_slides_capability",
    "build_spreadsheet_capability",
]
