# Reference Snapshot — Channel Security

`SecurityConfig` modes:

```text
compat
audit
strict
```

Recommended rollout from current upstream docs:
1. compatibility during migration if needed;
2. audit for staging/canary visibility;
3. strict after verification.

For this new Feishu integration:
- start canary in audit;
- promote to strict after normal behavior is confirmed.

Strict mode hardens:
- webhook signature behavior for encrypted webhook paths;
- insecure remote WS behavior;
- error responses;
- token-cache fallback behavior;
- optional WS fragment/concurrency resource limits.

Even though v0.1 uses WS, the security mode should still be explicit and tested.

Do not rely on adapter string escaping where the SDK already provides
`safe_content_text` and normalized text forms.
