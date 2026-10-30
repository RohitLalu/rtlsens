#!/usr/bin/env python3
"""Bug-injection (mutation) test for rtlsens.

Put this file in the project root (next to pyproject.toml), activate the venv, then run:

    python mutation_test.py                      # pytest only, about 3-5 minutes
    python mutation_test.py --accept-survivors   # then also run acceptance on each survivor (about 6 min each)

For each mutation the script copies the project to a temporary directory, injects ONE bug, and runs the
test command there. Your original files are never touched.

    KILLED    the tests went red (good: the bug is detected)
    SURVIVED  the tests stayed green (a gap: nothing noticed the bug)
    NO-MATCH  the source text to change was not found exactly once (the code has changed; fix the entry)

A baseline run on the unmodified copy comes first. If the baseline is not green the script stops,
because "everything is KILLED" would be meaningless.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (file under src/rtlsens, text to find (must occur exactly once), replacement, description)
MUTATIONS = [
    ("metrics.py", "v = ph * (1 - ph) * k / (k - 1)", "v = ph * (1 - ph)",
     "sigma_pred: drop the k/(k-1) correction"),
    ("metrics.py", "return float(run_pass(M).std(ddof=1))", "return float(run_pass(M).std(ddof=0))",
     "sigma_seed: ddof 1 -> 0"),
    ("metrics.py", "abs(delta) >= 2 * sig", "abs(delta) >= sig",
     "is_material: 2 sigma -> 1 sigma"),
    ("metrics.py", "and (lo > 0 or hi < 0)", "and True",
     "is_material: ignore the CI"),
    ("metrics.py", "return float((2.0 * c * (k - c) / (k * (k - 1))).mean())",
     "return float((c * (k - c) / (k * (k - 1))).mean())",
     "f_seed: factor 2 dropped"),
    ("metrics.py", "- 2.0 * c * (k - c) / (k * (k - 1))\n    return float(per_problem.mean())",
     "+ 2.0 * c * (k - c) / (k * (k - 1))\n    return float(per_problem.mean())",
     "excess_flip_ci: add the baseline instead of subtracting it"),
    ("metrics.py", "M0[idx].mean(axis=(1, 2))\n    return d, *pct_ci(boot)",
     "M0[idx[::-1]].mean(axis=(1, 2))\n    return d, *pct_ci(boot)",
     "delta_ci: unpaired bootstrap"),
    ("metrics.py", "[100 * a, 100 * (1 - a)]", "[100 * a, 100 * (1 - a) - 1]",
     "pct_ci: upper percentile shifted"),
    ("metrics.py", "(wrong.sum() + 0.5 * ties.sum())", "(wrong.sum() + 1.0 * ties.sum())",
     "reversal_prob: ties count in full"),
    ("metrics.py",
     "gains = float(((Mf == 1) & (M0 == 0)).mean())\n    losses = float(((Mf == 0) & (M0 == 1)).mean())",
     "gains = float(((Mf == 0) & (M0 == 1)).mean())\n    losses = float(((Mf == 1) & (M0 == 0)).mean())",
     "flips: gains and losses swapped"),
    ("metrics.py", "return float((M0 != M1).mean())", "return float((M0 > M1).mean())",
     "f_prompt: one-sided comparison"),
    ("metrics.py", "cvs.append(s.std(ddof=0) / s.mean())", "cvs.append(s.std(ddof=1) / s.mean())",
     "seed_cv: ddof 0 -> 1"),
    ("metrics.py", 'return (j["b"] / j["a"] - 1.0).to_numpy()', 'return (j["a"] / j["b"] - 1.0).to_numpy()',
     "tool_induced: ratio inverted"),
    ("metrics.py", "int(s0 != s2)", "int(s0 == s2)",
     "ordering_flip_fraction: condition inverted"),
    ("metrics.py", 'out["ratio"] = out["num_cells"] / out["ref_cells"]',
     'out["ratio"] = out["ref_cells"] / out["num_cells"]',
     "gate_frame: ratio inverted"),
    ("extract.py", "code = blocks[-1] if blocks else None", "code = blocks[0] if blocks else None",
     "X1: last fenced block -> first"),
    ("extract.py", '(.*?)```", re.S)', '(.*)```", re.S)',
     "FENCE: lazy -> greedy match"),
    ("extract.py", "[(;#]", "[(;#\\s]",
     "MODULE_SPAN: accept prose lines that start with 'module'"),
    ("extract.py", "if len(names) != 1 or", "if len(names) < 1 or",
     "N1: rename even when several modules exist"),
    ("prompts.py", "Please write a SystemVerilog module named TopModule that has the following interface.",
     "Please write a Verilog module named TopModule that has the following interface.",
     "P1: replacement wording changed"),
    ("generate.py", 'k=k, seed=int(cfg["seed_base"]) + k, params=cfg["sampling"]',
     'k=k, seed=int(cfg["seed_base"]), params=cfg["sampling"]',
     "generate: every sample gets the same seed"),
    ("backends.py", '"seed": seed, "stream": False,', '"stream": False,',
     "OpenAI backend: seed not sent"),
    ("simulate.py", "if n == 0:\n                no_mismatch = True",
     "if n >= 0:\n                no_mismatch = True",
     "classify_log: any mismatch count counts as PASS"),
]


def make_copy(dst: Path) -> None:
    """Copy the small parts of the project; link the big dataset instead of copying it."""
    for name in ("src", "tests", "configs", "environment"):
        if (ROOT / name).exists():
            shutil.copytree(ROOT / name, dst / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / "pyproject.toml", dst / "pyproject.toml")
    (dst / "results").mkdir()
    tp = ROOT / "third_party"
    if tp.exists():
        os.symlink(tp.resolve(), dst / "third_party")


def env_for(dst: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(dst / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["MPLBACKEND"] = "Agg"
    return env


def check_import(dst: Path) -> None:
    out = subprocess.run([sys.executable, "-c", "import rtlsens; print(rtlsens.__file__)"],
                         capture_output=True, text=True, env=env_for(dst), cwd=dst)
    path = out.stdout.strip()
    if not path.startswith(str(dst)):
        sys.exit(f"ERROR: the copy imports rtlsens from {path!r}, not from the temporary copy; "
                 "the mutation would not be tested. Check how rtlsens is installed.")


def run(cmd: list[str], dst: Path, timeout: int) -> tuple[bool, str]:
    """Return (green, note)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env_for(dst), cwd=dst, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
    return r.returncode == 0, tail[0][:90]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", default=f"{sys.executable} -m pytest -q -x -p no:cacheprovider",
                    help="test command to run in each copy (default: pytest -q -x)")
    ap.add_argument("--timeout", type=int, default=300, help="seconds per mutation for the test command")
    ap.add_argument("--accept-survivors", action="store_true",
                    help="run the full acceptance run (about 6 min on 1 CPU) on every survivor")
    ap.add_argument("--only", default="", help="substring: run only mutations whose description contains it")
    a = ap.parse_args()
    cmd = shlex.split(a.cmd)

    with tempfile.TemporaryDirectory(prefix="mut_base_") as td:
        base = Path(td)
        make_copy(base)
        check_import(base)
        print("baseline (unmodified copy) ...", flush=True)
        green, note = run(cmd, base, a.timeout)
        print(f"  baseline {'green' if green else 'RED'}: {note}")
        if not green:
            print("The baseline is not green, so mutation results would mean nothing. Fix that first.")
            return 2

    rows = []
    for fname, old, new, desc in MUTATIONS:
        if a.only and a.only not in desc:
            continue
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix="mut_") as td:
            dst = Path(td)
            make_copy(dst)
            p = dst / "src" / "rtlsens" / fname
            src = p.read_text()
            if src.count(old) != 1:
                rows.append((desc, "NO-MATCH", f"{src.count(old)} occurrences in {fname}", ""))
                print(f"NO-MATCH  {desc}", flush=True)
                continue
            p.write_text(src.replace(old, new))
            green, note = run(cmd, dst, a.timeout)
            status = "SURVIVED" if green else "KILLED"
            acc = ""
            if green and a.accept_survivors:
                print(f"SURVIVED pytest, running acceptance: {desc} ...", flush=True)
                acc_green, acc_note = run([sys.executable, "-m", "rtlsens.cli", "acceptance",
                                           "--config", "configs/experiment_planted.yaml"], dst, 3600)
                acc = "acceptance KILLED it" if not acc_green else "acceptance did NOT notice"
                status = "KILLED(acc)" if not acc_green else "SURVIVED"
            rows.append((desc, status, note if status == "KILLED" else "", acc))
            print(f"{status:<11s} {desc}  ({time.time() - t0:.0f}s)", flush=True)

    killed = sum(1 for r in rows if r[1].startswith("KILLED"))
    tested = sum(1 for r in rows if r[1] != "NO-MATCH")
    lines = ["# Mutation test report", "", f"Test command: `{a.cmd}`", f"Killed {killed} of {tested} mutations.", "",
             "| Status | Injected bug | Note |", "|---|---|---|"]
    for desc, st, note, acc in rows:
        lines.append(f"| {st} | {desc} | {(note or acc).replace('|', '/')} |")
    out = ROOT / "results" / "mutation_report.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"\nKilled {killed} of {tested}. Report: {out}")
    survivors = [r[0] for r in rows if r[1] == "SURVIVED"]
    if survivors:
        print("Survivors (nothing noticed these bugs):")
        for s in survivors:
            print("  -", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
