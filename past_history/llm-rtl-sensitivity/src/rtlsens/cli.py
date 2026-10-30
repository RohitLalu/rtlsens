"""python -m rtlsens.cli <stage> --config configs/experiment.yaml"""
from __future__ import annotations

import argparse
import json
import sys

from .config import load_config, rpath


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rtlsens")
    ap.add_argument("stage", choices=["preflight", "subset", "generate", "evaluate", "synth", "analyze",
                                      "all", "acceptance"])
    ap.add_argument("--config", default="configs/experiment.yaml")
    ap.add_argument("--results-dir", default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--limit-problems", type=int, default=None)
    a = ap.parse_args(argv)
    cfg = load_config(a.config, a.results_dir)

    def do(stage):
        if stage == "preflight":
            from .manifest import validate_manifest, write_manifest
            m = write_manifest(cfg)
            bad = validate_manifest(m)
            print(json.dumps(m, indent=2))
            print("manifest valid" if not bad else f"manifest problems: {bad}")
            return 0 if not bad else 1
        if stage == "subset":
            from .subset import check_subset
            return 0 if check_subset(cfg) else 1
        if stage == "generate":
            from .generate import run_generation
            print(run_generation(cfg, a.workers, a.limit_problems)); return 0
        if stage == "evaluate":
            from .evaluate import evaluate
            df = evaluate(cfg, a.jobs); print(f"eval rows: {len(df)}"); return 0
        if stage == "synth":
            from .evaluate import run_synth
            df = run_synth(cfg, n_jobs=a.jobs); print(f"synth rows: {len(df)}"); return 0
        if stage == "analyze":
            from .report import run_report
            print(run_report(cfg)); return 0
        if stage == "acceptance":
            from .acceptance import run_acceptance
            return 0 if run_acceptance(cfg) else 1
        raise SystemExit(f"unknown stage {stage}")

    if a.stage == "all":
        for s in ["preflight", "generate", "evaluate", "synth", "analyze"]:
            print(f"== {s}")
            rc = do(s)
            if rc:
                return rc
        return 0
    return do(a.stage)


if __name__ == "__main__":
    sys.exit(main())
