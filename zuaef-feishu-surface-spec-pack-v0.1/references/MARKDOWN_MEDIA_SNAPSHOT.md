# Reference Snapshot — Markdown, Files, Media

The current Channel SDK supports generic outbound forms including:
- markdown;
- post;
- image;
- file;
- audio;
- video.

For v0.1:
- use markdown/text for normal agent output;
- use file for artifacts/documents;
- use card for generic approvals/actions.

Do not rebuild:
- markdown conversion;
- chunking;
- media upload plumbing;
- file-key handling

unless the current SDK cannot satisfy a concrete zuaef-agent requirement.

A generic artifact path must be validated under the existing zuaef-agent workspace
and external-effect/path policy before handing it to the Feishu SDK.
