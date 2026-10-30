"""Acceptance tests A1-A10 of DESIGN.md Section 12, plus planted-truth checks P1-P7.

The planted checks compare pipeline output against exact values known from the stub model
definitions. They validate the harness, not any real LLM.
"""
from __future__ import annotations

import json
import os
import platform
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
import pandas as pd

from . import metrics as M
from .backends import FMT_OK, PlantedStub
from .config import load_config, rpath
from .evaluate import evaluate, load_generations, run_synth
from .generate import run_generation
from .manifest import build_manifest, validate_manifest, write_manifest
from .report import CONFIGS, run_report
from .util import read_names, sha256_file

Z_MAX = 3.5


class Checks:
    def __init__(self):
        self.rows: list[tuple[str, str, str, str]] = []

    def add(self, cid, name, status, detail):
        self.rows.append((cid, name, status, detail))
        print(f"[{status:7s}] {cid} {name}: {detail}", flush=True)

    @property
    def ok(self):
        return all(r[2] in ("PASS", "PARTIAL") for r in self.rows)


def _timed(fn, *a, **k):
    t = time.time(); r = fn(*a, **k); return r, time.time() - t


def ensure_planted(cfg_p: dict, timings: dict, n_jobs=None):
    if not rpath(cfg_p, "raw", "generations.jsonl").exists():
        _, timings["generate_s"] = _timed(run_generation, cfg_p)
    if not rpath(cfg_p, "eval", "eval.csv").exists():
        _, timings["evaluate_s"] = _timed(evaluate, cfg_p, n_jobs)
    if not rpath(cfg_p, "eval", "synth.csv").exists():
        _, timings["synth_s"] = _timed(run_synth, cfg_p, None, n_jobs)
    _, timings["analyze_s"] = _timed(run_report, cfg_p)


