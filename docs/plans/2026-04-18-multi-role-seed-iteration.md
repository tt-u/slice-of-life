# Multi-Role Seed Iteration Plan

> **For Hermes:** Use test-driven-development skill for every code change.

**Goal:** Improve multi-role seed UX, make role-relative initial worlds diverge more reliably, and expose richer inspection output for comparing viewpoints.

**Architecture:** Extend the seed inspection data model so each viewpoint exposes comparison metadata and the primary counterparty, then strengthen world calibration by reasoning about role-relative conflict even when raw seed metrics are similar. Keep entity roles material-defined and surface the new comparison data in CLI inspection output.

**Tech Stack:** Python 3.11, pytest, dataclasses, argparse CLI.

---

### Task 1: Add failing worldgen tests for multi-role ordering and symmetric-conflict divergence
- Write a test asserting `build_scenario_from_material()` promotes the selected role to the front of `playable_roles`.
- Write a test where two direct conflict parties have identical raw stats and confirm role-relative initial worlds still diverge materially.
- Run the specific tests and confirm they fail for the expected reason.

### Task 2: Add failing inspection/CLI tests for richer viewpoint comparison output
- Write a test asserting `inspect_material_seed()` returns comparison metadata (baseline role, metric deltas, primary counterparty, player entity).
- Write a CLI test asserting `--list-player-roles` prints the richer comparison lines.
- Run the specific tests and confirm they fail for the expected reason.

### Task 3: Implement the minimal domain + worldgen changes
- Extend the viewpoint inspection dataclasses with comparison fields.
- Normalize role ordering so the selected role comes first in generated scenario metadata.
- Strengthen viewpoint calibration using conflict-aware adjustments that still respect material-defined roles.
- Re-run the targeted tests until green.

### Task 4: Implement minimal CLI output changes
- Print baseline/comparison/counterparty details for each viewpoint.
- Re-run the CLI test until green.

### Task 5: Verify and live-check
- Run `python3.11 -m pytest tests/ -q`.
- Run one live codex-proxy inspection command against a material file with the required environment variables and capture the output.
