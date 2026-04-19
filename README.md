# Slice-of-Life Game Factory

A research-first, LLM-driven game factory for turning one real public conflict case into one frozen world and one playable game.

## Core flow

1. build or load a web-grounded research pack
2. freeze one role-specific world artifact
3. inspect selectable roles and turn counts
4. play from the stored immutable world
5. review the world-local ending

The historical flash-crash scenario remains in the repo only as sample/regression content. The core architecture now centers on research packs, frozen worlds, world-local action grammars, and runtime play from stored artifacts.

## Architecture notes

Current implementation-grounded architecture docs live under [`docs/plans/`](./docs/plans/README.md). Start there for the active action/runtime contracts and the migration audit; older draft plans in that directory are historical context only.

## Requirements

Live material generation and free-play against generated worlds still require an OpenAI-compatible endpoint and key:

```bash
export OPENAI_BASE_URL='http://127.0.0.1:8080/v1'
export OPENAI_API_KEY='***'
export OPENAI_MODEL='codex'
export NO_PROXY='127.0.0.1,localhost'
export no_proxy="$NO_PROXY"
```

Deterministic anchor-case research/freeze/inspect flows work without LLM credentials.

## Quick start

```bash
cd ~/projects/slice-of-life
python3.11 -m eventforge --help
python3.11 -m eventforge research-case --case wuhan-university-yang-jingyuan --output /tmp/wuhan-research.json
python3.11 -m eventforge freeze-world --case wuhan-university-yang-jingyuan --player-role 校方 --output /tmp/wuhan-school.json
python3.11 -m eventforge inspect-world --world-file /tmp/wuhan-school.json
python3.11 -m eventforge play --world-file /tmp/wuhan-school.json --mode auto --turns 4
```

## Tests

```bash
python3.11 -m pytest tests/ -q
```
