# -*- coding: utf-8 -*-
"""
Robustness / falsification battery for the real OSHA enforcement panel (fast version).

Interrogates the tension between raw DiD ~ 0 and value-added OLS / DML ~ -4~5%.

  R1  Common support (trim on pre-injury rate) -> DiD and V-A OLS
  R2  State x year fixed effects via FWL demeaning (absorbs state-plan heterogeneity)
  R3  Propensity-score matching 1:1 (caliper) -> post-match DiD / V-A + balance
  R4  Placebo treatment: "next inspection is programmed" as a fake treatment
  R5  Alternative outcomes: total penalty $, all-violation count (negative controls)
  R6  Extensive margin: P(any serious violation at next inspection)
  R7  AIPW (doubly robust, cross-fitted GBM)
"""
import json
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold

RNG = np.random.default_rng(2026)
PANEL = "data/real/osha_panel.csv"
COVS = ["pre_injury_rate", "log_employees", "risk_score", "complaints", "unionized"]
N_BOOT = 300

out_lines = []


def log(s=""):
    print(s, flush=True)
    out_lines.append(str(s))
    with open("data/real/robustness_results.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out_lines))


def build_X(df, treat_col="inspected", extra_dummies=None):
    """Compact design: [treatment] + covariates + FE dummies. Returns float array."""
    d = df.copy()
    fe = ["region", "index_year", "naics2"]
    frames = [d[[treat_col] + COVS].astype(float)]
    for c in fe:
        frames.append(pd.get_dummies(d[c].astype(str), prefix=c, drop_first=True).astype(float))
    if extra_dummies:
        frames.append(extra_dummies.astype(float))
    return pd.concat(frames, axis=1).values.astype(np.float64)


def ols_t(X, y):
    """Coefficient on column 0 (treatment) via least squares."""
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef[0]


def boot(X, y, n_boot=N_BOOT):
    coef = ols_t(X, y)
    bs = np.empty(n_boot)
    n = len(y)
    for b in range(n_boot):
        idx = RNG.integers(0, n, n)
        bs[b] = ols_t(X[idx], y[idx])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(coef), float(lo), float(hi)


def report(tag, coef, lo, hi, base, n):
    rel = 100 * coef / base if base else float("nan")
    sig = "SIG" if (lo < 0 and hi < 0) or (lo > 0 and hi > 0) else "n.s."
    log(f"  {tag:46s} coef={coef:+.4f} CI[{lo:+.4f},{hi:+.4f}] rel={rel:+6.1f}% n={n:>6d}  {sig}")
    return dict(tag=tag, coef=coef, lo=lo, hi=hi, rel=rel, n=int(n), sig=sig)


def did_raw(df, y="post_injury_rate", pre="pre_injury_rate"):
    g = df.groupby("inspected").agg(p=(pre, "mean"), q=(y, "mean"))
    return float((g.loc[1, "q"] - g.loc[1, "p"]) - (g.loc[0, "q"] - g.loc[0, "p"]))


results = {}
p = pd.read_csv(PANEL)
y_main = p["post_injury_rate"].values.astype(np.float64)
base_rate = float(y_main.mean())
Xb = build_X(p)

log("=" * 82)
log("ROBUSTNESS BATTERY — real OSHA construction enforcement panel (2010-2019)")
log("=" * 82)
log(f"N={len(p)}  treated={100*p.inspected.mean():.1f}%  post mean={base_rate:.3f}  pre mean={p.pre_injury_rate.mean():.3f}")

# ------------------------------------------------------------------ baseline
log("\n[BASELINE]")
c, lo, hi = boot(Xb, y_main)
results["baseline_va"] = report("V-A OLS (pre+covs+region/year/naics FE)", c, lo, hi, base_rate, len(p))
results["baseline_did"] = dict(tag="raw DiD (no adjustment)", coef=did_raw(p), rel=float("nan"))
log(f"  {'raw DiD (no covariate adjustment)':46s} coef={did_raw(p):+.4f}")
log(f"  {'naive (post_t - post_c)':46s} coef="
    f"{p.loc[p.inspected==1,'post_injury_rate'].mean()-p.loc[p.inspected==0,'post_injury_rate'].mean():+.4f}")

# ------------------------------------------------------- R1 common support
log("\n[R1] Common support — trim pre-injury rate to shared [0, P90]")
q90 = p["pre_injury_rate"].quantile(0.90)
sub = p[p["pre_injury_rate"] <= q90].copy()
log(f"  trim at pre<={q90:.0f}: n={len(sub)} (dropped {len(p)-len(sub)})")
log(f"  pre mean: treated={sub.loc[sub.inspected==1,'pre_injury_rate'].mean():.3f}  "
    f"control={sub.loc[sub.inspected==0,'pre_injury_rate'].mean():.3f}")
Xs, ys = build_X(sub), sub["post_injury_rate"].values.astype(np.float64)
c, lo, hi = boot(Xs, ys)
results["trim_va"] = report("V-A OLS, trimmed sample", c, lo, hi, ys.mean(), len(sub))
results["trim_did"] = dict(tag="raw DiD, trimmed", coef=did_raw(sub), rel=float("nan"))
log(f"  {'raw DiD, trimmed sample':46s} coef={did_raw(sub):+.4f}")

# --------------------------------------------- R2 state x year (FWL demean)
log("\n[R2] State x year fixed effects (FWL within-group demeaning)")
sy = (p["state"].astype(str) + "_" + p["index_year"].astype(str))
grp = pd.factorize(sy)[0]
G = grp.max() + 1
cnt = np.bincount(grp, minlength=G).astype(float)
cnt_safe = np.where(cnt == 0, 1, cnt)


def demean(M):
    M = np.asarray(M, dtype=np.float64)
    one = M.ndim == 1
    if one:
        M = M[:, None]
    out = np.empty_like(M)
    for j in range(M.shape[1]):
        sums = np.bincount(grp, weights=M[:, j], minlength=G)
        out[:, j] = M[:, j] - (sums / cnt_safe)[grp]
    return out[:, 0] if one else out


X_dm = demean(Xb)
y_dm = demean(y_main)
# treatment column is demeaned too -> coefficient is the within state-year effect
c, lo, hi = boot(X_dm, y_dm)
results["stateyear_va"] = report("V-A OLS + state x year FE (demeaned)", c, lo, hi, base_rate, len(p))
log(f"  state x year cells: {G}")

# -------------------------------------------------------- R3 PSM then DiD
log("\n[R3] Propensity-score matching 1:1 (GBM propensity, caliper 0.2 sd of logit)")
Xp = StandardScaler().fit_transform(p[COVS].astype(float).values)
tvec = p["inspected"].values.astype(int)
ps = GradientBoostingClassifier(random_state=0, n_estimators=120, max_depth=3).fit(Xp, tvec).predict_proba(Xp)[:, 1]
p3 = p.copy()
p3["logit"] = np.log(np.clip(ps, 1e-6, 1 - 1e-6) / (1 - np.clip(ps, 1e-6, 1 - 1e-6)))
tr, ct = p3[p3.inspected == 1], p3[p3.inspected == 0]
cal = 0.2 * p3["logit"].std()
nn = NearestNeighbors(n_neighbors=1).fit(ct[["logit"]].values)
dist, idx = nn.kneighbors(tr[["logit"]].values)
ok = dist[:, 0] <= cal
pm = pd.concat([tr[ok], ct.iloc[idx[ok, 0]]], ignore_index=True)
log(f"  propensity AUC proxy: mean ps treated={ps[tvec==1].mean():.3f} control={ps[tvec==0].mean():.3f}")
log(f"  matched pairs={len(pm)//2}; discarded {len(tr)-int(ok.sum())} of {len(tr)} treated")
for v in COVS:
    mt, mc = pm.loc[pm.inspected == 1, v].astype(float), pm.loc[pm.inspected == 0, v].astype(float)
    s = np.sqrt((mt.var() + mc.var()) / 2)
    smd = 0.0 if s == 0 else (mt.mean() - mc.mean()) / s
    log(f"    SMD {v:18s} {smd:+.3f}")
results["psm_did"] = dict(tag="PSM(1:1) then DiD", coef=did_raw(pm), rel=float("nan"), n=len(pm))
log(f"  {'PSM-matched DiD':46s} coef={did_raw(pm):+.4f} n={len(pm)}")
Xm, ym = build_X(pm), pm["post_injury_rate"].values.astype(np.float64)
c, lo, hi = boot(Xm, ym)
results["psm_va"] = report("PSM-matched V-A OLS", c, lo, hi, ym.mean(), len(pm))

# --------------------------------------------------- R4 placebo treatment
log("\n[R4] Placebo treatment — 'next inspection is programmed' as fake treatment")
log("     A future treatment must NOT predict the post outcome, conditional on pre + covariates.")
Xpl = Xb.copy()
Xpl[:, 0] = p["next_programmed"].astype(float).values
c, lo, hi = boot(Xpl, y_main)
results["placebo_treat"] = report("placebo: next_programmed -> post violations", c, lo, hi, base_rate, len(p))

# --------------------------------- R5 alternative / negative-control outcomes
log("\n[R5] Alternative outcomes (same treatment, same controls)")
for col, label in [("post_penalty", "total penalty $ at next inspection"),
                   ("post_n_viol", "all violations (count) at next inspection")]:
    yv = p[col].values.astype(np.float64)
    c, lo, hi = boot(Xb, yv)
    results[f"alt_{col}"] = report(f"V-A OLS: {label}", c, lo, hi, yv.mean(), len(p))

# ----------------------------------------------------- R6 extensive margin
log("\n[R6] Extensive vs intensive margin")
p["post_any"] = (p["post_injury_rate"] > 0).astype(float)
ya = p["post_any"].values.astype(np.float64)
c, lo, hi = boot(Xb, ya)
results["ext_any"] = report("V-A OLS: P(any serious violation) [LPM]", c, lo, hi, ya.mean(), len(p))
log(f"  base rate: treated={p.loc[p.inspected==1,'post_any'].mean():.3f}  "
    f"control={p.loc[p.inspected==0,'post_any'].mean():.3f}")

# --------------------------------------------------------------- R7 AIPW
log("\n[R7] AIPW (doubly robust, 5-fold cross-fitted GBM)")
Xa = Xb[:, 1:]  # covariates + dummies, no treatment
Ta, Ya = tvec, y_main
kf = KFold(n_splits=5, shuffle=True, random_state=2026)
mu1 = np.zeros(len(p)); mu0 = np.zeros(len(p)); e = np.zeros(len(p))
for tr_i, te_i in kf.split(Xa):
    m1 = GradientBoostingRegressor(random_state=0, n_estimators=150, max_depth=3).fit(Xa[tr_i][Ta[tr_i] == 1], Ya[tr_i][Ta[tr_i] == 1])
    m0 = GradientBoostingRegressor(random_state=0, n_estimators=150, max_depth=3).fit(Xa[tr_i][Ta[tr_i] == 0], Ya[tr_i][Ta[tr_i] == 0])
    mu1[te_i] = m1.predict(Xa[te_i])
    mu0[te_i] = m0.predict(Xa[te_i])
    e[te_i] = GradientBoostingClassifier(random_state=0, n_estimators=120, max_depth=3) \
        .fit(Xa[tr_i], Ta[tr_i]).predict_proba(Xa[te_i])[:, 1]
e = np.clip(e, 0.02, 0.98)
psi = mu1 - mu0 + Ta * (Ya - mu1) / e - (1 - Ta) * (Ya - mu0) / (1 - e)
aipw = float(psi.mean())
bs = np.array([psi[RNG.integers(0, len(psi), len(psi))].mean() for _ in range(500)])
lo, hi = np.percentile(bs, [2.5, 97.5])
results["aipw"] = report("AIPW (cross-fitted GBM, doubly robust)", aipw, lo, hi, base_rate, len(p))

# ------------------------------------------------------------- E-values
def e_value(rr):
    rr = 1 / rr if rr < 1 else rr
    return rr + np.sqrt(rr * (rr - 1))


log("\n[E-value]")
for key in ["baseline_va", "aipw"]:
    if key in results:
        rr = 1 + results[key]["coef"] / base_rate
        results[f"e_value_{key}"] = float(e_value(rr))
        log(f"  {results[key]['tag']:46s} RR={rr:.4f}  E-value={e_value(rr):.3f}")

# ------------------------------------------------------------------ save
log("\n" + "=" * 82)
log("SUMMARY")
log("=" * 82)
log(f"{'check':50s} {'coef':>9s} {'rel':>8s}  verdict")
for k, v in results.items():
    if isinstance(v, dict) and "coef" in v:
        rel = v.get("rel", float("nan"))
        rel_s = f"{rel:+7.1f}%" if isinstance(rel, float) and not np.isnan(rel) else "      -"
        log(f"{v['tag'][:50]:50s} {v['coef']:+9.4f} {rel_s}  {v.get('sig','')}")

with open("data/real/robustness_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
log("\nsaved -> data/real/robustness_results.json + .txt")
