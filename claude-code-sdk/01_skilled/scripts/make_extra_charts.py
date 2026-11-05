# -*- coding: utf-8 -*-
"""小米集团研报补充图表：营收利润、收入结构、估值对比、DCF 敏感性"""
import os, sys
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".claude", "skills", "financial_visualization", "scripts"))
from chart_generator import setup_chinese_font, ensure_dir  # noqa: E402

setup_chinese_font()
plt.rcParams["axes.unicode_minus"] = False
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "charts", "extra")
ensure_dir(OUT)

C_MAIN, C_ALT, C_GREY = "#1f5f8b", "#d97706", "#94a3b8"
PALETTE = ["#1f5f8b", "#d97706", "#0f766e", "#9f1239", "#6b7280"]

# ---------- 1. 营收与净利润趋势 ----------
years = ["2020", "2021", "2022", "2023", "2024", "2025"]
rev = [2458.66, 3283.09, 2800.44, 2709.70, 3659.06, 4572.87]
np_ = [203.13, 192.83, 25.03, 174.74, 235.78, 415.66]
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(years, rev, color=C_MAIN, width=0.55, label="营业收入（亿元）")
for b, v in zip(bars, rev):
    ax.text(b.get_x() + b.get_width() / 2, v + 60, f"{v:,.0f}", ha="center", fontsize=10)
ax.set_ylabel("营业收入（亿元）", fontsize=12)
ax.set_ylim(0, max(rev) * 1.22)
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)
ax2 = ax.twinx()
ax2.plot(years, np_, color=C_ALT, marker="o", linewidth=2.4, markersize=8, label="净利润（亿元）")
for x, v in zip(years, np_):
    ax2.annotate(f"{v:,.0f}", (x, v), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=10, color=C_ALT)
ax2.set_ylabel("净利润（亿元）", fontsize=12)
ax2.set_ylim(0, max(np_) * 1.45)
ax2.spines[["top"]].set_visible(False)
ax.set_title("小米集团 营业收入与净利润趋势（2020—2025）", fontsize=16, fontweight="bold", pad=16)
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=10, frameon=False)
ax.text(0.99, -0.13, "数据来源：公司年报（东方财富港股 F10）", transform=ax.transAxes, ha="right", fontsize=9, color="#64748b")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "营收与净利润趋势对比.png"), dpi=150, bbox_inches="tight", facecolor="white")
plt.close()

# ---------- 2. 收入结构（分业务） ----------
segments = ["智能手机", "IoT 与生活消费产品", "互联网服务", "智能电动汽车及创新业务", "其他"]
data = {
    "2024": [1917.59, 1041.03, 341.16, 327.54, 31.74],
    "2025": [1864.40, 1232.00, 374.40, 1060.69, 41.38],
}
fig, ax = plt.subplots(figsize=(12, 6.5))
bottom = np.zeros(len(data))
for i, seg in enumerate(segments):
    vals = np.array([0.0 if data[y][i] is None else data[y][i] for y in data])
    ax.bar(list(data.keys()), vals, bottom=bottom, color=PALETTE[i % len(PALETTE)],
           width=0.38, label=seg, edgecolor="white", linewidth=1.2)
    for j, (y, v) in enumerate(zip(data.keys(), vals)):
        if v > 120:
            ax.text(j, bottom[j] + v / 2, f"{v:,.0f}", ha="center", va="center",
                    fontsize=9, color="white" if i != 4 else "#334155")
    bottom += vals
for j, y in enumerate(data):
    ax.text(j, bottom[j] + 70, f"合计 {bottom[j]:,.0f}", ha="center", fontsize=10.5, fontweight="bold")
ax.set_ylabel("营业收入（亿元）", fontsize=12)
ax.set_ylim(0, bottom.max() * 1.16)
ax.set_title("小米集团 收入结构演变（2024—2025）", fontsize=16, fontweight="bold", pad=16)
ax.legend(loc="upper left", fontsize=9.5, frameon=False, ncol=1)
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)
ax.text(0.99, -0.10, "数据来源：公司年报分部资料", transform=ax.transAxes, ha="right", fontsize=9, color="#64748b")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "收入结构演变.png"), dpi=150, bbox_inches="tight", facecolor="white")
plt.close()

# ---------- 3. 估值水平对比 ----------
peers = ["小米集团", "比亚迪股份", "美的集团", "海尔智家", "比亚迪电子", "舜宇光学", "联想集团"]
pe = [17.42, 18.85, 13.92, 8.59, 19.45, 12.36, 45.87]
pb = [2.13, 2.31, 2.90, 1.28, 1.25, 2.05, 5.07]
x = np.arange(len(peers))
fig, ax = plt.subplots(figsize=(13, 6))
b1 = ax.bar(x - 0.2, pe, width=0.38, color=C_MAIN, label="PE(TTM)")
b2 = ax.bar(x + 0.2, pb, width=0.38, color=C_ALT, label="PB(MRQ)")
for b, v in list(zip(b1, pe)) + list(zip(b2, pb)):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.7, f"{v:.2f}", ha="center", fontsize=8.5)
ax.set_xticks(x)
ax.set_xticklabels(peers, fontsize=10)
ax.axhline(np.mean(pe[1:]), color=C_MAIN, linestyle="--", linewidth=1.1, alpha=0.7,
           label=f"同业 PE 均值 {np.mean(pe[1:]):.2f}x")
