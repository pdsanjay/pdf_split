"""Typed data model for the extraction layer.

The extractor emits a list of :class:`PageLayout` objects, one per page. Each
page holds reading-order :class:`Block` objects, and each block holds the
:class:`Span` objects PyMuPDF produced. Spans are the unit that carries font
metadata (size, bold flag, colour, position); blocks and pages add structure
and reading order on top.

All coordinates are in PDF points with the origin at the top-left of the page
(PyMuPDF's default), so a smaller ``y`` means higher on the page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

# PyMuPDF span ``flags`` is a bitmask. Only the bits we care about are named
# here; see https://pymupdf.readthedocs.io/ (TextPage flags).
_FLAG_SUPERSCRIPT = 1 << 0
_FLAG_ITALIC = 1 << 1
_FLAG_SERIFED = 1 << 2
_FLAG_MONOSPACED = 1 << 3
_FLAG_BOLD = 1 << 4

BBox = Tuple[float, float, float, float]


def _round_bbox(bbox: BBox, ndigits: int = 2) -> BBox:
    return tuple(round(float(v), ndigits) for v in bbox)  # type: ignore[return-value]


@dataclass(frozen=True)
class Span:
    """A run of characters sharing one font, size and colour.

    ``bold`` and ``italic`` are resolved from *both* the PyMuPDF flag bitmask
    and the font name, because many PDFs (including the sample policy doc)
    encode weight only in the font name (e.g. ``Verdana-Bold``) and leave the
    bold flag unset.
    """

    text: str
    font: str
    size: float
    flags: int
    color: int
    bbox: BBox
    origin: Tuple[float, float]

    @property
    def y(self) -> float:
        """Baseline y-position of the span (top-left origin)."""
        return self.origin[1]

    @property
    def bold(self) -> bool:
        return bool(self.flags & _FLAG_BOLD) or _name_says_bold(self.font)

    @property
    def italic(self) -> bool:
        return bool(self.flags & _FLAG_ITALIC) or "italic" in self.font.lower() or "oblique" in self.font.lower()

    @classmethod
    def from_fitz(cls, span: Dict[str, Any]) -> "Span":
        """Build a :class:`Span` from a PyMuPDF ``dict``-mode span."""
        return cls(
            text=span.get("text", ""),
            font=span.get("font", ""),
            size=round(float(span.get("size", 0.0)), 2),
            flags=int(span.get("flags", 0)),
            color=int(span.get("color", 0)),
            bbox=_round_bbox(span["bbox"]),
            origin=(round(float(span["origin"][0]), 2), round(float(span["origin"][1]), 2)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "font": self.font,
            "size": self.size,
            "flags": self.flags,
            "bold": self.bold,
            "italic": self.italic,
            "color": self.color,
            "bbox": list(self.bbox),
            "y": self.y,
        }


@dataclass
class Block:
    """A text block: a group of lines/spans that PyMuPDF laid out together.

    ``index`` is the reading-order position within the page (0-based, top to
    bottom then left to right).
    """

    index: int
    page_number: int
    bbox: BBox
    spans: List[Span] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Block text with a single space between spans, whitespace-normalised."""
        return " ".join(s.text.strip() for s in self.spans if s.text.strip())

    @property
    def y_top(self) -> float:
        return self.bbox[1]

    @property
    def dominant_size(self) -> float:
        """Font size covering the most characters in the block (0 if empty)."""
        if not self.spans:
            return 0.0
        weight: Dict[float, int] = {}
        for s in self.spans:
            weight[s.size] = weight.get(s.size, 0) + len(s.text.strip())
        return max(weight, key=weight.get)  # type: ignore[arg-type]

    @property
    def dominant_font(self) -> str:
        if not self.spans:
            return ""
        weight: Dict[str, int] = {}
        for s in self.spans:
            weight[s.font] = weight.get(s.font, 0) + len(s.text.strip())
        return max(weight, key=weight.get)  # type: ignore[arg-type]

    @property
    def is_bold(self) -> bool:
        """True when the majority of characters in the block are bold."""
        bold_chars = sum(len(s.text.strip()) for s in self.spans if s.bold)
        total = sum(len(s.text.strip()) for s in self.spans)
        return total > 0 and bold_chars * 2 >= total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "page_number": self.page_number,
            "bbox": list(self.bbox),
            "y_top": self.y_top,
            "text": self.text,
            "dominant_font": self.dominant_font,
            "dominant_size": self.dominant_size,
            "is_bold": self.is_bold,
            "spans": [s.to_dict() for s in self.spans],
        }


@dataclass
class PageLayout:
    """All reading-order text blocks for a single page."""

    page_number: int  # 1-based
    width: float
    height: float
    blocks: List[Block] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "blocks": [b.to_dict() for b in self.blocks],
        }


def _name_says_bold(font: str) -> bool:
    lowered = font.lower()
    return any(token in lowered for token in ("bold", "black", "heavy", "semibold", "-bd"))
