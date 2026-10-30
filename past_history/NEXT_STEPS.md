# NEXT_STEPS.md — Finish the harness, test it, then run it on real models

This document continues `DESIGN.md`. It covers four things: how to write `acceptance.py`, which unit tests to write, how to install Ollama and run the experiment, and what you should expect to see at each step.

## 0. Where things stand

Written and spot-checked in the sandbox: the config files, prompts, extraction rules, iverilog simulation with the harness's pass/fail rules, Yosys cell counts, resumable generation, evaluation, manifest, metrics, report, subset check, and the CLI. The stub models (oracle, empty_header, empty_module, prose, planted) are written too.

Spot checks that passed: the subset recompute reproduces the frozen 60 problems from 128 eligible; generation resume writes 0 new records on a second run; a 3-problem baseline gave the right answers for every stub (oracle all PASS, empty_header none, empty_module compile errors, prose NO_CODE); the manifest validates.

**Not written yet:** `acceptance.py`, the pytest files, `pyproject.toml`, the README. **Never executed yet:** `metrics.py` and `report.py`, so expect a few small bugs there (see 1.7). **Never run against a real server:** the Ollama client. The sandbox could not reach Ollama.

The code lives in the sandbox until it is packaged. Order of work:

1. Write `acceptance.py` and the tests (Sections 1 and 2) and fix what they find.
2. Package the project as a zip (this can be done for you once step 1 passes).
3. Install Ollama and run the smoke test, then the full run on your machine (Section 3).

The planted-truth checks matter most. They test the pipeline against known answers, so a failure there is a bug in the harness and not a property of any model.

---

## 1. Writing `acceptance.py`

### 1.1 Contract

File: `src/rtlsens/acceptance.py`. The CLI already calls it:

```python
def run_acceptance(cfg) -> bool:   # True when no check FAILED (SKIP is allowed)
```

It runs every check below, prints one line per check, and writes `results/acceptance_report.md`. Each check returns a `Result(id, status, detail)` with status `PASS`, `FAIL` or `SKIP`. A check that cannot run (for example no Ollama server) must report `SKIP` with the reason, never `PASS`.

### 1.2 Structure

```python
from dataclasses import dataclass

@dataclass
class Result:
    id: str
    status: str    # PASS | FAIL | SKIP
    detail: str

def _cfg(name, workdir):
    # load a sibling config but write into a throwaway results directory
    return load_config(Path(cfg["_root"]) / "configs" / name, results_dir=str(workdir / name))

def run_acceptance(cfg) -> bool:
    work = Path(tempfile.mkdtemp(prefix="rtlsens_acc_"))
    results = [a1_preflight(cfg), *a2_a3_controls(work), a4_determinism_of_eval(work),
               a5_pytest(cfg), a6_manifest(cfg), a7_counts(work), a8_cache(work),
               a9_seed_passthrough(cfg), a10_fresh_run(cfg), *planted_checks(work)]
    write_report(cfg, results)
    return all(r.status != "FAIL" for r in results)
```

Each check wraps its body in `try/except` and turns an exception into `FAIL` with the message, so one broken check does not hide the others.

### 1.3 Check-by-check specification

| ID | What to do | Pass condition |
|---|---|---|
| A1 | Run `iverilog -V` and `yosys -V`; write `environment/versions.lock.txt` (tool versions plus `pip freeze`). | First line of `iverilog -V` starts with `Icarus Verilog version 12`; Yosys found. |
| A2 | Selftest config: `run_generation`, `evaluate`. Look at model `oracle`. | Every row is `PASS`, in every config; row count equals 60 × (4K + K + 2) (K = 2 gives 720). |
| A3 | Same run, models `empty_header`, `empty_module`, `prose`. | `empty_header` and `empty_module` have zero `PASS` rows; `prose` has only `NO_CODE`. |
| A4 | Run `evaluate` twice on the same generations; hash `eval.csv` each time. | The two SHA-256 values are equal. |
| A5 | Run `pytest -q` as a subprocess. | Exit code 0. |
| A6 | `write_manifest` then `validate_manifest`. | Empty problem list. |
| A7 | For every (model, config) in `eval.csv`, count rows. | 60 × K for B0, X1, X2, N1, P1; 60 for T0-A and T0-B. Class counts sum to the same number. |
| A8 | Take 20 random generation records. Run `evaluate(records=..., dedupe=True, write=False)` and again with `dedupe=False`. | The two frames are identical (`pandas.testing.assert_frame_equal`). |
| A9 | Offline part: mock server test (Section 2, `test_backends.py`). Live part, only if `/api/version` answers: call the real backend (see 1.4). | Offline: payload contains `seed`, `temperature`, `top_p`, `max_tokens`. Live: same seed gives identical text; seeds 1000 and 1001 give different text on at least one of 5 problems. No server gives `SKIP` for the live part. |
| A10 | Copy the project to a new temp directory without `results/`. Write a 3-problem subset file and a config pointing to it. Run `python -m rtlsens.cli all` with the selftest-style stubs. | Exit code 0 and `T1.csv` to `T7.csv` exist. |

