"""Metrics of DESIGN.md Section 9. All functions take 0/1 matrices M of shape (N problems, K samples)."""
from __future__ import annotations

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ matrices
def pass_matrix(df: pd.DataFrame, model: str, config: str, problems: list[str]) -> np.ndarray:
    sub = df[(df["model"] == model) & (df["config"] == config)]
    if sub.empty:
        raise KeyError(f"no rows for model={model} config={config}")
    piv = (sub.assign(v=(sub["cls"] == "PASS").astype(int))
              .pivot(index="problem", columns="k", values="v").reindex(problems))
    if piv.isna().any().any():
        raise ValueError(f"incomplete grid for model={model} config={config}")
    return piv.to_numpy(dtype=int)


# ------------------------------------------------------------------ bootstrap
def boot_indices(n: int, b: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(b, n))


def pct_ci(vals: np.ndarray, level: float = 0.95) -> tuple[float, float]:
    a = (1 - level) / 2
    lo, hi = np.percentile(vals, [100 * a, 100 * (1 - a)])
    return float(lo), float(hi)


# ------------------------------------------------------------------ pass@1 family
def pass_at_1(M: np.ndarray) -> float:
    return float(M.mean())


def pass_at_1_ci(M: np.ndarray, idx: np.ndarray) -> tuple[float, float, float]:
    boot = M[idx].mean(axis=(1, 2))
    return pass_at_1(M), *pct_ci(boot)


def run_pass(M: np.ndarray) -> np.ndarray:
    return M.mean(axis=0)


def sigma_seed(M: np.ndarray) -> float:
    return float(run_pass(M).std(ddof=1))


def sigma_pred(M: np.ndarray) -> float:
    """sqrt(mean_i[p~_i(1-p~_i)] / N) with the unbiased variance term p^(1-p^) K/(K-1)."""
    n, k = M.shape
    ph = M.mean(axis=1)
    v = ph * (1 - ph) * k / (k - 1)
    return float(np.sqrt(v.sum()) / n)


def sigma_true(p: np.ndarray) -> float:
    """Exact sigma of a single-run pass@1 when the true per-problem probabilities p are known."""
    return float(np.sqrt((p * (1 - p)).sum()) / len(p))


def delta_ci(Mf: np.ndarray, M0: np.ndarray, idx: np.ndarray) -> tuple[float, float, float]:
    d = float(Mf.mean() - M0.mean())
    boot = Mf[idx].mean(axis=(1, 2)) - M0[idx].mean(axis=(1, 2))
    return d, *pct_ci(boot)


def is_material(delta: float, lo: float, hi: float, sig: float) -> bool:
    return abs(delta) >= 2 * sig and (lo > 0 or hi < 0)


# ------------------------------------------------------------------ flips
def flips(Mf: np.ndarray, M0: np.ndarray) -> dict:
    gains = float(((Mf == 1) & (M0 == 0)).mean())
    losses = float(((Mf == 0) & (M0 == 1)).mean())
    return {"gains": gains, "losses": losses, "flip": gains + losses}


def f_seed(M: np.ndarray) -> float:
    """Mean over ordered seed pairs k != k' of the fraction of problems whose outcome differs."""
    n, k = M.shape
    c = M.sum(axis=1)
    return float((2.0 * c * (k - c) / (k * (k - 1))).mean())


def f_prompt(M0: np.ndarray, M1: np.ndarray) -> float:
    return float((M0 != M1).mean())


def excess_flip_ci(M0: np.ndarray, M1: np.ndarray, idx: np.ndarray) -> tuple[float, float, float]:
    n, k = M0.shape
    c = M0.sum(axis=1)
    per_problem = (M0 != M1).mean(axis=1) - 2.0 * c * (k - c) / (k * (k - 1))
    return float(per_problem.mean()), *pct_ci(per_problem[idx].mean(axis=1))


