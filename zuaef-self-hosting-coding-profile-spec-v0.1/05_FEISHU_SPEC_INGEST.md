# 05 — Feishu Spec Ingestion

## Current gap

The generic Gateway model already has:

```python
InboundEnvelope.attachments: list[AttachmentRef]
```

and `bridge.project_prompt()` already includes attachment paths.

Current Feishu v0.1, however, ignores messages whose body has no text and logs non-text message kinds as unsupported.

This is the missing transport seam for:

```text
send spec.zip in Feishu -> Agent receives local path
```

## Required change

Extend `FeishuAdapter` only.

Do not modify Agent runtime semantics.

## Upstream SDK facts

Current repository pins:

```text
lark-channel-sdk==1.4.0
```

The Channel SDK already exposes:
- normalized `InboundMessage.resources`;
- resource descriptors;
- `download_resource(...)`;
- `download_resource_to_file(...)`.

Use the SDK's public API rather than calling Feishu OpenAPI manually.

## Target inbound behavior

Supported v0.1 resource:
- `file`

Optional if trivial:
- image

Audio/video are not needed for the coding outcome.

### Text + file

A message containing text and one file becomes:

```python
InboundEnvelope(
    text="按这个 spec 开工",
    attachments=[...],
)
```

### File-only

A file-only message from an authorized user must no longer be discarded.

Its envelope may use a short neutral text such as:

```text
Attached file.
```

or an empty text if upper layers already handle it correctly.

Do not invent a coding instruction from the file name.

## Download path

Use a workspace-confined path, conceptually:

```text
workspace/inbox/feishu/<message-id>/<safe-filename>
```

`AttachmentRef.local_path` remains workspace-relative.

Do not expose absolute host paths to the model.

## Safety rules

1. Download only after surface authorization has passed.
2. Limit file size using the existing Gateway max-upload setting.
3. Reject path traversal / unsafe destination names.
4. Do not overwrite an unrelated existing file.
5. One failed resource must not corrupt session state.
6. Do not parse/extract the archive in the transport.
7. Do not let the Feishu adapter inspect Spec semantics.
8. Preserve original filename when safely available.
9. Record mime/size when available from the normalized resource/download result.
10. Return a user-facing transport error if the requested attachment cannot be made available.

## Runner plumbing

`GatewayConfig.max_upload_bytes` already exists.

Pass it into `FeishuAdapter` as is already done for relevant surfaces; do not create a second Feishu-specific size setting unless the SDK requires it.

## Archive extraction

Archive extraction belongs to the coding task environment, not Feishu.

The Agent can use Python standard library from Shell, e.g. `zipfile`, inside the workspace.

Extraction rules:
- destination stays under workspace;
- reject absolute member paths;
- reject `..` escape;
- do not follow archive symlinks;
- inspect before copying anything into the repo.

This is ordinary coding task execution, not a new Spec runtime.

## Feishu permissions

Deployment must have the Feishu/Lark permissions required to read message resources. If live download returns permission denied, surface the missing permission as the blocker and do not fake a local attachment.

## Acceptance

Real Feishu canary:

1. operator sends a small `spec.zip`;
2. Bot acknowledges;
3. Gateway creates an `AttachmentRef`;
4. coding profile receives the workspace-relative path;
5. Agent lists/opens the Spec contents;
6. no SSH/manual copy is used.
