"""Yosys synthesis and gate-count proxy (num_cells). Scripts Y0/Y1/Y2 live in configs/yosys/."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

Y_NAMES = ["Y0", "Y1", "Y2"]


def load_scripts(yosys_dir: str) -> dict[str, str]:
    out = {}
    for i, name in enumerate(Y_NAMES):
        text = (Path(yosys_dir) / f"y{i}.ys").read_text()
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
        out[name] = "; ".join(lines)
    return out


def run_yosys(code: str, body: str, timeout_s: int = 120) -> tuple[bool, int]:
    with tempfile.TemporaryDirectory(prefix="rtlsens_y_") as td:
        dut = Path(td) / "dut.sv"
        out = Path(td) / "stat.json"
        dut.write_text(code)
        cmd = f"read_verilog -sv {dut}; {body}; tee -q -o {out} stat -json"
        try:
            r = subprocess.run(["yosys", "-q", "-p", cmd], capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return False, -1
        if r.returncode != 0 or not out.exists():
            return False, -1
        try:
            mods = json.loads(out.read_text())["modules"]
            return True, int(next(iter(mods.values()))["num_cells"])
        except (KeyError, StopIteration, ValueError):
            return False, -1


def _worker(args):
    key, code, body, timeout_s = args
    ok, n = run_yosys(code, body, timeout_s)
    return key, (ok, n)


def run_many(jobs: list[tuple], timeout_s: int = 120, n_jobs: int | None = None) -> dict:
    """jobs: list of (key, code, body). Returns {key: (ok, num_cells)}."""
    n_jobs = n_jobs or os.cpu_count() or 1
    args = [(k, c, b, timeout_s) for k, c, b in jobs]
    if n_jobs <= 1 or len(args) < 4:
        return dict(_worker(a) for a in args)
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        return dict(ex.map(_worker, args, chunksize=8))
