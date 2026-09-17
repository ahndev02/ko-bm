---
sessionID: ses_f582a55b0ffe0HSOYFEuC87P3h
baseMessageCount: 0
updatedAt: 2026-09-16T01:39:10.026Z
version: 1.1
date_created: 2026-09-16
owner: agent
tags: [spec, diagnostic]
---

# kobalt-700-benchmark-environment

# Introduction
This specification defines a benchmark environment for evaluating LLMs on **KoBALT-700** (Korean Benchmark for Advanced Linguistic Tasks; SNU CL_NLP Lab + LG AI Research; arXiv:2505.16125). KoBALT-700 is a contamination-resistant, linguistically-grounded multiple-choice benchmark: 700 expert-authored Korean items spanning 24 linguistic phenomena across 5 domains, scored by strict 0/1 exact match.

The environment specified here:

1. **Ingests** the dataset from HuggingFace (`snunlp/KoBALT-700`) with local caching and integrity validation.
2. **Runs** models through a unified backend abstraction — hosted API models (OpenAI-compatible default + native SDK adapters) and local open-weights models (HF `transformers` or vLLM, with the model's chat template).
3. **Executes** the official upstream inference protocol by default (Korean CoT prompt, greedy decoding, 2048-token cap, regex answer extraction) — overridable via run config for ablations.
4. **Scores** predictions by exact match and reports accuracy overall and per Class / Subclass / Level.
5. **Manages** runs as self-contained directories (config snapshot + predictions + results + logs), resumable after interruption, and **aggregates** completed runs into a single comparison table.

One CLI invocation = one model run. First end-to-end validation targets: one API model and one small (7–8B) local open-weights model. CI (GitHub Actions) runs unit + mock-backend integration tests on every push/PR.

## 1. Purpose & Scope

### Intended audience
Researchers and practitioners who want to (a) reproduce published KoBALT-700 baselines under identical protocol, or (b) evaluate new Korean-capable LLMs (API or open-weights) with the same harness.

### Boundaries
**In scope**
- Dataset ingestion, caching, and integrity validation.
- Prompt construction from the official Korean CoT template.
- Pluggable model inference: API backends and local open-weights backends (transformers / vLLM).
- Answer extraction (upstream two-stage regex logic) and 0/1 scoring.
- Reporting: per-item predictions, accuracy by Class, Subclass, Level; multi-run comparison table.
- Run lifecycle: single-command invocation, resumability, independent re-scoring.
- CI for the credential-free test suite.

**Out of scope**
- Human preference evaluation (the `Sampling_YN` study).
- Dataset item creation or modification; contamination analysis.
- Training/fine-tuning of models.
- Full 18-model upstream baseline reproduction at spec-acceptance time (achievable later as an outer loop over run configs — no new harness code required).

### Assumptions
- The dataset is public and non-gated on HuggingFace: subset `kobalt_v1`, split `raw`, 700 items, fields `ID/Class/Subclass/Question/Answer/Level/Sampling_YN`.
- License is **CC BY-NC 4.0** (non-commercial use only) — downstream usage must respect it.
- Python 3.11+ toolchain managed with **uv**; a GPU is available for local backends; the repository is hosted on GitHub (for Actions CI).

## 2. Definitions
- **KoBALT**: Korean Benchmark for Advanced Linguistic Tasks — 700 MCQ items across Syntax (300), Semantics (215), Pragmatics (81), Phonetics/Phonology (62), Morphology (42).
- **Item**: one multiple-choice question. Fields: `ID` (24-char string), `Class` (5 domain values), `Subclass` (24 phenomenon values), `Question` (70–1,170 chars, options A–J embedded in text; 5–10 options per item), `Answer` (single letter A–J), `Level` (1–3), `Sampling_YN` (0/1, human-preference-study flag; not used for scoring).
- **Backend**: pluggable model runner. Families: **API** (hosted chat models) and **Local** (open-weights via HF `transformers` or vLLM).
- **Run**: one CLI invocation evaluating one (backend, model, config) tuple; produces one **run directory**.
- **Run directory**: self-contained output folder — config snapshot, per-item predictions (JSONL), results summary (JSON), log file.
- **Exact match**: `predicted_answer == ground_truth_answer`; 0/1, no partial credit, no LLM judge.
- **Validation run**: an end-to-end run of the full 700-item set against a validation-target model, used to sanity-check the environment against upstream published scores.
- **Official protocol** (verified against upstream `data/inference_open-models.py`): system+user messages ("당신은 문제를 해결하는 전문가입니다." / user template instructing choice among A–J and requiring the answer to end with "정답은 [정답 보기]입니다."), tokenizer chat template applied with `add_generation_prompt=True`, greedy decoding (`do_sample=False`), `max_new_tokens=2048`, `eos_token_id` from tokenizer when present, `torch_dtype="auto"`, `device_map="auto"`, sequential per-item processing.

## 3. Requirements, Constraints & Guidelines

**Requirements**
- **REQ-001**: Load `snunlp/KoBALT-700` (subset `kobalt_v1`, split `raw`) via HuggingFace `datasets` with local caching.
- **REQ-002**: Build prompts as system+user messages using the official Korean CoT template by default; template text and extraction regex overridable via run config.
- **REQ-003**: Extract answers with the upstream two-stage logic: regex `정답은\s*(.*?)\s*입니다` → collect distinct uppercase A–J letters in order of first appearance → join with `", "`. The predicted answer equals ground truth only when exactly one letter is extracted and it matches. No match → `predicted_answer: null`, scored incorrect.
- **REQ-004**: Report accuracy overall, per Class, per Subclass, per Level; include per-item prediction records.
- **REQ-005**: Provide backend families: (a) API — OpenAI-compatible path as default plus native SDK adapters (e.g., Anthropic) where provider behavior requires it; (b) local open-weights — HF `transformers` and vLLM engines, selected in run config.
- **REQ-006**: Ship the official protocol as the default preset; prompt, extraction, and generation settings overridable via run config.
- **REQ-007**: Persist per-item predictions during inference so long runs can be resumed without re-inferring completed items.
- **REQ-008**: Provide a single CLI entrypoint: one command takes a model + run config and creates a run directory (config snapshot, predictions JSONL, results summary JSON, logs).
- **REQ-009**: Each run directory must be independently re-scorable — the scoring/aggregation step operates on stored predictions with no model calls.
- **REQ-010**: Provide a `compare` command aggregating multiple run directories into one comparison table (overall + per-Class accuracy per run).
- **REQ-011**: Manage dependencies via `pyproject.toml` + uv lockfile; Python 3.11+; heavy inference dependencies (vLLM, torch/CUDA) isolated as optional extras so the core install stays light.
- **REQ-012**: Validate the environment end-to-end with (a) one API model and (b) one small local open-weights model (7–8B class) before first release.
- **REQ-013**: GitHub Actions CI on every push/PR: install via uv, run unit tests and mock-backend integration tests; GPU-dependent and real-API tests excluded from CI.

**Security constraints**
- **SEC-001**: API keys supplied via environment variables only; never logged, persisted in results, or committed.
- **SEC-002**: CI must not require any real API credentials; no keys in workflow files.

**Constraints**
- **CON-001**: Python toolchain: uv + `pyproject.toml` + lockfile, Python 3.11+.
- **CON-002**: Default generation: greedy (`do_sample=False`), `max_new_tokens=2048`, `eos_token_id` from tokenizer when present; transformers loads with `torch_dtype="auto"`, `device_map="auto"`, `model.eval()`.

**Guidelines**
- **GUD-001**: Results artifacts must be self-describing: model id, backend/engine, generation config, prompt-template hash, dataset revision (pin the HF dataset revision hash in results metadata).
- **GUD-002**: API backends apply retry with backoff on transient errors and configurable request concurrency. (Upstream is sequential; concurrency is an opt-in throughput feature, not a protocol change.)

## 4. Interfaces & Data Contracts

**Dataset record** (per item, from HF):
```json
{"ID": "str(24)", "Class": "Syntax|Semantics|Pragmatics|Phonetics/Phonology|Morphology", "Subclass": "<one of 24>", "Question": "str(70–1170)", "Answer": "A"–"J", "Level": 1–3, "Sampling_YN": 0|1}
```

**Prompt contract (messages list)**:
```json
[
  {"role": "system", "content": "<system_text>"},
  {"role": "user",   "content": "<user_template with {question} substituted>"}
]
```
Local backends render via `apply_chat_template(messages, add_generation_prompt=True)`; API backends send the messages list as chat messages.

**Run config** (YAML/JSON; exact schema finalized at implementation):
```yaml
backend:
  family: api | transformers | vllm
  model: <model id>
  endpoint: <optional, for OpenAI-compatible endpoints>
  engine_opts: <optional engine-specific options, snapshotted per run>
generation:
  do_sample: false
  max_new_tokens: 2048
prompt:
  system: <official system text>
  user_template: <official user template>
extraction:
  regex: '정답은\s*(.*?)\s*입니다'
```

**Backend runner interface (conceptual)**: `generate(messages: list[list[dict]], config) -> list[str]` — shared by all backend families; prompt/render/parse/scoring code is identical across families.

**CLI (conceptual)**:
```
kobalt-eval run    --config run.yaml [--limit N] [--resume <run_dir>]
kobalt-eval score  <run_dir>
kobalt-eval compare <run_dir>... [--out table.md|table.json]
```
(Exact command/flag names finalized at implementation.)

**Prediction record** (JSONL, one line per item):
```json
{"id": "...", "model": "...", "backend": "api|transformers|vllm", "raw_output": "...", "predicted_answer": "H|null", "ground_truth": "H", "correct": true, "class": "Semantics", "subclass": "Implicature", "level": 2, "latency_ms": 1234}
```

**Results summary** (JSON): overall accuracy; accuracy grouped by Class, Subclass, Level; item counts; run metadata (config snapshot reference, dataset revision).

**Comparison table** (JSON/markdown): one row per run — model, backend, overall accuracy, accuracy per Class; derived strictly from each run's `results.json`.

**Run directory layout (conceptual)**:
```
<run_dir>/
├── config.snapshot.yaml   # exact config used, including engine_opts and template hash
├── predictions.jsonl      # per-item prediction records (append-ordered, resumable)
├── results.json           # accuracy aggregates + run metadata
└── run.log                # execution log (no secrets)
```

## 5. Acceptance Criteria
- **AC-001**: Given a fresh checkout, When `uv sync` completes and the dataset loader runs, Then all 700 items load with 5 valid Class values, 24 valid Subclass values, and answers in A–J.
- **AC-002**: Given a configured API backend, When `run` executes on a subset, Then a run directory is created containing exactly one prediction record per item, and API keys are sourced only from environment variables.
- **AC-003**: Given a local backend configured with either `transformers` or `vllm`, When `run` executes on a subset, Then the chat template is applied, decoding is greedy, predictions are deterministic, and the run is resumable after interruption.
- **AC-004**: Given per-item predictions, When `score` runs, Then overall and per-Class/Subclass/Level accuracies are computed and are comparable to published baselines under identical settings.
- **AC-005**: Given an interrupted run with partial predictions, When `run --resume` is invoked, Then only incomplete items are re-inferred and the final result covers all 700 items with no duplicate IDs.
- **AC-006**: Given a completed run directory, When `score` is re-invoked on it, Then identical results are produced without any model calls.
- **AC-007**: Given two or more completed run directories, When `compare` runs, Then a table with one row per run (overall + per-Class accuracies) is produced; corrupt or incomplete run directories are reported and skipped, not fatal.
- **AC-008**: Given a full validation pass, When the designated API model and the small local model are each run over all 700 items, Then both runs complete with results plausibly consistent with upstream published scores for comparable models (exact match only when the identical model is used).
- **AC-009**: Given a PR containing a regression in extraction or scoring logic, When CI runs, Then the corresponding failing test blocks the merge.

## 6. Test Automation Strategy
- **Framework**: pytest.
- **Unit tests**:
  - Prompt/messages builder — template substitution, exact official texts.
  - Two-stage answer extraction — multi-match with distinct letters (→ joined output), repeated letters deduplicated, missing phrase (→ null), empty output (→ null).
  - Scorer/aggregator math — against hand-computed fixture predictions.
  - `compare` aggregation — fixture run directories, including the incomplete-run skip path.
- **Integration tests**:
  - Subset runs against mock/stub backends with canned outputs, one stub per backend family (API, transformers, vLLM).
  - Dataset loader against a cached dataset fixture.
  - Resumability: interrupt mid-run, restart, verify completion and no duplicate IDs.
  - CLI smoke tests: `run` → run directory contents; `score` on stored predictions; `compare` over fixture run dirs.
- **Hardware-gated tests**: local-engine tests (real transformers/vLLM execution) marked with a GPU marker and skipped when no GPU is present, including in CI.
- **CI (GitHub Actions)**: on every push/PR — uv install, unit tests, mock-backend integration tests. No real API calls, no GPU jobs, no secrets required.

## 7. Rationale & Context
- **Protocol fidelity as default**: mirroring the official protocol (verified upstream behavior: chat template, greedy decoding, two-stage regex extraction, 2048-token cap) is required for apples-to-apples comparison with published baselines (Claude-3.7-Sonnet 0.61 … Mistral-7B-v0.3 0.12). Overridability supports ablations without forking the harness.
- **Hybrid API layer**: one OpenAI-compatible code path covers most providers and self-hosted servers; native SDK adapters exist only where provider-specific behavior (system-prompt handling, error semantics) matters. Small surface, no fidelity loss.
- **Dual local engines**: `transformers` reproduces upstream scripts exactly (reproducibility); vLLM makes 700-item sweeps fast at scale. Run config selects per run; both share the same prompt/parse/scoring path.
- **Sequential default, opt-in concurrency**: upstream processes items one at a time; the harness keeps that as default semantics and treats concurrency as a throughput option so result ordering/completeness semantics stay identical.
- **Self-contained run directories**: one command per run keeps provenance simple — the config snapshot travels with the results — and batch evaluation is an outer loop over configs rather than new harness code. `compare` reads only `results.json`, keeping aggregation decoupled from inference.
- **Validation strategy**: one API model + one small local model exercises the full stack (both backend families) at minimal cost; full 18-model reproduction is later just config repetition.
- **CI scope**: only credential-free tests run in CI; real-API and GPU tests need secrets/hardware and are run manually by the operator.
- **Exact-match 0/1**: keeps scoring trivially auditable; no LLM judge, matching upstream.

## 8. Dependencies & External Integrations
- **EXT-001**: HuggingFace Hub / `datasets` — dataset source for `snunlp/KoBALT-700` (public, non-gated); revision hash pinned in results metadata.
- **EXT-002**: API providers — OpenAI-compatible HTTP endpoints plus native SDK adapters (e.g., `openai`, `anthropic` packages); authentication via environment variables.
- **EXT-003**: Local inference engines — HF `transformers` and vLLM, installed as optional extras (`uv sync --extra ...`).
- **EXT-004**: Upstream reference implementation — github.com/snunlp/KoBALT-700 (`data/inference_open-models.py` et al.) as protocol source of truth. Behavior verified: chat template applied, greedy decoding, no batching, multi-letter extraction joined with `", "`.
- **EXT-005**: uv — environment and lockfile management (`uv sync`, extras).
- **EXT-006**: GitHub Actions — CI (unit + mock integration on push/PR).

## 9. Examples & Edge Cases

**Official user message (verbatim, upstream-confirmed)**:
```
다음 문제에 대해서 충분히 생각하고 추론하여, 10개의 보기(A, B, C, D, E, F, G, H, I, J) 중 정답을 고르세요.

{question}

답변은 반드시 다음 형식을 엄격히 지켜야 합니다: "정답은 [정답 보기]입니다."로 끝나야하고, [정답 보기]는 A, B, C, D, E, F, G, H, I, J 중 하나여야 합니다.정답: 문제를 풀기 위해, 한 번 천천히 생각해봅시다.
```
(System message: `당신은 문제를 해결하는 전문가입니다.`)

**Answer extraction (upstream logic)**:
- Response containing both "정답은 A입니다" and later "정답은 C입니다" → predicted `A, C` → never equals a single ground-truth letter → **incorrect by construction** (upstream-consistent).
- Response containing only "정답은 H입니다" → predicted `H` → compared directly against ground truth.
- Repeated mentions of the same letter → deduplicated, order of first appearance preserved.
- No "정답은 …입니다" phrase anywhere → `predicted_answer: null` → incorrect.
- Empty/truncated output → `predicted_answer: null` → incorrect.

**Engine semantics**:
- vLLM `engine_opts` differing from transformers defaults (e.g., kv-cache dtype) must not silently change generation semantics; engine opts live in the run config and are snapshotted per run.

**Comparison tooling**:
- `compare` against a run directory missing `results.json` (e.g., inference finished but scoring not run) → warn and skip that run, not crash.

## 10. Validation Criteria
- **Dataset integrity**: exactly 700 items; 5 Class values; 24 Subclass values; all `Answer` values in A–J; all `Level` values in 1–3.
- **Extraction correctness**: unit tests cover all documented edge cases with a 100% expected-verdict match.
- **Reproducibility**: identical config + cached backend → identical accuracy; `results.json` validates against its schema.
- **Baseline sanity**: an upstream-evaluated model run under the default preset lands near its published score (within run-to-run variance).
- **Resumability**: kill mid-run + resume → complete 700-item prediction file with no duplicate IDs.
- **Lockfile reproducibility**: `uv sync --locked` succeeds on a fresh machine; extras resolve independently.
- **CI cleanliness**: CI is green on a fresh clone without any secrets configured.

## 11. Related Specifications / Further Reading
- **arXiv:2505.16125** — the KoBALT paper (dataset design, domains, human evaluation study, baseline table).
- **HuggingFace dataset card** — `snunlp/KoBALT-700` (field definitions, viewer statistics, license CC BY-NC 4.0).
- **Upstream GitHub repository** — github.com/snunlp/KoBALT-700 (README baseline table; `data/inference_*.py` scripts as the protocol reference).

## Q&A history

Q: Which model backends must the benchmark harness support first?
A: Both API and local open-weights

Q: How strictly should the harness mirror the official inference protocol?
A: Official protocol as default, with overridable config for prompt/extraction/settings

Q: Which local inference engine should the local open-weights backend target?
A: Both, selectable in run config (Recommended)

Q: How should the harness invoke and manage runs?
A: Single CLI command per run (model + config file), results to a run directory (Recommended)

Q: Should the harness include a multi-run comparison/reporting tool (e.g., a baseline-style table across all completed runs)?
A: Yes — a compare command that aggregates run directories into one table (Recommended)

Q: How should the Python toolchain and dependencies be pinned?
A: uv + pyproject.toml with a lockfile; Python 3.11+ (Recommended)

Q: How should API backends be implemented?
A: Hybrid: OpenAI-compatible default + native SDK adapter where needed

Q: For local backends, how should prompts be fed to the model? (Upstream script behavior not yet confirmed.)
A: Apply the model's chat template (recommended — matches API chat semantics; I will verify upstream behavior before finalizing) (Recommended)

Q: Should CI be part of this spec (e.g., GitHub Actions)?
A: not sure what this means

Q: Which models should the environment target for its first end-to-end validation runs?
A: One API model + one small local model (e.g., a 7–8B open-weights) (Recommended)

Q: CI means an automatic test runner (e.g., GitHub Actions) that installs the environment and runs the test suite on every push/PR, so regressions are caught without anyone remembering to test. Do you want CI configured for this repo? (If you don't use GitHub, or prefer manual testing, choose accordingly.)
A: Yes — GitHub Actions running unit tests + mock-backend integration tests on every PR (Recommended)
