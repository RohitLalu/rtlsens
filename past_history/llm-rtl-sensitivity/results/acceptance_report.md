# Acceptance report

Environment: Icarus Verilog version 12.0 (stable) (); Yosys 0.56 (git sha1 9c447ad9d4b1ea589369364eea38b4d70da2c599, clang++ 17.0.0 -fPIC -O3); Python 3.13.7; macOS-26.5.2-arm64-arm-64bit-Mach-O.

| ID | Check | Status | Detail |
|---|---|---|---|
| A1 | preflight | PASS | Icarus Verilog version 12.0 (stable) () / Yosys 0.56 (git sha1 9c447ad9d4b1ea589369364eea38b4d70da2c599, clang++ 17.0.0 -fPIC -O3) |
| A2 | oracle (reference as model) | PASS | 720/720 PASS over 7 configs x 60 problems |
| A3 | negative controls | PASS | empty_header PASS=0/720 ({'MISMATCH': 720}); empty_module PASS=0/720; prose NO_CODE=720/720 |
| A4 | evaluate twice (jobs=1 then jobs=2) | PASS | sha256 9d411fa1c613 vs 9d411fa1c613 |
| A5 | pytest | PASS | 38 passed in 4.66s |
| A6 | manifest validation | PASS | planted manifest problems=0; real-config manifest flagged 3 (expected, no Ollama here): ['model model_a: digest unreachable (is the model server running?)', 'model model_b: digest unreachable (is the model server running?)'] |
| A7 | count integrity | PASS | generations 2640/2640; config row-count mismatches: [] |
| A8 | cache on/off on 20 random samples | PASS | 53 rows compared |
| A9 | seed passthrough | PARTIAL | mock server received seed 1001 and returned distinct text per seed: True; stub T=0.85 text differs across seeds on 50% of problems; T0 identity planted_a=1.00 (deterministic stub), planted_b=0.70 (nondeterministic stub by design). NOT TESTED: a real Ollama endpoint (unavailable here); repeat A9 against it before the full run. |
| A10 | fresh copy, full chain on 3 problems | PASS | exit 0, tables 7/7, 4s |
| P1 | pass@1 equals planted truth (z-scores) | PASS | max /z/ = 2.23 over 10 (model, config) cells; threshold 3.5 |
| P2 | sigma_seed formula calibration (Monte Carlo, 3000 replicates) | PASS | mean(obs/pred)=0.972 (theory ~0.97 for K=10), mean(pred/true)=1.000; pipeline run: 10/10 cells inside 0.5-2x band |
| P3 | format-rule gains/losses equal planted truth | PASS | max /z/ = 2.05 over 12 quantities |
| P4 | excess prompt-flip rate vs planted truth | PASS | planted_a: truth 0.040, measured 0.016 CI [-0.026, 0.057]; planted_b: truth 0.038, measured 0.026 CI [-0.014, 0.066] |
| P5 | determinism identity rates vs planted truth | PASS | planted_a raw 1.000 (truth 1.000); planted_b raw 0.700 (truth 0.722, 3SE=0.173); outcome identity 1.0 for both: True |
| P6 | gate-count chain (passing samples are reference code => ratio 1; Y0->Y2 matches reconstruction from REF rows) | PASS | all ratios exactly 1.0; distributions identical |
| P7 | bootstrap 95% CI coverage of planted pass@1 (300 replicates) | PASS | coverage 1.000 (>= 0.93 required; conservative coverage is expected because the bootstrap also resamples problems) |

## Stage timings (this machine, 1 CPU)

- selftest_evaluate_s: 11.1 s
- analyze_s: 3.2 s
