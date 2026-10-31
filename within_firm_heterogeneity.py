# -*- coding: utf-8 -*-
"""
within_firm_heterogeneity.py — 企业固定效应设计下的异质性与描述统计
输入：data/real/osha_transitions.csv（由 build_within_firm.py 生成）
输出：data/real/within_firm_hetero.txt/.json
"""
import json
import os
import numpy as np
import pandas as pd

OUT = "data/real"
d = pd.read_csv(os.path.join(OUT, "osha_transitions.csv"))
lines = []


def log(s=""):
    print(s, flush=True)
    lines.append(str(s))


def demean_by(M, grp):
    M = np.asarray(M, dtype=np.float64)
    if M.ndim == 1:
        M = M[:, None]
        one = True
    else:
        one = False
    g = pd.factorize(grp)[0]
    G = g.max() + 1
    cnt = np.bincount(g, minlength=G).astype(float)
    cnt = np.where(cnt == 0, 1, cnt)
    out = np.empty_like(M)
    for j in range(M.shape[1]):
        s = np.bincount(g, weights=M[:, j], minlength=G)
        out[:, j] = M[:, j] - (s / cnt)[g]
    return out.ravel() if one else out


def cluster_robust(X, y, firms):
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64).ravel()
    XtXinv = np.linalg.pinv(X.T @ X)
    beta = XtXinv @ (X.T @ y)
    e = y - X @ beta
    g = pd.factorize(firms)[0]
    G = g.max() + 1
    k = X.shape[1]
    scores = X * e[:, None]
    S = np.zeros((G, k))
    for j in range(k):
        S[:, j] = np.bincount(g, weights=scores[:, j], minlength=G)
    c = (G / max(G - 1, 1)) * ((len(y) - 1) / max(len(y) - k, 1))
    V = XtXinv @ (S.T @ S) @ XtXinv * c
    se = float(np.sqrt(max(V[0, 0], 0.0)))
    return float(beta[0]), se, int(G)


def fe_estimate(df, outcome="post", label=""):
    df = df.reset_index(drop=True)
    y = df[outcome].values.astype(np.float64)
    X = np.column_stack([
        df["treat"].astype(float).values,
        df["pre"].astype(float).values,
        df["gap_years"].astype(float).values,
        pd.get_dummies(df["year"].astype(str), drop_first=True).astype(float).values,
    ])
    X = demean_by(X, df["estab"].values)
    y = demean_by(y, df["estab"].values)
    c, se, G = cluster_robust(X, y, df["estab"].values)
    lo, hi = c - 1.96 * se, c + 1.96 * se
    base = df[outcome].mean()
    rel = 100 * c / base if base else float("nan")
    sig = "SIG" if (lo < 0 and hi < 0) or (lo > 0 and hi > 0) else "n.s."
    log(f"  {label:34s} coef={c:+.4f} se={se:.4f} CI[{lo:+.4f},{hi:+.4f}] rel={rel:+6.1f}% "
        f"n={len(df):>7d} firms={G:>6d}  {sig}")
    return dict(label=label, coef=c, se=se, lo=lo, hi=hi, rel=rel, n=int(len(df)),
                firms=G, sig=sig)


log("=" * 88)
log("WITHIN-FIRM HETEROGENEITY & DESCRIPTIVES")
log("=" * 88)

# ---------------- descriptives for the data section
log("\n[DESCRIPTIVES]")
log(f"  establishments: {d.estab.nunique():,}")
log(f"  inspection transitions: {len(d):,}")
g = d.groupby("estab").size()
log(f"  transitions per establishment: mean={g.mean():.2f} median={int(g.median())} max={int(g.max())}")
log(f"  inspections per establishment (n_insp): mean={d.groupby('estab')['n_insp'].max().mean():.2f}")
log(f"  treated share (inspection k programmed): {100*d.treat.mean():.1f}%")
log(f"  serious violations at k : mean={d.pre.mean():.3f} sd={d.pre.std():.3f} "
    f"share zero={100*(d.pre==0).mean():.1f}%")
log(f"  serious violations at k+1: mean={d.post.mean():.3f} sd={d.post.std():.3f} "
    f"share zero={100*(d.post==0).mean():.1f}%")
log(f"  gap between inspections (years): mean={d.gap_years.mean():.2f} median={d.gap_years.median():.2f}")
log(f"  calendar years: {int(d.year.min())}-{int(d.year.max())}")
log(f"  firms with both inspection types: {int((d.groupby('estab').treat.nunique()==2).sum()):,}")
log(f"  firms observed only programmed: {int((d.groupby('estab').treat.max()==1).sum()):,}")

# treated vs control raw pattern
log("\n  raw pattern (transition level):")
for t in (0, 1):
    s = d[d.treat == t]
    log(f"    {'programmed' if t else 'unprogrammed':14s} n={len(s):>7d}  pre={s.pre.mean():.3f}  "
        f"post={s.post.mean():.3f}  delta={s.post.mean()-s.pre.mean():+.3f}")

results = {}

# ---------------- heterogeneity (firm FE)
log("\n[HETEROGENEITY — firm FE, outcome = serious violations at next inspection]")
med = d.log_employees.median()
results["all"] = fe_estimate(d, label="all transitions")
results["small"] = fe_estimate(d[d.log_employees <= med], label=f"small firms (<= median emp)")
results["large"] = fe_estimate(d[d.log_employees > med], label=f"large firms (> median emp)")

log("\n  by baseline violation load:")
results["pre0"] = fe_estimate(d[d.pre == 0], label="clean record (pre = 0)")
results["prepos"] = fe_estimate(d[d.pre > 0], label="violations found (pre > 0)")

log("\n  by NAICS 2-digit (largest groups):")
for k in d.naics2.value_counts().head(4).index:
    results[f"naics_{k}"] = fe_estimate(d[d.naics2 == k], label=f"NAICS {k}")

log("\n  by gap length:")
results["gap_short"] = fe_estimate(d[d.gap_years <= 1], label="gap <= 1 year")
results["gap_long"] = fe_estimate(d[d.gap_years > 1], label="gap > 1 year")

log("\n  by union status:")
results["nonunion"] = fe_estimate(d[d.unionized == 0], label="non-union")
results["union"] = fe_estimate(d[d.unionized == 1], label="union")

log("\n  by period:")
results["early"] = fe_estimate(d[d.year <= 2014], label="2010-2014")
results["late"] = fe_estimate(d[d.year >= 2015], label="2015-2019")

with open(os.path.join(OUT, "within_firm_hetero.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
with open(os.path.join(OUT, "within_firm_hetero.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
log("\nsaved -> data/real/within_firm_hetero.{json,txt}")
