# 投稿文件包 · Safety Science（真实数据版 v2）

本目录是可直接投递 **Safety Science**（Elsevier，中科院 2 区 Top / JCR Q1 / IF≈6.2 / 订阅模式 0 版面费）的投稿文件包。
**v2 与 v1 的根本区别：全部实证数字来自真实 OSHA 执法数据，不再使用合成校准值。**

## 文件清单

| 文件 | 内容 | 语言 | 状态 |
|---|---|---|---|
| `00_说明_README.md` | 本索引与进度 | 中文 | 完成 |
| `01_CoverLetter.md` | 投稿信（已落款 Jared / Bohai） | 英文 | 完成，待补 ORCID |
| `02_Highlights.md` | 亮点（≤85 字符 ×5，已核对字符数） | 英文 | 完成 |
| `03_Manuscript.md` | 完整稿件（含表 1–4 真实结果、44 条参考文献；单作者第一人称） | 英文 | **完成，可投** |
| `04_GraphicalAbstract.md` | 图文摘要说明 | 中/英 | 完成 |
| `graphical_abstract.png` | 图文摘要成图（三联图，300 dpi，1500×1000） | 图 | **已生成** |

## 核心结论（真实数据）

样本：U.S. 建筑业 2010–2019，**59,621 家企业 / 142,354 条企业内检查转换**（OSHA 联邦执法全量库）。

| 估计策略 | 对下次检查 serious 违规的效应 |
|---|---|
| 混合比较（不调整） | **+22.6%**（符号相反） |
| Value-added OLS | −4.5%（显著） |
| Double ML | −3.7%（显著） |
| AIPW（双稳健） | −1.9%（不显著） |
| **企业固定效应（主结果）** | **−3.5%**（95% CI −5.9% ~ −0.4%） |
| **企业固定效应（switcher 子样本）** | **−4.8%** |

**论文的真正卖点是"符号反转"**：同一批记录，混合比较说检查**增加**违规 22.6%，企业内比较说**减少** 3.5%，差距约 26 个百分点、约 7 倍于效应本身。
安慰剂检验（用**未来**检查类型当假处理）：企业间 +26.1% → 企业内 +10.4%，证明随机截面的"检查效应"主要是选择性。

## 与 v1 的两处关键更正（不可回退）

1. **结局口径**：v1 声称"伤害率下降 ~10%"。真实执法库**不含**企业级伤害计数（ITA 300A 不在公开库），故 v2 结局为 **serious 违规数（合规绩效代理）**，全文不做伤害率断言。稿件 3.3 节、Limitations 第 1 条、Cover Letter 均已明示。
2. **文本 embedding 卖点作废**：2010–2019 事故表与检查表仅 **0.4%** 可链接（联邦/州计划口径差异），无法作高维控制。v2 不再声称该创新，改为「符号反转 + 企业内识别 + 安慰剂诊断」三件套。

## 复现链（每一张表都可重跑）

| 脚本 | 产出 |
|---|---|
| `build_real_dataset.py` | `data/real/osha_panel.csv`（企业级首检-次检面板，N=59,617） |
| `run_real_analysis.py` | `data/real/real_results.txt`（V-A OLS / DML / E-value） |
| `robustness_real.py` | `data/real/robustness_results.{txt,json}`（**表 2**＋安慰剂＋AIPW） |
| `build_within_firm.py` | `data/real/osha_transitions.csv`、`within_firm_results.*`（**表 3**） |
| `within_firm_heterogeneity.py` | `data/real/within_firm_hetero.*`（**表 4**） |
| `make_graphical_abstract.py` | `graphical_abstract.png` |

## 投递前检查清单

1. **参考文献已补齐**：正文 44 条、`references.bib` 44 条，双向核对无缺失无孤立；每条均已对照出版社 / PubMed / RePEc / NBER / RAND / DOL 记录核实。2.1–2.3 三节已写实（不再是占位符）。
2. **作者信息已全部就绪**：署名 `Bin Jiang (Jared)`、单位 `Qingdao Bohai Construction Group, Qingdao, China`、邮箱 `13963901396@163.com`、ORCID `0009-0008-3989-0924`；正文全文单作者第一人称 "I"；致谢已写通用版。
3. 图文摘要 `graphical_abstract.png` 已生成，投稿系统直接上传。
4. 投稿入口：`editorialmanager.com/safety`（见 `SCI投稿入口整理.md`）。
5. 选**订阅模式**（非 OA），0 版面费；误选 Open Choice 会弹 $4,150。
6. 代码已开源：https://github.com/BoHaiGIT/safety-inspection-causal ，稿件 Data availability 段已引用。
7. 投递前复核当年中科院分区与本单位认可目录（Safety Science 为 2 区 Top，非预警）。

## 审稿风险提示（主动写进稿件的部分）

- E-value 仅 **1.28**，稳健性偏弱 → 稿件 5.6 节已如实写明"modest and fragile"。
- 企业内安慰剂仍显著（+10.4%）→ 5.5 节已解释其含义并说明为何不构成推翻。
- 2015–2019 子期无效应 → 6.2 节列为最重要的开放问题。
- 罚金无变化 → 5.3 节给出机理解释（罚金由少数高 gravity 案件驱动）。

## 另一套期刊格式（ECAM / Emerald）

| 文件 | 用途 |
|---|---|
| `references_ECAM_Harvard.md` | 同一批 44 条文献的 **Emerald Harvard** 排版（ECAM 用），含格式差异对照表与重跑说明 |
| `make_ecam_refs.py` | 由 `references.bib` 生成上表文件；改 bib 后重跑即可 |

两份文献表的**正文 in-text 引用完全一致**（都是 author–year，两位作者 `(Gray and Mendeloff, 2005)`、三位以上 `(Haviland et al., 2012)`），因此换刊时**只换文末列表，正文不必改**。
