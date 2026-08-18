# Extraction layer — `pdf_splitter`

Implements **Epic 2 / task 2.1 — Extract text with layout & coordinates**
from the [POC task list](../transcripts/2026-08-05_discussion.md).

PyMuPDF (`fitz`) reads a PDF into **ordered, reading-order text blocks** whose
spans carry **font metadata**: font name, size, bold/italic flags, colour and
y-position.

> **Acceptance:** ordered blocks with font metadata. ✅

## Layout

```
src/
├── pdf_splitter/
│   ├── __init__.py      # public API: extract_layout, PageLayout, Block, Span
│   ├── models.py        # typed data model (Span / Block / PageLayout)
│   ├── extraction.py    # extract_layout() — the task 2.1 core
│   ├── cli.py           # command-line entry point
│   └── __main__.py      # enables `python -m pdf_splitter`
├── tests/
│   └── test_extraction.py
├── conftest.py          # puts src/ on the import path for pytest
└── requirements.txt
```

## Install

```bash
pip install -r src/requirements.txt
```

## Use as a library

```python
from pdf_splitter import extract_layout

pages = extract_layout("coverage_policy/mm_0070_..._allergy_testing.pdf")
for page in pages:
    for block in page.blocks:          # already in reading order
        print(page.page_number, round(block.y_top), block.dominant_size,
              block.is_bold, block.text)
```

### Data model

| Object | Key fields |
|---|---|
| `PageLayout` | `page_number` (1-based), `width`, `height`, `blocks` |
| `Block` | `index` (reading order), `bbox`, `y_top`, `text`, `dominant_font`, `dominant_size`, `is_bold`, `spans` |
| `Span` | `text`, `font`, `size`, `flags`, `bold`, `italic`, `color`, `bbox`, `y` |

**Bold detection** reads *both* the PyMuPDF flag bit (`1 << 4`) and the font
name (`Verdana-Bold`, `…-Black`, …), because the sample policy encodes weight
only in the font name and leaves the bold flag unset.

**Reading order** sorts blocks top-to-bottom then left-to-right (y-top rounded
to whole points so spans on one visual line group before column ordering).

## Use from the command line

Run as a module (from the `src` directory):

```bash
cd src

# whole document -> JSON file
python -m pdf_splitter ../coverage_policy/mm_0070_coveragepositioncriteria_allergy_testing.pdf \
    --out ../output/layout.json --pretty

# preview pages 2-3 on stdout
python -m pdf_splitter ../coverage_policy/mm_0070_coveragepositioncriteria_allergy_testing.pdf \
    --pages 2-3 --pretty
```

| Flag | Meaning |
|---|---|
| `--out PATH` | Write JSON here (default: stdout). Parent dirs created. |
| `--pages 2-3,5` | 1-based pages to extract (default: all). |
| `--pretty` | Indent the JSON. |
| `--keep-empty` | Keep blocks with no visible text. |

## Test

```bash
cd src
python -m pytest -q
```
