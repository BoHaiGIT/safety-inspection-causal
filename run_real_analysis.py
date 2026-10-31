"""
run_real_analysis.py —— 真实 OSHA 面板上的完整因果方法阶梯
=====================================================================
数据：data/real/osha_panel.csv（build_real_dataset.py 产出，N≈6万建筑企业）
结局：post_injury_rate = 下次检查的 serious 违规数（伤害的合规代理）
处理：inspected = 首检为 programmed(1) vs unprogrammed(0)

方法：
  1. 朴素 / 原始 DiD（post-pre）
  2. Value-added OLS（控制基线违规 + 协变量 + 地区/年份/NAICS FE）+ 自助 CI
  3. DML（econml LinearDML，discrete treatment）
  4. 因果森林（CausalForestDML）子组异质性（按 NAICS 2 位、规模）
  5. E-value 未测量混杂敏感性
输出：data/real/real_results.txt、real_results.json
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

PANEL = "data/real/osha_panel.csv"
OUT_TXT = "data/real/real_results.txt"
OUT_JSON = "data/real/real_results.json"
COVS = ["pre_injury_rate", "log_employees", "risk_score", "complaints", "unionized"]
FE = ["region", "index_year", "naics2"]


def design_matrix(p):
    X = pd.get_dummies(p[FE].astype(str), drop_first=True).astype(float)
    num = p[COVS].astype(float).copy()
    return pd.concat([num, X], axis=1).values, list(num.columns) + list(X.columns)


def e_value(rr):
    """VanderWeele 近似：给定风险比 RR(<1 用 1/RR)，返回 E-value。"""
    if rr is None or rr <= 0:
        return None
    r = rr if rr >= 1 else 1.0 / rr
    return r + np.sqrt(r * (r - 1.0))


def main():
    p = pd.read_csv(PANEL)
    lines, res = [], {}

    def log(s=""):
        print(s); lines.append(s)

    log("=" * 64)
    log("真实 OSHA 面板 —— 因果方法阶梯")
    log("=" * 64)
    log(f"N={len(p)}  处理组={p.inspected.mean():.1%}  "
        f"pre_mean={p.pre_injury_rate.mean():.3f}  post_mean={p.post_injury_rate.mean():.3f}")

    # ---- 1) 朴素 + 原始 DiD ----
    g = p.groupby("inspected").agg(pre=("pre_injury_rate", "mean"),
                                   post=("post_injury_rate", "mean"),
                                   n=("post_injury_rate", "size"))
    g["delta"] = g["post"] - g["pre"]
    naive = p.loc[p.inspected == 1, "post_injury_rate"].mean() - p.loc[p.inspected == 0, "post_injury_rate"].mean()
    did = g.loc[1, "delta"] - g.loc[0, "delta"]
    log("\n[1] 朴素/DiD")
    log(g.round(3).to_string())
    log(f"    朴素(post_t-post_c) = {naive:+.4f}")
    log(f"    原始DiD             = {did:+.4f}")

    # ---- 2) Value-added OLS + bootstrap ----
    Xv, names = design_matrix(p)
    Xv = np.column_stack([p["inspected"].astype(float).values, Xv])
    y = p["post_injury_rate"].values
    base = y.mean()
    coef = LinearRegression().fit(Xv, y).coef_[0]
    rng = np.random.default_rng(2026)
    bs = []
    for _ in range(500):
        i = rng.integers(0, len(p), len(p))
        bs.append(LinearRegression().fit(Xv[i], y[i]).coef_[0])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    rel = coef / base
    log("\n[2] Value-added OLS（控 pre + 协变量 + FE，500 自助）")
    log(f"    coef = {coef:+.4f}  95%CI [{lo:+.4f}, {hi:+.4f}]  相对 {rel*100:+.1f}%")
    log(f"    E-value(基于 RR≈{1+rel:.3f}) = {e_value(1+rel):.3f}")
    res["value_added_ols"] = {"coef": coef, "ci": [lo, hi], "rel_pct": rel * 100,
                              "e_value": e_value(1 + rel)}

    # ---- 3) DML（econml LinearDML）----
    try:
        from econml.dml import LinearDML
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        W, _ = design_matrix(p)
        T = p["inspected"].astype(int).values
        dml = LinearDML(
            model_y=RandomForestRegressor(n_estimators=200, min_samples_leaf=20, random_state=0, n_jobs=-1),
            model_t=RandomForestClassifier(n_estimators=200, min_samples_leaf=20, random_state=0, n_jobs=-1),
            discrete_treatment=True, cv=5, random_state=0)
        dml.fit(y, T, W=W)
        ate = float(dml.ate(X=None))
        try:
            ci = dml.ate_interval(X=None, alpha=0.05)
            lo_d, hi_d = float(ci[0]), float(ci[1])
        except Exception:
            lo_d = hi_d = float("nan")
        log("\n[3] DML（LinearDML，discrete treatment，5 折）")
        log(f"    ATE = {ate:+.4f}  95%CI [{lo_d:+.4f}, {hi_d:+.4f}]  相对 {ate/base*100:+.1f}%")
        res["dml_ate"] = {"ate": ate, "ci": [lo_d, hi_d], "rel_pct": ate / base * 100}
        globals()["_W"] = W
        globals()["_T"] = T
        globals()["_y"] = y
    except Exception as e:
        log(f"\n[3] DML 跳过：{e}")
        res["dml_ate"] = None

    # ---- 4) 因果森林异质性 ----
    try:
        from econml.dml import CausalForestDML
        W = globals()["_W"]; T = globals()["_T"]
        cf = CausalForestDML(discrete_treatment=True, n_estimators=300,
                             min_samples_leaf=40, cv=5, random_state=0, n_jobs=-1)
        cf.fit(y, T, W=W)
        # 子组：按 NAICS 2 位、按规模中位数
        Xn = p[["log_employees"]].values
        eff = cf.effect(X=Xn, T0=0, T1=1)
        p2 = p.assign(eff=eff)
        log("\n[4] 因果森林异质性（集团平均效应）")
        by_naics = p2.groupby("naics2")["eff"].agg(["mean", "size"]).sort_values("size", ascending=False).head(6)
        for idx, row in by_naics.iterrows():
            log(f"    NAICS {idx}: ATE={row['mean']:+.4f}  (n={int(row['size'])})")
        med = p2["log_employees"].median()
        sm = p2[p2.log_employees <= med]["eff"].mean()
        lg = p2[p2.log_employees > med]["eff"].mean()
        log(f"    小企业(≤中位规模): ATE={sm:+.4f} | 大企业: ATE={lg:+.4f}")
        res["forest_heterogeneity"] = {
            "by_naics": {str(i): float(r["mean"]) for i, r in by_naics.iterrows()},
            "small": float(sm), "large": float(lg)}
    except Exception as e:
        log(f"\n[4] 因果森林跳过：{e}")
        res["forest_heterogeneity"] = None

    # ---- 5) 结论 ----
    log("\n" + "=" * 64)
    log("结论：programmed 检查对下次 serious 违规数的影响")
    log(f"  首选估计（Value-added OLS）: {coef:+.4f}（相对 {rel*100:+.1f}%, "
        f"95%CI [{lo:+.4f},{hi:+.4f}]）")
    log("  口径说明：结局为 serious 违规（S/W/R）——安全合规绩效代理；")
    log("            OSHA 企业级伤害计数（ITA 300A）不在公开执法库，故不做伤害率断言。")
    log("=" * 64)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=float)
    print(f"\nsaved -> {OUT_TXT}, {OUT_JSON}")


if __name__ == "__main__":
    main()
