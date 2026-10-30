"""Stage 2: generation. Resumable, append-only JSONL, one record per sample."""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .backends import make_backend
from .config import rpath
from .prompts import build_user_prompt, load_system_prompt
from .util import read_names, sha256_text

SET_PARAMS = {"main": "sampling", "T0A": "t0_sampling", "T0B": "t0_sampling"}


def sample_id(model, problem, run_set, variant, k, seed, params) -> str:
    key = f"{model}|{problem}|{run_set}|{variant}|{k}|{seed}|{params['temperature']}|{params['top_p']}|{params['max_tokens']}"
    return sha256_text(key)[:16]


def build_jobs(cfg: dict, problems: list[str], limit_problems: int | None = None) -> list[dict]:
    if limit_problems:
        problems = problems[:limit_problems]
    jobs = []
    K = int(cfg["samples_per_problem"])
    for m in cfg["models"]:
        for prob in problems:
            for variant in cfg["prompt_variants"]:
                for k in range(K):
                    jobs.append(dict(model=m["name"], problem=prob, run_set="main", prompt_variant=variant,
                                     k=k, seed=int(cfg["seed_base"]) + k, params=cfg["sampling"]))
            for rs in ("T0A", "T0B"):
                p = cfg["t0_sampling"]
                jobs.append(dict(model=m["name"], problem=prob, run_set=rs, prompt_variant="P0",
                                 k=0, seed=int(p.get("seed", 0)), params=p))
    for j in jobs:
        j["sample_id"] = sample_id(j["model"], j["problem"], j["run_set"], j["prompt_variant"],
                                   j["k"], j["seed"], j["params"])
    return jobs


def load_done(path) -> set[str]:
    done = set()
    try:
        with open(path) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["sample_id"])
                except (ValueError, KeyError):
                    continue  # truncated last line after a kill
    except FileNotFoundError:
        pass
    return done


def run_generation(cfg: dict, workers: int | None = None, limit_problems: int | None = None,
                   retries: int = 3, progress_every: int = 100) -> dict:
    problems = read_names(cfg["subset_file"])
    out_path = rpath(cfg, "raw", "generations.jsonl")
    system = load_system_prompt(cfg)
    backends = {m["name"]: make_backend(m, cfg["dataset_dir"]) for m in cfg["models"]}
    jobs = build_jobs(cfg, problems, limit_problems)
    done = load_done(out_path)
    todo = [j for j in jobs if j["sample_id"] not in done]
    lock = threading.Lock()
    counter = {"n": 0, "err": 0}
    t0 = time.time()
    fh = open(out_path, "a")

    def work(j):
        user = build_user_prompt(cfg["dataset_dir"], j["problem"], j["prompt_variant"])
        p = j["params"]
        last = None
        for attempt in range(retries):
            try:
                t = time.time()
                r = backends[j["model"]].complete(
                    system, user, temperature=p["temperature"], top_p=p["top_p"],
                    max_tokens=p["max_tokens"], seed=j["seed"],
                    meta={"problem": j["problem"], "prompt_variant": j["prompt_variant"],
                          "run_set": j["run_set"], "k": j["k"]})
                lat = time.time() - t
                rec = {"sample_id": j["sample_id"], "model": j["model"], "problem": j["problem"],
                       "run_set": j["run_set"], "prompt_variant": j["prompt_variant"], "k": j["k"],
                       "seed": j["seed"], "temperature": p["temperature"], "top_p": p["top_p"],
                       "max_tokens": p["max_tokens"], "prompt_sha256": sha256_text(system + "\n" + user),
                       "raw_response": r["text"], "finish_reason": r["finish_reason"],
                       "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"],
                       "latency_s": round(lat, 3),
                       "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                with lock:
                    fh.write(json.dumps(rec) + "\n"); fh.flush()
                    counter["n"] += 1
                    if counter["n"] % progress_every == 0:
                        print(f"  generated {counter['n']}/{len(todo)}  ({time.time()-t0:.0f}s)", flush=True)
                return
            except Exception as e:  # network or server error: retry, then leave for a resume
                last = e
                time.sleep(2 ** attempt)
        with lock:
            counter["err"] += 1
        print(f"  FAILED after {retries} tries: {j['model']} {j['problem']} {j['run_set']} {j['prompt_variant']} k={j['k']}: {last}")

    workers = workers or int(cfg.get("workers", 1))
    if workers <= 1:
        for j in todo:
            work(j)
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(work, todo))
    fh.close()
    return {"total_jobs": len(jobs), "already_done": len(done & {j["sample_id"] for j in jobs}),
            "generated": counter["n"], "failed": counter["err"], "path": str(out_path)}