# ------------------------------------------------------------------ ranking
def reversal_prob(MA: np.ndarray, MB: np.ndarray) -> float:
    s0 = np.sign(MA.mean() - MB.mean())
    if s0 == 0:
        return float("nan")
    diff = run_pass(MA)[:, None] - run_pass(MB)[None, :]
    wrong = (np.sign(diff) != s0) & (diff != 0)
    ties = diff == 0
    return float((wrong.sum() + 0.5 * ties.sum()) / diff.size)


# ------------------------------------------------------------------ gate-count proxy
def gate_frame(eval_df: pd.DataFrame, synth_df: pd.DataFrame, model: str) -> pd.DataFrame:
    """One row per (passing B0 sample, Y): cells, reference cells, ratio."""
    ev = eval_df[(eval_df["model"] == model) & (eval_df["config"] == "B0") & (eval_df["cls"] == "PASS")]
    ok = synth_df[synth_df["ok"]]
    ref = ok[ok["code_sha256"] == "REF"][["problem", "Y", "num_cells"]].rename(columns={"num_cells": "ref_cells"})
    cand = ok[ok["code_sha256"] != "REF"]
    out = ev[["problem", "k", "code_sha256"]].merge(cand, on=["problem", "code_sha256"]).merge(ref, on=["problem", "Y"])
    out = out[out["ref_cells"] > 0].copy()
    out["ratio"] = out["num_cells"] / out["ref_cells"]
    return out


def tool_induced(gf: pd.DataFrame, y_from: str, y_to: str) -> np.ndarray:
    a = gf[gf["Y"] == y_from].set_index(["problem", "k"])["num_cells"]
    b = gf[gf["Y"] == y_to].set_index(["problem", "k"])["num_cells"]
    j = pd.concat([a, b], axis=1, join="inner", keys=["a", "b"])
    j = j[j["a"] > 0]
    return (j["b"] / j["a"] - 1.0).to_numpy()


def seed_cv(gf: pd.DataFrame, y: str = "Y0") -> np.ndarray:
    g = gf[gf["Y"] == y].groupby("problem")["num_cells"]
    cvs = []
    for _, s in g:
        if len(s) >= 2 and s.mean() > 0:
            cvs.append(s.std(ddof=0) / s.mean())
    return np.array(cvs)


def ordering_flip_fraction(gfA: pd.DataFrame, gfB: pd.DataFrame, y_a: str = "Y0", y_b: str = "Y2") -> tuple[float, int]:
    def med(gf, y):
        return gf[gf["Y"] == y].groupby("problem")["ratio"].median()
    a0, b0, a2, b2 = med(gfA, y_a), med(gfB, y_a), med(gfA, y_b), med(gfB, y_b)
    probs = sorted(set(a0.index) & set(b0.index) & set(a2.index) & set(b2.index))
    n_strict, n_flip = 0, 0
    for p in probs:
        s0, s2 = np.sign(a0[p] - b0[p]), np.sign(a2[p] - b2[p])
        if s0 != 0 and s2 != 0:
            n_strict += 1
            n_flip += int(s0 != s2)
    return (n_flip / n_strict if n_strict else float("nan")), n_strict


# ------------------------------------------------------------------ determinism
def determinism(gens: list[dict], eval_df: pd.DataFrame, model: str) -> dict:
    a = {r["problem"]: r["raw_response"] for r in gens if r["model"] == model and r["run_set"] == "T0A"}
    b = {r["problem"]: r["raw_response"] for r in gens if r["model"] == model and r["run_set"] == "T0B"}
    common = sorted(set(a) & set(b))
    raw_same = float(np.mean([a[p] == b[p] for p in common])) if common else float("nan")
    ea = eval_df[(eval_df["model"] == model) & (eval_df["config"] == "T0-A")].set_index("problem")["cls"].eq("PASS")
    eb = eval_df[(eval_df["model"] == model) & (eval_df["config"] == "T0-B")].set_index("problem")["cls"].eq("PASS")
    idx = ea.index.intersection(eb.index)
    out_same = float((ea[idx] == eb[idx]).mean()) if len(idx) else float("nan")
    return {"n_pairs": len(common), "raw_identity": raw_same, "outcome_identity": out_same}
