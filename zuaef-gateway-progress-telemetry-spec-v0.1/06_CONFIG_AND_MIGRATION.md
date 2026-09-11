# 06 — Configuration and Migration

## Existing environment variables remain canonical

```text
ZUAEF_RUN_ACK=true
ZUAEF_RUN_PROGRESS_SECONDS=25
ZUAEF_RUN_PROGRESS_SECONDS_2=50
```

## New semantics

Before v0.1:

```text
first and second are two fixed checkpoints only
```

After v0.1:

```text
first and second are seeds for the entire arithmetic-backoff sequence
```

Default user-visible sequence:

```text
25, 50, 100, 175, 275, 400, 550, ... seconds
```

## Disable behavior

```text
ZUAEF_RUN_PROGRESS_SECONDS=0
```

disables all mid-run progress.

ACK remains separately controlled by:

```text
ZUAEF_RUN_ACK
```

## Validation

At Gateway startup:

```text
first < 0                     -> ValueError
first > 0 and second <= first -> ValueError
```

Do not silently normalize invalid values.

## Documentation

Update the existing operator documentation and `.env.example` if these variables are currently undocumented there.

Document:

- the default sequence;
- 0-disable behavior;
- arithmetic seed semantics;
- code/env changes require Gateway process restart.

## No profile-level config

Do not add progress config to profile TOMLs.

Progress is Gateway presentation behavior shared by all profiles.
