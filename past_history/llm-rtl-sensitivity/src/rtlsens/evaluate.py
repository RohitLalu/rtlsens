"""Stages 3 and 4: extract + simulate (eval.csv) and synthesize passing samples (synth.csv)."""
from __future__ import annotations

import json

import pandas as pd

from . import simulate, synth
from .config import rpath
from .extract import apply_name_rule, extract_code
from .simulate import reference_as_dut
from .util import read_names, sha256_text

# config -> (run_set, prompt_variant, X, N)
EVAL_CONFIGS = {
    "B0": ("main", "P0", "X0", "N0"),
    "X1": ("main", "P0", "X1", "N0"),
    "X2": ("main", "P0", "X2", "N0"),
    "N1": ("main", "P0", "X0", "N1"),
    "P1": ("main", "P1", "X0", "N0"),
    "T0-A": ("T0A", "P0", "X0", "N0"),
    "T0-B": ("T0B", "P0", "X0", "N0"),
}
ROW_ORDER = ["model", "problem", "run_set", "prompt_variant", "k", "config"]


def load_generations(cfg: dict) -> list[dict]:
    recs = []
    with open(rpath(cfg, "raw", "generations.jsonl")) as f:
        for line in f:
            try:
                recs.append(json.loads(line))
            except ValueError:
                continue
    return recs


def evaluate(cfg: dict, n_jobs: int | None = None, dedupe: bool = True,
             records: list[dict] | None = None, write: bool = True) -> pd.DataFrame:
    recs = records if records is not None else load_generations(cfg)
    rows, sim_jobs, store = [], {}, {}
    for r in recs:
        for config, (run_set, variant, X, N) in EVAL_CONFIGS.items():
            if r["run_set"] != run_set or r["prompt_variant"] != variant:
                continue
            code = extract_code(r["raw_response"], X)
            row = {"sample_id": r["sample_id"], "model": r["model"], "problem": r["problem"],
                   "run_set": r["run_set"], "prompt_variant": variant, "k": r["k"], "config": config,
                   "X": X, "N": N, "code_sha256": "", "cls": "NO_CODE", "harness_code": "",
                   "n_mismatch": -1, "n_samples_tb": -1}
            if code is not None:
                code = apply_name_rule(code, N)
                sha = sha256_text(code)
                row["code_sha256"] = sha
                store[sha] = code
                key = (r["problem"], sha) if dedupe else (r["problem"], sha, r["sample_id"], config)
                sim_jobs[key] = (key, r["problem"], code)
                row["_key"] = key
            rows.append(row)
    results = simulate.run_many(list(sim_jobs.values()), cfg["dataset_dir"],
                                int(cfg.get("sim_timeout_s", 30)), n_jobs)
    for row in rows:
        key = row.pop("_key", None)
        if key is not None:
            res = results[key]
            row.update(cls=res["cls"], harness_code=res["harness_code"],
                       n_mismatch=res["n_mismatch"], n_samples_tb=res["n_samples_tb"])
    df = pd.DataFrame(rows).sort_values(ROW_ORDER, kind="stable").reset_index(drop=True)
    if write:
        df.to_csv(rpath(cfg, "eval", "eval.csv"), index=False, lineterminator="\n")
        rpath(cfg, "eval", "code_store.json").write_text(json.dumps(store, sort_keys=True))
    return df


def run_synth(cfg: dict, eval_df: pd.DataFrame | None = None, n_jobs: int | None = None,
              write: bool = True) -> pd.DataFrame:
    if eval_df is None:
        eval_df = pd.read_csv(rpath(cfg, "eval", "eval.csv"), keep_default_na=False)
    store = json.loads(rpath(cfg, "eval", "code_store.json").read_text())
    scripts = synth.load_scripts(cfg["yosys_dir"])
    passing = eval_df[(eval_df["config"] == "B0") & (eval_df["cls"] == "PASS")]
    items = sorted({(r.problem, r.code_sha256) for r in passing.itertuples()})
    jobs = []
    for prob, sha in items:
        for y, body in scripts.items():
            jobs.append(((prob, sha, y), store[sha], body))
    for prob in read_names(cfg["subset_file"]):
        code = reference_as_dut(cfg["dataset_dir"], prob)
        for y, body in scripts.items():
            jobs.append(((prob, "REF", y), code, body))
    res = synth.run_many(jobs, int(cfg.get("yosys_timeout_s", 120)), n_jobs)
    rows = [{"problem": p, "code_sha256": s, "Y": y, "ok": bool(ok), "num_cells": n}
            for (p, s, y), (ok, n) in res.items()]
    df = pd.DataFrame(rows).sort_values(["problem", "code_sha256", "Y"]).reset_index(drop=True)
    if write:
        df.to_csv(rpath(cfg, "eval", "synth.csv"), index=False, lineterminator="\n")
    return df
