"""Stage 5: tables T1-T7 and figures F1-F4 from raw records."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import metrics as M
from .config import rpath
from .evaluate import load_generations
from .util import read_names

CONFIGS = ["B0", "P1", "X1", "X2", "N1"]
PP = 100.0


def _load(cfg):
    ev = pd.read_csv(rpath(cfg, "eval", "eval.csv"), keep_default_na=False)
    sp = rpath(cfg, "eval", "synth.csv")
    sy = pd.read_csv(sp, keep_default_na=False) if sp.exists() else None
    if sy is not None:
        sy["ok"] = sy["ok"].astype(str).str.lower().eq("true")
    return ev, sy, load_generations(cfg)


def build_tables(cfg: dict) -> dict[str, pd.DataFrame]:
    ev, sy, gens = _load(cfg)
    problems = read_names(cfg["subset_file"])
    models = [m["name"] for m in cfg["models"]]
    N = len(problems)
    idx = M.boot_indices(N, int(cfg["bootstrap"]["n"]), int(cfg["bootstrap"]["seed"]))
    mats = {(m, c): M.pass_matrix(ev, m, c, problems) for m in models for c in CONFIGS}
    T: dict[str, pd.DataFrame] = {}

    # T1: pass@1 per model and config
    rows = []
    for m in models:
        for c in CONFIGS:
            p, lo, hi = M.pass_at_1_ci(mats[(m, c)], idx)
            rows.append(dict(model=m, config=c, pass_at_1_pp=p * PP, ci_lo_pp=lo * PP, ci_hi_pp=hi * PP,
                             n_problems=N, K=mats[(m, c)].shape[1]))
    T["T1"] = pd.DataFrame(rows)

    # T2: seed spread
    rows = []
    for m in models:
        for c in CONFIGS:
            X = mats[(m, c)]
            r = M.run_pass(X)
            so, sp_ = M.sigma_seed(X), M.sigma_pred(X)
            rows.append(dict(model=m, config=c, sigma_seed_obs_pp=so * PP, sigma_seed_pred_pp=sp_ * PP,
                             ratio_obs_over_pred=so / sp_ if sp_ > 0 else float("nan"),
                             run_min_pp=r.min() * PP, run_max_pp=r.max() * PP,
                             within_0p5_2x=bool(sp_ > 0 and 0.5 <= so / sp_ <= 2.0)))
    T["T2"] = pd.DataFrame(rows)

    # T3: factor effects and flips
    rows = []
    for m in models:
        B0 = mats[(m, "B0")]
        sig = M.sigma_seed(B0)
        for c in CONFIGS[1:]:
            Xc = mats[(m, c)]
            d, lo, hi = M.delta_ci(Xc, B0, idx)
            fl = M.flips(Xc, B0)
            mat = M.is_material(d, lo, hi, sig)
            verdict = ("material" if mat else
                       "detectable, below 2*sigma_seed" if (lo > 0 or hi < 0) else
                       "not distinguishable from noise")
            row = dict(model=m, factor=c, delta_pp=d * PP, ci_lo_pp=lo * PP, ci_hi_pp=hi * PP,
                       sigma_seed_pp=sig * PP, material=mat, verdict=verdict,
                       gains=fl["gains"], losses=fl["losses"], flip_rate=fl["flip"],
                       F_P=np.nan, F_S=np.nan, excess_flip=np.nan, excess_lo=np.nan, excess_hi=np.nan)
            if c == "P1":
                ex, elo, ehi = M.excess_flip_ci(B0, Xc, idx)
                row.update(F_P=M.f_prompt(B0, Xc), F_S=M.f_seed(B0), excess_flip=ex, excess_lo=elo, excess_hi=ehi)
            rows.append(row)
    T["T3"] = pd.DataFrame(rows)

    # T4: ranking (first two models)
    if len(models) >= 2:
        a, b = models[0], models[1]
        rows = []
        for c in CONFIGS:
            MA, MB = mats[(a, c)], mats[(b, c)]
            dab = MA.mean() - MB.mean()
            rows.append(dict(model_a=a, model_b=b, config=c, delta_ab_pp=dab * PP, sign=int(np.sign(dab)),
                             reversal_prob=M.reversal_prob(MA, MB),
                             sigma_seed_a_pp=M.sigma_seed(MA) * PP, sigma_seed_b_pp=M.sigma_seed(MB) * PP))
        T["T4"] = pd.DataFrame(rows)

    # T5: gate-count proxy
    gfs = {}
    if sy is not None:
        rows = []
        for m in models:
            gf = M.gate_frame(ev, sy, m)
            gfs[m] = gf
            for y in ["Y0", "Y1", "Y2"]:
                g = gf[gf["Y"] == y]
                rows.append(dict(model=m, metric=f"median_ratio_to_ref_{y}", value=float(g["ratio"].median()) if len(g) else np.nan, n=len(g)))
            for yf, yt in [("Y0", "Y1"), ("Y0", "Y2")]:
                d = M.tool_induced(gf, yf, yt)
                rows.append(dict(model=m, metric=f"tool_induced_{yf}_to_{yt}_median", value=float(np.median(d)) if len(d) else np.nan, n=len(d)))
                rows.append(dict(model=m, metric=f"tool_induced_{yf}_to_{yt}_IQR", value=float(np.subtract(*np.percentile(d, [75, 25]))) if len(d) else np.nan, n=len(d)))
            cv = M.seed_cv(gf, "Y0")
            rows.append(dict(model=m, metric="seed_induced_CV_median_Y0", value=float(np.median(cv)) if len(cv) else np.nan, n=len(cv)))
        if len(models) >= 2:
            frac, n = M.ordering_flip_fraction(gfs[models[0]], gfs[models[1]])
            rows.append(dict(model=f"{models[0]} vs {models[1]}", metric="ordering_flip_fraction_Y0_vs_Y2", value=frac, n=n))
        T["T5"] = pd.DataFrame(rows)

    # T6: determinism
    rows = []
    for m in models:
        d = M.determinism(gens, ev, m)
        rows.append(dict(model=m, **d))
    T["T6"] = pd.DataFrame(rows)

    # T7: factor importance
    t3 = T["T3"]
    rows = []
    for m in models:
        sig = t3[t3["model"] == m]["sigma_seed_pp"].iloc[0]
        rows.append(dict(model=m, item="Seed (sampling)", effect=sig, unit="pp (sigma_seed)", normalized=1.0, verdict="noise reference"))
        for r in t3[t3["model"] == m].itertuples():
            name = {"P1": "Prompt wording (P1)", "X1": "Extraction: last fenced block (X1)",
                    "X2": "Extraction: raw module span (X2)", "N1": "Module-name auto-rename (N1)"}[r.factor]
            rows.append(dict(model=m, item=name, effect=abs(r.delta_pp), unit="pp |delta pass@1|",
                             normalized=abs(r.delta_pp) / r.sigma_seed_pp if r.sigma_seed_pp > 0 else np.nan,
                             verdict=r.verdict))
            if r.factor == "P1":
                rows.append(dict(model=m, item="Prompt wording: excess per-problem flips", effect=r.excess_flip * PP,
                                 unit="pp of samples", normalized=np.nan,
                                 verdict="excess > 0 (CI excludes 0)" if r.excess_lo > 0 else "CI includes 0"))
        if sy is not None:
            gf = gfs[m]
            d = M.tool_induced(gf, "Y0", "Y2")
            rows.append(dict(model=m, item="Yosys script (Y0 vs Y2)", effect=float(np.median(np.abs(d))) * PP if len(d) else np.nan,
                             unit="% median |cell change|", normalized=np.nan, verdict="report script"))
    t7 = pd.DataFrame(rows)
    t7["_o"] = t7["normalized"].fillna(-1)
    T["T7"] = t7.sort_values(["model", "_o"], ascending=[True, False]).drop(columns="_o").reset_index(drop=True)

    for name, df in T.items():
        df.to_csv(rpath(cfg, "tables", f"{name}.csv"), index=False, float_format="%.6g")
    T["_gf"] = gfs  # type: ignore[assignment]
    T["_mats"] = mats  # type: ignore[assignment]
    return T


def build_figures(cfg: dict, T: dict) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = [m["name"] for m in cfg["models"]]
    mats = T["_mats"]
    out = []

    # F1: seed-run pass@1 per model and config
    fig, ax = plt.subplots(figsize=(8, 4))
    pos, labels = [], []
    for i, m in enumerate(models):
        for j, c in enumerate(CONFIGS):
            x = i * (len(CONFIGS) + 1) + j
            r = M.run_pass(mats[(m, c)]) * PP
            ax.scatter(np.full_like(r, x) + np.linspace(-0.2, 0.2, len(r)), r, s=12)
            ax.hlines(r.mean(), x - 0.3, x + 0.3, colors="k")
            pos.append(x); labels.append(f"{m}\n{c}" if j == 0 else c)
    ax.set_xticks(pos); ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("single-run pass@1 (%)"); ax.set_title("F1: seed-run pass@1 by model and configuration")
    fig.tight_layout(); p = rpath(cfg, "figures", "F1.pdf"); fig.savefig(p); plt.close(fig); out.append(str(p))

    # F2: flip rates against the seed baseline
    t3 = T["T3"]
    fig, ax = plt.subplots(figsize=(8, 4))
    w = 0.8 / max(1, len(models))
    for i, m in enumerate(models):
        s = t3[t3["model"] == m]
        x = np.arange(len(s)) + i * w
        ax.bar(x, s["gains"] * PP, w, label=f"{m} gains")
        ax.bar(x, s["losses"] * PP, w, bottom=s["gains"] * PP, label=f"{m} losses", alpha=0.6)
        fs = s["F_S"].dropna()
        if len(fs):
            ax.axhline(fs.iloc[0] * PP, ls="--", lw=0.8, color=f"C{i}")
    ax.set_xticks(np.arange(len(t3[t3["model"] == models[0]])) + w * (len(models) - 1) / 2)
    ax.set_xticklabels(t3[t3["model"] == models[0]]["factor"])
    ax.set_ylabel("samples whose outcome flips vs B0 (%)")
    ax.set_title("F2: flip rates (dashed = seed-to-seed baseline F_S)"); ax.legend(fontsize=7)
    fig.tight_layout(); p = rpath(cfg, "figures", "F2.pdf"); fig.savefig(p); plt.close(fig); out.append(str(p))

    # F3: tool-induced gate-count change
    gfs = T.get("_gf") or {}
    if gfs:
        fig, axs = plt.subplots(1, 2, figsize=(8, 3.5))
        for ax, (yf, yt) in zip(axs, [("Y0", "Y1"), ("Y0", "Y2")]):
            for m in models:
                d = M.tool_induced(gfs[m], yf, yt) * PP
                if len(d):
                    ax.hist(d, bins=30, alpha=0.5, label=m)
            ax.set_xlabel(f"cell-count change {yf}->{yt} (%)"); ax.legend(fontsize=7)
        fig.suptitle("F3: tool-induced gate-count change (passing B0 samples)")
        fig.tight_layout(); p = rpath(cfg, "figures", "F3.pdf"); fig.savefig(p); plt.close(fig); out.append(str(p))

    # F4: ranking gap vs seed noise
    if "T4" in T:
        t4 = T["T4"]
        fig, ax = plt.subplots(figsize=(7, 3.8))
        x = np.arange(len(t4))
        sig = np.sqrt(t4["sigma_seed_a_pp"] ** 2 + t4["sigma_seed_b_pp"] ** 2)
        ax.errorbar(x, t4["delta_ab_pp"], yerr=2 * sig, fmt="o", capsize=3)
        for xi, (d, rho) in enumerate(zip(t4["delta_ab_pp"], t4["reversal_prob"])):
            ax.annotate(f"rho={rho:.2f}", (xi, d), textcoords="offset points", xytext=(6, 6), fontsize=7)
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xticks(x); ax.set_xticklabels(t4["config"])
        ax.set_ylabel("pass@1(A) - pass@1(B) (pp)")
        ax.set_title("F4: model gap, +/-2*sqrt(sA^2+sB^2) band; rho = single-run reversal prob.", fontsize=9)
        fig.tight_layout(); p = rpath(cfg, "figures", "F4.pdf"); fig.savefig(p); plt.close(fig); out.append(str(p))
    return out


def run_report(cfg: dict) -> dict:
    T = build_tables(cfg)
    figs = build_figures(cfg, T)
    return {"tables": [k for k in T if not k.startswith("_")], "figures": figs}
