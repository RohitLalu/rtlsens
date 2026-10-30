"""Generation backends: a real OpenAI-compatible client plus stubs used for pipeline validation.

The stubs (oracle, empty_header, empty_module, prose, planted) never call an LLM. `planted`
produces outputs with known pass probabilities and known format quirks, so the analysis can be
checked against exact expected values (see acceptance.py). They say nothing about real models.
"""
from __future__ import annotations

import hashlib
import os
import random
import re
from pathlib import Path

import requests

from .simulate import reference_as_dut


class Backend:
    def complete(self, system: str, user: str, *, temperature: float, top_p: float,
                 max_tokens: int, seed: int, meta: dict) -> dict:
        raise NotImplementedError


class OpenAICompatBackend(Backend):
    """Chat-completions client for Ollama (http://localhost:11434/v1) or any compatible server."""

    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: int = 600):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "none")
        self.timeout = timeout

    def complete(self, system, user, *, temperature, top_p, max_tokens, seed, meta):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature, "top_p": top_p, "max_tokens": max_tokens,
            "seed": seed, "stream": False,
        }
        r = requests.post(f"{self.base_url}/chat/completions", json=payload,
                          headers={"Authorization": f"Bearer {self.api_key}"}, timeout=self.timeout)
        r.raise_for_status()
        d = r.json()
        ch = d["choices"][0]
        usage = d.get("usage") or {}
        return {"text": ch["message"].get("content") or "",
                "finish_reason": ch.get("finish_reason") or "unknown",
                "tokens_in": int(usage.get("prompt_tokens", 0)),
                "tokens_out": int(usage.get("completion_tokens", 0))}


# ---------------------------------------------------------------- stubs

def _fence(code: str) -> str:
    return f"Here is the implementation:\n\n```verilog\n{code.rstrip()}\n```\n\nThis design follows the specification.\n"


def _header_only(ref_dut: str) -> str:
    m = re.search(r"module\s+TopModule\s*\(.*?\)\s*;", ref_dut, re.S)
    if not m:
        return "module TopModule();\nendmodule\n"
    return m.group(0) + "\nendmodule\n"


