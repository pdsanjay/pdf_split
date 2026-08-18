"""Acceptance tests for task 2.1 — ordered blocks with font metadata.

Run from the ``src`` directory::

    cd src
    python -m pytest
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf_splitter import Block, PageLayout, Span, extract_layout

SAMPLE_PDF = (
    Path(__file__).resolve().parents[2]
    / "coverage_policy"
    / "mm_0070_coveragepositioncriteria_allergy_testing.pdf"
)


@pytest.fixture(scope="module")
def layouts() -> list[PageLayout]:
    assert SAMPLE_PDF.is_file(), f"sample PDF missing: {SAMPLE_PDF}"
    return extract_layout(SAMPLE_PDF)


def test_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        extract_layout("does-not-exist.pdf")


def test_one_layout_per_page(layouts: list[PageLayout]) -> None:
    # The sample policy is 14 pages.
    assert len(layouts) == 14
    assert [p.page_number for p in layouts] == list(range(1, 15))


def test_pages_filter_is_one_based() -> None:
    subset = extract_layout(SAMPLE_PDF, pages=[2, 3])
    assert [p.page_number for p in subset] == [2, 3]


def test_blocks_are_in_reading_order(layouts: list[PageLayout]) -> None:
    for page in layouts:
        assert page.blocks, f"page {page.page_number} has no text blocks"
        # index is contiguous 0..n-1
        assert [b.index for b in page.blocks] == list(range(len(page.blocks)))
        # non-decreasing y-top == top-to-bottom order
        tops = [round(b.y_top) for b in page.blocks]
        assert tops == sorted(tops)


def test_spans_carry_font_metadata(layouts: list[PageLayout]) -> None:
    span_seen = False
    for page in layouts:
        for block in page.blocks:
            for span in block.spans:
                span_seen = True
                assert isinstance(span, Span)
                assert span.font
                assert span.size > 0
                assert isinstance(span.bold, bool)
                assert isinstance(span.italic, bool)
                assert span.y == span.origin[1]
    assert span_seen, "no spans extracted from sample PDF"


def test_bold_detected_from_font_name() -> None:
    # Bold encoded only in the font name, flags bit unset.
    span = Span(
        text="Overview",
        font="Verdana-Bold",
        size=12.0,
        flags=0,
        color=0,
        bbox=(0, 0, 10, 10),
        origin=(0, 10),
    )
    assert span.bold is True


def test_bold_detected_from_flag_bit() -> None:
    span = Span(
        text="X",
        font="Verdana",
        size=10.0,
        flags=1 << 4,  # bold bit
        color=0,
        bbox=(0, 0, 5, 5),
        origin=(0, 5),
    )
    assert span.bold is True


def test_block_text_and_dominant_metadata() -> None:
    block = Block(
        index=0,
        page_number=1,
        bbox=(0, 0, 100, 20),
        spans=[
            Span("General ", "Verdana-Bold", 12.0, 0, 0, (0, 0, 40, 12), (0, 10)),
            Span("Background", "Verdana-Bold", 12.0, 0, 0, (40, 0, 100, 12), (40, 10)),
        ],
    )
    assert block.text == "General Background"
    assert block.dominant_size == 12.0
    assert block.dominant_font == "Verdana-Bold"
    assert block.is_bold is True


def test_known_heading_present_as_bold_span(layouts: list[PageLayout]) -> None:
    """The 'Coverage Policy' heading is a large bold span.

    PyMuPDF groups a whole section body into one block, so a heading is a span
    *inside* a block, not a standalone block. Isolating it into its own chunk
    is Epic 3 (section detection); task 2.1 only has to surface the span with
    correct font metadata — larger and bold relative to the ~10pt body text.
    """
    heading_spans = [
        span
        for page in layouts
        for block in page.blocks
        for span in block.spans
        if span.text.strip() == "Coverage Policy"
    ]
    assert heading_spans, "expected a 'Coverage Policy' span"
    assert any(s.bold and s.size >= 12 for s in heading_spans), (
        "expected 'Coverage Policy' to appear as a large bold heading span"
    )
