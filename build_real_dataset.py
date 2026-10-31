"""
build_real_dataset.py —— 从真实 OSHA 执法数据（datastash 镜像）构建因果分析面板
=====================================================================
数据源：storydrivendatasets-pre-2022-archive/osha-enforcement-datastash（GitHub 镜像，
        即 DOL enforcedata 数据目录的完整 CSV，覆盖 1970–2020）。真实数据，非合成。

企业标识：公开执法库无 establishment_id；host_est_key 有 61% 为哨兵空值 'HOST_EST_KEY_VALUE'。
         故采用【企业名规范化 + 州】作为企业键（无 ID 时的标准做法）：
         大写→去标点→去 Inc/LLC/Co/Corp 等后缀→合并空格，再拼州。

设计（数据驱动、可精确链接）：
  - 样本：建筑业（NAICS 23 或 SIC 15/16/17）2010–2019 检查
  - 单位：企业（name+state 键）× 首次检查
  - 处理：首次检查 programmed（insp_type∈{H,I,K}）=1，unprogrammed（{B,C,A,F,M,G,J,D,L}）=0
  - pre_injury_rate：首检发现的 serious 违规（S/W/R）
  - post_injury_rate：该企业【下一次】检查发现的 serious 违规（结局）
  - 协变量：log_employees、risk_score、prior_injuries(=pre)、complaints(B型检查数)、region、unionized
  结局口径：OSHA 企业级伤害计数（ITA 300A）不在公开执法库中，故以“严重违规强度”
           （serious violations，安全合规/绩效的公认代理）为结局。

输出：data/real/osha_panel.csv、data/real/build_report.txt
"""
from __future__ import annotations
import os, glob, re
import numpy as np
import pandas as pd

from data_loader import REGION_MAP, _naics_hazard

RAW = "data/raw/osha"
OUT_DIR = "data/real"
os.makedirs(OUT_DIR, exist_ok=True)

PROGRAMMED = {"H", "I", "K"}
UNPROGRAMMED = {"B", "C", "A", "F", "M", "G", "J", "D", "L"}
SERIOUS = {"S", "W", "R"}
DUMMY_KEY = "HOST_EST_KEY_VALUE"
_SUFFIX = re.compile(r"\b(INC|LLC|LTD|CO|CORP|COMPANY|INCORPORATED|LP|LLP|THE|DBA)\b")


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def _norm_name(s):
    s = str(s).upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_inspections():
    use = ["activity_nr", "host_est_key", "estab_name", "site_state", "naics_code",
           "sic_code", "insp_type", "nr_in_estab", "union_status", "owner_type", "open_date"]
    parts = [pd.read_csv(f, usecols=use, low_memory=False, dtype=str)
             for f in sorted(glob.glob(f"{RAW}/osha_inspection-*.csv"))]
    df = pd.concat(parts, ignore_index=True)
    df["year"] = pd.to_datetime(df["open_date"], errors="coerce").dt.year
    df["n_emp"] = _num(df["nr_in_estab"])
    naics = df["naics_code"].fillna("")
    sic = df["sic_code"].fillna("").str.replace(r"\.0$", "", regex=True)
    df["is_const"] = naics.str.startswith("23") | sic.str.match(r"^(15|16|17)")
    it = df["insp_type"].astype(str).str.upper().str.strip()
    df["programmed"] = it.isin(PROGRAMMED).astype(int)
    df["unprogrammed"] = it.isin(UNPROGRAMMED).astype(int)
    df["is_complaint"] = (it == "B").astype(int)
    us = df["union_status"].astype(str).str.upper().str.strip()
    df["unionized"] = us.isin({"Y", "U", "A"}).astype(int)
    df["naics2"] = naics.str[:2]
    df["region"] = df["site_state"].astype(str).str.upper().map(REGION_MAP).fillna("Other")
    # 企业键：规范化名 + 州
    nn = df["estab_name"].map(_norm_name)
    df["name_ok"] = (nn.str.len() >= 3) & (nn != "HOST EST KEY VALUE")
    df["est_key"] = nn + " | " + df["site_state"].astype(str).str.upper()
    df["has_host_key"] = (df["host_est_key"].notna()
                          & (df["host_est_key"] != DUMMY_KEY)).astype(int)
    return df


def load_violation_agg():
    parts = []
    for f in sorted(glob.glob(f"{RAW}/osha_violation-*.csv")):
        v = pd.read_csv(f, usecols=["activity_nr", "viol_type", "delete_flag", "current_penalty"],
                        low_memory=False, dtype=str)
        v = v[v["delete_flag"].fillna("") != "X"]
        v["serious"] = v["viol_type"].astype(str).str.upper().isin(SERIOUS).astype(int)
        v["pen"] = _num(v["current_penalty"]).fillna(0.0)
        parts.append(v.groupby("activity_nr").agg(
            n_viol=("activity_nr", "size"), n_serious=("serious", "sum"), penalty=("pen", "sum")))
    return pd.concat(parts).groupby(level=0).sum()


