from __future__ import annotations

import os
from pathlib import Path

import yaml

_PATH_KEYS = ("dataset_dir", "subset_file", "system_prompt_file", "yosys_dir", "results_dir")


def load_config(path, results_dir: str | None = None) -> dict:
    """Load a YAML config; relative paths resolve against the project root (parent of configs/)."""
    path = Path(path).resolve()
    cfg = yaml.safe_load(path.read_text())
    root = path.parent.parent
    cfg["_root"] = str(root)
    cfg["_config_path"] = str(path)
    for k in _PATH_KEYS:
        p = Path(cfg[k])
        cfg[k] = str(p if p.is_absolute() else root / p)
    env = os.environ.get("VERILOG_EVAL_DIR")
    if env:
        cfg["dataset_dir"] = env
    if results_dir:
        cfg["results_dir"] = str(Path(results_dir).resolve())
    return cfg


def rpath(cfg: dict, *parts: str) -> Path:
    p = Path(cfg["results_dir"]).joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
