"""Compile and simulate a DUT against a VerilogEval testbench; classify like scripts/sv-iv-analyze."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

IVERILOG_FLAGS = ["-Wall", "-Winfloop", "-Wno-timescale", "-g2012", "-s", "tb"]
MISMATCH_RE = re.compile(r"^Mismatches: (\d+) in (\d+) samples$")
COMPILE_CODES = set("Se0nwmpcC")


@dataclass
class SimResult:
    cls: str            # PASS, MISMATCH, COMPILE_ERROR, TIMEOUT, OTHER (NO_CODE is set by the caller)
    harness_code: str   # code as sv-iv-analyze would assign it
    n_mismatch: int     # -1 when no mismatch line was seen
    n_samples_tb: int   # -1 when no mismatch line was seen

    def asdict(self) -> dict:
        return asdict(self)


def classify_log(lines, code_text: str, compile_failed: bool = False) -> SimResult:
    """Mirror of the pass/fail logic in VerilogEval's scripts/sv-iv-analyze.

    Lines are processed in order (compile log first, then simulation output); the first
    decisive line wins. One deliberate deviation: a non-zero iverilog exit status counts as a
    compile error even if no line contains the word 'error'.
    """
    code = "?"
    error_c = compile_failed
    error_p = False
    no_mismatch = False
    n_mis, n_tb = -1, -1
    for line in lines:
        line = line.rstrip("\n")
        if "syntax error" in line:
            code = "S"; break
        if "error" in line:
            error_c = True
        if "error: This assignment requires an explicit cast" in line:
            code = "e"; break
        if "error: Sized numeric constant must have a size greater than zero" in line:
            code = "0"; break
        if "warning: always_comb process has no sensitivities" in line:
            code = "n"; break
        if "found no sensitivities so it will never trigger" in line:
            code = "n"; break
        if "is declared here as wire" in line:
            code = "w"; break
        if "Unknown module type" in line:
            code = "m"; break
        if "Unable to bind wire/reg" in line:
            error_p = True
        if "Unable to bind wire/reg/memory `clk'" in line:
            code = "c"; break
        if "TIMEOUT" in line:
            code = "T"; break
        m = MISMATCH_RE.match(line)
        if m:
            n = int(m.group(1))
            n_tb = int(m.group(2))
            if n == 0:
                no_mismatch = True
            else:
                n_mis = n
    if code == "?" and error_p:
        code = "p"
    if code == "?" and error_c:
        code = "C"
    if code == "?" and no_mismatch:
        code = "."
    if code == "?":
        code = "R"
        for line in code_text.splitlines():
            if "posedge reset" in line or "negedge reset" in line or "posedge r)" in line:
                code = "r"; break
    if code == ".":
        cls = "PASS"
    elif code == "T":
        cls = "TIMEOUT"
    elif code in COMPILE_CODES:
        cls = "COMPILE_ERROR"
    else:  # R or r
        cls = "MISMATCH" if n_mis > 0 else "OTHER"
    return SimResult(cls, code, n_mis, n_tb)


def run_one(problem: str, code: str, dataset_dir: str, timeout_s: int = 30) -> SimResult:
    d = Path(dataset_dir)
    with tempfile.TemporaryDirectory(prefix="rtlsens_") as td:
        dut = Path(td) / "dut.sv"
        dut.write_text(code)
        binp = Path(td) / "sim.out"
        comp = subprocess.run(
            ["iverilog", *IVERILOG_FLAGS, "-o", str(binp), str(dut),
             str(d / f"{problem}_test.sv"), str(d / f"{problem}_ref.sv")],
            capture_output=True, text=True,
        )
        log = (comp.stdout + comp.stderr).splitlines()
        failed = comp.returncode != 0
        if not failed:
            try:
                r = subprocess.run(["vvp", str(binp)], capture_output=True, text=True,
                                   timeout=timeout_s, cwd=td)
                log += (r.stdout + r.stderr).splitlines()
            except subprocess.TimeoutExpired:
                log.append("TIMEOUT")
        return classify_log(log, code, compile_failed=failed)


def _worker(args) -> tuple:
    key, problem, code, dataset_dir, timeout_s = args
    return key, run_one(problem, code, dataset_dir, timeout_s).asdict()


def run_many(jobs: list[tuple], dataset_dir: str, timeout_s: int = 30, n_jobs: int | None = None) -> dict:
    """jobs: list of (key, problem, code). Returns {key: SimResult-dict}."""
    n_jobs = n_jobs or os.cpu_count() or 1
    args = [(k, p, c, dataset_dir, timeout_s) for k, p, c in jobs]
    if n_jobs <= 1 or len(args) < 4:
        return dict(_worker(a) for a in args)
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        return dict(ex.map(_worker, args, chunksize=8))


def reference_as_dut(dataset_dir: str, problem: str) -> str:
    return (Path(dataset_dir) / f"{problem}_ref.sv").read_text().replace("RefModule", "TopModule")
