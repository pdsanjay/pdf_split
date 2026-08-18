# Discussion Transcript — 2026-08-05

**Project:** Section-Aware PDF Splitter for RAG (POC)
**Working directory:** `poc_01`
**Participants:** User (pdsanjay@hotmail.com), Claude Code

---

# Part A — Original Discussion (verbatim)

### User
> Please review the document. We have to develop a POC for linear, so develop a list of tasks first. The target is to develop a python code that parses the document and split the pdf in different sections. We will use it for creating RAG that parses only relevant sections. At present the split takes page-wise that is inherently faulty of missing relevant sections that fall in next page.

### Claude
Reviewed the project and the document. Findings:

**File:** `coverage_policy/mm_0070_coveragepositioncriteria_allergy_testing.pdf` — a 14-page Cigna *Medical Coverage Policy 0070: Allergy Testing and Non-Pharmacologic Treatment*.

Important structural facts for a section-splitter:

- The PDF has a **machine-readable Table of Contents** with dotted-leader entries mapping section → start page:

| Section | Starts p. | Actually spans |
|---|---|---|
| Overview | 2 | 2 |
| Coverage Policy | 2 | 2–3 |
| Coding Information | 3 | 3–4 |
| General Background | 4 | 4–10 |
| Health Equity Considerations | 10 | 10–11 |
| References | 11 | 11–13 |
| Revision Details | 13 | 13–14 |

- **Sections routinely cross page boundaries** (Coverage Policy 2→3, Coding Information 3→4, General Background 4→10) — this is exactly why page-wise splitting drops relevant content.
- Sections have **sub-headings** worth chunking on (e.g. *General Background* → *Testing* → *In Vivo Allergy Testing* / *In Vitro Allergy Testing*; *Treatment*; and Medically Necessary / Not Covered blocks).
- There are **CPT code tables** (Coding Information) that need table-aware handling, and repeating **page headers/footers** (`Page X of 14`, `Medical Coverage Policy: 0070`) that must be stripped.
- Because a reliable ToC exists, section boundaries can be detected robustly rather than guessed.

Then asked two clarifying questions:
1. **Delivery** — markdown list only / create in Linear via API / save as project file, and whether "Linear" is the PM tool or the app codename.
2. **Granularity** — top-level ToC sections / sections + sub-headings / decide during POC.

### User (answers)
- Delivery: *"Provide the list and I will enter the task in linear app."*
- Granularity: *"Sections + sub-headings (Recommended)."*

### Claude
Delivered the Linear-ready task breakdown (reproduced in full in Part B below), noting:
- **3.4 is the headline task** — direct fix for the page-wise problem.
- **5.2** is stretch for the POC — the sample doc has a clean ToC.

Closed by offering to start implementing (Epics 1–3 against the sample PDF).

### User
> develop a .md file in folder transcripts that stores all the discussion for today

### Claude
Created `transcripts/2026-08-05_discussion.md` capturing the discussion, then (this revision) restructured it into two parts: original discussion and summary.

---

# Part B — Summary

## 1. Objective
Develop a POC that parses a coverage-policy PDF and **splits it into semantic sections** for a RAG pipeline. Current approach splits **page-wise**, which is faulty because content flowing onto the next page is separated from its section. First deliverable: a **task list** for Linear.

## 2. Document Reviewed
- **File:** `coverage_policy/mm_0070_coveragepositioncriteria_allergy_testing.pdf`
- **What:** 14-page Cigna *Medical Coverage Policy 0070: Allergy Testing and Non-Pharmacologic Treatment*.
- **Key facts:** machine-readable ToC (section → start page); sections cross page boundaries; sub-headings worth chunking; CPT code tables; repeating headers/footers to strip; clean ToC enables robust boundary detection.

## 3. Decisions
| Question | Decision |
|---|---|
| Task list delivery | Provide as **markdown list**; user enters tasks into Linear manually. |
| Chunk granularity | **Sections + sub-headings** for better retrieval precision. |

## 4. Task Breakdown (Linear-ready)

**Project:** Section-Aware PDF Splitter for RAG (POC)
**Goal:** Replace page-wise splitting with section-aware splitting so RAG retrieves complete sections even when they cross page boundaries. Validated against `mm_0070_...allergy_testing.pdf`.
**POC success criteria:** One chunk per top-level section and per sub-heading, each with full text regardless of page breaks, with clean metadata — verified against the 7 known ToC sections.

### Epic 1 — Project setup
- **1.1 Scaffold POC repo & environment** — `src/`, `tests/`, `output/`; `requirements.txt` (`pymupdf`, `pypdf`, `pytest`); pin Python; README stub; `.gitignore`. *Acceptance:* deps install; sample PDF loads in smoke script.
- **1.2 Define the target output schema** — chunk JSON: `section_title`, `parent_section`, `level`, `page_start`, `page_end`, `text`, `source_file`, `doc_id`, `effective_date`. *Acceptance:* documented schema + sample chunk validates.

### Epic 2 — Extraction layer
- **2.1 Extract text with layout/coordinates** — PyMuPDF (`fitz`) spans per page with font size, bold flag, y-position. *Acceptance:* ordered blocks with font metadata.
- **2.2 Strip repeating headers/footers** — remove `Page X of 14`, `Medical Coverage Policy: 0070`. *Acceptance:* no boilerplate in body text; stripped count ≈ pages.

### Epic 3 — Section detection (core)
- **3.1 Parse the ToC into a canonical section map** — parse dotted-leader entries into ordered `(section_title, start_page)`. *Acceptance:* 7 expected sections with correct start pages.
- **3.2 Detect section headings in the body** — match ToC titles to standalone heading lines; font-size/bold corroboration; locate page + y. *Acceptance:* every section anchored; no false positives.
- **3.3 Detect sub-headings within sections** — second-level headings + parent linkage. *Acceptance:* correct hierarchy for sample doc.
- **3.4 Assemble sections across page boundaries** *(key deliverable)* — assign blocks to most recent heading; concatenate across page breaks until next heading. *Acceptance:* Coverage Policy p2–3, Coding Information p3–4, General Background p4–10 as single chunks; correct page ranges.

### Epic 4 — Content handling
- **4.1 Table-aware handling for Coding Information** — preserve CPT code+description tables. *Acceptance:* codes (86003, 95004, 95024, 0165U, 0178U, 95165) stay row-aligned.
- **4.2 Emit RAG chunks with metadata** — serialize to schema (JSON/JSONL); doc-level metadata (effective 04/15/2026, policy 0070). *Acceptance:* valid JSONL; full section text + metadata per record.

### Epic 5 — Validation & generalization
- **5.1 Validation harness against the sample PDF** — golden-file test on section count, titles, page ranges, no text lost/duplicated. *Acceptance:* `pytest` passes; total chunk text ≈ total body text.
- **5.2 Robustness / fallback for docs without a clean ToC** *(stretch)* — heuristic-only heading detection; configurable granularity. *Acceptance:* runs on a second policy PDF without a ToC.
- **5.3 CLI + README** — `python -m splitter <pdf> --out <dir> --level {section,subsection}`. *Acceptance:* one command PDF → chunks; README explains approach + limitations.

**Notes:** 3.4 is the headline task; 5.2 is stretch (sample doc has a clean ToC).

## 5. Open / Next Steps
- User to enter the tasks into the Linear app.
- Pending go-ahead to implement (proposed order: Epics 1–3 against the sample PDF).
