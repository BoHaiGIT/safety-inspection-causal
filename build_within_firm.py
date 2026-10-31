# -*- coding: utf-8 -*-
"""
build_within_firm.py — 企业内（固定效应）识别设计
=====================================================================
动机：横截面 V-A OLS 估计在安慰剂检验中失败（next_programmed 显著预测结局），
      说明存在强持续性企业异质性（高违规企业系统性被 targeted）。
      企业固定效应可吸收这种不随时间变化的异质性。

设计：
  对每家企业的连续检查对 (k, k+1)：
    treat_k  = 第 k 次检查为 programmed（H/I/K）=1，unprogrammed=0
    y_{k+1}  = 第 k+1 次检查发现的 serious 违规数（结局）
    pre_k    = 第 k 次检查的 serious 违规数（基线）
  估计：y_{k+1} ~ treat_k + pre_k + gap + year FE + firm FE
  识别变异：同一企业内 programmed / unprogrammed 检查类型的切换（switcher design）
  推断：按企业聚类 bootstrap（重抽企业）

输出：data/real/osha_transitions.csv、data/real/within_firm_results.txt/.json
"""
from __future__ import annotations
import json
import os
import numpy as np
import pandas as pd

from build_real_dataset import load_inspections, load_violation_agg

OUT_DIR = "data/real"
os.makedirs(OUT_DIR, exist_ok=True)
RNG = np.random.default_rng(2026)

log_lines = []


def log(s=""):
    print(s, flush=True)
    log_lines.append(str(s))


def build_transitions():
    ins = load_inspections()
    sel = ins[ins["is_const"] & (ins["year"] >= 2010) & (ins["year"] <= 2019) & ins["name_ok"]].copy()
    sel = sel[(sel["programmed"] == 1) | (sel["unprogrammed"] == 1)]
    vagg = load_violation_agg()
    sel = sel.merge(vagg, left_on="activity_nr", right_index=True, how="left")
    sel[["n_viol", "n_serious", "penalty"]] = sel[["n_viol", "n_serious", "penalty"]].fillna(0.0)
    sel = sel.sort_values(["est_key", "open_date"]).reset_index(drop=True)
    sel["seq"] = sel.groupby("est_key").cumcount()
    sel["n_insp"] = sel.groupby("est_key")["seq"].transform("max") + 1

    cur = sel.copy()
    nxt = sel.copy()
    nxt["seq"] = nxt["seq"] - 1
    m = cur.merge(nxt, on=["est_key", "seq"], suffixes=("", "_nx"))
    m = m[m["est_key"].isin(sel.loc[sel["n_insp"] >= 2, "est_key"].unique())]
    m["gap_years"] = (pd.to_datetime(m["open_date_nx"]) - pd.to_datetime(m["open_date"])).dt.days / 365.25
    m = m[m["gap_years"] >= 0]

    d = pd.DataFrame({
        "estab": m["est_key"].values,
        "treat": m["programmed"].astype(int).values,
        "pre": m["n_serious"].astype(float).values,
        "post": m["n_serious_nx"].astype(float).values,
        "pre_n_viol": m["n_viol"].astype(float).values,
        "post_n_viol": m["n_viol_nx"].astype(float).values,
        "pre_penalty": m["penalty"].astype(float).values,
        "post_penalty": m["penalty_nx"].astype(float).values,
        "gap_years": m["gap_years"].values,
        "year": m["year"].values,
        "naics2": m["naics2"].values,
        "state": m["site_state"].values,
        "region": m["region"].values,
        "log_employees": np.log1p(pd.to_numeric(m["nr_in_estab"], errors="coerce").clip(lower=0).fillna(0)).values,
        "unionized": m["unionized"].astype(int).values,
        "seq": m["seq"].values,
        "n_insp": m["n_insp"].values,
    })
    d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=["pre", "post", "gap_years"]).reset_index(drop=True)
    return d


def demean_by(M, grp):
    """FWL: demean columns of M by group id (firm)."""
    M = np.asarray(M, dtype=np.float64)
    if M.ndim == 1:
        M = M[:, None]
    g = pd.factorize(grp)[0]
    G = g.max() + 1
    cnt = np.bincount(g, minlength=G).astype(float)
    cnt = np.where(cnt == 0, 1, cnt)
    out = np.empty_like(M)
    for j in range(M.shape[1]):
        s = np.bincount(g, weights=M[:, j], minlength=G)
        out[:, j] = M[:, j] - (s / cnt)[g]
    return out


