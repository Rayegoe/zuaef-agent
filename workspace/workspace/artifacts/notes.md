# Task context reconstruction

Task: IteraTeR document revision, depth 1, domain unknown, human revision primarily addressed clarity.

The workspace under `workspaces/` is not available through the ACE tool layer — every ACE pull (list_materials, read_material, retrieve_exemplars, retrieve_knowledge, check_claim, save_artifact) fails with `Unknown article workspace` for every article id I tried. The only article ids that succeed are the handful of `final.md` artifacts already present under `artifacts/`.

Available durable material (from artifacts, read directly):

- `artifacts/report.md` — a research report on the "Outcome-First PydanticAI Agent Engineering Guide v2.0" (ZUAEF agent project). Five findings from §3 and §7.
- `know/...` (none besides `concepts/outcome-lock.md`)
- Numerous HW-951 / ESP32 bring-up article `final.md` drafts (in Chinese), same underlying facts told in different narrative structures.

What is *missing*: the "BEFORE document" that this revision task asks me to revise, and any explicit AFTER/revision target. The task statement ("domain: unknown, revision depth 1 ... human revision primarily addressed clarity") does not name which document is the BEFORE, nor where its content lives.

I cannot fabricate a BEFORE document. I also cannot save an artifact via save_artifact because the article workspace id is unknown/unresolvable.
