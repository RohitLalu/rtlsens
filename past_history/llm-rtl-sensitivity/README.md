# llm-rtl-sensitivity

One-factor-at-a-time sensitivity study of LLM-generated RTL evaluation (see `DESIGN.md`).
Measures how much pass@1 and a Yosys gate-count proxy move when one evaluation variable changes:
sampling seed, prompt wording, code-extraction rule, module-name handling, synthesis script.

## Quick start

```bash
bash environment/setup.sh                       # tools, package, pinned VerilogEval
python -m rtlsens.cli acceptance                # harness checks (no LLM needed), writes results/acceptance_report.md
python -m rtlsens.cli subset --config configs/experiment.yaml     # must print: subset MATCHES frozen list
```

## Real experiment

1. Start Ollama and pull two models; put their tags in `configs/experiment.yaml`.
2. `python -m rtlsens.cli preflight` (manifest must be valid, i.e. digests found).
3. **Before the full run**, repeat acceptance check A9 against the live server (seed passthrough, T=0 repeat).
4. `python -m rtlsens.cli all` (preflight, generate, evaluate, synth, analyze). Generation is resumable.
5. Tables `results/main/tables/T1..T7.csv`, figures `results/main/figures/F1..F4.pdf`.

## Stages

| Command | Purpose |
|---|---|
| `preflight` | write and validate `manifest.json` |
| `subset` | recompute eligibility and the seeded 60-problem subset, compare with `configs/problem_subset.txt` |
| `generate [--workers N] [--limit-problems N]` | LLM calls, append-only `raw/generations.jsonl` |
| `evaluate [--jobs N]` | extraction + compile + simulate, `eval/eval.csv` |
| `synth [--jobs N]` | Yosys on passing samples and references, `eval/synth.csv` |
| `analyze` | tables and figures |
| `acceptance` | A1-A10 plus planted-truth checks P1-P7 |

## Stub models (no LLM)

`configs/experiment_selftest.yaml` (oracle and negative controls) and `configs/experiment_planted.yaml`
(models with known pass probabilities and format quirks) exercise the whole chain. Results from these
configs validate the harness; they are not findings about any real model.

## Layout

See `DESIGN.md` Section 5. Additions beyond that tree: `backends.py` (OpenAI-compatible client and stubs),
`evaluate.py` (stages 3-4 orchestration), `acceptance.py`.
