"""Eligibility filter and seeded subset (DESIGN.md Section 6.1)."""
from __future__ import annotations

import json
import random
import re
import tempfile
from pathlib import Path

from . import simulate, synth
from .config import rpath
from .prompts import P1_PATTERN
from .util import read_names


def reference_selftest(dataset_dir: str, problems: list[str] | None = None, timeout_s: int = 30) -> dict[str, str]:
    """Run each reference solution (renamed TopModule) through the harness; return {problem: class}."""
    problems = problems or read_names(Path(dataset_dir) / "problems.txt")
    jobs = [(p, p, simulate.reference_as_dut(dataset_dir, p)) for p in problems]
    res = simulate.run_many(jobs, dataset_dir, timeout_s, n_jobs=1)
    return {p: res[p]["cls"] for p in problems}


def eligible_problems(dataset_dir: str) -> tuple[list[str], dict[str, int]]:
    scripts = synth.load_scripts(str(Path(__file__).resolve().parents[2] / "configs" / "yosys"))
    body = scripts["Y0"]
    d = Path(dataset_dir)
    problems = read_names(d / "problems.txt")
    st = reference_selftest(dataset_dir, problems)
    excl = {"selftest": 0, "synth": 0, "cells0": 0, "prompt": 0}
    elig = []
    for p in problems:
        if st[p] != "PASS":
            excl["selftest"] += 1; continue
        ok, n = synth.run_yosys(simulate.reference_as_dut(dataset_dir, p), body)
        if not ok:
            excl["synth"] += 1; continue
        if n == 0:
            excl["cells0"] += 1; continue
        if not P1_PATTERN.search((d / f"{p}_prompt.txt").read_text()):
            excl["prompt"] += 1; continue
        elig.append(p)
    return elig, excl


def draw_subset(eligible: list[str], n: int = 60, seed: int = 42) -> list[str]:
    return sorted(random.Random(seed).sample(sorted(eligible), n))


def check_subset(cfg: dict) -> bool:
    elig, excl = eligible_problems(cfg["dataset_dir"])
    sub = draw_subset(elig)
    frozen = read_names(cfg["subset_file"])
    rpath(cfg, "subset_recomputed.json").write_text(json.dumps({"eligible": elig, "excluded": excl, "subset": sub}, indent=1))
    print(f"eligible={len(elig)} excluded={excl} recomputed_subset={len(sub)}")
    match = sub == frozen
    print("subset MATCHES frozen list" if match else "subset DOES NOT MATCH frozen list")
    return match
