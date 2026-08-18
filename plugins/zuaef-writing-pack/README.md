# ZUAEF Writing Pack adapter

This is intentionally a thin consumer adapter for the external
`Rayegoe/zuaef_writing` repository.

- `skill_dirs` points at the pack's external `skills/` directory;
- one native toolset wraps `sanlian_catalog`, `sanlian_search`, and
  `sanlian_read`;
- no semantic ranking, technique extraction, EditorialEvidence, memory,
  sensors, or workflow state is added here;
- no source text is copied into `zuaef-agent` or ACE.

Install this package into the same environment as `zuaef-agent`, then set
`pack_root` in the profile or `ZUAEF_WRITING_PACK_ROOT` in the environment.
