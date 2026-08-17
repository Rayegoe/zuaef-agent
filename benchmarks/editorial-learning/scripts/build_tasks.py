#!/usr/bin/env python3
"""Deterministically build the editorial-learning benchmark from data/raw/.

Selection rules are fixed sorts/filters (no randomness): rerunning on the
same raw tree reproduces the same tasks. This is the same rule set as the
first build (z-workspace), ported to the repository layout.

Repository policy (operator, 2026-08-17):
  committed (git)                     local only (data/, gitignored)
  ----------------                    --------------------------------
  tasks/T##.json                      data/derived/tasks_full/T##.json
    bounded excerpts (<=1500 chars)     complete before/after/material texts
    sha256 of the FULL texts            (consumed by run_benchmark.py)
    record id / license / selection
  evidence/human_patches.jsonl        data/raw/ (fetched by fetch_sources.py)
  evidence/seed_snapshot.jsonl
  provenance/sources.jsonl + licenses.md
  benchmark.jsonl
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
RAW = REPO / "data" / "raw"
DERIVED = REPO / "data" / "derived"

sys.path[:0] = [
    str(REPO / "plugins" / "zuaef-ace-writing"),
    str(REPO / "src"),
]
from zuaef_ace_writing.editorial import (
    run_trajectory_sensors,
    seed_evidence,
)

EXCERPT = 1500          # committed before/after excerpt bound (chars)
SPAN_EXCERPT = 220      # committed delta span bound
DOWNLOADED_AT = "2026-08-17"

LICENSES = {
    "iterater": {
        "dataset": "IteraTeR (human_doc_level)",
        "url": "https://github.com/vipulraheja/iterater (dataset/IteraTeR.zip)",
        "license": "Apache-2.0 (repository)",
        "license_note": "Repository license covers code and in-repo data; "
        "underlying revised texts remain (c) their original authors. Committed "
        "excerpts carry attribution via doc_id.",
    },
    "tetra": {
        "dataset": "TETRA (professional edits of ACL papers)",
        "url": "https://github.com/chemicaltree/tetra (original/)",
        "license": "CC BY 4.0",
        "license_note": "Repo README: 'This work is licensed under a Creative "
        "Commons Attribution 4.0 International License.'",
    },
    "wpbench": {
        "dataset": "WritingPreferenceBench (Chinese)",
        "url": "https://huggingface.co/datasets/m-a-p/Writing-Preference-Bench "
        "(WP_bench_chinese.json)",
        "license": "ODC-BY",
        "license_note": "GitHub README states ODC-BY; HF page metadata has shown "
        "Apache-2.0. Conservative treatment: ODC-BY attribution, original "
        "prompt_id preserved in every record.",
    },
    "re3": {
        "dataset": "Re3-Sci",
        "url": "https://tudatalib.ulb.tu-darmstadt.de/handle/tudatalib/4300",
        "license": "CC BY 4.0 (DataLib item)",
        "license_note": "DataLib bitstream checkSum (MD5) verified at fetch "
        "time; verify the item-page license before redistributing.",
    },
}

SENSOR_ACTION = {
    "template_connectors": "break_trajectory",
    "summary_pressure": "delay_interpretation",
    "uniform_paragraphs": "break_trajectory",
    "low_concrete_anchor_density": "retrieve_concrete_memory",
    "abstract_noun_density": "return_to_observation",
}
NUMBER_RE = re.compile(r"[0-9０-９]")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def excerpt(text: str, limit: int = 160) -> str:
    return " ".join(text.split())[:limit]


def make_task(seq, source, record_id, language, domain, material, before, after,
              before_origin, after_origin, delta, license_key, selection_rule,
              evidence_ids):
    task_id = f"T{seq:02d}"
    committed = {
        "task_id": task_id,
        "sequence": seq,
        "source": source,
        "language": language,
        "domain": domain,
        "material": {
            "prompt_excerpt": excerpt(material, EXCERPT),
            "sha256": sha256_text(material),
        },
        "before": {
            "excerpt": excerpt(before, EXCERPT),
            "sha256": sha256_text(before),
            "origin": before_origin,
        },
        "after": {
            "excerpt": excerpt(after, EXCERPT),
            "sha256": sha256_text(after),
            "origin": after_origin,
        },
        "delta": delta,
        "provenance": {
            "dataset": LICENSES[license_key]["dataset"],
            "record_id": record_id,
            "license": LICENSES[license_key]["license"],
            "selection_rule": selection_rule,
        },
        "agent_run": {
            "signals": None, "evidence_retrieved": None,
            "intervention": None, "save_vetoed": None,
        },
        "outcome": {
            "blind_preference": None, "claim_preserved": None,
            "human_edit_distance": None,
        },
        "learning": {
            "promote_to_evidence": bool(evidence_ids),
            "evidence_ids": evidence_ids,
        },
    }
    (BENCH / "tasks").mkdir(exist_ok=True)
    (BENCH / "tasks" / f"{task_id}.json").write_text(
        json.dumps(committed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    full = {
        "task_id": task_id, "material": material,
        "before": before, "after": after,
    }
    (DERIVED / "tasks_full").mkdir(parents=True, exist_ok=True)
    (DERIVED / "tasks_full" / f"{task_id}.json").write_text(
        json.dumps(full, ensure_ascii=False), encoding="utf-8"
    )
    return committed


# --- T01-T06: IteraTeR --------------------------------------------------------


def load_iterater():
    docs = []
    for split in ("dev", "test", "train"):
        path = RAW / "iterater" / "IteraTeR" / "human_doc_level" / f"{split}.json"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                rec["_split"] = split
                docs.append(rec)
    return docs


def build_iterater(tasks, evidence):
    docs = load_iterater()
    slots = [
        (1, "clarity"), (2, "fluency"), (3, "coherence"), (4, "style"),
        (5, "clarity"), (6, "fluency"),
    ]
    used: set[str] = set()

    def usable(doc, intent):
        return [
            (i, a) for i, a in enumerate(doc.get("edit_actions", []))
            if a.get("major_intent") == intent and a.get("before") and a.get("after")
        ]

    for seq, intent in slots:
        ranked = sorted(
            (d for d in docs if d["doc_id"] not in used and usable(d, intent)),
            key=lambda d: (-len(usable(d, intent)), d["doc_id"]),
        )
        doc = ranked[0] if seq in (1, 2, 3, 4) else ranked[1]
        used.add(doc["doc_id"])
        actions = usable(doc, intent)
        evidence_ids = []
        # v0.1 mapping: clarity -> return_to_observation (closest frozen
        # action, medium confidence; rationale states the mapping honestly).
        if intent == "clarity":
            for i, action in actions[:6]:
                evid = {
                    "id": f"human.iterater.{doc['doc_id']}.clarity.{i}",
                    "source_type": "human_patch",
                    "source_ref": f"iterater:human_doc:{doc['doc_id']}#action{i}",
                    "situation_tags": ["drafting", "nonfiction", "academic"],
                    "trigger_signals": ["abstract_noun_density"],
                    "action": "return_to_observation",
                    "directive": (
                        "Replace the vague or ambiguous formulation with the "
                        "explicit, concrete one, as this human revision did."
                    ),
                    "rationale": (
                        "IteraTeR human revision, intent=clarity; v0.1 mapping "
                        "clarity -> return_to_observation (closest frozen "
                        "action, medium confidence)."
                    ),
                    "weight": 4.0,
                    "approved_by": "human-editor",
                    "before_excerpt": excerpt(action["before"] or ""),
                    "after_excerpt": excerpt(action["after"] or ""),
                }
                evidence.append(evid)
                evidence_ids.append(evid["id"])
        delta = {
            "intent": intent,
            "spans": [
                {
                    "before": excerpt(a["before"] or "", SPAN_EXCERPT),
                    "after": excerpt(a["after"] or "", SPAN_EXCERPT),
                    "intent": a["major_intent"],
                    "raw_intents": a.get("raw_intents", [])[:3],
                }
                for _, a in actions[:8]
            ],
            "operations": [intent],
            "preserve": ["claims", "source_refs"],
            "edit_action_count": len(doc.get("edit_actions", [])),
        }
        material = (
            f"IteraTeR document revision task (domain: {doc.get('domain', 'unknown')}, "
            f"revision depth {doc.get('revision_depth', '?')}). Revise the BEFORE "
            f"document. The human revision primarily addressed {intent}."
        )
        tasks.append(make_task(
            seq, "iterater", doc["doc_id"], "en", doc.get("domain", "unknown"),
            material, doc["before_revision"], doc["after_revision"],
            "iterater_before_revision", "iterater_human_after_revision",
            delta, "iterater",
            f"max usable {intent} actions; tie-break by doc_id; pass "
            f"{'1' if seq in (1, 2, 3, 4) else '2'}",
            evidence_ids,
        ))


# --- T07-T10: TETRA -----------------------------------------------------------


def tetra_parse(path: Path):
    root = ET.parse(path).getroot()
    before_parts, after_parts, edits = [], [], []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag == "text":
            txt = "".join(node.itertext())
            before_parts.append(txt)
            after_parts.append(txt)
        elif tag == "edit":
            original = "".join(node.itertext()).strip()
            crr = (node.attrib.get("crr") or "").strip()
            before_parts.append(original)
            after_parts.append(crr)
            if original or crr:
                edits.append({
                    "type": node.attrib.get("type", ""),
                    "before": original,
                    "after": crr,
                    "comments": node.attrib.get("comments", ""),
                })
    return {
        "doc_id": root.attrib.get("id", path.stem),
        "editor": root.attrib.get("editor", "?"),
        "before": "".join(before_parts),
        "after": "".join(after_parts),
        "edits": edits,
    }


def build_tetra(tasks, evidence):
    files = sorted((RAW / "tetra").glob("*.xml"))
    parsed = [tetra_parse(p) for p in files]

    def count(doc, *needles):
        return sum(
            1 for e in doc["edits"]
            if any(x in e["type"].lower() for x in needles)
        )

    slots = [
        (7, ("redundancy",), "redundancy"),
        (8, ("readability",), "readability"),
        (9, ("consistency", "word order", "flow"), "consistency_flow"),
        (10, ("readability",), "no_intervention_expected"),
    ]
    used: set[str] = set()
    for seq, needles, label in slots:
        ranked = sorted(
            (d for d in parsed
             if d["editor"] == "A" and d["doc_id"] not in used and count(d, *needles) > 0),
            key=lambda d: (-count(d, *needles), d["doc_id"]),
        )
        if seq == 10:
            ranked = [d for d in ranked if d["doc_id"] not in used]
            doc = ranked[1] if len(ranked) > 1 else ranked[0]
        else:
            doc = ranked[0]
        used.add(doc["doc_id"])
        evidence_ids = []
        matched = [e for e in doc["edits"]
                   if any(x in e["type"].lower() for x in needles)]
        if seq != 10:
            for i, e in enumerate(matched):
                comment = e["comments"].lower()
                etype = e["type"].lower()
                if "clarity" in etype:
                    action, trigger = "return_to_observation", "abstract_noun_density"
                elif any(w in comment for w in ("repet", "rhythm", "choppy", "smoother", "flows")):
                    action, trigger = "break_trajectory", "template_connectors"
                else:
                    continue
                evid = {
                    "id": f"human.tetra.{doc['doc_id']}.{doc['editor']}.{i}",
                    "source_type": "human_patch",
                    "source_ref": f"tetra:original:{doc['doc_id']}-{doc['editor']}#edit{i}",
                    "situation_tags": ["drafting", "nonfiction", "academic"],
                    "trigger_signals": [trigger],
                    "action": action,
                    "directive": (
                        "Apply the professional editor's move: replace the "
                        "abstract formulation with the concrete one / break the "
                        "repetitive rhythm."
                    ),
                    "rationale": (
                        f"TETRA professional edit (type={e['type']}); editor "
                        f"comment: {excerpt(e['comments'], 120)}"
                    ),
                    "weight": 4.0,
                    "approved_by": "human-editor",
                    "before_excerpt": excerpt(e["before"]),
                    "after_excerpt": excerpt(e["after"]),
                }
                evidence.append(evid)
                evidence_ids.append(evid["id"])
        if seq == 10:
            before = after = doc["after"]
            before_origin = after_origin = "tetra_professionally_edited"
            delta = {
                "intent": "none_expected",
                "spans": [],
                "operations": [],
                "preserve": ["everything"],
                "note": "Input is already professionally edited; correct behavior "
                        "is sensors-quiet/no intervention or evidence-insufficient "
                        "SAVE.",
            }
            evidence_ids = []
        else:
            before, after = doc["before"], doc["after"]
            before_origin = after_origin = None
            before_origin = "tetra_reconstructed_original"
            after_origin = "tetra_professional_edit"
            delta = {
                "intent": label,
                "spans": [
                    {"before": excerpt(e["before"], SPAN_EXCERPT),
                     "after": excerpt(e["after"], SPAN_EXCERPT),
                     "type": e["type"], "comment": excerpt(e["comments"], SPAN_EXCERPT)}
                    for e in matched[:8]
                ],
                "operations": sorted({e["type"] for e in matched}),
                "preserve": ["claims", "source_refs"],
            }
        material = (
            f"TETRA professional editing task (paper {doc['doc_id']}, editor "
            f"{doc['editor']}). The BEFORE text is reconstructed by reverting "
            f"the editor's tracked edits; AFTER applies them."
        )
        tasks.append(make_task(
            seq, "tetra", f"{doc['doc_id']}-{doc['editor']}", "en", "acl_paper",
            material, before, after, before_origin, after_origin,
            delta, "tetra",
            f"max edits matching {needles} among editor-A files; tie-break doc_id",
            evidence_ids,
        ))


# --- T11-T16: WritingPreferenceBench (Chinese) ---------------------------------


WP_TAGS = {
    11: ("科普文章", "zh_nonfiction"),
    12: ("广告文案-营销邮件", "promotional_communication"),
    13: ("产品说明书", "functional_document"),
    14: ("剧本-脚本", "script_dialogue"),
    15: ("角色扮演", "role_playing"),
    16: ("抽象文学-亚文化", "subjective_style"),
}


def build_wpbench(tasks, evidence):
    wp = json.loads((RAW / "WP_bench_chinese.json").read_text(encoding="utf-8"))
    by_tag: dict[str, list[tuple[int, dict]]] = {}
    for idx, rec in enumerate(wp):
        by_tag.setdefault(rec["tag"], []).append((idx, rec))

    for seq, (tag, domain) in WP_TAGS.items():
        pool = by_tag.get(tag, [])
        if not pool:
            raise SystemExit(f"WP_bench tag {tag!r} not found")
        scored = [
            r for r in pool
            if r[1]["chosen"].get("score", 0) > r[1]["rejected"].get("score", 0)
        ] or pool

        def long_pair(rec):
            return (len(rec["rejected"]["response"]) >= 500
                    and len(rec["chosen"]["response"]) >= 500)

        def dropped(rec):
            return sorted(
                set(run_trajectory_sensors(rec["rejected"]["response"]))
                - set(run_trajectory_sensors(rec["chosen"]["response"]))
            )

        pick = next(
            ((i, r) for i, r in scored if long_pair(r) and dropped(r)),
            next(((i, r) for i, r in scored if long_pair(r)), scored[0]),
        )
        _, rec = pick
        before = rec["rejected"]["response"]
        after = rec["chosen"]["response"]
        sig_before = run_trajectory_sensors(before)
        sig_after = run_trajectory_sensors(after)
        dropped_sensors = sorted(set(sig_before) - set(sig_after))
        evidence_ids = []
        # T16 (subjective style): chosen may legitimately fire sensors;
        # sensor != truth, so this task never yields evidence.
        if seq != 16:
            for sensor in dropped_sensors:
                evid = {
                    "id": f"human.wpbench.{rec['prompt_id']}.{sensor}",
                    "source_type": "human_patch",
                    "source_ref": f"wpbench:{rec['prompt_id']} (tag {tag})",
                    "situation_tags": [
                        "drafting",
                        "nonfiction" if seq == 11 else "creative",
                        domain,
                    ],
                    "trigger_signals": [sensor],
                    "action": SENSOR_ACTION[sensor],
                    "directive": (
                        "Move off the trajectory this sensor marks: the "
                        "human-preferred text does not share it."
                    ),
                    "rationale": (
                        f"WritingPreferenceBench human preference (tag {tag}): "
                        f"sensor {sensor} fires on the rejected response "
                        f"(score {rec['rejected'].get('score')}) and not on the "
                        f"chosen one (score {rec['chosen'].get('score')}). "
                        f"v0.1 deterministic sensor-diff extraction."
                    ),
                    "weight": 4.0,
                    "approved_by": "human-editor",
                    "before_excerpt": excerpt(before),
                    "after_excerpt": excerpt(after),
                }
                evidence.append(evid)
                evidence_ids.append(evid["id"])
        delta = {
            "intent": "human_preference",
            "spans": [],
            "operations": dropped_sensors,
            "preserve": ["claims"],
            "signals_before": sig_before,
            "signals_after": sig_after,
            "note": "No edit spans exist in preference pairs; operations are "
                    "the sensor differences between rejected and chosen "
                    "(deterministic).",
        }
        material = (
            f"WritingPreferenceBench 中文任务（类别：{tag}）。写作要求原文如下。\n\n"
            f"{rec['prompt']}"
        )
        tasks.append(make_task(
            seq, "wpb", rec["prompt_id"], "zh", domain,
            material, before, after,
            "human_preference_rejected", "human_preference_chosen",
            delta, "wpbench",
            f"for tag {tag}: first file-order record with chosen.score > "
            f"rejected.score, both responses >=500 chars, and >=1 sensor the "
            f"chosen text drops; fallback first long, then first scored",
            evidence_ids,
        ))


# --- T17-T20: Re3-Sci ----------------------------------------------------------


def _re3_review_text(doc_dir: Path, limit: int = 1500) -> str:
    review_dir = doc_dir / "review"
    if not review_dir.is_dir():
        return ""
    report = min(review_dir.glob("*.json"))
    data = json.loads(report.read_text(encoding="utf-8"))
    parts = [
        n["content"] for n in data.get("nodes", [])
        if n.get("content") and n.get("ntype") != "article-title"
    ]
    return "\n\n".join(parts)[:limit]


def _re3_edit_summary_text(doc_dir: Path, doc: str, limit: int = 1200) -> str:
    resp = doc_dir / "response" / f"{doc}_edit_summary.json"
    if not resp.is_file():
        return ""
    data = json.loads(resp.read_text(encoding="utf-8"))
    parts = [n["content"] for n in data.get("nodes", []) if n.get("content")]
    return "\n\n".join(parts)[:limit]


def build_re3(tasks, evidence):
    root = RAW / "re3" / "Re3-Sci_v1"
    if not root.is_dir():
        raise SystemExit("data/raw/re3 missing — run scripts/fetch_sources.py first")
    with (root / "data_human" / "revision" / "edits_s.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    both = [r for r in rows if r["text_src"].strip() and r["text_tgt"].strip()]

    slots = [
        (17, ("Modify,Clarity",), "review_triggered_clarity", True),
        (18, ("Modify,Grammar",), "review_triggered_grammar_fluency", False),
        (19, ("Modify,Fact/Evidence",), "review_triggered_evidence_revision", False),
        (20, ("Modify,Clarity", "Modify,Grammar", "Modify,Fact/Evidence"),
         "holistic_revision_with_response", False),
    ]

    def docs_by(golds):
        counts: dict[str, int] = {}
        for r in both:
            if r["gold"] in golds:
                counts[r["doc_name"]] = counts.get(r["doc_name"], 0) + 1
        return counts

    used: set[str] = set()
    for seq, golds, label, emit_evidence in slots:
        counts = docs_by(golds)
        candidates = [d for d in counts if d not in used]
        eligible = [
            d for d in candidates
            if _re3_review_text(root / "docs" / d)
            and (seq != 20 or _re3_edit_summary_text(root / "docs" / d, d))
        ]
        ranked = sorted(eligible or candidates, key=lambda d: (-counts[d], d))
        doc = ranked[0]
        used.add(doc)
        sel = [r for r in both if r["doc_name"] == doc and r["gold"] in golds][:25]
        before = "\n".join(r["text_tgt"].strip() for r in sel)
        after = "\n".join(r["text_src"].strip() for r in sel)
        evidence_ids = []
        if emit_evidence:
            for r in sel[:6]:
                evid = {
                    "id": f"human.re3.{doc}.clarity.{r['edit_index']}",
                    "source_type": "human_patch",
                    "source_ref": f"re3:edits_s:{r['edit_index']} ({doc})",
                    "situation_tags": [
                        "drafting", "nonfiction", "academic", "review_triggered",
                    ],
                    "trigger_signals": ["abstract_noun_density"],
                    "action": "return_to_observation",
                    "directive": (
                        "Replace the unclear formulation with the clearer, more "
                        "explicit one, as this author revision did in response "
                        "to review."
                    ),
                    "rationale": (
                        f"Re3-Sci gold label {r['gold']} (majority of 3 human "
                        f"annotators); v0.1 mapping clarity -> "
                        f"return_to_observation (closest frozen action, medium "
                        f"confidence). Reviewer-triggered revision."
                    ),
                    "weight": 4.0,
                    "approved_by": "human-editor",
                    "before_excerpt": excerpt(r["text_tgt"]),
                    "after_excerpt": excerpt(r["text_src"]),
                }
                evidence.append(evid)
                evidence_ids.append(evid["id"])
        review_text = _re3_review_text(root / "docs" / doc)
        summary_text = _re3_edit_summary_text(root / "docs" / doc, doc) if seq == 20 else ""
        material = (
            f"Re3-Sci collaborative revision task (paper {doc}). The passage "
            f"below is a real peer-review excerpt that triggered the author's "
            f"revision; revise the BEFORE passage accordingly.\n\n"
            f"--- REVIEWER REPORT (excerpt) ---\n{review_text}"
        )
        if summary_text:
            material += (
                f"\n\n--- AUTHOR EDIT SUMMARY (human-written, do not copy "
                f"verbatim) ---\n{summary_text}"
            )
        delta = {
            "intent": label,
            "spans": [
                {"before": excerpt(r["text_tgt"], SPAN_EXCERPT),
                 "after": excerpt(r["text_src"], SPAN_EXCERPT),
                 "gold": r["gold"], "section": r.get("sec_title_tgt", "")}
                for r in sel[:8]
            ],
            "operations": sorted({r["gold"] for r in sel}),
            "preserve": ["claims", "source_refs"],
            "note": "src=NEW/v2, tgt=OLD/v1 per data_human README; edits are "
                    "sentence-aligned human annotations (3-annotator majority).",
        }
        tasks.append(make_task(
            seq, "re3", doc, "en", "scientific_paper",
            material, before, after,
            "re3_v1_old_sentences", "re3_v2_new_sentences",
            delta, "re3",
            f"doc with most {golds} both-span edits, review text present; "
            f"tie-break doc_name",
            evidence_ids,
        ))


# --- outputs -------------------------------------------------------------------


def write_seed_snapshot() -> None:
    (BENCH / "evidence").mkdir(exist_ok=True)
    with (BENCH / "evidence" / "seed_snapshot.jsonl").open("w", encoding="utf-8") as fh:
        for seed in seed_evidence():
            fh.write(seed.model_dump_json() + "\n")


def write_outputs(tasks, evidence) -> None:
    with (BENCH / "evidence" / "human_patches.jsonl").open("w", encoding="utf-8") as fh:
        for e in evidence:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    (BENCH / "provenance").mkdir(exist_ok=True)
    localmap = {
        "iterater": RAW / "IteraTeR.zip",
        "tetra": RAW / "tetra",
        "wpbench": RAW / "WP_bench_chinese.json",
        "re3": RAW / "re3-sci.zip",
    }
    with (BENCH / "provenance" / "sources.jsonl").open("w", encoding="utf-8") as fh:
        for key, meta in LICENSES.items():
            path = localmap[key]
            entry = {
                "dataset": meta["dataset"],
                "url": meta["url"],
                "license": meta["license"],
                "license_note": meta["license_note"],
                "downloaded_at": DOWNLOADED_AT,
            }
            if path.is_file():
                data = path.read_bytes()
                entry["bytes"] = len(data)
                entry["sha256"] = hashlib.sha256(data).hexdigest()
            elif path.is_dir():
                entry["files"] = sorted(p.name for p in path.glob("*"))
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with (BENCH / "benchmark.jsonl").open("w", encoding="utf-8") as fh:
        for t in tasks:
            fh.write(json.dumps({
                "task_id": t["task_id"],
                "sequence": t["sequence"],
                "source": t["source"],
                "record_id": t["provenance"]["record_id"],
                "language": t["language"],
                "domain": t["domain"],
                "delta_intent": t["delta"]["intent"],
                "evidence_ids": t["learning"]["evidence_ids"],
            }, ensure_ascii=False) + "\n")

    licenses_md = ["# Licenses", ""]
    for meta in LICENSES.values():
        licenses_md += [
            f"## {meta['dataset']}",
            f"- URL: {meta['url']}",
            f"- License: {meta['license']}",
            f"- Note: {meta['license_note']}",
            "",
        ]
    (BENCH / "provenance" / "licenses.md").write_text(
        "\n".join(licenses_md), encoding="utf-8"
    )


def main() -> None:
    tasks, evidence = [], []
    build_iterater(tasks, evidence)
    build_tetra(tasks, evidence)
    build_wpbench(tasks, evidence)
    build_re3(tasks, evidence)
    write_seed_snapshot()
    write_outputs(tasks, evidence)
    print(f"tasks: {len(tasks)} | evidence entries: {len(evidence)}")
    for t in tasks:
        print(f"  {t['task_id']} {t['source']:<8} {t['provenance']['record_id']:<40} "
              f"{t['delta']['intent']:<30} evidence={len(t['learning']['evidence_ids'])}")


if __name__ == "__main__":
    main()