def build_panel():
    ins = load_inspections()
    diag = {"steps": []}
    diag["steps"].append(f"检查总数(全行业全期): {len(ins)}")

    sel = ins[ins["is_const"] & (ins["year"] >= 2010) & (ins["year"] <= 2019) & ins["name_ok"]].copy()
    diag["steps"].append(f"建筑业2010-2019且企业名有效: {len(sel)}")

    vagg = load_violation_agg()
    sel = sel.merge(vagg, left_on="activity_nr", right_index=True, how="left")
    sel[["n_viol", "n_serious", "penalty"]] = sel[["n_viol", "n_serious", "penalty"]].fillna(0.0)
    diag["steps"].append(f"有违规聚合的检查: {int((sel['n_viol'] > 0).sum())}")

    sel = sel.sort_values(["est_key", "open_date"])
    sel["seq"] = sel.groupby("est_key").cumcount()
    first = sel[sel["seq"] == 0].set_index("est_key")
    second = sel[sel["seq"] == 1].set_index("est_key")
    diag["steps"].append(f"企业数(名+州键): {sel['est_key'].nunique()}")
    diag["steps"].append(f"有≥2次检查的企业: {len(second)}")

    ok = first[(first["programmed"] == 1) | (first["unprogrammed"] == 1)].copy()
    common = ok.index.intersection(second.index)
    ok, sec = ok.loc[common], second.loc[common]
    diag["steps"].append(f"首检类型明确且有次检: {len(ok)}")

    comp = sel.groupby("est_key")["is_complaint"].sum()

    panel = pd.DataFrame(index=ok.index)
    panel["inspected"] = ok["programmed"].astype(int)
    panel["pre_injury_rate"] = ok["n_serious"].astype(float)
    panel["post_injury_rate"] = sec["n_serious"].astype(float)
    panel["pre_n_viol"] = ok["n_viol"].astype(float)
    panel["post_n_viol"] = sec["n_viol"].astype(float)
    panel["pre_penalty"] = ok["penalty"].astype(float)
    panel["post_penalty"] = sec["penalty"].astype(float)
    panel["log_employees"] = np.log1p(ok["n_emp"].clip(lower=0).fillna(0))
    panel["prior_injuries"] = ok["n_serious"].astype(float)
    haz = _naics_hazard(ok["naics2"].fillna("99"))
    panel["risk_score"] = (ok["n_serious"].astype(float) / 5.0).clip(0, 1).fillna(haz)
    panel.loc[panel["risk_score"].isna(), "risk_score"] = haz
    panel["complaints"] = comp.reindex(ok.index).fillna(0).astype(float)
    panel["region"] = ok["region"].values
    panel["unionized"] = ok["unionized"].astype(int).values
    panel["naics2"] = ok["naics2"].values
    panel["state"] = ok["site_state"].values
    panel["index_year"] = ok["year"].values
    panel["gap_years"] = (pd.to_datetime(sec["open_date"]) - pd.to_datetime(ok["open_date"])).dt.days / 365.25
    panel["next_programmed"] = sec["programmed"].astype(int).values
    panel["has_host_key"] = ok["has_host_key"].astype(int).values

    panel = panel.replace([np.inf, -np.inf], np.nan)
    panel = panel.dropna(subset=["pre_injury_rate", "post_injury_rate", "log_employees"]).reset_index()
    panel = panel.rename(columns={"est_key": "estab"})

    diag["n"] = len(panel)
    diag["treated_share"] = float(panel["inspected"].mean()) if len(panel) else 0.0
    diag["mean_post_treated"] = float(panel.loc[panel["inspected"] == 1, "post_injury_rate"].mean())
    diag["mean_post_control"] = float(panel.loc[panel["inspected"] == 0, "post_injury_rate"].mean())

    outp = os.path.join(OUT_DIR, "osha_panel.csv")
    panel.to_csv(outp, index=False)
    with open(os.path.join(OUT_DIR, "build_report.txt"), "w", encoding="utf-8") as f:
        for s in diag["steps"]:
            f.write(s + "\n")
        f.write(f"\n最终面板行数: {diag['n']}\n处理组占比: {diag['treated_share']:.1%}\n")
        f.write(f"post(处理)={diag['mean_post_treated']:.3f}  post(对照)={diag['mean_post_control']:.3f}\n")
    print("\n".join(diag["steps"]))
    print(f"\n最终面板: {diag['n']} 行, 处理组 {diag['treated_share']:.1%}")
    print(f"post mean: 处理={diag['mean_post_treated']:.3f} 对照={diag['mean_post_control']:.3f}")
    print("saved ->", outp)
    return panel


if __name__ == "__main__":
    build_panel()
