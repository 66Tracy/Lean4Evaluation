# Lean4Evaluation

LLM Formal Mathematics Evaluation Framework for Lean 4. Assesses LLM capabilities on two tasks:

- **Task1 (Translation)**: Translate natural language math statements into Lean 4 formal theorem declarations, scored by a judge model on equivalence, Mathlib style, and syntax correctness.
- **Task2 (Proof, Pass@k)**: Generate k tactic proofs for each theorem, execute them via a Lean runner API, and compute the Pass@k metric.

## Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- A Lean runner API server (for Task2)
- An OpenAI-compatible LLM API endpoint

### Install

```bash
uv sync
```

### Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `TEST_API_URL` | LLM API base URL for the model being evaluated |
| `TEST_MODEL_NAME` | Model name |
| `TEST_API_KEY` | API key |
| `JUDGE_API_URL` | Judge model API URL (optional, defaults to TEST) |
| `JUDGE_MODEL_NAME` | Judge model name (optional, defaults to TEST) |
| `JUDGE_API_KEY` | Judge API key (optional, defaults to TEST) |
| `LEAN_API_URL` | Lean runner API endpoint (default: `http://localhost:8000/run`) |

## Usage

### Task1: Translation Quality Evaluation

```bash
uv run python scripts/run_task1.py \
  --data benchmarks/MiniF2F/MiniF2F-test-examples.jsonl \
  --output results/task1_output.jsonl \
  --concurrency 5
```

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--data` | (required) | Input benchmark JSONL |
| `--output` | (required) | Output JSONL path |
| `--prompt` | `prompts/task1_translate.txt` | Translation prompt template |
| `--judge-prompt` | `prompts/task1_judge.txt` | Judge prompt template |
| `--judge-model` | from `.env` | Override judge model name |
| `--judge-url` | from `.env` | Override judge API URL |
| `--judge-key` | from `.env` | Override judge API key |
| `--concurrency` | 5 | Max concurrent API calls |

**Output format** (JSONL, one record per line):

```json
{"id": "...", "nl_statement": "...", "formal_statement": "...", "pred": "...", "equivalence": 5, "mathlib_style": 4, "syntax": 1, "final_score": 9}
```

Scoring: `final_score = (equivalence + mathlib_style) * syntax` (max 10).

### Task2: Proof Capability Evaluation (Pass@k)

```bash
uv run python scripts/run_task2.py \
  --data benchmarks/MiniF2F/MiniF2F-test-examples.jsonl \
  --output results/task2_output.jsonl \
  --k 5 \
  --temperature 0.7
```

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--data` | (required) | Input benchmark JSONL |
| `--output` | (required) | Output JSONL path |
| `--prompt` | `prompts/task2_prove.txt` | Proof prompt template |
| `--k` | 5 | Proof attempts per theorem |
| `--temperature` | 0.7 | Sampling temperature |
| `--seed-base` | None | Base seed for reproducibility |
| `--lean-api` | from `.env` | Lean runner API URL |
| `--lean-concurrency` | 5 | Max concurrent Lean executions |
| `--lean-timeout` | 60 | Lean execution timeout (seconds) |
| `--concurrency` | 5 | Max concurrent LLM API calls |

**Output format** (JSONL):

```json
{"id": "...", "formal_statement": "...", "k": 5, "success_count": 3, "pass_at_k": 1.0, "details": [{"proof": "...", "success": true, "elapsed_sec": 12.5}, ...]}
```

Pass@k formula: `1 - C(n-c, k) / C(n, k)` where n = total attempts, c = successes.

## Benchmark Data

Input JSONL files should have the following fields per record:

| Field | Description |
|---|---|
| `id` | Unique problem identifier |
| `split` | Dataset split (e.g., "test") |
| `formal_statement` | Lean 4 theorem with `sorry` placeholder |
| `header` | Mathlib imports and namespace declarations |
| `nl_statement` | Natural language problem statement |
| `informal_proof` | Human-readable proof |

Example data is provided in `benchmarks/MiniF2F/MiniF2F-test-examples.jsonl`.

## Project Structure

```
src/
  core/
    client.py       # AsyncOpenAI wrapper with retry and concurrency control
    config.py       # Environment/config loading
    utils.py        # JSONL I/O, prompt loading, code/JSON extraction
  tasks/
    task1.py        # Translation evaluation logic
    task2.py        # Proof evaluation + Pass@k logic
  lean_runner_api.py  # Lean code execution client (provided)
prompts/            # Prompt templates (customizable)
scripts/            # CLI entry points
benchmarks/         # Benchmark datasets
```