def cluster_robust(X, y, firms):
    """OLS coefficient on col 0 with CR1 cluster-robust SE (analytic, fast)."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64).ravel()
    XtX = X.T @ X
    XtXinv = np.linalg.pinv(XtX)
    beta = XtXinv @ (X.T @ y)
    e = y - X @ beta
    # cluster sums of score contributions: S_g = sum_i x_i e_i
    g = pd.factorize(firms)[0]
    G = g.max() + 1
    k = X.shape[1]
    scores = X * e[:, None]
    S = np.zeros((G, k))
    for j in range(k):
        S[:, j] = np.bincount(g, weights=scores[:, j], minlength=G)
    meat = S.T @ S
    n = len(y)
    c = (G / max(G - 1, 1)) * ((n - 1) / max(n - k, 1))
    V = XtXinv @ meat @ XtXinv * c
    se = float(np.sqrt(max(V[0, 0], 0.0)))
    coef = float(beta[0])
    return coef, coef - 1.96 * se, coef + 1.96 * se, se, int(G)


d = build_transitions()
log("=" * 82)
log("WITHIN-FIRM (FIXED-EFFECTS) IDENTIFICATION — real OSHA construction transitions")
log("=" * 82)
log(f"transitions (firm x consecutive inspection pair): {len(d):,}")
log(f"unique establishments: {d.estab.nunique():,}")
log(f"treated share (inspection k programmed): {100*d.treat.mean():.1f}%")
log(f"pre mean={d.pre.mean():.3f}  post mean={d.post.mean():.3f}")

# --- identifying variation: firms with BOTH inspection types
g = d.groupby("estab")["treat"].agg(["mean", "size"])
switchers = g[(g["mean"] > 0) & (g["mean"] < 1)].index
dw = d[d.estab.isin(switchers)].reset_index(drop=True)
log(f"\n[switcher subsample] firms with BOTH programmed and unprogrammed inspections: {len(switchers):,} "
    f"({100*len(switchers)/d.estab.nunique():.1f}% of firms)")
log(f"  transitions in switcher sample: {len(dw):,}   treated share {100*dw.treat.mean():.1f}%")
log(f"  firms with >=2 transitions: {int((dw.groupby('estab').size()>=2).sum()):,}")

results = {}


def run(tag, df, fe=True, outcome="post", extra=None):
    df = df.copy()
    y = df[outcome].values.astype(np.float64)
    cols = [df["treat"].astype(float).values, df["pre"].astype(float).values,
            df["gap_years"].astype(float).values]
    names = ["treat", "pre", "gap"]
    # year dummies
    yd = pd.get_dummies(df["year"].astype(str), prefix="y", drop_first=True).astype(float).values
    cols.append(yd)
    if extra:
        cols.append(pd.get_dummies(df[extra].astype(str), drop_first=True).astype(float).values)
    X = np.column_stack(cols)
    if fe:
        X = demean_by(X, df["estab"].values)
        y = demean_by(y, df["estab"].values).ravel()
    c, lo, hi, se, ng = cluster_robust(X, y, df["estab"].values)
    base = df[outcome].mean()
    rel = 100 * c / base if base else float("nan")
    sig = "SIG" if (lo < 0 and hi < 0) or (lo > 0 and hi > 0) else "n.s."
    log(f"  {tag:52s} coef={c:+.4f} se={se:.4f} CI[{lo:+.4f},{hi:+.4f}] rel={rel:+6.1f}% n={len(df):>7d} G={ng:>6d}  {sig}")
    return dict(tag=tag, coef=c, se=se, lo=lo, hi=hi, rel=rel, n=int(len(df)),
                clusters=ng, sig=sig, rf=float(1 + c / base) if base else None)


log("\n[1] Pooled OLS (no firm FE) — same sample, for comparison")
results["pooled_all"] = run("pooled OLS, all transitions", d, fe=False)
results["pooled_sw"] = run("pooled OLS, switcher sample", dw, fe=False)

log("\n[2] Firm fixed effects (the decisive test)")
results["fe_all"] = run("firm FE, all transitions", d, fe=True)
results["fe_sw"] = run("firm FE, switcher sample", dw, fe=True)
results["fe_sw_recency"] = run("firm FE, switcher, + state dummies", dw, fe=True, extra="state")

log("\n[3] Firm FE, alternative outcomes (switcher sample)")
results["fe_sw_allviol"] = run("firm FE: all violations (count)", dw, fe=True, outcome="post_n_viol")
results["fe_sw_penalty"] = run("firm FE: total penalty $", dw, fe=True, outcome="post_penalty")
dw["post_any"] = (dw["post"] > 0).astype(float)
results["fe_sw_any"] = run("firm FE: P(any serious violation)", dw, fe=True, outcome="post_any")

log("\n[4] Placebo within firm: does a FUTURE programmed inspection predict the")
log("    outcome, conditional on firm FE? (should be null if FE absorbs heterogeneity)")
d2 = d.copy()
nx = d.groupby("estab")["treat"].shift(-1)
d2["placebo_treat"] = nx
d2 = d2.dropna(subset=["placebo_treat"]).reset_index(drop=True)
sw2 = set(d2.estab) 
dw2 = d2[d2.estab.isin(set(dw.estab))].reset_index(drop=True)
d2["treat_orig"] = d2["treat"]
d2["treat"] = d2["placebo_treat"]
results["fe_placebo"] = run("firm FE, placebo = NEXT programmed", d2, fe=True)
log(f"  (placebo sample n={len(d2):,})")

log("\n[5] E-value for the firm-FE estimate")
def e_value(rr):
    rr = 1 / rr if rr < 1 else rr
    return rr + np.sqrt(rr * (rr - 1))
rr = results["fe_sw"]["rf"]
if rr:
    log(f"  firm FE switcher: RR={rr:.4f} -> E-value={e_value(rr):.3f}")
    results["e_value_fe_sw"] = float(e_value(rr))

log("\n" + "=" * 82)
log("SUMMARY")
log("=" * 82)
for k, v in results.items():
    if isinstance(v, dict):
        log(f"{v['tag'][:52]:52s} {v['coef']:+9.4f} {v['rel']:+7.1f}%  {v['sig']}")

d.to_csv(os.path.join(OUT_DIR, "osha_transitions.csv"), index=False)
with open(os.path.join(OUT_DIR, "within_firm_results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
with open(os.path.join(OUT_DIR, "within_firm_results.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))
log("\nsaved -> data/real/osha_transitions.csv + within_firm_results.{json,txt}")
