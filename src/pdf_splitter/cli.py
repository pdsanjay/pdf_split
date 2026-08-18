"""Command-line entry point for the extraction layer.

Examples
--------
Dump the whole sample PDF to ``output/layout.json``::

    python -m pdf_splitter ../coverage_policy/mm_0070_..._allergy_testing.pdf \
        --out ../output/layout.json

Preview only pages 2-3 as pretty JSON on stdout::

    python -m pdf_splitter sample.pdf --pages 2-3 --pretty
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .extraction import extract_layout


def _parse_pages(spec: Optional[str]) -> Optional[List[int]]:
    """Parse ``"2-3,5"`` into ``[2, 3, 5]`` (1-based). ``None`` -> all pages."""
    if not spec:
        return None
    pages: List[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return sorted(set(pages))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf_splitter",
        description="Extract ordered, font-annotated text blocks from a PDF (task 2.1).",
    )
    parser.add_argument("pdf", type=Path, help="Path to the source PDF.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON here. Defaults to stdout.",
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="1-based pages to extract, e.g. '2-3,5'. Default: all.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Indent the JSON output for readability.",
    )
    parser.add_argument(
        "--keep-empty",
        action="store_true",
        help="Keep blocks that contain no visible text.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        layouts = extract_layout(
            args.pdf,
            pages=_parse_pages(args.pages),
            keep_empty_blocks=args.keep_empty,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "source_file": str(args.pdf),
        "page_count": len(layouts),
        "block_count": sum(len(p.blocks) for p in layouts),
        "pages": [p.to_dict() for p in layouts],
    }
    text = json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(
            f"Wrote {payload['block_count']} blocks across {payload['page_count']} "
            f"page(s) to {args.out}",
            file=sys.stderr,
        )
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
