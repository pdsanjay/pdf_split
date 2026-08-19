"""Task 3.1 — Parse the ToC into a canonical section map.

The sample policy prints a textual Table of Contents on page 1 as
*dotted-leader* entries — a section title, a run of dots, then the start
page::

    Overview ............................................. 2
    Coverage Policy .................................... 2
    Coding Information ............................... 3
    ...

This module turns that block into an ordered list of :class:`TocEntry`
``(section_title, start_page)`` — the canonical section map that Epic 3's
heading detection and cross-page assembly (tasks 3.2–3.4) build on.

Acceptance criterion (from the task list): *7 expected sections with correct
start pages*. For ``mm_0070_...allergy_testing.pdf`` :func:`parse_toc` returns
exactly the seven ToC sections with the page numbers printed above.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import fitz  # PyMuPDF

PathLike = Union[str, Path]

# A dotted-leader ToC line: <title> <dots> <page>. The leaders are two or more
# dot characters (optionally spaced, as some PDFs render ". . ."); the title is
# everything before them and the page is the trailing integer.
_TOC_LINE = re.compile(r"^(?P<title>.+?)\s*[.…](?:\s*[.…]){1,}\s*(?P<page>\d+)$")

# Where the ToC begins, and lines that mark its end (the sample follows the ToC
# with a "Related Coverage Resources" list that has no page numbers).
_DEFAULT_TOC_MARKER = "table of contents"
_DEFAULT_STOP_MARKERS = ("related coverage resources", "instructions for use")


@dataclass(frozen=True)
class TocEntry:
    """One canonical section: its title and 1-based start page."""

    section_title: str
    start_page: int

    def to_dict(self) -> Dict[str, object]:
        return {"section_title": self.section_title, "start_page": self.start_page}


def parse_toc(
    pdf_path: PathLike,
    *,
    toc_marker: str = _DEFAULT_TOC_MARKER,
    stop_markers: Sequence[str] = _DEFAULT_STOP_MARKERS,
    max_scan_pages: int = 3,
) -> List[TocEntry]:
    """Parse the dotted-leader Table of Contents into an ordered section map.

    Parameters
    ----------
    pdf_path:
        Path to the source PDF.
    toc_marker:
        Case-insensitive text that introduces the ToC. Collection of entries
        starts on the line *after* the line containing this marker.
    stop_markers:
        Case-insensitive texts that end the ToC (e.g. a following
        "Related Coverage Resources" list). Collection also stops at the end
        of the ToC page.
    max_scan_pages:
        How many leading pages to search for ``toc_marker`` before giving up.

    Returns
    -------
    list[TocEntry]
        Sections in document order, each with its printed start page. Empty if
        no ToC is found.

    Raises
    ------
    FileNotFoundError
        If ``pdf_path`` does not exist.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    with fitz.open(path) as doc:
        page_index = _find_toc_page(doc, toc_marker, max_scan_pages)
        if page_index is None:
            return []
        lines = doc[page_index].get_text("text").splitlines()

    return _entries_from_lines(lines, toc_marker, stop_markers)


def _find_toc_page(doc: "fitz.Document", toc_marker: str, max_scan_pages: int) -> Optional[int]:
    """Return the index of the first page whose text contains ``toc_marker``."""
    marker = toc_marker.lower()
    for page_index in range(min(max_scan_pages, doc.page_count)):
        if marker in doc[page_index].get_text("text").lower():
            return page_index
    return None


def _entries_from_lines(
    lines: Sequence[str],
    toc_marker: str,
    stop_markers: Sequence[str],
) -> List[TocEntry]:
    """Collect dotted-leader entries between the ToC marker and a stop marker."""
    marker = toc_marker.lower()
    stops = tuple(s.lower() for s in stop_markers)

    entries: List[TocEntry] = []
    collecting = False

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        lowered = line.lower()
        if not collecting:
            if marker in lowered:
                collecting = True  # start on the next line
            continue

        if any(stop in lowered for stop in stops):
            break

        match = _TOC_LINE.match(line)
        if match:
            title = re.sub(r"\s+", " ", match.group("title")).strip()
            entries.append(TocEntry(section_title=title, start_page=int(match.group("page"))))

    return entries
