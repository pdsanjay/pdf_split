"""Task 2.1 — Extract text with layout / coordinates.

Uses PyMuPDF (``fitz``) to read a PDF into ordered text blocks whose spans
carry font metadata: font name, size, bold/italic flags, colour and
y-position.

Acceptance criterion (from the task list): *ordered blocks with font
metadata*. :func:`extract_layout` returns blocks sorted into human reading
order (top to bottom, then left to right) with that metadata attached.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Union

import fitz  # PyMuPDF

from .models import Block, PageLayout, Span

PathLike = Union[str, Path]


def extract_layout(
    pdf_path: PathLike,
    pages: Optional[Iterable[int]] = None,
    *,
    keep_empty_blocks: bool = False,
) -> List[PageLayout]:
    """Extract ordered, font-annotated text blocks from ``pdf_path``.

    Parameters
    ----------
    pdf_path:
        Path to the source PDF.
    pages:
        Optional iterable of **1-based** page numbers to restrict extraction
        to. ``None`` (default) processes every page.
    keep_empty_blocks:
        When ``False`` (default), blocks whose spans contain no visible text
        are dropped. Set ``True`` to keep them (e.g. for debugging layout).

    Returns
    -------
    list[PageLayout]
        One :class:`PageLayout` per processed page, in document order. Blocks
        within a page are in reading order and carry font metadata via their
        spans.

    Raises
    ------
    FileNotFoundError
        If ``pdf_path`` does not exist.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    wanted = set(pages) if pages is not None else None
    layouts: List[PageLayout] = []

    with fitz.open(path) as doc:
        for page_index in range(doc.page_count):
            page_number = page_index + 1  # expose 1-based numbers
            if wanted is not None and page_number not in wanted:
                continue

            page = doc[page_index]
            raw = page.get_text("dict")
            blocks = _blocks_from_page(raw, page_number, keep_empty_blocks)

            layouts.append(
                PageLayout(
                    page_number=page_number,
                    width=float(raw.get("width", page.rect.width)),
                    height=float(raw.get("height", page.rect.height)),
                    blocks=blocks,
                )
            )

    return layouts


def _blocks_from_page(raw_page: dict, page_number: int, keep_empty: bool) -> List[Block]:
    """Convert one PyMuPDF ``dict`` page into ordered :class:`Block` objects."""
    collected: List[Block] = []

    for raw_block in raw_page.get("blocks", []):
        # type 0 == text block; type 1 == image block (skipped here).
        if raw_block.get("type", 0) != 0:
            continue

        spans: List[Span] = []
        for line in raw_block.get("lines", []):
            for raw_span in line.get("spans", []):
                spans.append(Span.from_fitz(raw_span))

        if not keep_empty and not any(s.text.strip() for s in spans):
            continue

        collected.append(
            Block(
                index=-1,  # assigned after sorting into reading order
                page_number=page_number,
                bbox=tuple(round(float(v), 2) for v in raw_block["bbox"]),  # type: ignore[arg-type]
                spans=spans,
            )
        )

    # Reading order: top-to-bottom, then left-to-right. Rounding the y-top to
    # whole points groups spans that sit on the same visual line despite tiny
    # sub-pixel differences before falling back to x for column order.
    collected.sort(key=lambda b: (round(b.bbox[1]), b.bbox[0]))
    for i, block in enumerate(collected):
        block.index = i

    return collected
