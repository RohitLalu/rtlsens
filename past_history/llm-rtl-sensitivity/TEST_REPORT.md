# Base-case test report — `rtlsens` harness v0.1.0

Date: 2026-10-12. Environment: Ubuntu 24.04 sandbox, 1 CPU, Icarus Verilog 12.0, Yosys 0.33, Python 3.12.3,
VerilogEval commit `c498220d0a52`. Full check log: `results/acceptance_report.md`.

**Scope.** No LLM was run: the sandbox has no GPU, Ollama or model access. "Base case" here means baseline
configuration B0 evaluated with (a) an oracle that returns the reference solution, (b) negative controls, and
(c) two stub models with *known* pass probabilities and *known* format quirks, so every measured quantity can be
compared with an exact expected value. **The planted-run numbers describe stubs, not real models, and must not be quoted as findings.**

## 1. What was built

`src/rtlsens/` (prompts, extraction X0–X2/N0–N1, harness-compatible simulation, Yosys, resumable generation,
metrics of DESIGN.md §9, tables T1–T7, figures F1–F4, manifest, acceptance), `tests/` (38 pytest cases),
configs for the real run, the oracle/controls run and the planted run. About 2,000 lines.

## 2. Results

| ID | Check | Status | Evidence |
|---|---|---|---|
| A1 | preflight | PASS | Icarus 12.0, Yosys 0.33 |
| A2 | oracle | PASS | 720/720 PASS, 7 configs × 60 problems |
| A3 | negative controls | PASS | correct-ports/no-logic module 0/720 PASS (all MISMATCH); empty module 0/720; prose 720/720 NO_CODE |
| A4 | evaluate twice (jobs 1 vs 2) | PASS | `eval.csv` byte-identical |
| A5 | pytest | PASS | 38 passed |
| A6 | manifest | PASS | stub manifest valid; real-config manifest correctly flagged incomplete (no server) |
| A7 | count integrity | PASS | 2,640/2,640 generations; every (model, config) has N·K rows |
| A8 | cache on/off | PASS | identical outcomes on 20 random samples |
| A9 | seed passthrough | **PARTIAL** | verified against a mock OpenAI-compatible server and the stubs; **not** against a real Ollama endpoint |
| A10 | fresh copy, full chain | PASS | exit 0, 7/7 tables |
| P1 | pass@1 vs planted truth | PASS | max \|z\| = 2.23 over 10 cells |
| P2 | σ_seed formula (Monte Carlo) | PASS | mean(obs/pred) = 0.972, theory about 0.97; mean(pred/true) = 1.000 |
| P3 | gains/losses from format rules | PASS | max \|z\| = 2.05 over 12 quantities |
| P4 | excess prompt flips | PASS | truth 0.040 / 0.038 inside measured CIs |
| P5 | T=0 determinism | PASS | planted_a 1.00 (truth 1.00); planted_b 0.70 (truth 0.72) |
| P6 | gate-count chain | PASS | ratios exactly 1.0; Y0→Y2 distribution equals independent reconstruction |
| P7 | CI coverage | PASS | 1.000 (conservative: the bootstrap also resamples problems) |

Reference self-test and subset (from the harness, 156 problems): 152 PASS, 3 TIMEOUT, 1 COMPILE_ERROR; 128 eligible;
the seeded 60-problem subset is reproduced exactly (`subset` stage: "MATCHES frozen list").

Truth vs measured pass@1 on the planted run (percent):

| Model | B0 | P1 | X1 | X2 | N1 |
|---|---|---|---|---|---|
| planted_a truth / measured | 47.4 / 49.7 | 48.2 / 47.3 | 44.5 / 45.0 | 50.3 / 53.5 | 52.0 / 55.0 |
| planted_b truth / measured | 34.4 / 36.3 | 37.5 / 39.8 | 34.4 / 36.3 | 43.4 / 44.5 | 35.3 / 37.5 |

Measured values sit slightly above truth in most cells; B0, X1, X2 and N1 re-score the same 600 responses, so those cells are not independent, and all are within 2.3 standard errors.

Pipeline output on the planted run (T7, model planted_a): the three format rules shift pass@1 by 3.8–5.3 pp (CI excludes 0, below 2σ_seed = 6.2 pp), prompt rewording by −2.3 pp (CI includes 0). For planted_b, X2 is *material* (+8.2 pp). These reproduce the planted format-quirk rates, which is what the check is for.

## 3. Problems found and fixed during testing

1. **X2 captured prose.** A unit test with a line starting "module is a keyword" produced a wrong extraction; the pattern now requires `(`, `;` or `#` after the module name.
2. **Verdict wording.** The design's two-level verdict called a 5 pp, CI-excluding-zero shift "not distinguishable from noise". T3/T7 now have three levels; the "material" rule itself is unchanged.
3. **Cost estimate.** Yosys took about 0.75 s per run (252 s for 336 runs on 1 CPU); DESIGN.md Appendix D records this.
4. **Dataset defects** (already in the design): 4 reference solutions fail the harness's own classification and are excluded.

## 4. Not tested, and limits

- No real model, so none of the hypotheses in DESIGN.md §11 has been tested. Real-run behaviour that stubs cannot exercise: truncated outputs (`finish_reason = length`), reasoning text, Yosys rejecting model code, server errors and retries beyond the mock.
- In the planted run, every passing sample is the reference code, so gate-count results (T5) only check the mechanics.
- Stage timings here (stub generation 0.9 s, evaluation 18 s for 6,240 rows, Yosys 252 s, analysis 3 s) say nothing about real generation time, which dominates (design estimate: 5–10 h on one GPU).

## 5. To run the real experiment

```bash
bash environment/setup.sh
# edit configs/experiment.yaml: two Ollama model tags
python -m rtlsens.cli preflight          # manifest must show digests
# repeat A9 against the live server: two seeds differ at T=0.85; two T=0 runs match
python -m rtlsens.cli all                # resumable; use --workers 2-4 for generation
```