### 1.4 Sketch of the live seed check (A9, untested)

```python
def a9_live(cfg):
    m = next(m for m in cfg["models"] if m["backend"] == "openai_compat")
    try:
        requests.get(m["base_url"].rstrip("/")[:-3] + "/api/version", timeout=3).raise_for_status()
    except requests.RequestException:
        return Result("A9-live", "SKIP", "no Ollama server reachable")
    be = make_backend(m, cfg["dataset_dir"])
    probs = read_names(cfg["subset_file"])[:5]
    call = lambda p, s: be.complete(load_system_prompt(cfg), build_user_prompt(cfg["dataset_dir"], p, "P0"),
                                    temperature=0.85, top_p=0.95, max_tokens=256, seed=s,
                                    meta={"problem": p, "prompt_variant": "P0"})["text"]
    same = all(call(p, 1000) == call(p, 1000) for p in probs)
    diff = any(call(p, 1000) != call(p, 1001) for p in probs)
    ok = same and diff
    return Result("A9-live", "PASS" if ok else "FAIL", f"same-seed identical={same}, different-seed differs={diff}")
```

Ollama's documentation lists `seed`, `temperature`, `top_p` and `max_tokens` as supported fields on `/v1/chat/completions`, so the payload is expected to work. This check proves it on your machine and your Ollama version.

### 1.5 Planted-truth checks (the important ones)

Run `experiment_planted.yaml` through `run_generation`, `evaluate`, `run_synth`, and `build_tables`. Then compare against what the stub was told to do. For each model `m`, let `stub = make_backend(m, dataset_dir)`, `N = 60`, `K = 10`. Let `p0_i = stub.p_variant(problem_i, "P0")` and `p1_i = stub.p_variant(problem_i, "P1")`.

| ID | Quantity | Truth | Pass condition |
|---|---|---|---|
| P1 | pass@1 for each config in B0, P1, X1, X2, N1 | `pi_i = stub.expected_pass(problem_i, config)`; truth = mean of `pi_i` | `abs(measured - truth) <= 4 * se`, with `se = sqrt(sum(K * pi_i * (1 - pi_i))) / (N * K)` (add `1e-9`) |
| P2 | σ_seed at B0 | `metrics.sigma_true(pi)` with `pi` for B0 | observed σ_seed within 0.5× to 2× of truth; predicted σ (formula from Section 9 of DESIGN.md) within 0.5× to 2× of truth |
| P3 | gains and losses for X1, X2, N1 against B0 | let `rate(f)` be the format probabilities (`clean = 1 - sum(rates)`); gain rate = sum of `rate(f)` for `f` in `FMT_OK[c] - FMT_OK["B0"]`; loss rate for `FMT_OK["B0"] - FMT_OK[c]`; truth = mean of `p0_i * gain_rate` (or loss rate) | within 4 se, with `se` computed as in P1 using `q_i = p0_i * rate` |
| P4 | excess flip for P1 | per problem `a = p0_i * f`, `b = p1_i * f` with `f = stub.fmt_prob_ok("B0")`; truth = mean of `a(1-b) + b(1-a) - 2a(1-a)` | `abs(measured - truth) <= 3 * (hi - lo) / 3.92` using the bootstrap CI from T3 |
| P5 | determinism | `planted_a`: `t0_nondeterminism = 0`; `planted_b`: 0.15 | `planted_a` raw identity is exactly 1.0; `planted_b` is within 4 standard errors of `(1 - 0.15)^2 = 0.7225` (se = `sqrt(0.7225 * 0.2775 / 60)`); outcome identity is 1.0 for both |
| P6 | gate-count proxy | every passing B0 sample is the reference solution renamed | all ratios to reference equal 1.0 for Y0, Y1, Y2; seed-induced CV is 0; tool-induced change Y0 to Y2 equals the reference cell-count ratio Y2/Y0 minus 1, recomputed from the `REF` rows of `synth.csv` |
| P7 | ranking | planted_a has a higher mean `pi` than planted_b | sign of Δ_AB at B0 matches the sign of the truth difference; reversal probability within ±0.15 of a Monte Carlo estimate (draw 20,000 pairs of seed-runs from Bernoulli(`pi`)) |
| P8 | material verdicts | known by construction | with the planted rates, X1, X2 and N1 effects are a few percentage points; check that `is_material` agrees with the `2 * sigma_true` rule applied to the *true* effect, and report any disagreement as a warning, not a failure |

