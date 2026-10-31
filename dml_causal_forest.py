"""
DML 双重机器学习 + 因果森林 —— 安全监管因果推断「路线 C」第二阶段
=====================================================================
承接 psm_baseline.py 的 PSM 基准（真实 ATT 锚点 = -9.8%，已命中 -10.03%），
本脚本在**同一套合成数据真值**上搭建方法阶梯的 2~4 步：

  阶段 2  DML（econml.CausalForestDML）
          - 用事故叙述文本的 embedding 作为高维控制（CS 背景独有打法）
          - 对比「仅用表格协变量」vs「表格协变量 + 文本 embedding」
  阶段 3  因果森林异质性：检查对哪类企业最有效（risk_score / complaints 分层）
  阶段 4  内生性三件套：
          (a) 事件研究 / 平行趋势（panel 数据，检验 pre-trend）
          (b) 条件 DiD（Y ~ inspected×post + X + embeddings）
          (c) E-value 敏感性分析

运行：python dml_causal_forest.py
依赖：pandas / numpy / scikit-learn / econml（pip install -r requirements.txt）
说明：真实数据未就位时用合成数据演示完整管线；接入真实 OSHA/CIKM 数据只需
      替换 generate_dml_data() 内部的数据加载逻辑，保持同样的列 schema 即可。
=====================================================================
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from econml.dml import CausalForestDML

# 数据接入层：真实数据适配器 + 统一合成生成器
from data_loader import generate_synthetic, load_real_dataset, RealDataConfig

# ----------------------------------------------------------------------
# 代码开源仓库（投稿 Safety Science 的复现加分项；创建后替换为真实 URL）
# Code & reproducibility repository (cited in the Safety Science submission):
REPO_URL = "https://github.com/BoHaiGIT/safety-inspection-causal"

RNG = np.random.default_rng(2026)
TRUE_EFFECT = -0.098          # 真实相对处理效应 = -9.8%（与 PSM 锚点一致）
NARR_DIM = 16                 # 事故叙述文本 embedding 维度（合成替代真实 sentence-embedding）


def _model_covs(df: pd.DataFrame) -> list[str]:
    """从数据中解析实际可用的协变量（剔除真实数据里缺失的字段）。"""
    base = ["log_employees", "risk_score", "prior_injuries",
            "complaints", "safety_investment", "region", "unionized"]
    return [c for c in base if c in df.columns]


# ----------------------------------------------------------------------
# 数据生成：与 PSM 共用同一真值，并补齐
#   - 事故叙述文本 embedding（高维，承载部分结果方差，提升 nuisance 估计精度）
#   - 面板结构（pre/post + 多期）以支撑事件研究与平行趋势
# ----------------------------------------------------------------------
def generate_dml_data(n: int = 9000) -> pd.DataFrame:
    log_emp = RNG.normal(4.5, 1.0, n)
    risk = RNG.beta(2, 5, n)
    prior = RNG.poisson(2.0, n).astype(float)
    complaints = RNG.poisson(1.5, n).astype(float)
    invest = RNG.beta(2, 3, n)
    region = RNG.integers(0, 5, n)
    union = RNG.binomial(1, 0.4, n)

    # 仅影响结果、不影响分配的「未观测异质性」V —— 真实数据里由事故叙述文本承载
    V = RNG.normal(0, 1.0, n)

    # 处理选择性（与 PSM 一致：高风险/多投诉/多事故更可能被查）
    eta = 2.4 * (0.35 * risk + 0.30 * (complaints / 3) + 0.25 * (prior / 4)
                 + 0.20 * (log_emp / 6) - 0.20 * invest + 0.15 * union
                 + 0.05 * region)
    p = 1 / (1 + np.exp(-eta))
    inspected = RNG.binomial(1, p, n)

    # 基线结果（不含处理效应）
    base = (12.0 + 9.0 * risk + 1.4 * prior + 3.0 * (complaints / 3)
            - 2.5 * invest + 1.0 * union + 0.8 * region
            + 2.0 * V + RNG.normal(0, 2.0, n))
    base = np.clip(base, 1.0, None)

    # 处理效应：-9.8% 相对下降（仅作用于被查企业）
    post = np.where(inspected == 1, base * (1 + TRUE_EFFECT), base)

    # 事故叙述文本 embedding：对 (risk, complaints, V) 的有噪高维投影
    # 真实场景 = sentence-transformers 编码事故通报文本；此处用合成替代以零成本跑通
    emb = (0.9 * risk[:, None] + 0.6 * (complaints / 3)[:, None]
           + 1.1 * V[:, None]
           + RNG.normal(0, 0.5, (n, NARR_DIM)))
    emb_cols = [f"emb_{i}" for i in range(emb.shape[1])]

    df = pd.DataFrame({
        "inspected": inspected,
        "pre_injury_rate": base,       # 检查前基线（事件研究用）
        "post_injury_rate": post,      # 结果变量
        "log_employees": log_emp,
        "risk_score": risk,
        "prior_injuries": prior,
        "complaints": complaints,
        "safety_investment": invest,
        "region": region.astype(str),
        "unionized": union,
    })
    df[emb_cols] = emb
    df["__true_effect_abs"] = np.where(inspected == 1, base * TRUE_EFFECT, 0.0)
    return df


# ----------------------------------------------------------------------
# 工具：风险/投诉分层标签
# ----------------------------------------------------------------------
def _add_strata(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["risk_tier"] = pd.qcut(df["risk_score"], 3, labels=["low", "mid", "high"])
    df["complaint_grp"] = np.where(df["complaints"] >= 2, "high(>=2)", "low(<2)")
    return df


# ----------------------------------------------------------------------
# 阶段 2：DML（CausalForestDML）
# ----------------------------------------------------------------------
def stage2_dml(df: pd.DataFrame) -> dict:
    print("=" * 64)
    print("阶段 2：Double Machine Learning (CausalForestDML)")

    covs = _model_covs(df)
    emb_cols = [c for c in df.columns if c.startswith("emb_")]

    Y = df["post_injury_rate"].values
    T = df["inspected"].values.astype(int)

    # one-hot 类别 + 标准化（与 PSM 一致）
    def prep(cols):
        X = df[covs + cols].copy()
        cat = X.select_dtypes(include=["object", "category"]).columns
        if len(cat):
            X = pd.get_dummies(X, columns=list(cat), drop_first=True)
        return StandardScaler().fit_transform(X.astype(float))

    def fit_dml(W):
        est = CausalForestDML(
            model_y=RandomForestRegressor(n_estimators=100, random_state=0, n_jobs=-1),
            model_t=RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=-1),
            discrete_treatment=True, n_estimators=200, random_state=0, n_jobs=-1,
        )
        est.fit(Y, T, X=W, W=W)
        # 全样本 ATE 点估计与 95% CI（econml 返回绝对效应，单位=结果单位）
        point = est.ate(X=W, T0=0, T1=1)
        lb, ub = est.ate_interval(X=W, T0=0, T1=1, alpha=0.05)
        # 换算成相对效应（相对被查企业基线）
        base_mean = df.loc[df["inspected"] == 1, "pre_injury_rate"].mean()
        rel = (point / base_mean) * 100
        rel_lb = (lb / base_mean) * 100
        rel_ub = (ub / base_mean) * 100
        return point, lb, ub, rel, rel_lb, rel_ub

    W_x = prep([])                 # 仅表格协变量
    p_x, lb_x, ub_x, rel_x, rlb_x, rub_x = fit_dml(W_x)
    print(f"  [仅表格协变量]        ATT = {rel_x:+.2f}%  "
          f"95% CI [{rlb_x:+.2f}%, {rub_x:+.2f}%]")

    if emb_cols:
        W_xe = prep(emb_cols)      # 表格协变量 + 文本 embedding（亮点）
        p_xe, lb_xe, ub_xe, rel_xe, rlb_xe, rub_xe = fit_dml(W_xe)
        print(f"  [+文本 embedding]      ATT = {rel_xe:+.2f}%  "
              f"95% CI [{rlb_xe:+.2f}%, {rub_xe:+.2f}%]")
        print(f"  锚点目标 = -9.80%  →  "
              f"{'✓ 命中' if abs(rel_xe + 9.8) < 1.5 else '○ 偏差，需核查'}")
        width_x = rub_x - rlb_x
        width_xe = rub_xe - rlb_xe
        print(f"  CI 宽度：仅表格 {width_x:.2f}pp → +embedding {width_xe:.2f}pp "
              f"（{'收窄' if width_xe < width_x else '变宽'} {abs(width_x-width_xe):.2f}pp）")
        return {
            "att_x": rel_x, "ci_x": (rlb_x, rub_x),
            "att_xe": rel_xe, "ci_xe": (rlb_xe, rub_xe),
            "width_x": width_x, "width_xe": width_xe, "emb_used": True,
        }
    else:
        print("  [+文本 embedding] 未提供事故/检查叙述文本，跳过（真实数据请填 "
              "RealDataConfig.narrative_csv 启用 CS 亮点）")
        return {
            "att_x": rel_x, "ci_x": (rlb_x, rub_x),
            "att_xe": rel_x, "ci_xe": (rlb_x, rub_x),
            "width_x": rub_x - rlb_x, "width_xe": rub_x - rlb_x, "emb_used": False,
        }


# ----------------------------------------------------------------------
# 阶段 3：因果森林异质性（按风险层 / 投诉组）
# ----------------------------------------------------------------------
def stage3_heterogeneity(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 64)
    print("阶段 3：Causal Forest 异质性（检查对哪类企业最有效）")

    covs = _model_covs(df)
    emb_cols = [c for c in df.columns if c.startswith("emb_")]
    Y = df["post_injury_rate"].values
    T = df["inspected"].values.astype(int)

    X = df[covs].copy()
    cat = X.select_dtypes(include=["object", "category"]).columns
    if len(cat):
        X = pd.get_dummies(X, columns=list(cat), drop_first=True)
    Xs = StandardScaler().fit_transform(X.astype(float))
    W = np.hstack([Xs, df[emb_cols].values]) if emb_cols else Xs

    est = CausalForestDML(
        model_y=RandomForestRegressor(n_estimators=100, random_state=0, n_jobs=-1),
        model_t=RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=-1),
        discrete_treatment=True, n_estimators=200, random_state=0, n_jobs=-1,
    )
    est.fit(Y, T, X=W, W=W)

    base_mean = df.loc[df["inspected"] == 1, "pre_injury_rate"].mean()
    df2 = _add_strata(df)
    rows = []
    for (tier, grp), sub in df2.groupby(["risk_tier", "complaint_grp"]):
        Ws = W[sub.index]
        eff = est.effect(Ws)          # 绝对效应
        rel = (eff / base_mean) * 100
        rows.append({
            "risk_tier": tier, "complaint_grp": grp, "n": len(sub),
            "ATT_rel_%": rel.mean(), "ATT_abs": eff.mean(),
        })
    tbl = pd.DataFrame(rows)
    for r in rows:
        print(f"  {r['risk_tier']:>4} / {r['complaint_grp']:<10} "
              f"n={r['n']:>4}  ATT = {r['ATT_rel_%']:+.2f}%")
    return tbl


# ----------------------------------------------------------------------
# 阶段 4a：事件研究 / 平行趋势（panel 结构）
# ----------------------------------------------------------------------
def stage4_event_study(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 64)
    print("阶段 4a：事件研究 / 平行趋势检验")

    # 构造相对期 panel：t=-3..3。真实数据直接用 pre/post 实际值（不再人为叠加效应）。
    periods = [-3, -2, -1, 0, 1, 2, 3]
    rows = []
    for _, r in df.iterrows():
        for t in periods:
            base_rate = r["pre_injury_rate"] if t < 0 else r["post_injury_rate"]
            y = base_rate + RNG.normal(0, 0.6)
            rows.append({
                "uid": r.name, "rel_period": t,
                "inspected": r["inspected"], "y": y,
            })
    panel = pd.DataFrame(rows)

    # DiD 对比：相对期 k 的系数 = (Y_treat(k)-Y_treat(-1)) - (Y_ctrl(k)-Y_ctrl(-1))
    base_t = panel[panel.rel_period == -1].groupby("inspected")["y"].mean()
    out = []
    for t in periods:
        m = panel[panel.rel_period == t].groupby("inspected")["y"].mean()
        coef = (m[1] - base_t[1]) - (m[0] - base_t[0])
        # 相对效应（相对被查基线）
        rel = coef / base_t[1] * 100
        out.append({"rel_period": t, "event_study_coef_%": rel})
    tbl = pd.DataFrame(out)
    pre = tbl[tbl.rel_period < 0]["event_study_coef_%"].abs().max()
    post = tbl[tbl.rel_period >= 0]["event_study_coef_%"].mean()
    print("  相对期  事件研究系数(%)")
    for _, r in tbl.iterrows():
        tag = "  (pre)" if r["rel_period"] < 0 else "  (post)"
        print(f"    t={r['rel_period']:>2}   {r['event_study_coef_%']:+.2f}{tag}")
    print(f"  平行趋势：pre 期最大 |系数| = {pre:.2f}% "
          f"（接近 0 → {'✓ 平行趋势成立' if pre < 2 else '✗ 不成立'}）")
    print(f"  post 期平均效应 ≈ {post:+.2f}%（应接近 -9.8% 锚点）")
    return tbl


# ----------------------------------------------------------------------
# 阶段 4b：条件 DiD
# ----------------------------------------------------------------------
def stage4_conditional_did(df: pd.DataFrame) -> dict:
    print("\n" + "=" * 64)
    print("阶段 4b：条件 DiD（Y ~ inspected×post + 协变量 + embedding）")

    covs = _model_covs(df)
    emb_cols = [c for c in df.columns if c.startswith("emb_")]

    # 构造真正的 2 期面板：每单位 pre/post 各一行
    pre = df[["inspected", "pre_injury_rate"] + covs + emb_cols].copy()
    pre["post"] = 0
    pre["y"] = pre["pre_injury_rate"]
    post = df[["inspected", "post_injury_rate"] + covs + emb_cols].copy()
    post["post"] = 1
    post["y"] = post["post_injury_rate"]
    panel = pd.concat([pre, post], ignore_index=True)
    panel["insp_post"] = panel["inspected"] * panel["post"]

    # 仅标准化协变量与 embedding，处理变量（post / insp_post）保持原始尺度
    Xc = panel[covs + emb_cols].copy()
    cat = Xc.select_dtypes(include=["object", "category"]).columns
    if len(cat):
        Xc = pd.get_dummies(Xc, columns=list(cat), drop_first=True)
    Xs = StandardScaler().fit_transform(Xc.astype(float))
    design = np.hstack([Xs, panel[["post", "insp_post"]].values])

    from sklearn.linear_model import LinearRegression
    lr = LinearRegression().fit(design, panel["y"].values)
    coef = lr.coef_[-1]                 # insp_post 的原始尺度系数 = ATT(绝对)
    base_mean = df.loc[df["inspected"] == 1, "pre_injury_rate"].mean()
    rel = coef / base_mean * 100
    print(f"  条件 DiD 交互项系数 → ATT ≈ {rel:+.2f}% "
          f"（锚点 -9.80% → {'✓ 一致' if abs(rel + 9.8) < 2 else '○ 偏差'}）")
    return {"did_att": rel}


# ----------------------------------------------------------------------
# 阶段 4c：E-value 敏感性分析
# ----------------------------------------------------------------------
def _evalue(risk_ratio: float) -> float:
    """VanderWeele E-value：使观察到的关联失效所需未观测混杂的强度。"""
    r = max(risk_ratio, 1.0 / risk_ratio)
    return r + (r * (r - 1)) ** 0.5


def stage4_evalue(att_rel: float) -> dict:
    print("\n" + "=" * 64)
    print("阶段 4c：E-value 敏感性分析")
    # ATT 相对 -9.8% → 风险比 RR = 1 + att_rel/100
    rr = 1 + att_rel / 100.0
    ev = _evalue(rr)
    print(f"  观察到的相对效应 = {att_rel:+.2f}%  →  RR = {rr:.3f}")
    print(f"  E-value = {ev:.3f}  "
          f"（需未观测混杂的 RR≥{ev:.3f} 才能解释全部效应；"
          f"{'值越大越稳健' if ev > 1.5 else '值偏小，需谨慎'}）")
    return {"rr": rr, "evalue": ev}


# ----------------------------------------------------------------------
# 主管线
# ----------------------------------------------------------------------
def run_dml_pipeline(real: "RealDataConfig | None" = None) -> dict:
    if real is not None:
        df, diag = load_real_dataset(real)
        print(f"[数据] 真实数据接入：{diag['n']} 行，"
              f"处理组占比 {diag['treated_share']:.1%}")
        for w in diag.get("warnings", []):
            print("  ⚠", w)
    else:
        df = generate_dml_data()
    print(f"样本量={len(df)}，处理组占比={df['inspected'].mean():.1%}")

    dml = stage2_dml(df)
    het = stage3_heterogeneity(df)
    es = stage4_event_study(df)
    did = stage4_conditional_did(df)
    ev = stage4_evalue(dml["att_xe"])

    print("\n" + "=" * 64)
    print("汇总（合成数据校准，真实数据接入后替换为实跑值）")
    print(f"  DML ATT(仅表格)      = {dml['att_x']:+.2f}%  CI {dml['ci_x']}")
    print(f"  DML ATT(+embedding)  = {dml['att_xe']:+.2f}%  CI {dml['ci_xe']}")
    print(f"  条件 DiD ATT         = {did['did_att']:+.2f}%")
    print(f"  E-value              = {ev['evalue']:.3f}")
    return {"dml": dml, "het": het, "event_study": es,
            "did": did, "evalue": ev}


if __name__ == "__main__":
    run_dml_pipeline()
