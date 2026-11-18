# -*- coding: utf-8 -*-
"""财务图表生成工具函数"""
import os
import warnings
from typing import List, Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

CHINESE_FONTS = [
    "SimHei",
    "PingFang SC",
    "Hiragino Sans GB",
    "Heiti SC",
    "Noto Sans CJK JP",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "STHeiti",
    "Songti SC",
    "DejaVu Sans",
]


def setup_chinese_font():
    """设置支持中文的 matplotlib 字体"""
    plt.rcParams["axes.unicode_minus"] = False
    available_fonts = set(f.name for f in matplotlib.font_manager.fontManager.ttflist)
    for font in CHINESE_FONTS:
        if font in available_fonts:
            plt.rcParams["font.family"] = [font]
            return font
    warnings.warn("未找到合适的中文字体，图表中的中文可能显示为方框")
    return None


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def load_ratio_csv(filepath: str) -> Optional[pd.DataFrame]:
    """加载单张财务比率 CSV"""
    if not os.path.exists(filepath):
        return None
    try:
        return pd.read_csv(filepath, encoding="utf-8-sig")
    except Exception as e:
        print(f"[错误] 读取 {filepath} 失败: {e}")
        return None


def load_company_ratios(code: str, years: List[str], input_dir: str) -> pd.DataFrame:
    """加载一家公司多年度的财务比率"""
    rows = []
    for year in years:
        filename = f"{code}_{year}年度财务计算结果.csv"
        filepath = os.path.join(input_dir, filename)
        df = load_ratio_csv(filepath)
        if df is not None and not df.empty:
            rows.append(df)
    if not rows:
        return pd.DataFrame()
    combined = pd.concat(rows, ignore_index=True)
    if "年份" in combined.columns:
        combined["年份"] = combined["年份"].astype(str)
    return combined


METRIC_GROUPS = {
    "盈利能力": {
        "metrics": ["毛利率", "净利率"],
        "y_label": "比率",
        "format": "{:.1%}",
    },
    "偿债能力": {
        "metrics": ["资产负债率", "流动比率", "速动比率"],
        "y_label": "比率",
        "format": "{:.2f}",
    },
    "运营能力": {
        "metrics": ["总资产周转率", "应收账款周转天数", "存货周转天数"],
        "y_label": "数值",
        "format": "{:.2f}",
    },
    "现金流能力": {
        "metrics": ["现金流匹配度", "销售现金比率"],
        "y_label": "比率",
        "format": "{:.2f}",
    },
}


def _format_value(value, fmt: str) -> str:
    """格式化数值用于图表标签"""
    if pd.isna(value):
        return ""
    try:
        return fmt.format(float(value))
    except (ValueError, TypeError):
        return str(value)


def draw_trend_chart(
    company_name: str,
    company_code: str,
    years: List[str],
    input_dir: str,
    metrics: List[str],
    group_name: str,
    output_path: str,
) -> bool:
    """
    绘制单公司多年度趋势图（折线图）
    """
    ensure_dir(os.path.dirname(output_path))

    valid_metrics = [m for m in metrics if m]
    if not valid_metrics:
        print(f"[跳过] {group_name}:无可用指标")
        return False

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    plotted = False
    for idx, metric in enumerate(valid_metrics):
        values = []
        valid_years = []
        for year in years:
            filename = f"{company_code}_{year}年度财务计算结果.csv"
            filepath = os.path.join(input_dir, filename)
            df = load_ratio_csv(filepath)
            if df is None or df.empty or metric not in df.columns:
                continue
            value = df[metric].iloc[0]
            if pd.notna(value):
                try:
                    values.append(float(value))
                    valid_years.append(year)
                except (ValueError, TypeError):
                    pass

        if values:
            ax.plot(
                valid_years,
                values,
                marker="o",
                linewidth=2,
                markersize=8,
                color=colors[idx % len(colors)],
                label=metric,
            )
            fmt = METRIC_GROUPS.get(group_name, {}).get("format", "{:.2f}")
            for x, y in zip(valid_years, values):
                ax.annotate(
                    _format_value(y, fmt),
                    (x, y),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha="center",
                    fontsize=9,
                )
            plotted = True

    if not plotted:
        plt.close()
        print(f"[跳过] {group_name}:无有效数据")
        return False

    ax.set_title(f"{company_name} {group_name}指标趋势分析", fontsize=16, fontweight="bold")
    ax.set_xlabel("年份", fontsize=12)
    ax.set_ylabel(METRIC_GROUPS.get(group_name, {}).get("y_label", "数值"), fontsize=12)
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  ✅ 已生成: {output_path}")
    return True


def draw_comparison_chart(
    target_name: str,
    target_code: str,
    competitors: List[dict],
    latest_year: str,
    input_dir: str,
    metrics: List[str],
    group_name: str,
    output_path: str,
) -> bool:
    """
    绘制多公司对比图（柱状图）
    """
    ensure_dir(os.path.dirname(output_path))

    valid_metrics = [m for m in metrics if m]
    if not valid_metrics:
        print(f"[跳过] {group_name}:无可用指标")
        return False

    companies = [(target_name, target_code)]
    for c in competitors:
        companies.append((c["stock_name"], c["stock_code"]))

    data = {m: [] for m in valid_metrics}
    company_labels = []

    for comp_name, comp_code in companies:
        company_labels.append(comp_name)
        filename = f"{comp_code}_{latest_year}年度财务计算结果.csv"
        filepath = os.path.join(input_dir, filename)
        df = load_ratio_csv(filepath)
        for m in valid_metrics:
            if df is not None and not df.empty and m in df.columns:
                value = df[m].iloc[0]
                try:
                    data[m].append(float(value) if pd.notna(value) else 0)
                except (ValueError, TypeError):
                    data[m].append(0)
            else:
                data[m].append(0)

    n_groups = len(companies)
    n_metrics = len(valid_metrics)
    bar_width = 0.8 / n_metrics
    x = range(n_groups)

    fig, ax = plt.subplots(figsize=(14, 7))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    for i, metric in enumerate(valid_metrics):
        offset = (i - (n_metrics - 1) / 2) * bar_width
        positions = [xi + offset for xi in x]
        bars = ax.bar(
            positions,
            data[metric],
            bar_width,
            color=colors[i % len(colors)],
            label=metric,
        )
        fmt = METRIC_GROUPS.get(group_name, {}).get("format", "{:.2f}")
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                _format_value(height, fmt),
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )

    ax.set_title(f"{group_name}对比分析({latest_year}年)", fontsize=16, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(company_labels, rotation=15, ha="right", fontsize=10)
    ax.set_ylabel(METRIC_GROUPS.get(group_name, {}).get("y_label", "数值"), fontsize=12)
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  ✅ 已生成: {output_path}")
    return True