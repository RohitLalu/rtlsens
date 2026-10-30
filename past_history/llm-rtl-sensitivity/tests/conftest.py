from __future__ import annotations

import copy
from pathlib import Path

import pytest

from rtlsens.config import load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def base_cfg():
    cfg = load_config(ROOT / "configs" / "experiment_selftest.yaml")
    if not (Path(cfg["dataset_dir"]) / "problems.txt").exists():
        pytest.skip("VerilogEval dataset not found; run environment/setup.sh or set VERILOG_EVAL_DIR")
    return cfg


@pytest.fixture
def make_cfg(base_cfg, tmp_path):
    def _make(models, n_problems=3, K=2, backend_cfg=None):
        cfg = copy.deepcopy(base_cfg)
        names = Path(base_cfg["subset_file"]).read_text().split()[:n_problems]
        sub = tmp_path / "subset.txt"
        sub.write_text("\n".join(names) + "\n")
        cfg["subset_file"] = str(sub)
        cfg["results_dir"] = str(tmp_path / "res")
        cfg["samples_per_problem"] = K
        cfg["models"] = models
        cfg["bootstrap"] = {"n": 500, "seed": 1}
        return cfg
    return _make
