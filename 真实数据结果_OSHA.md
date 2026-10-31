# 真实 OSHA 数据 — 安全检查有效性因果分析（结果存档）

> 本文件记录**真实数据**的完整链路与结果，替代此前合成数据的 −9.8% 演示值。
> 生成时间：2026-10-30　数据快照：OSHA 执法数据至 2020 年

---

## 1. 数据来源（真实，非合成）

| 项 | 内容 |
|---|---|
| 来源 | GitHub 镜像 `storydrivendatasets-pre-2022-archive/osha-enforcement-datastash`（即美国劳工部 OSHA 执法数据目录全量 CSV） |
| 获取方式 | 沙箱可直连 `codeload.github.com`，下载 526MB 整包（`data/raw/osha_datastash.zip`），已解压至 `data/raw/osha/` |
| 规模 | 检查 **4,783,331** 条（1970–2020）；事故 **134,948** 条；违规 **12,488,743** 条 |
| 原 API 方案 | DOL Open Data API 需免费 Key，但注册页在企业网下打不开；`www.osha.gov` 为 403（WAF）。GitHub 镜像绕开此限制 |

## 2. 研究设计（数据驱动，全程精确链接）

- **样本**：建筑业（NAICS 23 或 SIC 15/16/17）2010–2019 检查
- **企业键**：公开库无 `establishment_id`；`host_est_key` 有 61% 为哨兵空值。
  改用 **企业名规范化 + 州**（大写／去标点／去 Inc-LLC-Co 等后缀）作为企业键。
- **单位**：企业 × 首次检查
- **处理**：首检为 programmed（`insp_type` ∈ {H,I,K}）=1；unprogrammed（{B,C,A,F,M,G,J,D,L}）=0
- **前置**：`pre_injury_rate` = 首检 serious 违规数（S/W/R）
- **结局**：`post_injury_rate` = 该企业**下一次**检查的 serious 违规数
- **协变量**：`log_employees`、`risk_score`、`prior_injuries`、`complaints`、`region`、`unionized`；回归含地区／年份／NAICS 固定效应

> **口径说明（重要）**：OSHA 企业级伤害计数（ITA 300A）不在公开执法库中，无法获取。
> 故结局采用 **serious 违规强度**——安全合规绩效的公认代理，可精确链接。全文不做"伤害率下降"的断言。

## 3. 样本

| 指标 | 值 |
|---|---|
| 有效企业数（≥2 次检查） | **59,617** |
| 处理组占比 | 70.6% |
| pre 均值 / post 均值 | 1.534 / 1.165 |

## 4. 结果

### 4.1 主效应（对"下次检查 serious 违规数"）

| 方法 | 估计 | 95% CI | 相对 | 显著性 |
|---|---|---|---|---|
| 朴素（post_t − post_c） | +0.044 | — | +3.7% | 未调整（受选择性污染） |
| 原始 DiD（post−pre 组间差） | −0.008 | — | — | 近零 |
| **Value-added OLS（控基线+协变量+FE）** | **−0.0527** | [−0.086, −0.017] | **−4.5%** | 显著 |
| **DML（LinearDML, 5 折）** | **−0.0426** | [−0.081, −0.005] | **−3.7%** | 显著 |

**E-value = 1.27**：需一个与处理、结局关联强度均约 1.27 倍的未测量混杂才能解释掉该效应——**稳健性偏弱**，需在局限中说明。

### 4.2 异质性（分组 Value-added OLS）

| 子组 | coef | 相对 | n |
|---|---|---|---|
| 小企业（≤中位规模） | −0.035 | −2.9% | 30,401 |
| **大企业（>中位规模）** | **−0.059** | **−5.3%** | 29,216 |
| NAICS 23（建筑业整体） | −0.051 | −4.3% | 59,171 |
| 支持服务（NAICS 56） | −0.312 | −36.2% | 428（噪声大） |

**结论**：programmed（定向）检查使后续 serious 违规小幅下降约 **4–5%**；**大企业效果更强**（−5.3% vs 小企业 −2.9%）。

## 5. 与合成演示值的差异（必须正视）

| 项 | 合成演示（旧） | 真实数据（本文件） |
|---|---|---|
| 结局 | 伤害率 | serious 违规数（合规代理） |
| 效应 | −9.8% | −4.5%（OLS）／−3.7%（DML） |
| 样本 | 9,000 合成 | 59,617 真实建筑企业 |

> 合成的 −9.8% 是人为设定的锚点，**不可作为真实结论**。真实效应更温和（−4~5%），且结局是合规指标而非伤害率。

## 6. 复现步骤

```bash
# 1) 下载镜像整包（约 526MB）
curl -L -o data/raw/osha_datastash.zip \
  "https://codeload.github.com/storydrivendatasets-pre-2022-archive/osha-enforcement-datastash/zip/refs/heads/master"
# 2) 解压所需分表（inspection/accident/accident_abstract/violation/data_dictionary 等）
# 3) 构建面板
python build_real_dataset.py          # -> data/real/osha_panel.csv
# 4) 全方法阶梯
python run_real_analysis.py           # -> data/real/real_results.txt / .json
```

## 7. 局限（投稿需写入 Limitations）

1. **结局为违规而非伤害**：无 ITA 300A 企业伤害计数（公开执法库不含）。
2. **企业名为模糊链接**：无 establishment_id，name+state 可能误合并同名企业（衰减偏误）。
3. **处理非随机**：programmed 瞄准高风险企业；已用基线违规 + 协变量 + FE 调整，但残余选择仍在。
4. **均值回归**：已用 pre 基线控制，仍有残余。
5. **E-value 1.27 偏低**：对未测量混杂不稳健。
6. **数据截至 2020**：不含 2021+ 政策变化。

## 8. 文件清单

- `build_real_dataset.py` — 真实面板构建
- `run_real_analysis.py` — OLS/DiD/DML/E-value 方法阶梯
- `data/real/osha_panel.csv` — 分析面板（59,617 行）
- `data/real/real_results.txt` / `.json` — 结果
- `data/real/build_report.txt` — 构建日志
