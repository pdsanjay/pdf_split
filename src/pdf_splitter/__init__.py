"""Section-Aware PDF Splitter for RAG — POC package.

Public surface for the extraction layer (Epic 2, task 2.1):

    from pdf_splitter import extract_layout, PageLayout, Block, Span

`extract_layout` turns a PDF into ordered, reading-order text blocks whose
spans carry font metadata (size, bold/italic flags, colour, y-position).
"""

from .models import Block, PageLayout, Span
from .extraction import extract_layout
from .boilerplate import strip_boilerplate, StripResult

__all__ = ["extract_layout", "PageLayout", "Block", "Span", "strip_boilerplate", "StripResult"]

__version__ = "0.1.0"
