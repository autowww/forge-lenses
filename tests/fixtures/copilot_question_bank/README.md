# Copilot question bank (headless E2E)

Representative operator prompts for **Forge Lenses SDLC Copilot**, run against the Python engine only (no Studio UI).

## Fixture workspace

`workspace/alpha` and `workspace/beta` are minimal git-style repo folders with `README.md` and `forge/charge.md` for grounding tests.

## Run (mock — CI-safe)

```bash
cd forge-lenses
python3 -m pytest tests/test_copilot_question_bank.py -q
```

Uses a mocked LLM that returns grounding-aware text. Asserts **orchestration**: strategy (`single_shot` vs `portfolio_map_reduce`), citation counts, map subtasks, focused-repo roster skip.

## Run (live LLM)

```bash
export LENSES_COPILOT_LIVE=1
# optional: real multi-repo workspace instead of mini fixture
# export LENSES_COPILOT_WORKSPACE=/home/you/Code
export LENSES_COPILOT_LIVE_PROVIDER=openai_compatible
# export LENSES_COPILOT_LIVE_MODEL=ctx-unlim-qwen3-1p7b:latest
python3 -m pytest tests/test_copilot_question_bank.py -q -k live
```

Live tier adds **heuristic quality** checks (`must_mention`, `must_not_mention`) and an optional **LLM judge** (on by default; disable with `LENSES_COPILOT_JUDGE=0`).

## Question list

See [`questions.yaml`](questions.yaml) — project-dashboard identity, portfolio map-reduce, home overview, search, and vague scoped prompts.

## Harness module

[`tests/copilot_eval_harness.py`](../../copilot_eval_harness.py) — load bank, run `run_copilot_chat_multi`, evaluate orchestration + quality.
