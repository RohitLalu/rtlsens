"""Run manifest (DESIGN.md Section 8.1)."""
from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import rpath
from .util import read_names, sha256_file, sha256_text

REQUIRED = ["created_utc", "git_commit_harness", "git_commit_verilog_eval", "os", "python", "iverilog",
            "yosys", "ollama", "hardware", "models", "problem_subset_sha256", "system_prompt_sha256",
            "sampling", "factor_levels"]


def _run(cmd, cwd=None) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20, cwd=cwd)
        return (r.stdout + r.stderr).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _first_line(s: str) -> str:
    return s.splitlines()[0].strip() if s else ""


def _cpu() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def _ram_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                return round(int(line.split()[1]) / 1048576, 1)
    except OSError:
        pass
    return 0.0


def _git(path) -> str:
    out = _first_line(_run(["git", "rev-parse", "HEAD"], cwd=str(path)))
    return out if len(out) == 40 else "unversioned"


def _ollama(models: list[dict]) -> tuple[str, list[dict]]:
    """Version and digests for openai_compat models served by Ollama; 'stub' for stubs."""
    version, out = "stub", []
    for m in models:
        entry = {"name": m["name"], "digest": "stub", "quant": "stub"}
        if m["backend"] == "openai_compat":
            base = m["base_url"].rstrip("/")
            root = base[:-3] if base.endswith("/v1") else base
            entry.update(digest="unreachable", quant="unknown")
            version = "unreachable"
            try:
                version = requests.get(f"{root}/api/version", timeout=3).json().get("version", "unknown")
                tags = requests.get(f"{root}/api/tags", timeout=3).json().get("models", [])
                for t in tags:
                    if t.get("name") == m["model"] or t.get("model") == m["model"]:
                        entry["digest"] = t.get("digest", "unknown")
                        entry["quant"] = (t.get("details") or {}).get("quantization_level", "unknown")
            except (requests.RequestException, ValueError):
                pass
        out.append(entry)
    return version, out


def build_manifest(cfg: dict) -> dict:
    gpu = _first_line(_run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])) or "none detected"
    ollama_version, models = _ollama(cfg["models"])
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit_harness": _git(cfg["_root"]),
        "git_commit_verilog_eval": _git(Path(cfg["dataset_dir"]).parent),
        "os": platform.platform(),
        "python": platform.python_version(),
        "iverilog": _first_line(_run(["iverilog", "-V"])),
        "yosys": _first_line(_run(["yosys", "-V"])),
        "ollama": ollama_version,
        "hardware": {"cpu": _cpu(), "gpu": gpu, "ram_gb": _ram_gb()},
        "models": models,
        "problem_subset_sha256": sha256_text(" ".join(read_names(cfg["subset_file"]))),
        "system_prompt_sha256": sha256_file(cfg["system_prompt_file"]),
        "sampling": {**cfg["sampling"], "seeds": [int(cfg["seed_base"]) + k for k in range(int(cfg["samples_per_problem"]))],
                     "t0": cfg["t0_sampling"]},
        "factor_levels": {"P": cfg["prompt_variants"], "X": ["X0", "X1", "X2"], "N": ["N0", "N1"],
                          "Y": ["Y0", "Y1", "Y2"]},
    }


def validate_manifest(m: dict) -> list[str]:
    """Return a list of problems; empty means valid."""
    bad = []
    for k in REQUIRED:
        v = m.get(k)
        if v is None or v == "" or v == [] or v == {}:
            bad.append(f"missing or empty: {k}")
    for sub in ("cpu", "gpu"):
        if not (m.get("hardware") or {}).get(sub):
            bad.append(f"hardware.{sub} empty")
    for e in m.get("models") or []:
        for f in ("name", "digest", "quant"):
            if not e.get(f):
                bad.append(f"model {e.get('name')}: {f} empty")
        if e.get("digest") in ("unreachable", "unknown"):
            bad.append(f"model {e.get('name')}: digest {e.get('digest')} (is the model server running?)")
    if m.get("ollama") in ("unreachable", "unknown"):
        bad.append(f"ollama version {m.get('ollama')}")
    return bad


def write_manifest(cfg: dict) -> dict:
    m = build_manifest(cfg)
    rpath(cfg, "manifest.json").write_text(json.dumps(m, indent=2))
    return m
