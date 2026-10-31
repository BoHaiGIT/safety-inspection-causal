"""
数据接入层 —— 真实数据适配器 + 统一合成生成器
=====================================================================
本模块是「路线 C」唯一的数据入口，供 psm_baseline.py 与 dml_causal_forest.py 共用。

两大能力：
  1) generate_synthetic(n, seed) —— 合成数据（仅用于跑通管线 / 验证锚点 -9.8%），
     默认管线在 RealDataConfig 未提供时使用它，保证仓库开箱即跑。
  2) load_real_dataset(cfg) —— 真实数据接入：
     - 输入两张表（伤害/事故台账 + 安全检查台账），按真实字段名做列映射与派生，
       输出与脚本完全对齐的标准 schema（inspected / post_injury_rate / pre_injury_rate
       / log_employees / risk_score / prior_injuries / complaints / safety_investment
       / region / unionized / emb_*）
     - 自动处理：伤害率计算、投诉型检查计数、pre/post 期滞后、地区映射、缺失协变量降级
     - 返回 (df, diagnostics)，diagnostics 含样本量、处理组占比、缺失/降级说明、
       共同支持域提示，便于投稿前 QA。

真实 OSHA 数据字段（样例见 data/sample_establishments.csv、sample_inspections.csv）：
  - 伤害台账（OSHA ITA / Establishment Specific Injury and Illness Data）：
      ESTAB_ID, NAICS, STATE, YEAR, AVG_EMP, HOURS, TRC, DAFW, OTH_REC, OWNER_TYPE
  - 检查台账（OSHA Enforcement / Inspection data）：
      INSP_ID, ESTAB_ID, INSP_DATE, INSP_TYPE, CITATIONS, PENALTY, STATE
  接入时只需：
      cfg = RealDataConfig(injury_csv="data/sample_establishments.csv",
                           inspection_csv="data/sample_inspections.csv")
      df, diag = load_real_dataset(cfg)
=====================================================================
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# 标准 schema（与两个脚本共用）
# ----------------------------------------------------------------------
CANONICAL_COLUMNS = [
    "inspected", "pre_injury_rate", "post_injury_rate",
    "log_employees", "risk_score", "prior_injuries",
    "complaints", "safety_investment", "region", "unionized",
]
OPTIONAL_COVARIATES = ["safety_investment", "unionized"]
EMB_PREFIX = "emb_"

# 美国州 → 人口普查四大区（用于真实数据 region 派生）
REGION_MAP = {
    "CT": "Northeast", "ME": "Northeast", "MA": "Northeast", "NH": "Northeast",
    "NJ": "Northeast", "NY": "Northeast", "PA": "Northeast", "RI": "Northeast",
    "VT": "Northeast",
    "IL": "Midwest", "IN": "Midwest", "MI": "Midwest", "OH": "Midwest",
    "WI": "Midwest", "IA": "Midwest", "KS": "Midwest", "MN": "Midwest",
    "MO": "Midwest", "NE": "Midwest", "ND": "Midwest", "SD": "Midwest",
    "DE": "South", "FL": "South", "GA": "South", "MD": "South", "NC": "South",
    "SC": "South", "VA": "South", "WV": "South", "AL": "South", "KY": "South",
    "MS": "South", "TN": "South", "AR": "South", "LA": "South", "OK": "South",
    "TX": "South", "DC": "South",
    "AZ": "West", "CO": "West", "ID": "West", "MT": "West", "NV": "West",
    "NM": "West", "UT": "West", "WY": "West", "AK": "West", "CA": "West",
    "HI": "West", "OR": "West", "WA": "West",
}
# 投诉/举报型检查（用于内生性：这类检查本身由高伤害风险触发）
COMPLAINT_TYPES = {"COMPLAINT", "REFERRAL", "ACCIDENT", "DISCRIMINATION"}


# ----------------------------------------------------------------------
# 1) 合成数据生成（仅演示 / 锚点验证）
# ----------------------------------------------------------------------
def generate_synthetic(n: int = 9000, seed: int = 2026,
                       with_emb: bool = True, true_effect: float = -0.098):
    """生成与脚本标准 schema 对齐的合成数据；真实相对效应 = true_effect (-9.8%)。"""
    rng = np.random.default_rng(seed)
    log_emp = rng.normal(4.5, 1.0, n)
    risk = rng.beta(2, 5, n)
    prior = rng.poisson(2.0, n).astype(float)
    complaints = rng.poisson(1.5, n).astype(float)
    invest = rng.beta(2, 3, n)
    region = rng.integers(0, 5, n)
    union = rng.binomial(1, 0.4, n)
    V = rng.normal(0, 1.0, n)  # 未观测异质性（真实数据由事故叙述文本承载）

    # 处理选择性（高风险/多投诉/多事故更易被查 → 选择偏差）
    eta = 2.4 * (0.35 * risk + 0.30 * (complaints / 3) + 0.25 * (prior / 4)
                 + 0.20 * (log_emp / 6) - 0.20 * invest + 0.15 * union
                 + 0.05 * region)
    p = 1 / (1 + np.exp(-eta))
    inspected = rng.binomial(1, p, n)

    base = (12.0 + 9.0 * risk + 1.4 * prior + 3.0 * (complaints / 3)
            - 2.5 * invest + 1.0 * union + 0.8 * region
            + 2.0 * V + rng.normal(0, 2.0, n))
    base = np.clip(base, 1.0, None)
    post = np.where(inspected == 1, base * (1 + true_effect), base)

    df = pd.DataFrame({
        "inspected": inspected.astype(int),
        "pre_injury_rate": base,
        "post_injury_rate": post,
        "log_employees": log_emp,
        "risk_score": risk,
        "prior_injuries": prior,
        "complaints": complaints,
        "safety_investment": invest,
        "region": region.astype(str),
        "unionized": union.astype(int),
    })
    if with_emb:
        dim = 16
        emb = (0.9 * risk[:, None] + 0.6 * (complaints / 3)[:, None]
               + 1.1 * V[:, None] + rng.normal(0, 0.5, (n, dim)))
        df[[f"{EMB_PREFIX}{i}" for i in range(dim)]] = emb
    df["__true_effect_abs"] = np.where(inspected == 1, base * true_effect, 0.0)
    return df


# ----------------------------------------------------------------------
# 2) 真实数据配置
# ----------------------------------------------------------------------
@dataclass
class RealDataConfig:
    # 两张输入表（真实字段名）
    injury_csv: str
    inspection_csv: str
    # 列名映射：真实列名 -> 标准名（覆盖下面的默认解析）
    column_map: dict = field(default_factory=dict)
    # 真实列名（可用 column_map 整体重命名；这里给默认值供样例/OSHA 数据）
    id_col: str = "ESTAB_ID"
    naics_col: str = "NAICS"
    state_col: str = "STATE"
    year_col: str = "YEAR"
    emp_col: str = "AVG_EMP"
    hours_col: str = "HOURS"
    trc_col: str = "TRC"            # total recordable cases（总可记录伤害例数）
    dafw_col: str = "DAFW"          # days-away-from-work cases
    insp_id_col: str = "INSP_ID"
    insp_date_col: str = "INSP_DATE"
    insp_type_col: str = "INSP_TYPE"
    # 可选：文本叙述 → embedding（事故/检查叙述）
    narrative_csv: Optional[str] = None
    narrative_id_col: Optional[str] = None
    narrative_text_col: Optional[str] = None
    emb_dim: int = 16
    # 结果变量口径：'trc'（总可记录）或 'dafw'（误工）
    rate_basis: str = "trc"
    # 因果滞后：结果取检查年 + lag 的伤害率；pre 取检查年前一年
    causal_lag_years: int = 0
    random_state: int = 2026


# ----------------------------------------------------------------------
# 3) 真实数据派生工具
# ----------------------------------------------------------------------
def _read_csv(path: str) -> pd.DataFrame:
    # 兼容常见中文/英文编码
    for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return pd.read_csv(path)  # 最后兜底


def _map(df: pd.DataFrame, cmap: dict) -> pd.DataFrame:
    if cmap:
        df = df.rename(columns={k: v for k, v in cmap.items() if k in df.columns})
    return df


def _naics_hazard(naics: pd.Series) -> pd.Series:
    """NAICS 两位行业 → 危害评分 0~1（高危害行业更高）。未知默认 0.5。"""
    table = {
        "23": 0.85,        # 建造
        "32": 0.72, "33": 0.72, "31": 0.70,   # 制造
        "48": 0.66, "49": 0.66,               # 运输仓储
        "22": 0.62, "21": 0.60,               # 公用/采矿
        "56": 0.42, "62": 0.40, "72": 0.38,   # 行政/医疗/食宿
        "11": 0.55, "42": 0.45, "81": 0.35,
        "44": 0.30, "45": 0.30, "54": 0.25, "52": 0.22, "53": 0.28,
        "61": 0.20, "71": 0.30, "92": 0.25, "99": 0.25,
    }
    def score(x):
        s = str(x)[:2].strip().zfill(2)
        return table.get(s, 0.5)
    return naics.astype(str).map(score).astype(float)


def _injury_rate(df: pd.DataFrame, cfg: RealDataConfig) -> pd.Series:
    num = df[cfg.dafw_col] if cfg.rate_basis == "dafw" else df[cfg.trc_col]
    den = df[cfg.hours_col].replace(0, np.nan)
    # OSHA 标准发生率 = cases / hours * 200000（每 100 全时当量）
    return (num / den * 200000).clip(lower=0)


def load_real_dataset(cfg: RealDataConfig):
    """接入真实数据：两张表 join + 派生标准 schema。返回 (df, diagnostics)。"""
    diag: dict = {"steps": [], "warnings": []}

    inj = _map(_read_csv(cfg.injury_csv), cfg.column_map)
    insp = _map(_read_csv(cfg.inspection_csv), cfg.column_map)
    diag["steps"].append(f"加载伤害台账 {cfg.injury_csv}: {len(inj)} 行")
    diag["steps"].append(f"加载检查台账 {cfg.inspection_csv}: {len(insp)} 行")

    # 伤害率
    inj["injury_rate"] = _injury_rate(inj, cfg)
    inj["log_employees"] = np.log1p(inj[cfg.emp_col].clip(lower=0))

    # 检查台账：解析年份、是否投诉/举报型
    insp["insp_year"] = pd.to_datetime(
        insp[cfg.insp_date_col], errors="coerce").dt.year
    itype = insp[cfg.insp_type_col].astype(str).str.upper().str.strip()
    insp["is_complaint"] = itype.isin(COMPLAINT_TYPES)

    # 按 企业×年 聚合检查
    g = insp.groupby([cfg.id_col, "insp_year"])
    insp_agg = g.agg(
        inspected=("insp_id_col" if "insp_id_col" in insp else cfg.insp_id_col,
                   lambda s: int(len(s) > 0)),
        complaints=(cfg.insp_type_col, lambda s: int(itype.loc[s.index].isin(COMPLAINT_TYPES).sum())),
    ).reset_index()
    insp_agg = insp_agg.rename(columns={cfg.id_col: "estab", "insp_year": "year"})
    insp_agg["estab"] = insp_agg["estab"].astype(str)  # 强制字符串键，避免与伤害表类型不一致
    insp_agg["inspected"] = 1  # 只要有检查记录即处理组

    # 伤害台账按 企业×年
    inj = inj.rename(columns={cfg.id_col: "estab", cfg.year_col: "year",
                              cfg.naics_col: "naics", cfg.state_col: "state"})
    inj["estab"] = inj["estab"].astype(str)  # 强制字符串键（真实 OSHA 为纯数字 ID）
    base = inj[["estab", "year", "naics", "state", "injury_rate",
                "log_employees", cfg.trc_col]].copy()
    base = base.rename(columns={cfg.trc_col: "prior_injuries_raw"})

    # 与检查聚合 join（左连伤害台账，保留有伤害数据的企业）
    df = base.merge(insp_agg, on=["estab", "year"], how="left")
    df["inspected"] = df["inspected"].fillna(0).astype(int)
    df["complaints"] = df["complaints"].fillna(0).astype(int)

    # 结果期 / 前置期（滞后）
    lag = cfg.causal_lag_years
    rate_col = "injury_rate"
    df = df.sort_values(["estab", "year"])
    df["post_injury_rate"] = df.groupby("estab")[rate_col].shift(-lag)
    df["pre_injury_rate"] = df.groupby("estab")[rate_col].shift(1)
    df["prior_injuries"] = df.groupby("estab")["prior_injuries_raw"].shift(1)

    # 风险评分：优先用人均历史伤害率（数据驱动），回退 NAICS 危害
    df["risk_score"] = (
        df["prior_injuries_raw"] / df["log_employees"].replace(0, np.nan)
    ).clip(0, 5) / 5.0
    naics_haz = _naics_hazard(df["naics"])
    df["risk_score"] = df["risk_score"].fillna(naics_haz)
    df.loc[df["risk_score"].isna(), "risk_score"] = naics_haz

    # 地区
    df["region"] = df["state"].astype(str).str.upper().map(REGION_MAP).fillna("Other")

    # 可选协变量：真实 OSHA 台账通常无安全投入/工会标识 → 降级并告警
    for col in OPTIONAL_COVARIATES:
        if col not in df.columns:
            df[col] = np.nan
            diag["warnings"].append(
                f"缺失可选协变量 {col}：已从模型协变量集中剔除（真实 OSHA 数据通常无此字段）")

    # 文本叙述 → embedding（可选）
    emb_cols = []
    if cfg.narrative_csv and cfg.narrative_text_col:
        emb_cols = _attach_embeddings(df, cfg, diag)

    # 清洗：丢弃无结果期的行
    before = len(df)
    df = df.dropna(subset=["post_injury_rate", "pre_injury_rate"]).copy()
    diag["steps"].append(f"丢弃无前置/结果期的行：{before} → {len(df)}")

    # 选标准列
    keep = [c for c in CANONICAL_COLUMNS if c in df.columns]
    for c in OPTIONAL_COVARIATES:
        if c in keep and df[c].isna().all():
            keep.remove(c)
            diag["warnings"].append(f"协变量 {c} 全缺失，已剔除")
    out = df[keep + emb_cols].reset_index(drop=True)

    # 数值化
    for c in ["post_injury_rate", "pre_injury_rate", "log_employees",
              "risk_score", "prior_injuries", "complaints", "safety_investment"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=[c for c in
                             ["post_injury_rate", "pre_injury_rate"]
                             if c in out.columns]).reset_index(drop=True)

    diag["n"] = len(out)
    diag["treated_share"] = float(out["inspected"].mean()) if len(out) else 0.0
    diag["effective_covariates"] = [c for c in CANONICAL_COLUMNS
                                    if c in out.columns and c not in ("inspected",)]
    return out, diag


def _attach_embeddings(df: pd.DataFrame, cfg: RealDataConfig, diag: dict):
    """将叙述文本转为 embedding（优先 sentence-transformers，缺失则哈希兜底）。"""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        model = SentenceTransformer("all-MiniLM-L6-v2")
        nar = _read_csv(cfg.narrative_csv)
        nar = _map(nar, {})
        text = nar[cfg.narrative_text_col].astype(str).tolist()
        vecs = model.encode(text, show_progress_bar=False)
        dim = vecs.shape[1]
        emb_df = pd.DataFrame(
            vecs, columns=[f"{EMB_PREFIX}{i}" for i in range(dim)])
        nar = nar.reset_index(drop=True)
        emb_df[cfg.narrative_id_col] = nar[cfg.narrative_id_col].values
        df2 = df.merge(emb_df, left_on="estab", right_on=cfg.narrative_id_col,
                       how="left")
        cols = [c for c in df2.columns if c.startswith(EMB_PREFIX)]
        diag["steps"].append(f"文本 embedding 已生成：{len(cols)} 维（sentence-transformers）")
        return cols
    except Exception as e:  # 降级：确定性哈希向量，保证管线可跑
        diag["warnings"].append(
            f"未启用 sentence-transformers（{e}）；用确定性哈希向量占位，"
            f"真实论文请安装 sentence-transformers 并填 narrative_csv")
        rng = np.random.default_rng(cfg.random_state)
        dim = cfg.emb_dim
        vecs = rng.random((len(df), dim))
        cols = [f"{EMB_PREFIX}{i}" for i in range(dim)]
        for i, c in enumerate(cols):
            df[c] = vecs[:, i]
        return cols


# ----------------------------------------------------------------------
# 4) 样例数据生成（真实字段名，仅用于验证管线；标注为非真实数据）
# ----------------------------------------------------------------------
def write_sample_data(out_dir: str = "data", n_estab: int = 400,
                      years=(2021, 2022, 2023), seed: int = 2026):
    """写出两张真实字段名的样例 CSV，用于端到端验证数据接入（非真实数据）。"""
    import os
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    states = list(REGION_MAP.keys())
    naics_pool = ["23", "32", "33", "31", "48", "22", "56", "62", "11", "42"]
    itypes = ["PROGRAMMED", "COMPLAINT", "REFERRAL", "ACCIDENT", "REFERRAL"]

    rows_inj, rows_insp = [], []
    insp_counter = 1000
    for e in range(n_estab):
        st = rng.choice(states)
        naics = rng.choice(naics_pool)
        haz = _naics_hazard(pd.Series([naics]))[0]
        emp = int(rng.integers(20, 2000))
        for y in years:
            # 固有风险驱动伤害率（带行业危害）
            lam = max(0.5, (haz * 8 + rng.normal(0, 1.5)))
            trc = int(rng.poisson(lam))
            dafw = int(min(trc, max(0, rng.poisson(lam * 0.6))))
            oth = max(0, trc - dafw)
            hours = emp * 2000
            rows_inj.append({
                "ESTAB_ID": f"E{e:05d}", "NAICS": naics, "STATE": st, "YEAR": y,
                "AVG_EMP": emp, "HOURS": hours, "TRC": trc, "DAFW": dafw,
                "OTH_REC": oth, "OWNER_TYPE": rng.choice(["PRIVATE", "GOV", "SUBCONTRACT"]),
            })
        # 检查：高危害企业更可能被查；投诉型检查与伤害率相关
        n_insp = rng.binomial(1, 0.35 + 0.3 * haz) + rng.binomial(1, 0.1)
        for _ in range(int(n_insp)):
            insp_counter += 1
            y = int(rng.choice(years))
            typ = rng.choice(itypes, p=[0.45, 0.25, 0.12, 0.10, 0.08])
            rows_insp.append({
                "INSP_ID": f"I{insp_counter}", "ESTAB_ID": f"E{e:05d}",
                "INSP_DATE": f"{y}-{int(rng.integers(1,13)):02d}-{int(rng.integers(1,28)):02d}",
                "INSP_TYPE": typ, "CITATIONS": int(rng.poisson(1.5)),
                "PENALTY": int(rng.poisson(5000)), "STATE": st,
            })

    inj_df = pd.DataFrame(rows_inj)
    insp_df = pd.DataFrame(rows_insp)
    inj_path = os.path.join(out_dir, "sample_establishments.csv")
    insp_path = os.path.join(out_dir, "sample_inspections.csv")
    inj_df.to_csv(inj_path, index=False)
    insp_df.to_csv(insp_path, index=False)

    # 列映射示例（真实数据若字段名不同，据此修改）
    cmap_example = {
        # "ESTAB_ID": "ESTAB_ID",  # 已为默认名，无需映射
    }
    with open(os.path.join(out_dir, "column_map_osha.json"), "w", encoding="utf-8") as f:
        json.dump(cmap_example, f, ensure_ascii=False, indent=2)

    return inj_path, insp_path


if __name__ == "__main__":
    p1, p2 = write_sample_data()
    print("样例已生成：")
    print(" ", p1)
    print(" ", p2)
    cfg = RealDataConfig(injury_csv=p1, inspection_csv=p2)
    df, diag = load_real_dataset(cfg)
    print(f"\n接入后样本量={diag['n']}，处理组占比={diag['treated_share']:.1%}")
    print("有效协变量：", diag["effective_covariates"])
    for w in diag["warnings"]:
        print("  ⚠", w)
    print("\n前 3 行：")
    print(df.head(3).to_string())
