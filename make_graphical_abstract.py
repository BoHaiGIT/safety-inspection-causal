# -*- coding: utf-8 -*-
"""
make_graphical_abstract.py — Safety Science 图文摘要（单张三联图）
面板 A：同一批记录上六种估计策略的效应（符号反转）
面板 B：安慰剂检验（未来 programmed 检查）
面板 C：企业内固定效应异质性森林图
输出：投稿文件_SafetyScience/graphical_abstract.png
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#333333",
    "savefig.dpi": 300,
})

C_NEG = "#c0392b"
C_POS = "#2471a3"
C_GREY = "#7f8c8d"
C_ACC = "#16a085"

fig = plt.figure(figsize=(11.6, 7.6))
gs = fig.add_gridspec(2, 2, width_ratios=[1.18, 1.0], height_ratios=[1.0, 1.02],
                      wspace=0.30, hspace=0.40,
                      left=0.085, right=0.975, top=0.855, bottom=0.085)

# ----------------------------------------------------------------- Panel A
axA = fig.add_subplot(gs[0, 0])
labels = ["Pooled\n(no adjustment)", "Value-added\nOLS", "Double ML", "AIPW\n(doubly robust)",
          "Firm FE\n(all transitions)", "Firm FE\n(switchers)"]
vals = [22.6, -4.5, -3.7, -1.9, -3.5, -4.8]
ci = [None, None, None, None, (-5.9, -0.4), (-6.1, -0.6)]
ys = np.arange(len(labels))[::-1]
for y, v, c, lab in zip(ys, vals, ci, labels):
    solid = ("Firm FE" in lab) or ("Pooled" in lab)
    col = C_POS if v > 0 else C_NEG
    axA.barh(y, v, height=0.60, color=col, alpha=1.0 if solid else 0.45,
             edgecolor="none", zorder=3)
    if c:
        axA.plot([c[0], c[1]], [y, y], color="#2c3e50", lw=1.0, zorder=4,
                 solid_capstyle="butt")
        for e in c:
            axA.plot([e, e], [y - 0.12, y + 0.12], color="#2c3e50", lw=0.9, zorder=4)
    # value label placed at the end of the whisker / bar with a clear offset
    end = c[0] if (c and v < 0) else v
    if v > 0:
        axA.text(v + 0.8, y, f"{v:+.1f}%", va="center", ha="left",
                 fontsize=9.4, fontweight="bold", color=col, zorder=5)
    else:
        axA.text(end - 0.9, y, f"{v:+.1f}%", va="center", ha="right",
                 fontsize=9.4, fontweight="bold", color=col, zorder=5)
axA.axvline(0, color="#333333", lw=1.0, zorder=2)
axA.set_yticks(ys)
axA.set_yticklabels(labels, fontsize=8.6)
axA.set_xlim(-15.5, 29)
axA.set_ylim(-0.75, len(labels) - 0.35)
axA.set_xlabel("Effect on serious violations at next inspection (%)", fontsize=9)
axA.set_title("A   Six estimators on the same records:\nthe sign flips when establishment propensity is removed",
              fontsize=9.8, loc="left", fontweight="bold", pad=9)
axA.grid(axis="x", ls=":", lw=0.6, color="#bdc3c7", zorder=0)
axA.set_axisbelow(True)
for s in ("top", "right"):
    axA.spines[s].set_visible(False)
axA.annotate("selection: programmed inspections go to\nhigh-violation establishments",
             xy=(21.5, ys[0] + 0.02), xytext=(7.2, ys[0] - 0.85),
             fontsize=7.4, color=C_POS, ha="left", va="top",
             arrowprops=dict(arrowstyle="->", color=C_POS, lw=0.9,
                             connectionstyle="arc3,rad=-0.25"))

# ----------------------------------------------------------------- Panel B
axB = fig.add_subplot(gs[0, 1])
pl_labels = ["Between\nestablishments", "Within\nestablishment"]
pl_vals = [26.1, 10.4]
x = np.arange(2)
bars = axB.bar(x, pl_vals, width=0.44, color=[C_POS, "#7fb3d5"], edgecolor="none", zorder=3)
for b, v in zip(bars, pl_vals):
    axB.text(b.get_x() + b.get_width() / 2, v + 0.8, f"+{v:.1f}%", ha="center",
             fontsize=10, fontweight="bold", color=C_POS, zorder=4)
axB.axhline(0, color="#333333", lw=1.0)
axB.axhline(3.5, color=C_NEG, lw=1.1, ls="--", zorder=2,
            label="estimated within-firm effect (c. 3.5%)")
axB.legend(loc="upper right", frameon=False, fontsize=7.2,
           handlelength=1.6, borderaxespad=0.2)
axB.set_xticks(x)
axB.set_xticklabels(pl_labels, fontsize=8.8)
axB.set_xlim(-0.55, 1.55)
axB.set_ylim(0, 30)
axB.set_ylabel("Placebo coefficient (%)", fontsize=9)
axB.set_title("B   Placebo: substituting a FUTURE programmed\ninspection still predicts the outcome",
              fontsize=9.8, loc="left", fontweight="bold", pad=9)
axB.grid(axis="y", ls=":", lw=0.6, color="#bdc3c7", zorder=0)
axB.set_axisbelow(True)
for s in ("top", "right"):
    axB.spines[s].set_visible(False)

# ----------------------------------------------------------------- Panel C
axC = fig.add_subplot(gs[1, :])
het = [
    ("Large establishments", -6.1, -9.1, -1.2, True),
    ("Small establishments", -2.3, -6.9, +2.3, False),
    ("Unionised", -16.0, -15.1, -1.4, True),
    ("Non-unionised", -2.7, -5.7, +0.4, False),
    ("Gap > 1 year", -5.8, -12.1, -0.1, True),
    ("Gap <= 1 year", +2.3, -1.4, +5.2, False),
    ("Clean record at index", -5.1, -5.0, 0.0, True),
    ("Already cited at index", +3.3, -2.3, +11.9, False),
    ("2010-2014", -3.1, -6.4, +0.9, False),
    ("2015-2019", +2.5, -2.5, +7.3, False),
]
yh = np.arange(len(het))[::-1]
LAB_X = 13.6
for y, (lab, v, lo, hi, sig) in zip(yh, het):
    col = C_NEG if v < 0 else C_POS
    axC.plot([lo, hi], [y, y], color=col, lw=1.5, alpha=0.85, zorder=3,
             solid_capstyle="round")
    for e in (lo, hi):
        axC.plot([e, e], [y - 0.12, y + 0.12], color=col, lw=1.1, zorder=3)
    axC.scatter([v], [y], s=44, color=col if sig else "white", edgecolor=col,
                linewidth=1.4, zorder=4)
    axC.text(LAB_X, y, f"{v:+.1f}%" + ("" if sig else "  n.s."),
             va="center", ha="left", fontsize=7.9,
             color=col if sig else C_GREY,
             fontweight="bold" if sig else "normal")
axC.axvline(0, color="#333333", lw=1.0, zorder=2)
axC.axvline(-3.5, color=C_ACC, lw=1.0, ls="--", alpha=0.85, zorder=1)
axC.set_yticks(yh)
axC.set_yticklabels([h[0] for h in het], fontsize=8.4)
axC.set_xlim(-19.5, 19.5)
axC.set_ylim(-1.35, len(het) - 0.35)
axC.set_xticks([-15, -10, -5, 0, 5, 10])
axC.set_xlabel("Within-establishment effect on serious violations at next inspection (%)", fontsize=9)
axC.set_title("C   Where the effect lives:  filled markers are significant at 95%, open markers are not; bars are 95% cluster-robust CIs",
              fontsize=9.8, loc="left", fontweight="bold", pad=9)
axC.grid(axis="x", ls=":", lw=0.6, color="#bdc3c7", zorder=0)
axC.set_axisbelow(True)
for s in ("top", "right", "left"):
    axC.spines[s].set_visible(False)
axC.text(-18.8, -0.95, "dashed line: pooled within-firm estimate (-3.5%)",
         fontsize=7.4, color=C_ACC, ha="left", va="center")

# ----------------------------------------------------------------- header
fig.text(0.085, 0.965,
         "Programmed safety inspections cut later serious violations by c. 3-5% once establishment propensity is removed",
         fontsize=11.4, fontweight="bold", ha="left", va="center")
fig.text(0.085, 0.918,
         "U.S. construction, 2010-2019   |   59,621 establishments   |   142,354 inspection-to-inspection transitions   |   OSHA federal enforcement registry",
         fontsize=8.0, color="#5d6d7e", ha="left", va="center")

out = os.path.join("投稿文件_SafetyScience", "graphical_abstract.png")
fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight")
print("saved ->", out)
