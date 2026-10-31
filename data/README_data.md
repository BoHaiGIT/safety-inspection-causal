# 数据接入说明（Data Integration Guide）

本项目的数据层分为两条互不依赖的路径：

1. **真实数据路径（论文使用）**：OSHA 执法数据镜像 → `osha_panel.csv` / `osha_transitions.csv` → 全部实证结果。
2. **通用适配器路径**：`data_loader.py` 的 `RealDataConfig`，用于接入任意两表结构（伤害台账 + 检查台账）的数据，服务于第二篇（中文数据）。

---

## 1. 获取真实数据（论文所用）

### 1.1 数据来源

美国劳工部 OSHA 执法数据目录的公开 CSV 镜像：

```
https://codeload.github.com/storydrivendatasets-pre-2022-archive/osha-enforcement-datastash/zip/refs/heads/master
```

约 526 MB 压缩包，解压后包含 `data/stashed/` 下的分表：

| 目录 | 内容 | 论文用途 |
|---|---|---|
| `osha_inspection` | 检查主表（4,783,331 条） | 处理变量 `insp_type`、协变量、企业链接 |
| `osha_violation` | 违规与罚金（12,488,743 条） | **结局变量**（serious 违规数、罚金） |
| `osha_accident` / `osha_accident_abstract` | 事故记录与叙述 | 论文未使用（见 1.4） |
| `osha_data_dictionary` | 字段字典 | 字段对齐 |

### 1.2 关键字段

| 字段 | 说明 |
|---|---|
| `insp_type` | 检查类型字母码。**programmed = {H, I, K}**；unprogrammed = {B(投诉), C(转介), A(事故), F(跟进), M(死亡/灾难), G, J, D, L} |
| `naics_code` / `sic_code` | 行业。建筑业 = NAICS 以 `23` 开头，或 SIC ∈ {15,16,17} |
| `open_date` | `yyyymmdd` 数值型 |
| `nr_in_estab` | 企业雇员数 |
| `host_est_key` | **不可用**：建筑业记录中 61% 为哨兵字符串 `HOST_EST_KEY_VALUE` |
| `viol_type` | `S`=serious、`W`=willful、`R`=repeat；论文结局只计 S/W/R |
| `delete_flag` | `X` 表示已删除，须剔除 |
| `activity_nr` | 检查唯一号，**违规表 ↔ 检查表**的精确链接键 |

### 1.3 企业标识（本文最大工程障碍）

公开执法库**没有** establishment id。论文采用：

```
key = normalise(estab_name) + " | " + site_state
normalise: 大写 → 去标点 → 去 INC|LLC|LTD|CO|CORP|COMPANY|INCORPORATED|LP|LLP|THE|DBA → 合并空格
```

效果：59,621 家建筑企业、142,354 条企业内检查转换；其中 10,986 家（18.4%）在两种检查类型下都被观察到，构成 switcher 识别子样本。

> 该规则会**拆分**以不同商号报备的同一法人，也可能**合并**同州同名不同厂。两类的误差在企业固定效应设计中都被差分掉（凡在 key 内恒定的都被吸收）。

### 1.4 为什么不用事故叙述文本 / 伤害率

- **伤害率**：企业级伤害计数（Form 300A）是**另一套**采集，不在公开执法库中。故结局为 serious 违规数（合规代理），全文不做伤害率断言。
- **文本 embedding**：事故表 `summary_nr` 与检查表 `activity_nr` 在 2010–2019 仅 **0.4%** 可链接（联邦计划与州计划口径差异），无法构成代表性样本，故不用作文本控制变量。

### 1.5 可选：走 DOL Open Data API

`download_osha_v2.ps1`（零安装 PowerShell）调用：

```
https://apiprod.dol.gov/v4/get/OSHA/{table}/csv?limit=&offset=&filter_object=<json>&X-API-KEY=<key>
```

需在 `dataportal.dol.gov` 免费注册取 Key（单行存入 `api_key.txt`）。脚本带 429 限流退避与 413 降量。**论文分析不依赖此路径**，镜像下载已足够。

---

## 2. 派生数据

| 文件 | 内容 | 生成脚本 |
|---|---|---|
| `data/real/osha_panel.csv` | 企业级「首检 → 次检」面板，N = 59,617 | `build_real_dataset.py` |
| `data/real/osha_transitions.csv` | 企业 × 连续检查对，N = 142,354（含 `treat`/`pre`/`post`/`gap_years`/`log_employees`） | `build_within_firm.py` |

两者体积较大（7 MB / 17 MB），未纳入版本库；按 `README.md` 的步骤可完整重建。各表的估计结果已以 JSON/TXT 形式存于 `data/real/`，可直接核对论文表 2–4。

---

## 3. 通用适配器 `data_loader.py`（第二篇中文数据用）

`RealDataConfig` 接受**两张表**：

- 伤害/事故台账：企业 ID、年份、事故数、雇员数
- 检查台账：企业 ID、检查日期、检查类型

适配器会派生标准 schema（`inspected` / `post_injury_rate` / `log_employees` / `risk_score` / `region` / `unionized` 等）、映射州→地区、计算伤害率、并自动剔除缺失的可选协变量。列名不一致时用 `column_map` 映射（见 `column_map_osha.json` 示例）。

第二篇（中文数据）对应字段：

| 标准列 | 中文数据来源 |
|---|---|
| 企业 ID | 统一社会信用代码（四库一平台） |
| 检查日期 / 类型 | 省级「双随机、一公开」公示 |
| 事故数 | 住建部房屋市政工程生产安全事故通报 |
| 处罚 | 四库一平台行政处罚记录 |

---

## 4. 关于合成校准数据

带 −9.8% 锚点的合成数据由 `data_loader.generate_synthetic()` 生成，供 `psm_baseline.py` / `dml_causal_forest.py` 做**方法验证**（证明估计阶梯能回收已知真值）。该 −9.8% 是校准锚点，**不是实证发现**，也未在稿件中被引用为实证结果。

`data_loader.RealDataConfig` 亦可用任意两表结构（伤害台账 + 检查台账）驱动；列名不一致时用 `column_map_osha.json` 提供映射（该文件已给出中文数据字段的示例映射）。

真实数据的结论见 `README.md` 与 `投稿文件_SafetyScience/03_Manuscript.md`。
