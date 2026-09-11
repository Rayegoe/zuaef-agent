# 10 — Acceptance and Test Matrix

## A. Composition gates

A1. New plugin installs through normal repository workspace sync.

A2. Plugin is discoverable by existing plugin CLI.

A3. Pilot profile validates before model execution.

A4. Four artifact capabilities are supplied through the current plugin capability seam.

A5. No functional changes to core/runtime/composition.

A6. Shell remains disabled in the pilot profile.

## B. Security/path gates

B1. `../../outside.docx` input/output attempt is rejected.

B2. Absolute output outside workspace is rejected.

B3. Attempt to write under `workspace/knowledge/` is rejected.

B4. Attempt to write final output under `workspace/inbox/` is rejected.

B5. Capability cannot choose an arbitrary executable.

B6. Process calls use bounded timeout and never interpolate a shell command string.

## C. DOCX gates

C1. Create a Chinese/English mixed business report with headings, bullets, table, and local image.

C2. Reopen successfully.

C3. Render successfully in supported deployment.

C4. Structured revision updates an exact price and does not erase unrelated paragraphs.

C5. Unsupported advanced edit fails clearly rather than corrupting the file.

## D. PDF gates

D1. Convert generated DOCX to PDF.

D2. Render selected PDF pages.

D3. Merge two PDFs in requested order.

D4. Select a page range and produce a valid result.

D5. Bad/malformed PDF returns recoverable error.

## E. Slides gates

E1. Generate <=6 slide management deck from structured input.

E2. Include title, key-message, bullets, table, and simple chart across the deck.

E3. Reopen/inspect package.

E4. Convert/render successfully in supported deployment.

E5. Revise one slide without rebuilding a different deck.

E6. No dependency on copied OAI slide templates.

## F. Spreadsheet gates

F1. Generate workbook with at least two sheets.

F2. Inputs remain editable.

F3. Derived scenario values use formulas where business logic should remain editable.

F4. Number formats are correct for currency and percentages.

F5. Workbook contains a summary visual or chart in the pricing acceptance case.

F6. Reopen successfully.

F7. If recalculation engine is present, recalculate and inspect cached results.

F8. If recalculation engine is absent, preserve formulas and report limitation without fabricating evaluated values.

## G. Natural-language routing gates

Use a real model lane in addition to deterministic unit tests where practical.

G1. “给我一个 Excel 版本” selects Spreadsheet.

G2. “整理成明天给老板汇报的 5 页材料” selects Slides without requiring “PPT”.

G3. “做一份能直接发客户的正式版本” selects a fixed final deliverable, normally PDF, without requiring “PDF”.

G4. “做个以后还要继续修改的完整方案” selects editable document output, normally DOCX.

G5. “把成本、运费、平台费都算进去，做三个售价情景” selects Spreadsheet.

G6. “给我老板汇报和详细计算表” may select Slides + Spreadsheet in one run.

G7. “总结一下这份文件说了什么” does not create an office artifact unless another requirement calls for one.

G8. No routing acceptance test depends solely on one exact keyword.

## H. Feishu gates

H1. Existing incoming Feishu file attachment still lands inside inbox.

H2. A completed eligible artifact can be sent with existing surface document method.

H3. With auto-delivery enabled, terminal artifact run sends final artifact without a second user command.

H4. Manual artifacts command remains functional as recovery.

H5. Delivery failure is reported separately and does not alter completed run truth.

H6. Artifact larger than configured surface limit is not uploaded automatically.

## I. Clean deployment gates

I1. Plugin imports and tests without the local `oai/` tree.

I2. Production code contains no runtime reference to `oai/`.

I3. Production code contains no runtime reference to `/home/oai/`.

I4. x86_64 local development lane passes.

I5. ARM64/OrangePi dependency probe passes for the promoted subset.

## J. Quality gates

J1. Final artifact folder contains final deliverables only, not render PNG debris.

J2. Create/revise tools perform structure QA automatically.

J3. Supported deployment performs render QA automatically.

J4. When visual preview is unsupported, implementation/report does not claim visual parity.

J5. Full repository tests and lint pass.