def _resp(text: str) -> dict:
    return {"text": text, "finish_reason": "stop", "tokens_in": 0, "tokens_out": max(1, len(text) // 4)}


class OracleStub(Backend):
    def __init__(self, dataset_dir): self.d = dataset_dir
    def complete(self, system, user, *, temperature, top_p, max_tokens, seed, meta):
        return _resp(_fence(reference_as_dut(self.d, meta["problem"])))


class EmptyHeaderStub(Backend):
    """Correct port list, no logic: must never pass."""
    def __init__(self, dataset_dir): self.d = dataset_dir
    def complete(self, system, user, *, temperature, top_p, max_tokens, seed, meta):
        return _resp(_fence(_header_only(reference_as_dut(self.d, meta["problem"]))))


class EmptyModuleStub(Backend):
    def complete(self, system, user, *, temperature, top_p, max_tokens, seed, meta):
        return _resp(_fence("module TopModule();\nendmodule\n"))


class ProseStub(Backend):
    def complete(self, system, user, *, temperature, top_p, max_tokens, seed, meta):
        return _resp("I would approach this by thinking about the truth table carefully, but I will not write code.")


def _h(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def _u(*parts) -> float:
    return int(_h(*parts)[:12], 16) / float(16 ** 12)


TB_BLOCK = "```verilog\nmodule tb;\n  initial $display(\"hello\");\nendmodule\n```"

# Which format draws still extract a usable module, per evaluation config.
FMT_OK = {
    "B0": {"clean", "tb_after"},
    "X1": {"clean", "tb_first"},
    "X2": {"clean", "tb_after", "nofence"},
    "N1": {"clean", "tb_after", "renamed"},
}
FMT_OK["P1"] = FMT_OK["B0"]


class PlantedStub(Backend):
    """Stub with known truth. Per-problem pass probability p_i, format quirks with fixed rates."""

    def __init__(self, name: str, dataset_dir: str, scale=1.0, p1_jitter=0.3,
                 t0_nondeterminism=0.0, fmt=None):
        self.salt, self.d = name, dataset_dir
        self.scale, self.jitter, self.nd = float(scale), float(p1_jitter), float(t0_nondeterminism)
        f = fmt or {}
        self.rates = {k: float(f.get(k, 0.0)) for k in ("tb_after", "tb_first", "nofence", "renamed")}

    # ---- truth
    def base_p(self, problem: str) -> float:
        u = _u(self.salt, problem, "a")
        if u < 0.30:
            p = 0.0
        elif u < 0.60:
            p = 0.25 + 0.5 * _u(self.salt, problem, "b")
        else:
            p = 1.0
        return min(1.0, p * self.scale)

    def p_variant(self, problem: str, variant: str) -> float:
        p = self.base_p(problem)
        if variant == "P1":
            u = _u(self.salt, problem, "j")
            d = -self.jitter if u < 1 / 3 else (self.jitter if u < 2 / 3 else 0.0)
            p = min(1.0, max(0.0, p + d))
        return p

    def fmt_prob_ok(self, config: str) -> float:
        r = self.rates
        probs = {"tb_after": r["tb_after"], "tb_first": r["tb_first"], "nofence": r["nofence"],
                 "renamed": r["renamed"]}
        probs["clean"] = 1.0 - sum(r.values())
        return sum(probs[f] for f in FMT_OK[config])

    def expected_pass(self, problem: str, config: str) -> float:
        variant = "P1" if config == "P1" else "P0"
        return self.p_variant(problem, variant) * self.fmt_prob_ok(config)

    # ---- generation
    def _format(self, u: float) -> str:
        r, acc = self.rates, 0.0
        for k in ("tb_after", "tb_first", "nofence", "renamed"):
            acc += r[k]
            if u < acc:
                return k
        return "clean"

    def complete(self, system, user, *, temperature, top_p, max_tokens, seed, meta):
        problem, variant = meta["problem"], meta["prompt_variant"]
        p = self.p_variant(problem, variant)
        if temperature > 0:
            rng = random.Random(int(_h(self.salt, problem, variant, seed)[:16], 16))
            u_pass, u_fmt = rng.random(), rng.random()
        else:
            u_pass = _u(self.salt, problem, variant, "t0pass")
            u_fmt = _u(self.salt, problem, variant, "t0fmt")
        ref = reference_as_dut(self.d, problem)
        code = ref if u_pass < p else _header_only(ref)
        fmt = self._format(u_fmt)
        if fmt == "renamed":
            code = code.replace("module TopModule", "module top_module", 1)
        lead, tail = "Here is the implementation:\n\n", "\nThis module implements the described behavior.\n"
        if fmt in ("clean", "renamed"):
            text = f"{lead}```verilog\n{code.rstrip()}\n```\n{tail}"
        elif fmt == "tb_after":
            text = f"{lead}```verilog\n{code.rstrip()}\n```\n\nA quick testbench:\n\n{TB_BLOCK}\n"
        elif fmt == "tb_first":
            text = f"First, a testbench:\n\n{TB_BLOCK}\n\nAnd the design:\n\n```verilog\n{code.rstrip()}\n```\n"
        else:  # nofence
            text = f"{lead}{code.rstrip()}\n{tail}"
        if temperature == 0 and self.nd > 0 and random.random() < self.nd:
            text += f"\n// nd {os.urandom(4).hex()}\n"
        return _resp(text)


def make_backend(model_cfg: dict, dataset_dir: str) -> Backend:
    kind = model_cfg["backend"]
    if kind == "openai_compat":
        return OpenAICompatBackend(model_cfg["base_url"], model_cfg["model"], model_cfg.get("api_key"))
    if kind == "oracle":
        return OracleStub(dataset_dir)
    if kind == "empty_header":
        return EmptyHeaderStub(dataset_dir)
    if kind == "empty_module":
        return EmptyModuleStub()
    if kind == "prose":
        return ProseStub()
    if kind == "planted":
        return PlantedStub(model_cfg["name"], dataset_dir, **model_cfg.get("planted", {}))
    raise ValueError(f"unknown backend {kind!r}")
