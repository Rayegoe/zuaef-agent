# 08 — Feishu Integration

## Existing transport facts to preserve

The current Feishu adapter already:

- receives file resources;
- saves them below `workspace/inbox/feishu/<message-id>/...`;
- exposes them to the run as attachments;
- has a generic `send_document(channel_id, path, caption=...)` method.

The GatewayService already has receipt-aware artifact sending for the existing explicit artifacts command.

Do not add format-specific behavior to the Feishu adapter.

## Target UX

For an artifact-producing natural-language run, the user should not have to issue a second command just to receive the file.

Target sequence:

```text
Feishu message + attachment
    -> normal profile run
    -> artifact capability creates final file
    -> existing run settlement records artifact
    -> gateway sends concise terminal text
    -> gateway sends eligible final artifact file(s)
```

## Generic auto-delivery change

Refactor the current receipt-artifact sending loop in `GatewayService` into one generic helper, conceptually:

```text
_send_receipt_artifacts(session, receipt)
```

Reuse it from:

- the existing manual artifacts command;
- terminal settlement when automatic artifact delivery is enabled.

Do not duplicate the path/size checks.

## Configuration

Use one small gateway setting for automatic artifact delivery if the current product should preserve manual behavior for some deployments.

Recommended semantics:

```text
ZUAEF_GATEWAY_AUTO_ARTIFACTS=true|false
```

For the Feishu knowledge-worker + artifacts deployment, set it to true.

If the repository already has a generic equivalent flag by implementation time, reuse it instead of creating another.

## Delivery scope

Only send artifact files listed by the settled run and passing the existing gateway containment/file-size rules.

Do not scan the whole `workspace/artifacts/` tree after every run.

## Delivery failure

A Feishu upload failure does not rewrite the completed execution result.

The gateway should:

- log the transport failure;
- send a short text warning when possible;
- keep the durable delivery copy/path available through existing mechanisms;
- allow the manual artifact command as recovery.

## Input/output symmetry

This produces the desired Feishu work loop:

```text
Upload source file
-> ask naturally
-> ZUAEF reads it
-> ZUAEF produces result
-> file comes back to the same chat
-> user replies with revision instructions
-> ZUAEF revises and returns the next version
```

## No native Feishu document objects in v0.1

Do not create Feishu Docs, Feishu Sheets, or Drive objects in this work. Standard file upload/download is sufficient for the first closed loop.

Native Feishu document projection is a separate product decision after artifact production is proven.
