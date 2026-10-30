from rtlsens.simulate import classify_log, reference_as_dut, run_one
from rtlsens.subset import reference_selftest


def L(*xs):
    return list(xs)


def test_pass():
    r = classify_log(L("Hint: Total mismatched samples is 0 out of 20 samples", "Mismatches: 0 in 20 samples"), "")
    assert (r.cls, r.harness_code, r.n_samples_tb) == ("PASS", ".", 20)


def test_mismatch():
    r = classify_log(L("Mismatches: 5 in 20 samples"), "")
    assert (r.cls, r.harness_code, r.n_mismatch) == ("MISMATCH", "R", 5)


def test_mismatch_with_reset_heuristic_code_r():
    r = classify_log(L("Mismatches: 5 in 20 samples"), "always @(posedge reset) q<=0;")
    assert (r.cls, r.harness_code) == ("MISMATCH", "r")


def test_timeout_beats_zero_mismatch_line():
    r = classify_log(L("TIMEOUT", "Mismatches: 0 in 200000 samples"), "")
    assert r.cls == "TIMEOUT"


def test_syntax_and_other_compile_codes():
    assert classify_log(L("dut.sv:3: syntax error"), "").harness_code == "S"
    assert classify_log(L("x.sv:1: error: Unknown module type: foo"), "").harness_code == "m"
    assert classify_log(L("something error happened"), "").harness_code == "C"
    assert classify_log(L("warning: always_comb process has no sensitivities"), "").cls == "COMPILE_ERROR"


def test_compile_failure_without_error_word_is_compile_error():
    assert classify_log(L(), "", compile_failed=True).cls == "COMPILE_ERROR"


def test_no_result_line_is_other():
    r = classify_log(L("some output"), "")
    assert r.cls == "OTHER"


def test_real_runs(base_cfg):
    d = base_cfg["dataset_dir"]
    ok = reference_as_dut(d, "Prob001_zero")
    assert run_one("Prob001_zero", ok, d).cls == "PASS"
    wrong = "module TopModule(output zero);\n assign zero = 1'b1;\nendmodule\n"
    r = run_one("Prob001_zero", wrong, d)
    assert r.cls == "MISMATCH" and r.n_mismatch == 20
    assert run_one("Prob001_zero", "module TopModule(output zero) endmodule", d).cls == "COMPILE_ERROR"


def test_preflight_exclusions_reproduce(base_cfg):
    probs = ["Prob082_lfsr32", "Prob099_m2014_q6c", "Prob141_count_clock", "Prob156_review2015_fancytimer"]
    got = reference_selftest(base_cfg["dataset_dir"], probs)
    assert got == {"Prob082_lfsr32": "TIMEOUT", "Prob099_m2014_q6c": "COMPILE_ERROR",
                   "Prob141_count_clock": "TIMEOUT", "Prob156_review2015_fancytimer": "TIMEOUT"}