# ---------------------------------------------------------------- mock OpenAI-compatible server
class _H(BaseHTTPRequestHandler):
    seen: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _H.seen.append(body)
        out = json.dumps({"choices": [{"message": {"content": f"seed={body['seed']}"}, "finish_reason": "stop"}],
                          "usage": {}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

    def log_message(self, *a):
        pass


def run_acceptance(cfg_any: dict) -> bool:
    root = Path(cfg_any["_root"])
    cfg_s = load_config(root / "configs" / "experiment_selftest.yaml")
    cfg_p = load_config(root / "configs" / "experiment_planted.yaml")
    cfg_r = load_config(root / "configs" / "experiment.yaml")
    probs = read_names(cfg_p["subset_file"]); N = len(probs); K = int(cfg_p["samples_per_problem"])
    C = Checks(); timings: dict = {}

    # ---- A1
    man = build_manifest(cfg_s)
    lock = root / "environment" / "versions.lock.txt"
    lock.write_text("\n".join([man["iverilog"], man["yosys"], f"python {man['python']}", man["os"]]) + "\n")
    ok = man["iverilog"].startswith("Icarus Verilog version 12") and bool(man["yosys"])
    C.add("A1", "preflight", "PASS" if ok else "FAIL", f"{man['iverilog']} | {man['yosys']}")

    # ---- A2 / A3
    shutil.rmtree(cfg_s["results_dir"], ignore_errors=True)
    run_generation(cfg_s)
    ev_s, timings["selftest_evaluate_s"] = _timed(evaluate, cfg_s, 1)
    orc = ev_s[ev_s["model"] == "oracle"]
    a2 = (orc["cls"] == "PASS").all()
    C.add("A2", "oracle (reference as model)", "PASS" if a2 else "FAIL",
          f"{int((orc['cls']=='PASS').sum())}/{len(orc)} PASS over {orc['config'].nunique()} configs x {orc['problem'].nunique()} problems")
    hdr, mod, pro = (ev_s[ev_s["model"] == m] for m in ("empty_header", "empty_module", "prose"))
    a3 = (hdr["cls"] != "PASS").all() and (mod["cls"] != "PASS").all() and (pro["cls"] == "NO_CODE").all()
    C.add("A3", "negative controls", "PASS" if a3 else "FAIL",
          f"empty_header PASS={int((hdr['cls']=='PASS').sum())}/{len(hdr)} ({ {k: int(v) for k, v in hdr['cls'].value_counts().items()} }); "
          f"empty_module PASS={int((mod['cls']=='PASS').sum())}/{len(mod)}; prose NO_CODE={int((pro['cls']=='NO_CODE').sum())}/{len(pro)}")

    # ---- A4
    p = rpath(cfg_s, "eval", "eval.csv"); h1 = sha256_file(p)
    evaluate(cfg_s, 2); h2 = sha256_file(p)
    C.add("A4", "evaluate twice (jobs=1 then jobs=2)", "PASS" if h1 == h2 else "FAIL", f"sha256 {h1[:12]} vs {h2[:12]}")

    # ---- A5
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"], cwd=root, capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    C.add("A5", "pytest", "PASS" if r.returncode == 0 else "FAIL", tail)

    # ---- planted pipeline
    ensure_planted(cfg_p, timings)
    ev = pd.read_csv(rpath(cfg_p, "eval", "eval.csv"), keep_default_na=False)
    sy = pd.read_csv(rpath(cfg_p, "eval", "synth.csv"), keep_default_na=False)
    sy["ok"] = sy["ok"].astype(str).str.lower().eq("true")
    gens = load_generations(cfg_p)
    models = [m["name"] for m in cfg_p["models"]]
    stubs = {m["name"]: PlantedStub(m["name"], cfg_p["dataset_dir"], **m["planted"]) for m in cfg_p["models"]}

    # ---- A6
    mp = write_manifest(cfg_p)
    bad_p = validate_manifest(mp)
    bad_r = validate_manifest(build_manifest(cfg_r))
    C.add("A6", "manifest validation", "PASS" if (not bad_p and bad_r) else "FAIL",
          f"planted manifest problems={len(bad_p)}; real-config manifest flagged {len(bad_r)} (expected, no Ollama here): {bad_r[:2]}")

    # ---- A7
    bad = []
    for m in models:
        for c in list(CONFIGS) + ["T0-A", "T0-B"]:
            n = int(((ev["model"] == m) & (ev["config"] == c)).sum())
            want = N if c.startswith("T0") else N * K
            if n != want:
                bad.append((m, c, n, want))
    n_gen = len(gens); want_gen = len(models) * N * (2 * K + 2)
    C.add("A7", "count integrity", "PASS" if not bad and n_gen == want_gen else "FAIL",
          f"generations {n_gen}/{want_gen}; config row-count mismatches: {bad[:3]}")

    # ---- A8
    rnd = random.Random(0)
    sample = rnd.sample([g for g in gens if g["run_set"] == "main"], 20)
    a = evaluate(cfg_p, 1, True, sample, write=False)
    b = evaluate(cfg_p, 1, False, sample, write=False)
    same = a.drop(columns=[]).reset_index(drop=True).equals(b.reset_index(drop=True))
    C.add("A8", "cache on/off on 20 random samples", "PASS" if same else "FAIL", f"{len(a)} rows compared")

    # ---- A9
    _H.seen = []
    srv = HTTPServer(("127.0.0.1", 0), _H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    from .backends import OpenAICompatBackend
    be = OpenAICompatBackend(f"http://127.0.0.1:{srv.server_address[1]}/v1", "m")
    t1 = be.complete("s", "u", temperature=0.85, top_p=0.95, max_tokens=8, seed=1001, meta={})["text"]
    t2 = be.complete("s", "u", temperature=0.85, top_p=0.95, max_tokens=8, seed=1002, meta={})["text"]
    srv.shutdown()
    mock_ok = _H.seen[0]["seed"] == 1001 and t1 != t2
    g = {(x["model"], x["problem"], x["run_set"], x["prompt_variant"], x["k"]): x["raw_response"] for x in gens}
    diff_seed = np.mean([g[("planted_a", pr, "main", "P0", 0)] != g[("planted_a", pr, "main", "P0", 1)] for pr in probs])
    t0a = np.mean([g[("planted_a", pr, "T0A", "P0", 0)] == g[("planted_a", pr, "T0B", "P0", 0)] for pr in probs])
    t0b = np.mean([g[("planted_b", pr, "T0A", "P0", 0)] == g[("planted_b", pr, "T0B", "P0", 0)] for pr in probs])
    ok9 = mock_ok and diff_seed > 0 and t0a == 1.0
    C.add("A9", "seed passthrough", "PARTIAL" if ok9 else "FAIL",
          f"mock server received seed 1001 and returned distinct text per seed: {mock_ok}; stub T=0.85 text differs across seeds on {diff_seed:.0%} of problems; "
          f"T0 identity planted_a={t0a:.2f} (deterministic stub), planted_b={t0b:.2f} (nondeterministic stub by design). "
          "NOT TESTED: a real Ollama endpoint (unavailable here); repeat A9 against it before the full run.")

    # ---- A10
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "proj"
        shutil.copytree(root, dst, symlinks=True, ignore=shutil.ignore_patterns("results", ".git", "__pycache__", "*.egg-info", ".pytest_cache"))
        (dst / "results").mkdir()
        (dst / "configs" / "subset3.txt").write_text("\n".join(probs[:3]) + "\n")
        txt = (dst / "configs" / "experiment_planted.yaml").read_text()
        txt = txt.replace("configs/problem_subset.txt", "configs/subset3.txt").replace("results/planted", "results/fresh")
        (dst / "configs" / "experiment_fresh.yaml").write_text(txt)
        env = dict(os.environ, PYTHONPATH=str(dst / "src"))
        t = time.time()
        r = subprocess.run([sys.executable, "-m", "rtlsens.cli", "all", "--config", "configs/experiment_fresh.yaml", "--jobs", "1"],
                           cwd=dst, env=env, capture_output=True, text=True)
        tabs = sorted(p.name for p in (dst / "results" / "fresh" / "tables").glob("T*.csv")) if (dst / "results" / "fresh" / "tables").exists() else []
        ok10 = r.returncode == 0 and len(tabs) == 7
        C.add("A10", "fresh copy, full chain on 3 problems", "PASS" if ok10 else "FAIL",
              f"exit {r.returncode}, tables {len(tabs)}/7, {time.time()-t:.0f}s" + ("" if ok10 else f"; stderr tail: {r.stderr[-300:]}"))

    # ================= planted-truth checks =================
    mats = {(m, c): M.pass_matrix(ev, m, c, probs) for m in models for c in CONFIGS}
    # P1
    zs = []
    for m in models:
        for c in CONFIGS:
            pi = np.array([stubs[m].expected_pass(pr, c) for pr in probs])
            se = np.sqrt((K * pi * (1 - pi)).sum()) / (N * K)
            zs.append((m, c, (mats[(m, c)].mean() - pi.mean()) / se))
    zmax = max(abs(z) for *_, z in zs)
    C.add("P1", "pass@1 equals planted truth (z-scores)", "PASS" if zmax <= Z_MAX else "FAIL",
          f"max |z| = {zmax:.2f} over {len(zs)} (model, config) cells; threshold {Z_MAX}")

    # P2: sigma calibration by Monte Carlo
    rng = np.random.default_rng(0)
    ratios_po, ratios_pt = [], []
    for m in models:
        pi = np.array([stubs[m].expected_pass(pr, "B0") for pr in probs])
        for _ in range(1500):
            X = (rng.random((N, K)) < pi[:, None]).astype(int)
            ratios_po.append(M.sigma_seed(X) / M.sigma_pred(X)); ratios_pt.append(M.sigma_pred(X) / M.sigma_true(pi))
    mo, mt = float(np.mean(ratios_po)), float(np.mean(ratios_pt))
    T2 = pd.read_csv(rpath(cfg_p, "tables", "T2.csv"))
    in_band = int(T2["within_0p5_2x"].sum())
    C.add("P2", "sigma_seed formula calibration (Monte Carlo, 3000 replicates)",
          "PASS" if (0.90 <= mo <= 1.05 and 0.93 <= mt <= 1.07) else "FAIL",
          f"mean(obs/pred)={mo:.3f} (theory ~0.97 for K=10), mean(pred/true)={mt:.3f}; pipeline run: {in_band}/{len(T2)} cells inside 0.5-2x band")

    # P3: gains / losses
    zf = []
    for m in models:
        st = stubs[m]; r = st.rates; pbar = np.array([st.p_variant(pr, "P0") for pr in probs])
        for c in ("X1", "X2", "N1"):
            ok0, okc = FMT_OK["B0"], FMT_OK[c]
            probs_fmt = {"tb_after": r["tb_after"], "tb_first": r["tb_first"], "nofence": r["nofence"], "renamed": r["renamed"], "clean": 1 - sum(r.values())}
            qg = sum(v for k, v in probs_fmt.items() if k in okc and k not in ok0)
            ql = sum(v for k, v in probs_fmt.items() if k in ok0 and k not in okc)
            fl = M.flips(mats[(m, c)], mats[(m, "B0")])
            for name, q in (("gains", qg), ("losses", ql)):
                pi = pbar * q
                se = np.sqrt(max((K * pi * (1 - pi)).sum(), 1e-9)) / (N * K)
                zf.append((m, c, name, (fl[name] - pi.mean()) / se))
    zfm = max(abs(z) for *_, z in zf)
    C.add("P3", "format-rule gains/losses equal planted truth", "PASS" if zfm <= Z_MAX else "FAIL",
          f"max |z| = {zfm:.2f} over {len(zf)} quantities")

    # P4: excess prompt flips
    idx = M.boot_indices(N, int(cfg_p["bootstrap"]["n"]), int(cfg_p["bootstrap"]["seed"]))
    out4 = []
    for m in models:
        st = stubs[m]
        pi0 = np.array([st.expected_pass(pr, "B0") for pr in probs]); pi1 = np.array([st.expected_pass(pr, "P1") for pr in probs])
        truth = float(((pi0 * (1 - pi1) + pi1 * (1 - pi0)) - 2 * pi0 * (1 - pi0)).mean())
        ex, lo, hi = M.excess_flip_ci(mats[(m, "B0")], mats[(m, "P1")], idx)
        se = (hi - lo) / (2 * 1.96)
        out4.append((m, truth, ex, lo, hi, abs(ex - truth) <= 3 * se))
    C.add("P4", "excess prompt-flip rate vs planted truth", "PASS" if all(o[-1] for o in out4) else "FAIL",
          "; ".join(f"{m}: truth {t:.3f}, measured {e:.3f} CI [{l:.3f}, {h:.3f}]" for m, t, e, l, h, _ in out4))

    # P5: determinism
    d = {m: M.determinism(gens, ev, m) for m in models}
    q = (1 - stubs["planted_b"].nd) ** 2
    se5 = np.sqrt(q * (1 - q) / d["planted_b"]["n_pairs"])
    ok5 = d["planted_a"]["raw_identity"] == 1.0 and abs(d["planted_b"]["raw_identity"] - q) <= 3 * se5 \
        and all(v["outcome_identity"] == 1.0 for v in d.values())
    C.add("P5", "determinism identity rates vs planted truth", "PASS" if ok5 else "FAIL",
          f"planted_a raw {d['planted_a']['raw_identity']:.3f} (truth 1.000); planted_b raw {d['planted_b']['raw_identity']:.3f} (truth {q:.3f}, 3SE={3*se5:.3f}); outcome identity 1.0 for both: {all(v['outcome_identity']==1.0 for v in d.values())}")

    # P6: gate-count pipeline
    ok6, notes = True, []
    ref = sy[sy["code_sha256"] == "REF"].set_index(["problem", "Y"])["num_cells"]
    for m in models:
        gf = M.gate_frame(ev, sy, m)
        if not np.allclose(gf["ratio"], 1.0):
            ok6 = False; notes.append(f"{m}: ratio != 1")
        got = np.sort(M.tool_induced(gf, "Y0", "Y2"))
        pr_k = gf[gf["Y"] == "Y0"][["problem", "k"]]
        exp = np.sort(np.array([ref[(p_, "Y2")] / ref[(p_, "Y0")] - 1 for p_ in pr_k["problem"] if ref[(p_, "Y0")] > 0]))
        if got.shape != exp.shape or not np.allclose(got, exp):
            ok6 = False; notes.append(f"{m}: tool-induced distribution differs from independent reconstruction")
    C.add("P6", "gate-count chain (passing samples are reference code => ratio 1; Y0->Y2 matches reconstruction from REF rows)",
          "PASS" if ok6 else "FAIL", "; ".join(notes) or "all ratios exactly 1.0; distributions identical")

    # P7: CI coverage by Monte Carlo
    cover, R = 0, 300
    pi = np.array([stubs["planted_a"].expected_pass(pr, "B0") for pr in probs]); truth = pi.mean()
    bi = M.boot_indices(N, 300, 5)
    for _ in range(R):
        X = (rng.random((N, K)) < pi[:, None]).astype(int)
        _, lo, hi = M.pass_at_1_ci(X, bi)
        cover += lo <= truth <= hi
    C.add("P7", "bootstrap 95% CI coverage of planted pass@1 (300 replicates)", "PASS" if cover / R >= 0.93 else "FAIL",
          f"coverage {cover/R:.3f} (>= 0.93 required; conservative coverage is expected because the bootstrap also resamples problems)")

    # ---- report
    write_acceptance_report(root, C, timings, man, zs, zf)
    return C.ok


def write_acceptance_report(root: Path, C: Checks, timings: dict, man: dict, zs, zf):
    lines = ["# Acceptance report", "", f"Environment: {man['iverilog']}; {man['yosys']}; Python {man['python']}; {man['os']}.", "",
             "| ID | Check | Status | Detail |", "|---|---|---|---|"]
    for cid, name, st, det in C.rows:
        lines.append(f"| {cid} | {name} | {st} | {det.replace('|', '/')} |")
    lines += ["", "## Stage timings (this machine, 1 CPU)", ""]
    for k, v in timings.items():
        lines.append(f"- {k}: {v:.1f} s")
    (root / "results" / "acceptance_report.md").write_text("\n".join(lines) + "\n")
