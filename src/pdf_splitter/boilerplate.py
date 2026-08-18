"""Task — Strip repeating headers/footers.

Removes boilerplate that repeats on (nearly) every page — page numbers such as
``Page 1 of 14`` and running heads such as ``Medical Coverage Policy: 0070`` —
so downstream steps see body text only.

Two signals decide what is boilerplate:

1. **Position** — the block sits in the top or bottom margin band of the page
   (a header/footer zone), not in the body.
2. **Repetition** — the block's *normalised signature* (digits masked, case and
   whitespace folded) recurs on a large fraction of pages. Masking digits makes
   ``Page 1 of 14`` and ``Page 2 of 14`` share one signature.

A block is stripped when it repeats across pages *and* lives in a margin band,
or when it matches a known boilerplate pattern outright. The design goal (from
the task's acceptance criterion) is *no boilerplate in body text; stripped count
≈ number of pages*.

Usage::

    from pdf_splitter import extract_layout, strip_boilerplate

    layouts = extract_layout("policy.pdf")
    result = strip_boilerplate(layouts)
    print(result.stripped_count)   # ≈ pages
    clean = result.layouts         # PageLayouts with header/footer blocks gone
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Pattern, Sequence

from .models import Block, PageLayout

# Known boilerplate phrasings, stripped regardless of position/repetition. These
# match the running head and page footer in the sample allergy-testing policy;
# extend via ``extra_patterns`` for other documents.
_DEFAULT_PATTERNS: List[Pattern[str]] = [
    re.compile(r"^page\s+\d+\s+of\s+\d+$", re.IGNORECASE),
    re.compile(r"^medical\s+coverage\s+policy\s*[:#-]?\s*\d+$", re.IGNORECASE),
]


def _signature(text: str) -> str:
    """Fold a block's text into a page-independent signature.

    Digits become ``#`` and runs of whitespace collapse to one space, so the
    same running head with a changing page number maps to a single signature.
    """
    masked = re.sub(r"\d+", "#", text.lower())
    return re.sub(r"\s+", " ", masked).strip()


@dataclass
class StripResult:
    """Outcome of :func:`strip_boilerplate`.

    ``layouts`` are new :class:`PageLayout` objects with boilerplate blocks
    removed and block ``index`` values re-numbered into a contiguous reading
    order. The originals are left untouched.
    """

    layouts: List[PageLayout]
    stripped_count: int = 0
    stripped_signatures: List[str] = field(default_factory=list)


def strip_boilerplate(
    layouts: Sequence[PageLayout],
    *,
    min_repeat_ratio: float = 0.5,
    margin_ratio: float = 0.12,
    extra_patterns: Sequence[Pattern[str]] | None = None,
) -> StripResult:
    """Remove repeating header/footer blocks from extracted page layouts.

    Parameters
    ----------
    layouts:
        Page layouts as returned by :func:`pdf_splitter.extract_layout`.
    min_repeat_ratio:
        Fraction of pages a signature must appear on (in a margin band) to
        count as boilerplate. ``0.5`` means "on at least half the pages".
    margin_ratio:
        Height fraction, measured from each edge, that defines the header
        (top) and footer (bottom) bands. ``0.12`` ≈ top/bottom 12% of a page.
    extra_patterns:
        Additional compiled regexes to treat as always-boilerplate, matched
        against each block's whole text (case handled by the pattern).

    Returns
    -------
    StripResult
        Cleaned layouts plus how many blocks were stripped and which
        signatures triggered removal.
    """
    patterns = list(_DEFAULT_PATTERNS)
    if extra_patterns:
        patterns.extend(extra_patterns)

    page_count = len(layouts) or 1

    # Pass 1 — count each signature's appearances inside margin bands.
    band_counts: Dict[str, int] = {}
    for page in layouts:
        top_band = page.height * margin_ratio
        bottom_band = page.height * (1.0 - margin_ratio)
        for block in page.blocks:
            if _in_margin(block, top_band, bottom_band):
                sig = _signature(block.text)
                if sig:
                    band_counts[sig] = band_counts.get(sig, 0) + 1

    repeating = {
        sig
        for sig, count in band_counts.items()
        if count >= min_repeat_ratio * page_count
    }

    # Pass 2 — rebuild each page without its boilerplate blocks.
    cleaned: List[PageLayout] = []
    stripped_count = 0
    stripped_sigs: set[str] = set()

    for page in layouts:
        top_band = page.height * margin_ratio
        bottom_band = page.height * (1.0 - margin_ratio)
        kept: List[Block] = []

        for block in page.blocks:
            sig = _signature(block.text)
            matches_pattern = any(p.match(block.text.strip()) for p in patterns)
            repeats_in_margin = sig in repeating and _in_margin(block, top_band, bottom_band)

            if matches_pattern or repeats_in_margin:
                stripped_count += 1
                if sig:
                    stripped_sigs.add(sig)
                continue
            kept.append(block)

        # Re-number kept blocks so index stays a contiguous reading order.
        for new_index, block in enumerate(kept):
            block.index = new_index

        cleaned.append(
            PageLayout(
                page_number=page.page_number,
                width=page.width,
                height=page.height,
                blocks=kept,
            )
        )

    return StripResult(
        layouts=cleaned,
        stripped_count=stripped_count,
        stripped_signatures=sorted(stripped_sigs),
    )


def _in_margin(block: Block, top_band: float, bottom_band: float) -> bool:
    """True when the block sits in the header (top) or footer (bottom) band."""
    return block.y_top <= top_band or block.y_top >= bottom_band
