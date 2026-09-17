# KoBALT-700 benchmark harness

Evaluation harness for [KoBALT-700](https://huggingface.co/datasets/snunlp/KoBALT-700)
(Korean Benchmark for Advanced Linguistic Tasks; SNU CL_NLP Lab + LG AI Research):
700 expert-authored Korean multiple-choice items across 5 linguistic domains,
scored by strict 0/1 exact match under the official upstream inference protocol
(Korean CoT prompt, greedy decoding, 2048-token cap, regex answer extraction).
One CLI invocation evaluates one model; runs are self-contained directories
(config snapshot + predictions + results + logs), resumable and re-scorable,
and multiple runs can be aggregated with `compare`.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev        # core deps + pytest/pytest-cov for the test suite
```

Optional extras (kept out of the default install so it stays light):

| Extra          | Contents                                     |
|----------------|----------------------------------------------|
| `transformers` | HF `transformers` + `accelerate` local engine |
| `vllm`         | vLLM local engine (Linux only)               |
| `dev`          | `pytest`, `pytest-cov`                       |

```bash
uv sync --extra transformers   # local HF engine (reproduces upstream scripts)
uv sync --extra vllm           # fast local sweeps (Linux only)
```

## CLI usage

```bash
# Evaluate (subset first for smoke tests; drop --limit for the full 700)
export OPENAI_API_KEY=...   # keys come from env vars only, never config files
kobalt-eval run --config run.yaml --limit 10 --out runs/smoke-gpt
kobalt-eval run --config run.yaml --out runs/full-gpt

# Resume an interrupted run (only missing items are re-inferred)
kobalt-eval run --config run.yaml --resume runs/full-gpt

# Re-score a run directory (no model calls, byte-identical on repeat)
kobalt-eval score runs/full-gpt

# Aggregate runs into one table (markdown to stdout, or --out table.md/.json)
kobalt-eval compare runs/full-gpt runs/full-local
kobalt-eval compare runs/full-gpt runs/full-local --out table.md
```

Run tests (offline; GPU and live-network tests skip by default):

```bash
uv run pytest -q              # everything: unit + mock-backend integration
uv run pytest -m "not gpu" -q # the CI selection
KOBALT_TEST_LIVE=1 uv run pytest -q          # also hit the real HF dataset
KOBALT_TEST_GPU_LIVE=1 uv run pytest -m gpu -q  # real local-engine inference
```

## Example run config

```yaml
backend:
  family: api            # api | transformers | vllm
  model: gpt-4o-mini
  api_provider: openai   # openai | anthropic (only when family == api)
  # endpoint: https://...  # optional, for OpenAI-compatible endpoints
  max_retries: 3
  concurrency: 1         # 1 = sequential (upstream default)
generation:
  do_sample: false
  max_new_tokens: 2048
prompt:
  system: 당신은 문제를 해결하는 전문가입니다.
  user_template: |
    다음 문제에 대해서 충분히 생각하고 추론하여, 10개의 보기(A, B, C, D, E, F, G, H, I, J) 중 정답을 고르세요.

    {question}

    답변은 반드시 다음 형식을 엄격히 지켜야 합니다: "정답은 [정답 보기]입니다."로 끝나야하고, [정답 보기]는 A, B, C, D, E, F, G, H, I, J 중 하나여야 합니다.정답: 문제를 풀기 위해, 한 번 천천히 생각해봅시다.
extraction:
  regex: '정답은\s*(.*?)\s*입니다'
```

Local-engine example (`family: transformers`, `model: <hf-id>`):
`generation.do_sample`/`max_new_tokens` drive greedy decoding, and any
engine-specific knobs go under `backend.engine_opts` (snapshotted per run).

## License note

The KoBALT-700 dataset ([snunlp/KoBALT-700](https://huggingface.co/datasets/snunlp/KoBALT-700))
is released under **CC BY-NC 4.0 — non-commercial use only**. Respect it in
downstream usage. This harness code is MIT (see `pyproject.toml`).

## References

- Spec: `interview/benchmark-environment-for-https-huggingface-co-d-eafd696f-288b-434b-917e-5d99536ceaa7.md`
- Upstream repo: [github.com/snunlp/KoBALT-700](https://github.com/snunlp/KoBALT-700)
  (protocol reference: `data/inference_*.py`)
- Paper: arXiv:2505.16125
