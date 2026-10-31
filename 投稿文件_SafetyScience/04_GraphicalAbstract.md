# Graphical Abstract（图文摘要）

*Safety Science* 要求投稿时提供一张 **Graphical Abstract**：单张图，直观传达研究设计与核心结论，配一句图注。

## 已生成的成图

**文件**：`graphical_abstract.png`（300 dpi，约 1500 × 1000 px，白底）

生成脚本：项目根目录 `make_graphical_abstract.py`（可重跑，数据硬编码自 `data/real/*_results.json`）。

### 构图（三联）

| 面板 | 内容 |
|---|---|
| **A** | 同一批 142,354 条转换上六种估计策略的效应：混合 **+22.6%** → V-A OLS **−4.5%** → DML **−3.7%** → AIPW −1.9% → 企业 FE **−3.5%** → switcher **−4.8%**。直观呈现**符号反转**。 |
| **B** | 安慰剂检验（用**未来** programmed 检查替换处理）：企业间 +26.1% → 企业内 +10.4%。虚线标出估计效应量级（约 3.5%），说明选择性信号**大于**效应本身。 |
| **C** | 企业内固定效应的异质性森林图（10 个子组，95% 聚类稳健 CI）：大企业 −6.1%、工会 −16.0%、间隔>1 年 −5.8%、零基线记录 −5.1% 显著；小企业、已受罚企业、2015 年后不显著。 |

### 设计要点

- 红=负效应（减少违规），蓝=正效应（增加违规）——与中文语境"涨红跌绿"无关，此处是效应方向语义色，投稿英文刊无歧义。
- 面板 A 中浅色柱 = 依赖函数形式/需正则化的估计，深色柱 = 论文主结果（混合为反例、企业 FE 为主结果）。
- 面板 C 实心点=95% 显著，空心点=不显著，避免"看起来都显著"的误读。

## 图注（Caption，英文，1 句）

> *On 142,354 inspection-to-inspection transitions across 59,621 U.S. construction establishments (2010–2019), pooled comparison reports that programmed inspections are followed by 22.6% **more** serious violations, whereas within-establishment estimation reverses the sign to 3.5–4.8% **fewer**; a placebo that substitutes a future programmed inspection remains strongly positive (+26.1% between establishments, +10.4% within), showing that selection exceeds the effect being estimated, and the deterrent effect concentrates in large, unionised, and currently-clean establishments.*

## 投稿系统参数

- 文件类型选 `Graphical Abstract`。
- Safety Science 要求最小 531 × 1328 px（或 1328 × 531 px），本图 1500 × 1000 px 满足横向要求。
- 若系统提示尺寸不符，将 `make_graphical_abstract.py` 中 `figsize` 改为 `(13.3, 5.3)` 重跑即可得到 1328 × 531 比例版本。
