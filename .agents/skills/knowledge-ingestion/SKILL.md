---
name: knowledge-ingestion
description: Convert observed source material into durable evidence-backed file-native knowledge nodes when the user asks the agent to learn, ingest, catalog, or build knowledge from a source.
---
# Knowledge ingestion

Use this only when a source has actually been observed through an available tool or user-provided material.

1. Preserve a source node first (`sources/<stable-id>`), including the canonical resource and concrete evidence locator when available.
2. Search existing knowledge before minting a new concept.
3. Prefer augmenting an existing concept over creating a duplicate topical summary.
4. Write reusable concepts, methods, claims, tools, examples, or references; do not dump an undifferentiated transcript into `concepts/`.
5. Every important claim must remain traceable to an observed source. If the source is incomplete, record the uncertainty.
6. Keep raw/long extracted material in an artifact or source node and keep concept nodes compact.
