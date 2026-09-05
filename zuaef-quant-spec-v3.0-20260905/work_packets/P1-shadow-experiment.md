# WP5 — Experiment Manager + S0/S1/S2

## Goal
Allow Agent/Code to diagnose and test strategy changes without contaminating production.

## Tasks
- experiment schema/lifecycle;
- baseline config snapshot and immutable variant diff;
- S0 scratch runner;
- S1 replay runner integration;
- S2 live shadow mode;
- result metrics and report;
- explicit reject/promote transition.

## Initial experiments
- Top30/50/80 candidate count;
- one-variable trigger sensitivity;
- market-regime filter;
- exit-policy comparison with fixed entry.

## Acceptance
No experiment can alter production evidence/config. Promotion is an explicit new strategy version.
