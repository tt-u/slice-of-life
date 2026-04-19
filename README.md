# Flash Crash Demo

An event-centered, LLM-driven decision simulation.

## Premise

You are the founder of a crypto project at the center of a token crash crisis. Each turn you choose one action. Other agents — KOLs, whales, market makers, community organizers, and the exchange — generate their own profiles, trigger pre-turn events, and react to you. The run ends with a new global world state plus a shareable summary.

## Requirements

This project is now **LLM-only**. You must provide an OpenAI-compatible endpoint and key.

```bash
export OPENAI_BASE_URL='http://127.0.0.1:8080/v1'
export OPENAI_API_KEY='your-key'
export OPENAI_MODEL='codex'
export NO_PROXY='127.0.0.1,localhost'
export no_proxy="$NO_PROXY"
```

## Quick start

```bash
cd ~/projects/slice-of-life
python3.11 play.py --mode auto --turns 6
python3.11 play.py --mode interactive --turns 6
```

## Tests

```bash
python3.11 -m pytest tests/ -q
```