Why 4 standard errors: with 2 models × 5 configs × many checks, a 2-standard-error band would fail by chance. The stubs are seeded, so results are the same on every run; if a check fails, it fails every time and points to a bug.

### 1.6 Report format

`results/acceptance_report.md`: a header with date, tool versions and Python version; one table row per check with ID, status and detail; below it, for each FAIL, the measured value, the truth and the tolerance. Print the same table to the terminal.

### 1.7 Known risks to look for first

- `report.py` and `metrics.py` have never run. Likely trouble spots: models with zero passing samples (empty frames in `gate_frame` and `tool_induced`), σ = 0 (division in T2 and T7), and `pandas` boolean columns read back from CSV (`synth.csv` `ok` is converted in `_load`).
- `evaluate` assumes all configs of a model exist. If a run is cut short, `pass_matrix` raises `incomplete grid`; that is intended.
- The `all` command does not run `acceptance`; run it separately.

---

## 2. Tests (`pytest`)

### 2.1 Setup

`pyproject.toml` (so `pip install -e .` works and pytest finds `src`):

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "rtlsens"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["numpy", "pandas", "scipy", "matplotlib", "pyyaml", "requests"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
markers = ["slow: needs the dataset and several seconds"]
```

`tests/conftest.py` provides three fixtures: `root` (project root), `dataset_dir` (skip the test if `third_party/verilog-eval/dataset_spec-to-rtl` is missing and `VERILOG_EVAL_DIR` is unset), and `tool_check` (skip tests that need `iverilog` or `yosys` when they are not on PATH).

### 2.2 Test files and cases

**`test_extract.py`** (no tools needed)

- One fenced block: X0, X1 and X2 return the same module.
- Two blocks (A then B): X0 returns A, X1 returns B.
- No fence: X0 and X1 return `None`; X2 returns the module when `module` starts a line.
- Prose sentence "This module implements …" is not mistaken for a module start by X2.
- Fence tagged `systemverilog` works.
- Unclosed fence (truncated output): X0 returns `None`.
- Empty fence: returns `None`.
- N1 renames a single `module top_module(...)` and an `endmodule : top_module` label; for `module top_module(input a); endmodule : top_module` the result is `module TopModule(input a); endmodule : TopModule`.
- N1 leaves code with two modules unchanged; N0 never changes anything.

**`test_prompts.py`**

- P0 equals the stripped prompt file.
- P1 matches the rewrite pattern exactly once for all 60 subset problems and changes nothing else (compare after replacing the new sentence back).
- A problem outside the standard opening raises `ValueError`.
- An unknown variant raises.

**`test_simulate_classify.py`** (`classify_log` with synthetic logs, plus two real runs)

- `["Mismatches: 0 in 20 samples"]` is PASS.
- `["Mismatches: 3 in 20 samples"]` is MISMATCH with `n_mismatch = 3`; with code containing `posedge reset` the harness code is `r`.
- `["x.sv:3: syntax error"]` is COMPILE_ERROR (`S`).
- `["... Unknown module type: TopModule"]` is COMPILE_ERROR (`m`).
- `["TIMEOUT", "Mismatches: 0 in 5 samples"]` is TIMEOUT, and so is the reverse order.
- `[]` with `compile_failed=True` is COMPILE_ERROR (`C`); `[]` otherwise is OTHER.
- Real run: Prob001 reference renamed to TopModule is PASS; `assign zero = 1'b1` is MISMATCH with 20 mismatches.

**`test_metrics.py`** (hand-computed values)

- `f_seed` for one problem with 5 passes in 10 samples: `2*5*5/(10*9) = 0.5556`.
- `sigma_pred` for two problems with `p̂ = [0.5, 0.0]` and K = 10: `sqrt(0.25*10/9)/2 = 0.2635`.
- `flips`: `Mf = [[1,0],[0,0]]`, `M0 = [[0,0],[1,0]]` gives gains 0.25, losses 0.25, flip 0.5.
- `reversal_prob`: A with 6 passes in each of 2 runs; B with 4 and 7 passes; gives 0.5 (two of the four run pairs are reversed).
- `pass_at_1`, `run_pass`, `sigma_seed` on a 2×2 matrix.
- `boot_indices` is reproducible for a fixed seed and `pct_ci` returns lo ≤ hi.
- `determinism` on a small fake record list.
- `gate_frame`, `tool_induced`, `seed_cv` on a tiny hand-built frame, including an empty frame (must return empty arrays, not raise).

**`test_backends.py`**

- Start `http.server` in a thread as a mock `/v1/chat/completions`; assert the request JSON has `model`, `messages` (system then user), `temperature`, `top_p`, `max_tokens`, `seed`; return a canned response and check the parsed dict.
- `PlantedStub`: same seed gives the same text; different seeds give different text for at least one problem; at temperature 0 with `t0_nondeterminism = 0` two calls are identical.
- `expected_pass` is between 0 and 1 and `fmt_prob_ok("B0")` equals `1 - tb_first - nofence - renamed`.

**`test_generate_resume.py`**

- Run generation on 2 problems; run again; second run writes 0 records.
- Truncate the last line of `generations.jsonl` (simulate a kill); the next run tolerates it and regenerates only the missing sample.
- Job count equals models × problems × (variants × K + 2).

**`test_selftest_oracle.py`** (marked `slow`)

- Oracle on the first 5 subset problems: PASS under all 7 configs.
- `empty_header`: no PASS.

**`test_subset.py`** (marked `slow`, about 20 seconds)

- `eligible_problems` returns 128 problems with exclusions `{selftest: 4, synth: 7, cells0: 13, prompt: 4}`; `draw_subset` equals `configs/problem_subset.txt`.

**`test_manifest.py`**

- A manifest with one required field set to `""` is reported by `validate_manifest`; a complete one returns an empty list.

### 2.3 Running

```bash
pytest -q                 # all
pytest -q -m "not slow"   # quick loop
```

### 2.4 Expectation

All tests pass. Without the slow tests the run takes a few seconds; with them, roughly half a minute (estimate). If the test run takes minutes, a test is simulating more than it needs to.

---

## 3. Install Ollama and run the real experiment

Do this on the machine with the GPU. Windows users should run the harness inside WSL2 (Ubuntu); Ollama itself can run on Windows or inside WSL.

### 3.1 Prepare the machine

```bash
sudo apt update && sudo apt install -y iverilog yosys python3-venv git
iverilog -V | head -1      # must say 12.x
yosys -V
```

VerilogEval needs Icarus Verilog 12. Ubuntu 24.04 ships 12.0. Ubuntu 22.04 ships an older version, and Homebrew may give a newer one; both can change results. If your version is not 12.x, install 12 from source or via conda before continuing, and record the version in the manifest.

```bash
cd llm-rtl-sensitivity
python3 -m venv .venv && source .venv/bin/activate
pip install -e . pytest
git clone https://github.com/NVlabs/verilog-eval third_party/verilog-eval
git -C third_party/verilog-eval checkout c498220d0a52248f8e3fdffe279075215bde2da6
```

The last line pins the same VerilogEval commit used for the design (it was `HEAD` when the design was prepared). Run the tests and the acceptance checks now:

```bash
pytest -q
python -m rtlsens.cli acceptance --config configs/experiment_planted.yaml
```

Do not continue until every check is PASS or SKIP (A9-live is expected to SKIP until Ollama is running).

### 3.2 Install Ollama

- Linux: `curl -fsSL https://ollama.com/install.sh | sh`
- macOS and Windows: download the installer from `ollama.com/download`.

Check it:

```bash
ollama --version
curl http://localhost:11434/api/version      # prints {"version":"..."}
```

If the curl fails, start the server in a terminal with `ollama serve`.

GPU check: with an NVIDIA driver installed, Ollama uses the GPU automatically. Run a model, then `ollama ps`; the PROCESSOR column should say `100% GPU`. If it says CPU, stop and fix the driver first: the full run is not feasible on CPU (see 3.8).

### 3.3 Pull two models

Pick two 7–8B instruct or coder models from different families. Examples that were used in the design:

```bash
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
ollama list          # note exact names; each is roughly 4-5 GB
```

Avoid reasoning models that print their thinking: they make extraction results harder to interpret. If a tag above no longer exists, `ollama list` and the Ollama model library show current names; any two suitable models work as long as you record them.

### 3.4 Check the endpoint by hand

```bash
curl http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "qwen2.5-coder:7b",
  "messages": [{"role": "user", "content": "Write a Verilog AND gate module."}],
  "temperature": 0.85, "top_p": 0.95, "max_tokens": 200, "seed": 1000
}'
```

Run it twice. With the same seed the two answers should be identical; change `"seed"` to 1001 and the answer should change. If not, stop: the seed study cannot work (see the troubleshooting table in 4.5).

### 3.5 Edit `configs/experiment.yaml`

Only the `models` block normally needs changes:

```yaml
models:
  - {name: model_a, backend: openai_compat, base_url: "http://localhost:11434/v1", model: "qwen2.5-coder:7b"}
  - {name: model_b, backend: openai_compat, base_url: "http://localhost:11434/v1", model: "llama3.1:8b"}
```

- `name`: label used in all tables; keep it short.
- `model`: exact tag from `ollama list`.
- `base_url`: ends with `/v1`.
- `workers`: how many requests run at once. Keep 1 for the first runs.

Do not change `sampling`, `seed_base`, `prompt_variants` or `samples_per_problem` unless you are using a fallback lever (3.8) and will state it in the write-up.

### 3.6 Smoke test on the real server

Create `configs/experiment_smoke.yaml` as a copy of `experiment.yaml` with these changes: `results_dir: results/smoke`, `samples_per_problem: 2`, and `subset_file: configs/problem_subset_smoke.txt` (a file holding the first 3 names from `problem_subset.txt`). Then:

```bash
python -m rtlsens.cli preflight --config configs/experiment_smoke.yaml
python -m rtlsens.cli all       --config configs/experiment_smoke.yaml
wc -l results/smoke/raw/generations.jsonl     # expect 36
```

`36 = 2 models × 3 problems × (2 prompts × 2 samples + 2 determinism runs)`. Open `results/smoke/raw/generations.jsonl` and read three `raw_response` values by eye. With 3 problems the confidence intervals mean nothing; the goal is only to see that every stage runs on real model output.

### 3.7 Go/no-go checklist before the full run

1. `preflight` prints no problems, and the manifest shows your Ollama version, both model digests and your GPU.
2. A9-live is PASS in `acceptance` (rerun it with `experiment.yaml` so it finds your Ollama models).
3. Smoke run finished; no `NO_CODE` rate above about 20% (if so, read the raw responses first).
4. Time per generation known: `latency_s` in the JSONL. Multiply by 2,640 and divide by `workers` to estimate total time.
5. Determinism runs: in the smoke `T6.csv`, raw identity near 1.0. If it is not, see 4.5.

### 3.8 Full run

```bash
nohup python -m rtlsens.cli generate --config configs/experiment.yaml --workers 2 > gen.log 2>&1 &
tail -f gen.log                                   # progress every 100 samples
wc -l results/main/raw/generations.jsonl          # target: 2640
```

Safe to interrupt: rerun the same command and it skips finished samples. When it reaches 2,640:

```bash
python -m rtlsens.cli evaluate --config configs/experiment.yaml --jobs 4
python -m rtlsens.cli synth    --config configs/experiment.yaml --jobs 4
python -m rtlsens.cli analyze  --config configs/experiment.yaml
```

For parallel requests, start Ollama with `OLLAMA_NUM_PARALLEL=2` (or the value you want) set in its environment, and set `workers` to match.

**Fallback levers**, in this order, if generation is too slow: set `samples_per_problem` to 5; cut the subset file to the first 40 names; drop `P1` for model B; replace one model with an API model (same code path, different `base_url`). On a CPU-only machine a 7B model produces only a few tokens per second, which makes 2,640 generations take days; use the levers or an API model. Write down every lever you used.

---

## 4. What to expect

### 4.1 Step by step

| Step | Expected output |
|---|---|
| `pytest -q` | all pass, seconds to about half a minute |
| `acceptance` (planted config) | A1–A8 and A10 PASS; A9-live SKIP before Ollama; P1–P7 PASS |
| smoke generation | 36 records, no `FAILED after` lines |
| full generation | 2,640 records; roughly 5–10 hours on one 8 GB GPU for a 7–8B model at 30–40 tokens per second (estimate); fewer if requests run in parallel |
| `evaluate` | `eval.csv` with 2 × 60 × (4K + K + 2) = 2 × 60 × 52 = 6,240 rows at K = 10; a few minutes (156 reference simulations took 11 s in pre-flight) |
| `synth` | `synth.csv`; minutes |
| `analyze` | `results/main/tables/T1–T7.csv` and `figures/F1–F4.pdf`; about a minute |

### 4.2 Expected values for the real models (priors, not promises)

- **pass@1** (T1): in the tens of percent for 7–8B models on this benchmark. The VerilogEval v2 revision paper reports about 34% for one 6.7B domain-specific model; check its exact setting before comparing.
- **σ_seed** (T2): a few percentage points. Observed should be within 0.5× to 2× of the predicted value; if not, investigate before reporting.
- **P1 prompt rewording** (T3): aggregate change probably inside the seed noise, with some per-problem flips.
- **X and N factors** (T3): depend on how often the model adds extra code blocks or renames the module. These are exact re-scores of the same text, so any difference is a pure harness effect. For a model that always returns one clean fenced block, expect zero.
- **Yosys scripts** (T5): large absolute differences for arithmetic-heavy designs, near zero for tiny ones. In pre-flight, the popcount reference gave 1351, 4263 and 3324 cells under Y0, Y1 and Y2.
- **Determinism at temperature 0** (T6): near 1.0 on a single machine with one request at a time.

### 4.3 How to read the results

Start with T7 (factor ranking), then T2 (is the noise sensible), T6 (are seeds trustworthy), T3 and T4.

| Pattern | Meaning |
|---|---|
| Every generation-side effect inside 2σ_seed | These factors do not move pass@1 at this size; say so, it is a valid result |
| X or N marked material | Post-processing rules must go into the manifest; headline numbers changed with no model change |
| Reversal probability well above 0 | A single-run model comparison at this size is unreliable |
| Excess flip above 0 while the average is unchanged | Wording changes which problems pass, not how many |
| Yosys scripts differ a lot but ordering is stable | Compare models only under one stated script |

### 4.4 Red flags

- A model with pass@1 of 0 or near 0: wrong tag, wrong prompt, or all answers lack a fenced block. Read 5 raw responses.
- `NO_CODE` above 20% under X0: the model ignores "put the code in a fenced code block". That is a finding for the X factors, but check that responses are not empty because of an error.
- Many `finish_reason: length`: answers are cut at 1,024 tokens. Count them (`grep -c '"finish_reason": "length"'`) and report the number.
- The 10 seeds give identical text at temperature 0.85: the server ignores the seed.

### 4.5 Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `connection refused` on port 11434 | server not running | `ollama serve`, or start the service |
| `model not found` | tag in config differs from `ollama list` | copy the exact tag |
| Same seed gives different text | parallel requests, GPU nondeterminism, or a changed model between runs | set `OLLAMA_NUM_PARALLEL=1` and retest; keep one machine and one Ollama version; report the identity rate |
| Different seeds give identical text | seed ignored or temperature effectively 0 | check the payload (`temperature` 0.85); update Ollama; if it persists the seed study is invalid on this setup |
| `incomplete grid` in analyze | generation or evaluate stopped early | rerun `generate` (resumes), then `evaluate` |
| All `COMPILE_ERROR` for a model | module not named `TopModule`, or prose inside the code | read a raw response; N1 and X2 exist to measure exactly this |
| iverilog warnings about SystemVerilog constructs | iverilog is not 12.x | install 12.x |
| `analyze` crashes on a column or an empty frame | untested code path in `report.py` or `metrics.py` | fix and add a test (see 1.7) |

---

## 5. Order of operations (checklist)

- [ ] Write `acceptance.py`; write the pytest files and `pyproject.toml`.
- [ ] `pytest -q` passes.
- [ ] `acceptance` with the planted config: all PASS or SKIP; fix harness bugs until it is.
- [ ] Package the project (zip) with a short test report.
- [ ] Install iverilog 12, Yosys, Python venv, clone VerilogEval at the pinned commit.
- [ ] Install Ollama; pull two models; hand-test the endpoint with the same seed twice.
- [ ] Edit `models` in `configs/experiment.yaml`.
- [ ] Smoke run (3 problems, K = 2); read raw responses.
- [ ] Go/no-go checklist (3.7).
- [ ] Full generation; evaluate; synth; analyze.
- [ ] Read T7, T2, T6, T3, T4; write up with the limitations from DESIGN.md Section 14 and any fallback levers used.
