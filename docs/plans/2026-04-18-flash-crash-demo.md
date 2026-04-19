# Flash Crash Demo Implementation Plan

**Goal:** Build a playable text-mode demo where the player is the central figure in a crypto crash event, chooses actions each turn, and receives world responses plus a final judged outcome.

**Architecture:** Use a small deterministic simulation core with seeded NPC agents, clear scenario state variables, and optional OpenAI-compatible LLM augmentation for agent profile generation and flavored world narration. Keep the game fully playable without an API key.

**Tasks:**
1. Bootstrap a fresh src-layout Python project with local launchers and tests.
2. Model scenario, agents, actions, world state, and judged outcomes.
3. Implement deterministic crisis simulation loop and scoring.
4. Add OpenAI-compatible LLM client for profile/narration generation with robust fallback.
5. Add CLI for interactive and auto play.
6. Verify with tests and a playable run.