ax.set_ylabel("倍数（倍）", fontsize=12)
ax.set_ylim(0, 52)
ax.set_title("小米集团与可比公司估值水平对比（2026-10-27 收盘）", fontsize=16, fontweight="bold", pad=16)
ax.legend(fontsize=10, frameon=False, loc="upper left")
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "估值水平对比.png"), dpi=150, bbox_inches="tight", facecolor="white")
plt.close()

# ---------- 4. DCF 敏感性 ----------
# 复用估值模型计算结果（权益价值，港元/股）
waccs = [0.10, 0.105, 0.11, 0.115, 0.12]
gs = [0.02, 0.025, 0.03, 0.035, 0.04]
grid = np.array([
    [15.14, 15.66, 16.25, 16.93, 17.73],
    [14.53, 14.98, 15.49, 16.07, 16.74],
    [13.98, 14.38, 14.82, 15.32, 15.89],
    [13.50, 13.84, 14.23, 14.66, 15.15],
    [13.06, 13.37, 13.71, 14.08, 14.51],
])
fig, ax = plt.subplots(figsize=(10.5, 6))
im = ax.imshow(grid, cmap="YlGnBu", aspect="auto")
ax.set_xticks(range(len(gs)))
ax.set_xticklabels([f"{g:.1%}" for g in gs])
ax.set_yticks(range(len(waccs)))
ax.set_yticklabels([f"{w:.1%}" for w in waccs])
ax.set_xlabel("永续增长率 g", fontsize=12)
ax.set_ylabel("WACC", fontsize=12)
for i in range(len(waccs)):
    for j in range(len(gs)):
        ax.text(j, i, f"{grid[i, j]:.1f}", ha="center", va="center", fontsize=10,
                color="white" if (grid[i, j] - grid.min()) / (grid.max() - grid.min()) > 0.62 else "#1e293b")
ax.set_title("DCF 敏感性分析：每股权益价值（港元，中性情景）", fontsize=16, fontweight="bold", pad=16)
fig.colorbar(im, ax=ax, label="港元/股", shrink=0.85)
ax.text(0.99, -0.16, "基准情形 WACC=11.0%、g=3.0%，对应 14.82 港元/股；现价 25.66 港元", transform=ax.transAxes,
        ha="right", fontsize=9, color="#475569")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "DCF敏感性分析.png"), dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
# ---------- 5. 盈利能力与费用结构 ----------
years5 = ["2021", "2022", "2023", "2024", "2025"]
gm = [17.75, 16.99, 21.21, 20.92, 22.26]        # 毛利率 %
nm = [5.87, 0.89, 6.45, 6.44, 9.09]             # 净利率 %
nm_adj = [5.87, 0.89, 6.45, 6.23, 6.65]         # 扣重估净利率 %（估算）
rd = [4.01, 5.72, 7.05, 6.57, 7.25]             # 研发费用率 %
sell = [6.39, 7.61, 7.10, 6.94, 7.26]           # 销售及分销费用率 %

fig, ax = plt.subplots(figsize=(12.5, 6.2))
x5 = np.arange(len(years5))
w = 0.165
series = [
    ("毛利率", gm, C_MAIN, -2 * w),
    ("净利率（报表）", nm, "#9f1239", -1 * w),
    ("净利率（扣重估）", nm_adj, "#e11d48", 0),
    ("研发费用率", rd, C_ALT, 1 * w),
    ("销售及分销费用率", sell, "#0f766e", 2 * w),
]
for name, vals, color, offset in series:
    bars = ax.bar(x5 + offset, vals, width=w, color=color, label=name)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.35, f"{v:.1f}", ha="center", fontsize=7.8)
ax.bar(x5, [0] * len(x5), width=0, label="")
ax.set_xticks(x5)
ax.set_xticklabels(years5, fontsize=11)
ax.set_ylabel("百分比（%）", fontsize=12)
ax.set_ylim(0, max(gm) * 1.30)
ax.set_title("小米集团 盈利能力与费用结构（2021—2025）", fontsize=16, fontweight="bold", pad=16)
ax.legend(fontsize=9.5, frameon=False, loc="upper left")
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)

# 标注 2025 年重估盈余的影响
# 2025 年重估盈余影响：在两条净利率柱之间加高亮竖线
ax.axvspan(4 - 0.62 * w, 4 + 2.2 * w, ymin=0, ymax=9.8 / (max(gm) * 1.30),
           color="#f97316", alpha=0.10, zorder=0)
ax.text(4 + 0.8 * w, 10.1, "重估盈余\n影响 2.4pct", fontsize=8.8, color="#92400e",
        ha="center", va="bottom")
ax.text(0.99, -0.12, "注：2025 年投资重估盈余 133.12 亿元，占除税前溢利 26.81%；扣重估净利率按 16.27% 有效税率还原",
        transform=ax.transAxes, ha="right", fontsize=8.5, color="#64748b")
ax.text(0.99, -0.19, "数据来源：公司年报（东方财富港股 F10）", transform=ax.transAxes,
        ha="right", fontsize=8.5, color="#64748b")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "盈利能力与费用结构.png"), dpi=150, bbox_inches="tight", facecolor="white")
plt.close()

print("done")
