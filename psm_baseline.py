"""
PSM 基准复现框架 —— 安全监管因果推断「路线 C」第一步
=====================================================================
目标：复现 CIKM 2025 基准效应（ATT ≈ -9.8%，即安全检查使后续伤害率下降约 9.8%）
方法阶梯：PSM 基准 → DML 双重机器学习 → 因果森林异质性 → 内生性三件套
         （事件研究/平行趋势 + 条件 DiD + E-value 敏感性分析）

管线：数据加载 → 倾向得分估计 → 匹配 → 平衡性检验 → 效应估计
依赖：pandas / numpy / scikit-learn / matplotlib（pip install -r requirements.txt）

说明：
- 真实数据未就位时，框架自动生成「合成数据」演示完整管线，并把真实 ATT 设为 -9.8%
  以验证匹配能还原锚点；接入真实 OSHA/CIKM 数据后只需改 PSMConfig.data_path。
- 第二阶段内生性讨论的「投诉数 complaints」已作为混杂因子纳入，方便后续做
  反向因果（投诉多的工地本来就更危险）的敏感性对照。
=====================================================================
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

# 数据接入层：真实数据适配器 + 统一合成生成器
from data_loader import (
    generate_synthetic, load_real_dataset, RealDataConfig,
)

# ----------------------------------------------------------------------
# 代码开源仓库（投稿 Safety Science 的复现加分项；创建后替换为真实 URL）
# Code & reproducibility repository (cited in the Safety Science submission):
REPO_URL = "https://github.com/BoHaiGIT/safety-inspection-causal"


# ----------------------------------------------------------------------
# 1) 配置：数据集选择与变量定义（一鱼两吃：公开集 / 自建中文集共用同一套管线）
# ----------------------------------------------------------------------
@dataclass
class PSMConfig:
    # 'osha_cikm' = OSHA/CIKM 公开数据集（第一篇，投 Safety Science）
    # 'cn_selfbuilt' = 住建部事故通报 + 四库一平台 + 双随机公示（第二篇，投 ECAM）
    dataset: str = "osha_cikm"

    # 真实数据 CSV 路径；留 None 则生成合成数据演示
    data_path: str | None = None

    # 变量名（与真实数据列名对齐；若列名不同，用 COLUMN_MAP 重命名）
    treatment: str = "inspected"          # 是否接受安全检查 0/1
    outcome: str = "post_injury_rate"     # 后续伤害/事故率（结果变量）
    # 混杂因子（含后续内生性讨论所需的 complaints）
    covariates: list[str] = field(default_factory=lambda: [
        "log_employees", "risk_score", "prior_injuries",
        "complaints", "safety_investment", "region", "unionized",
    ])
    caliper: float = 0.05        # 卡尺：匹配允许的最大倾向得分绝对差
    random_state: int = 2026
    bootstrap: int = 500         # 自助法重复次数（效应置信区间）

    # 真实数据列名 → 本框架标准列名 的映射（按需填写）
    column_map: dict = field(default_factory=lambda: {
        # 例："ESTAB": "log_employees", "INJ_RATE": "post_injury_rate", ...
    })

    # 真实数据配置（RealDataConfig）；提供时优先加载真实数据（两表 join 模式）
    real: "RealDataConfig | None" = None


# 真实数据与标准 schema 的对照（仅作文档，不阻断运行）
EXPECTED_SCHEMA = """
标准列名            含义                      类型
--------------------------------------------------------------
inspected         是否接受安全检查           0/1（处理）
post_injury_rate  后续伤害/事故率           连续（结果）
log_employees     企业规模（员工数对数）     连续
risk_score        固有风险等级 0~1           连续
prior_injuries    历史伤害次数              连续
complaints        投诉次数（内生性关键）     连续
safety_investment 前期安全投入 0~1          连续
region            地区编码                  类别
unionized         是否工会化 0/1            0/1
"""


# ----------------------------------------------------------------------
# 2) 数据加载
# ----------------------------------------------------------------------
def load_data(cfg: PSMConfig) -> pd.DataFrame:
    if cfg.real is not None:
        df, diag = load_real_dataset(cfg.real)
        print(f"[数据] 真实数据接入完成：{diag['n']} 行，"
              f"处理组占比 {diag['treated_share']:.1%}")
        for w in diag.get("warnings", []):
            print("  ⚠", w)
    elif cfg.data_path:
        df = pd.read_csv(cfg.data_path)
        if cfg.column_map:
            df = df.rename(columns=cfg.column_map)
        missing = [c for c in [cfg.treatment, cfg.outcome] + cfg.covariates
                   if c not in df.columns]
        if missing:
            raise ValueError(f"数据缺失列：{missing}\n期望 schema：\n{EXPECTED_SCHEMA}")
        eff = [c for c in cfg.covariates if c in df.columns]
        dropped = [c for c in cfg.covariates if c not in df.columns]
        if dropped:
            print(f"[数据] 协变量剔除缺失字段：{dropped}")
        cfg._eff_covs = eff  # type: ignore[attr-defined]
        return df
    else:
        df = generate_synthetic()
        print("[数据] 未提供真实数据，使用合成数据演示（真实 ATT 锚点 -9.8%）")

    # 解析实际可用协变量（剔除真实数据中缺失的字段，如 safety_investment/unionized）
    eff = [c for c in cfg.covariates if c in df.columns]
    dropped = [c for c in cfg.covariates if c not in df.columns]
    if dropped:
        print(f"[数据] 协变量剔除缺失字段：{dropped}")
    cfg._eff_covs = eff  # type: ignore[attr-defined]
    return df


def _synthetic_data(cfg: PSMConfig, n: int = 8000) -> pd.DataFrame:
    """生成合成数据：真实 ATT 设为 -9.8%，用于验证匹配能还原锚点。"""
    rng = np.random.default_rng(cfg.random_state)
    log_emp = rng.normal(4.5, 1.0, n)
    risk = rng.beta(2, 5, n)                       # 0~1 偏低的固有风险
    prior = rng.poisson(2.0, n).astype(float)
    complaints = rng.poisson(1.5, n).astype(float)
    invest = rng.beta(2, 3, n)                     # 0~1 安全投入
    region = rng.integers(0, 5, n)
    union = rng.binomial(1, 0.4, n)

    # 处理选择性：高风险、多投诉、多事故、大规模企业更可能被查（造成选择偏差）
    eta = 2.4 * (0.35 * risk + 0.30 * (complaints / 3) + 0.25 * (prior / 4)
                 + 0.20 * (log_emp / 6) - 0.20 * invest + 0.15 * union
                 + 0.05 * region)
    p = 1 / (1 + np.exp(-eta))
    inspected = rng.binomial(1, p, n)

    # 结果基线（不含处理效应）：风险/投诉/事故↑ → 伤害率↑；投入↑ → ↓
    base = (12.0 + 9.0 * risk + 1.4 * prior + 3.0 * (complaints / 3)
            - 2.5 * invest + 1.0 * union + 0.8 * region
            + rng.normal(0, 3.0, n))
    base = np.clip(base, 1.0, None)
    # 真实处理效应：-9.8% 相对下降（仅作用于被查企业）
    effect = -0.098 * base
    post = np.where(inspected == 1, base + effect, base)

    return pd.DataFrame({
        "inspected": inspected,
        "post_injury_rate": post,
        "log_employees": log_emp,
        "risk_score": risk,
        "prior_injuries": prior,
        "complaints": complaints,
        "safety_investment": invest,
        "region": region.astype(str),
        "unionized": union,
    })


# ----------------------------------------------------------------------
# 3) 倾向得分估计（Logistic Regression）
# ----------------------------------------------------------------------
def _is_categorical(s: pd.Series) -> bool:
    return (s.dtype == object or str(s.dtype) == "str"
            or pd.api.types.is_string_dtype(s)
            or isinstance(s.dtype, pd.CategoricalDtype))


def estimate_propensity_score(df: pd.DataFrame, cfg: PSMConfig) -> pd.Series:
    covs = getattr(cfg, "_eff_covs", cfg.covariates)
    X = df[covs].copy()
    # 类别变量 one-hot；连续变量标准化
    cat = [c for c in X.columns if _is_categorical(X[c])]
    if len(cat):
        X = pd.get_dummies(X, columns=list(cat), drop_first=True)
    X = StandardScaler().fit_transform(X.astype(float))
    y = df[cfg.treatment].astype(int)

    model = LogisticRegression(max_iter=1000, C=1.0, solver="lbfgs")
    model.fit(X, y)
    ps = model.predict_proba(X)[:, 1]

    auc = roc_auc_score(y, ps)
    print(f"[PS 模型] Logistic 拟合完成 | AUC={auc:.3f} "
          f"（接近 0.5 表示无强选择性，接近 1 表示强选择性）")
    return pd.Series(ps, index=df.index, name="propensity")


# ----------------------------------------------------------------------
# 4) 匹配（1:1 最近邻 + 卡尺，无放回贪心）
# ----------------------------------------------------------------------
def match(df: pd.DataFrame, ps: pd.Series, cfg: PSMConfig) -> pd.DataFrame:
    df = df.assign(propensity=ps)
    treated = df.index[df[cfg.treatment] == 1].tolist()
    control = df.index[df[cfg.treatment] == 0].tolist()

    ctrl_ps = df.loc[control, "propensity"].to_dict()
    used: set[int] = set()
    pairs = []

    for t in treated:
        t_ps = df.loc[t, "propensity"]
        best, best_d = None, np.inf
        for c in control:
            if c in used:
                continue
            d = abs(t_ps - ctrl_ps[c])
            if d <= cfg.caliper and d < best_d:
                best, best_d = c, d
        if best is not None:
            used.add(best)
            pairs.append((t, best))

    if not pairs:
        raise RuntimeError("未匹配到任何对，请放宽 caliper 或检查共同支持域。")

    t_idx, c_idx = zip(*pairs)
    matched = df.loc[list(t_idx) + list(c_idx)].copy()
    matched["__match_role"] = ["treated"] * len(t_idx) + ["control"] * len(c_idx)
    print(f"[匹配] 成功匹配 {len(pairs)} 对 "
          f"（处理组 {len(treated)} 人，匹配率 {len(pairs)/len(treated):.1%}）")
    return matched


# ----------------------------------------------------------------------
# 5) 平衡性检验（标准化均差 SMD，匹配前后对比）
# ----------------------------------------------------------------------
def _smd_num(group1: pd.Series, group2: pd.Series) -> float:
    m1, m2 = group1.mean(), group2.mean()
    s1, s2 = group1.std(), group2.std()
    pooled = np.sqrt((s1**2 + s2**2) / 2)
    return (m1 - m2) / pooled if pooled > 0 else 0.0


def _smd_cat(group1: pd.Series, group2: pd.Series) -> float:
    """类别变量：取各水平比例差的标准化均差的最大值。"""
    cats = set(group1.astype(str)) | set(group2.astype(str))
    best = 0.0
    for c in cats:
        p1 = (group1.astype(str) == c).mean()
        p2 = (group2.astype(str) == c).mean()
        pooled = np.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / 2)
        if pooled > 0:
            best = max(best, abs(p1 - p2) / pooled)
    return best


def balance_diagnostics(full: pd.DataFrame, matched: pd.DataFrame,
                        cfg: PSMConfig) -> pd.DataFrame:
    covs = getattr(cfg, "_eff_covs", cfg.covariates)
    rows = []
    for cov in covs:
        g_t = full.loc[full[cfg.treatment] == 1, cov]
        g_c = full.loc[full[cfg.treatment] == 0, cov]
        m_t = matched.loc[matched["__match_role"] == "treated", cov]
        m_c = matched.loc[matched["__match_role"] == "control", cov]
        fn = _smd_cat if _is_categorical(full[cov]) else _smd_num
        rows.append({
            "covariate": cov,
            "SMD_before": fn(g_t, g_c),
            "SMD_after": fn(m_t, m_c),
        })
    tbl = pd.DataFrame(rows)
    max_after = tbl["SMD_after"].abs().max()
    print(f"[平衡] 匹配前最大 |SMD|={tbl['SMD_before'].abs().max():.3f}；"
          f"匹配后最大 |SMD|={max_after:.3f} "
          f"（<0.1 视为达到平衡）")
    return tbl


# ----------------------------------------------------------------------
# 6) 效应估计（ATT + 自助法置信区间，相对/绝对双口径）
# ----------------------------------------------------------------------
def estimate_att(matched: pd.DataFrame, cfg: PSMConfig,
                 boot: int | None = None) -> dict:
    y_t = matched.loc[matched["__match_role"] == "treated", cfg.outcome]
    y_c = matched.loc[matched["__match_role"] == "control", cfg.outcome]
    att_abs = y_t.mean() - y_c.mean()
    att_rel = att_abs / y_t.mean() * 100.0

    # 朴素（未调整）对比，用于展示选择偏差被修正了多少
    full = matched  # 仅用于占位；真实朴素估计在 main 中用全样本算
    n_boot = boot if boot is not None else cfg.bootstrap
    rng = np.random.default_rng(cfg.random_state)
    pairs_t = y_t.values
    pairs_c = y_c.values
    bs = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(pairs_t), len(pairs_t))
        a = pairs_t[idx].mean() - pairs_c[idx].mean()
        bs.append(a / pairs_t[idx].mean() * 100.0)
    lo, hi = np.percentile(bs, [2.5, 97.5])

    return {
        "att_abs": att_abs,
        "att_rel": att_rel,
        "ci95_rel": (lo, hi),
        "n_pairs": len(pairs_t),
    }


# ----------------------------------------------------------------------
# 主管线
# ----------------------------------------------------------------------
def run_pipeline(cfg: PSMConfig) -> dict:
    print("=" * 64)
    print("阶段 1：数据加载")
    df = load_data(cfg)
    print(f"  样本量={len(df)}，处理组占比={df[cfg.treatment].mean():.1%}")

    print("\n阶段 2：倾向得分估计")
    ps = estimate_propensity_score(df, cfg)

    print("\n阶段 3：匹配")
    matched = match(df, ps, cfg)

    print("\n阶段 4：平衡性检验")
    bal = balance_diagnostics(df, matched, cfg)

    print("\n阶段 5：效应估计")
    # 朴素估计（全样本，未调整）
    naive_t = df.loc[df[cfg.treatment] == 1, cfg.outcome].mean()
    naive_c = df.loc[df[cfg.treatment] == 0, cfg.outcome].mean()
    naive_rel = (naive_t - naive_c) / naive_t * 100.0

    res = estimate_att(matched, cfg)
    print(f"  朴素（未调整）相对效应 = {naive_rel:+.2f}%")
    print(f"  PSM 调整后 ATT(绝对) = {res['att_abs']:.3f}")
    print(f"  PSM 调整后 ATT(相对) = {res['att_rel']:+.2f}%  "
          f"95% CI [{res['ci95_rel'][0]:+.2f}%, {res['ci95_rel'][1]:+.2f}%]")
    hit = "✓ 命中" if abs(res['att_rel'] + 9.8) < 1.5 else "○ 偏差，需核查"
    print(f"  锚点目标 = -9.80%  →  {hit}")

    return {"df": df, "matched": matched, "balance": bal, "result": res,
            "naive_rel": naive_rel}


if __name__ == "__main__":
    cfg = PSMConfig()           # 默认合成数据演示
    out = run_pipeline(cfg)

    # 如需接入真实数据：
    # cfg = PSMConfig(data_path="data/osha_cikm.csv",
    #                 column_map={"ESTAB": "log_employees", ...})
    # out = run_pipeline(cfg)
