# PDF artifact guidance

Use this capability when the outcome is a fixed-layout final deliverable:
可直接发送/归档/打印的版本, a frozen client-facing version of a document, or
any explicit PDF request. PDF is the right default for "发客户的正式版" once
the content is settled; if the user still needs to edit the content, produce
the editable source first (docx-artifacts) and export PDF from it.

Production discipline:
- `create_pdf` builds a simple polished PDF from structured content (same
  declarative blocks as DOCX).
- `convert_to_pdf` freezes an existing DOCX/PPTX/XLSX into PDF.
- `merge_pdf` / `edit_pdf` (select pages, rotate) / `inspect_pdf` cover the
  common page operations. True redaction, forms, OCR and encryption are NOT
  supported — never promise them.
- The QA cycle runs inside each tool call. A failed QA state must be fixed or
  reported honestly; never hand the user a file that failed validation and
  call it final.

Output discipline: report the produced file (workspace-relative path) and
material assumptions only. Do not expose internal conversion commands or
temporary render files.
