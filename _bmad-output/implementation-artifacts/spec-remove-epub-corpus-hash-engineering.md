---
title: 'Remove EPUB corpus hash engineering'
type: 'refactor'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'c98504fb05c9dff350db49b2bc34e687b0ea7264'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The WhereMyLife corpus implementation introduced a SHA-based identity chain across EPUB input, article Markdown, manifest rows, receipts, and retrieval. That chain is not required by the writing-corpus contract and makes deterministic source retrieval look like an integrity subsystem.

**Approach:** Remove only the hash fields, hashing code, receipt hash fields, and retrieval-time hash comparison introduced by the EPUB corpus work. Keep deterministic article boundaries, contiguous lexical windows, source provenance, path safety, and existing independent integrity mechanisms outside this corpus feature.

## Boundaries & Constraints

**Always:** Preserve one-article-per-Markdown output, paragraph order, title, source, URL, source-entry, article path, deterministic manifest ordering, and malformed-corpus/path-safety errors. Regenerate the real WhereMyLife batch after the code change.

**Ask First:** If removal appears to require changing `mechanical_prepare` source identity or the repository’s pre-existing `BUILD_MANIFEST` mechanism, stop and ask; those are separate mechanisms.

**Never:** Do not add replacement fingerprints, checksums, manifests of manifests, receipt integrity layers, LLM preprocessing, summaries, semantic labels, or article selection logic. Do not rewrite the closed predecessor WO receipt.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | Valid EPUB with NCX and article entries | Markdown, manifest, and receipt contain provenance and counts, but no corpus hash fields | N/A |
| RETRIEVAL | Valid generated batch and lexical query | Search returns bounded contiguous source windows without hash validation | N/A |
| MISSING_ARTICLE | Manifest points to missing or unsafe article path | Corpus does not silently read outside the batch | Raise `CorpusError` |

</frozen-after-approval>

## Code Map

- `tools/epub_to_corpus.py` -- deterministic EPUB-to-Markdown/manifest/receipt converter; remove corpus hash production.
- `plugins/zuaef-ace-writing/zuaef_ace_writing/epub_corpus.py` -- file-native corpus loader and lexical window renderer; remove hash requirements and comparison.
- `tests/test_epub_corpus.py` -- converter, retrieval, provenance, determinism, and malformed-path coverage.
- `data/writing-corpus/wheremylife/2026-08-20/` -- regenerated real WhereMyLife corpus batch used as external evidence.

## Tasks & Acceptance

**Execution:**
- [x] `tools/epub_to_corpus.py` -- emit corpus artifacts without hash fields or hashing helpers -- keep the index deterministic and provenance-bearing.
- [x] `plugins/zuaef-ace-writing/zuaef_ace_writing/epub_corpus.py` -- remove hash data and retrieval validation -- keep safe paths and contiguous lexical windows.
- [x] `tests/test_epub_corpus.py` -- replace hash assertions with no-hash and malformed-path assertions -- preserve behavior coverage.
- [x] `data/writing-corpus/wheremylife/2026-08-20/` -- regenerate from the requested EPUB -- prove the real artifact batch follows the revised contract.

**Acceptance Criteria:**
- Given a valid EPUB, when conversion completes, then article Markdown, `manifest.jsonl`, and `receipt.json` contain no corpus hash fields or hash-derived values.
- Given a valid corpus batch, when a lexical query is retrieved, then the result retains title/source/url/source-entry/path and contiguous paragraphs without computing or comparing a hash.
- Given a missing or unsafe manifest article path, when retrieval runs, then `CorpusError` is raised.
- Given the repository test suite, when focused and full tests run, then all applicable tests pass; unrelated pre-existing lint findings remain unchanged.

## Spec Change Log

## Design Notes

The manifest remains a deterministic index, not an integrity manifest. File paths and provenance fields identify the source location needed by the writer; they do not assert byte identity. Existing hashes outside this feature are explicitly preserved because this change is scoped to the hash chain introduced by the EPUB corpus WO.

## Verification

**Commands:**
- `uv run pytest -q tests/test_epub_corpus.py tests/test_ace_writing_plugin.py tests/test_production_writing.py` -- expected: all focused tests pass.
- `uv run pytest -q` -- expected: full suite passes.
- `rg -n 'hashlib|sha256|^(hash|epub_sha256):|"(hash|epub_sha256|manifest_sha256)"' data/writing-corpus/wheremylife/2026-08-20 tools/epub_to_corpus.py plugins/zuaef-ace-writing/zuaef_ace_writing/epub_corpus.py` -- expected: no corpus hash machinery or fields.

## Suggested Review Order

**Corpus contract**

- Converter now emits only provenance and deterministic ordering fields.
  [`epub_to_corpus.py:236`](../../tools/epub_to_corpus.py#L236)

- Receipt remains a count-and-location summary without integrity infrastructure.
  [`epub_to_corpus.py:348`](../../tools/epub_to_corpus.py#L348)

**Retrieval boundaries**

- Manifest loading preserves provenance while removing byte-identity validation.
  [`epub_corpus.py:89`](../../plugins/zuaef-ace-writing/zuaef_ace_writing/epub_corpus.py#L89)

- Path safety remains an explicit failure boundary for malformed corpus indexes.
  [`epub_corpus.py:67`](../../plugins/zuaef-ace-writing/zuaef_ace_writing/epub_corpus.py#L67)

- Search and rendering retain contiguous windows and mechanical source references.
  [`epub_corpus.py:190`](../../plugins/zuaef-ace-writing/zuaef_ace_writing/epub_corpus.py#L190)

**Evidence**

- Tests cover no-hash output, determinism, contiguous retrieval, missing, and unsafe paths.
  [`test_epub_corpus.py:50`](../../tests/test_epub_corpus.py#L50)

- The regenerated real batch provides the requested production-shaped artifact evidence.
  [`receipt.json:1`](../../data/writing-corpus/wheremylife/2026-08-20/receipt.json#L1)
