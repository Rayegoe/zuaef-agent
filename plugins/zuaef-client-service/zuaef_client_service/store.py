"""File-native corpus store for the Client Service Decision Slice (SPEC §23/§54).

Reads canonical assets (knowledge, semantics, evidence, customer state) from
``slice_root`` and writes only runtime records: customer state under
``state/customers/`` and interaction receipts under ``state/interactions/``.
Business doctrine (policies/semantics/knowledge/evidence) is read-only at
runtime — the State Mutation Boundary (§54) forbids rewriting it from a tool.

Retrieval is lexical/file-native for v0.1 (§24); no vector DB.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .models import (
    CustomerState,
    EvidenceRef,
    InteractionReceipt,
    KnowledgeItem,
    SemanticPreference,
)

_EVIDENCE_INDEX_NAME = "evidence/evidence_ledger.jsonl"
_KNOWLEDGE_NAME = "knowledge/knowledge_pack.yaml"
_SEMANTICS_NAME = "semantics/semantic_preferences.yaml"
_STATE_ROOT = "state"
_CUSTOMERS_ROOT = "state/customers"
_INTERACTIONS_ROOT = "state/interactions"


class CorpusError(RuntimeError):
    """A corpus problem (missing file, unparsable YAML/JSONL, broken ref).

    Maps to the SPEC §47 ``blocked`` terminal: fail loud, never fabricate.
    """


def _tokenize(text: str) -> set[str]:
    """Word tokens plus Chinese character bigrams for lexical matching.

    English/number words split on boundaries; Chinese stays one run per
    continuous phrase, so we additionally emit bigrams — "成功案例" appears
    inside both the query and the evidence text even without a segmenter.
    """
    tokens: set[str] = set()
    for word in re.findall(r"[a-zA-Z0-9_]{1,40}", text.lower()):
        if len(word) >= 2:
            tokens.add(word)
    hanzi = re.findall(r"[\u4e00-\u9fff]+", text)
    for run in hanzi:
        tokens.add(run)
        tokens.update(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


class ClientServiceStore:
    """Loads corpus assets lazily and persists runtime records. No judgment."""

    def __init__(self, slice_root: Path) -> None:
        self.slice_root = Path(slice_root).expanduser().resolve()
        if not self.slice_root.is_dir():
            raise CorpusError(f"slice_root missing: {self.slice_root}")
        self._evidence: list[dict[str, Any]] | None = None
        self._knowledge: list[KnowledgeItem] | None = None
        self._semantics: list[SemanticPreference] | None = None

    # -- corpus reads --------------------------------------------------------

    def evidence_records(self) -> list[dict[str, Any]]:
        """All evidence ledger records (private; used for lexical lookup)."""
        if self._evidence is None:
            path = self.slice_root / _EVIDENCE_INDEX_NAME
            records: list[dict[str, Any]] = []
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise CorpusError(f"evidence jsonl corrupt: {path}: {exc}") from exc
            except FileNotFoundError as exc:
                raise CorpusError(f"evidence ledger missing: {path}") from exc
            self._evidence = records
        return self._evidence

    def knowledge_items(self) -> list[KnowledgeItem]:
        if self._knowledge is None:
            data = _load_yaml(self.slice_root / _KNOWLEDGE_NAME)
            rows = data.get("knowledge_items", data.get("knowledge", []))
            self._knowledge = [
                KnowledgeItem(
                    knowledge_id=r.get("knowledge_id", ""),
                    statement=r.get("statement", ""),
                    domain=r.get("domain", ""),
                    evidence_ids=r.get("evidence_ids", []),
                )
                for r in rows
            ]
        return self._knowledge

    def semantic_preferences(self) -> list[SemanticPreference]:
        if self._semantics is None:
            data = _load_yaml(self.slice_root / _SEMANTICS_NAME)
            rows = data.get("semantic_preferences", [])
            self._semantics = [
                SemanticPreference(
                    preference_id=r.get("preference_id", ""),
                    name=r.get("name", ""),
                    description=r.get("description", ""),
                    evidence_ids=r.get("evidence_ids", []),
                )
                for r in rows
            ]
        return self._semantics

    def evidence_by_ids(self, evidence_ids: list[str]) -> list[EvidenceRef]:
        """Resolve ids to refs for receipt/context display (id + provenance)."""
        by_id = {r.get("evidence_id"): r for r in self.evidence_records()}
        refs: list[EvidenceRef] = []
        for eid in evidence_ids:
            record = by_id.get(eid)
            if record is None:
                continue
            refs.append(
                EvidenceRef(
                    evidence_id=eid,
                    speaker=record.get("speaker", ""),
                    context_summary=record.get("context_summary", ""),
                    status=record.get("evidence_status", "OBSERVED"),
                    source_pack_id=record.get("source_pack_id", ""),
                )
            )
        return refs

    def search_evidence(self, query: str, limit: int = 8) -> list[EvidenceRef]:
        """Lexical evidence lookup: token overlap over text + context summary.

        Returns at most ``limit`` refs ordered by overlap score (ties by
        ledger order). No embedding model in v0.1 (§24).
        """
        tokens = _tokenize(query)
        if not tokens:
            return []
        scored: list[tuple[int, dict[str, Any]]] = []
        for record in self.evidence_records():
            haystack = _tokenize(
                f"{record.get('original_text', '')} {record.get('context_summary', '')}"
            )
            overlap = len(tokens & haystack)
            if overlap > 0:
                scored.append((overlap, record))
        scored.sort(key=lambda item: -item[0])  # stable: ties keep ledger order
        return [
            EvidenceRef(
                evidence_id=r.get("evidence_id", ""),
                speaker=r.get("speaker", ""),
                context_summary=r.get("context_summary", ""),
                status=r.get("evidence_status", "OBSERVED"),
                source_pack_id=r.get("source_pack_id", ""),
            )
            for _, r in scored[:limit]
        ]

    # -- customer state (runtime, private) -----------------------------------

    def customer_state_path(self, customer_id: str) -> Path:
        return self.slice_root / _CUSTOMERS_ROOT / f"{customer_id}.yaml"

    def load_customer_state(self, customer_id: str) -> CustomerState:
        path = self.customer_state_path(customer_id)
        if not path.is_file():
            return CustomerState(customer_id=customer_id)
        data = _load_yaml(path)
        return CustomerState.model_validate(data)

    def write_customer_state(
        self, state: CustomerState, *, history: bool = True
    ) -> Path:
        """Persist state under state/customers/ (§15 rules 6-7: history kept)."""
        target = self.customer_state_path(state.customer_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        if history and target.is_file():
            history_dir = self.slice_root / _CUSTOMERS_ROOT / f"{state.customer_id}.history"
            history_dir.mkdir(parents=True, exist_ok=True)
            seq = len(list(history_dir.glob("*.yaml"))) + 1
            (history_dir / f"{seq:04d}.yaml").write_text(
                target.read_text(encoding="utf-8"), encoding="utf-8"
            )
        target.write_text(
            yaml.safe_dump(state.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return target

    # -- interaction receipts (runtime, private) ------------------------------

    def append_interaction(self, receipt: InteractionReceipt) -> dict:
        """Append one interaction receipt under state/interactions/ (§28)."""
        out_dir = self.slice_root / _INTERACTIONS_ROOT
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{receipt.interaction_id}.json"
        path.write_text(
            json.dumps(receipt.model_dump(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "interaction_id": receipt.interaction_id,
            "written": True,
            "path": str(path),
            "sha256": _sha256(path.read_bytes()),
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CorpusError(f"corpus file missing: {path}") from exc
    except yaml.YAMLError as exc:
        raise CorpusError(f"corpus yaml invalid: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CorpusError(f"corpus file not a mapping: {path}")
    return data


def _sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()
