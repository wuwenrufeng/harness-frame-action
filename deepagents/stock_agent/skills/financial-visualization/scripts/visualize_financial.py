#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""财务可视化主脚本"""
import argparse
import json
import os
import sys
from typing import List, Optional

from chart_generator import (
    METRIC_GROUPS,
    draw_comparison_chart,
    draw_trend_chart,
    ensure_dir,
    load_ratio_csv,
    setup_chinese_font,
)


GROUP_INTROS = {
    "盈利能力": "盈利能力反映公司通过经营获取利润的能力。",
    "偿债能力": "偿债能力反映公司偿还短期和长期债务的能力。",
    "运营能力": "运营能力反映公司利用资产创造收入的效率。",
    "现金流能力": "现金流能力反映公司经营活动产生现金的能力。",
}


def parse_args():
    parser = argparse.ArgumentParser(description="生成财务分析图表和报告")
    parser.add_argument("--code", required=True, help="目标公司股票代码")
    parser.add_argument("--name", required=True, help="目标公司名称")
    parser.add_argument("--years", required=True, nargs="+", help="分析年份列表")
    parser.add_argument("--input-dir", default="/workspace/data/financial_caculates",
                        help="比率 CSV 输入目录")
    parser.add_argument("--output-dir", default="/workspace/analyze_agent_outputs",
                        help="单公司分析输出目录")
    parser.add_argument("--compare-output-dir", default="/workspace/compare_company_report_outputs",
                        help="对比分析输出目录")
    parser.add_argument("--competitors", default="/workspace/data/report/competitors.json",
                        help="竞争对手 JSON 文件路径")
    parser.add_argument("--mode", choices=["single", "compare", "both"], default="both",
                        help="生成模式: single 仅单公司, compare 仅对比, both 全部")
    return parser.parse_args()


def generate_trend_charts(args) -> List[str]:
    """生成单公司趋势图"""
    output_dir = os.path.join(args.output_dir, f"{args.code}_{args.name}")
    ensure_dir(output_dir)
    print(f"\n[单公司趋势分析] 输出目录: {output_dir}")

    generated = []
    for group_name, group_config in METRIC_GROUPS.items():
        output_path = os.path.join(
            output_dir, f"{args.name}{group_name}指标趋势分析.png"
        )
        success = draw_trend_chart(
            company_name=args.name,
            company_code=args.code,
            years=args.years,
            input_dir=args.input_dir,
            metrics=group_config["metrics"],
            group_name=group_name,
            output_path=output_path,
        )
        if success:
            generated.append(output_path)

    return generated


def generate_comparison_charts(args) -> List[str]:
    """生成对比分析图"""
    competitors = load_competitors(args.competitors)
    if not competitors:
        print("\n[跳过对比分析] 未提供有效的 competitors.json")
        return []

    output_dir = os.path.join(
        args.compare_output_dir, f"{args.code}_{args.name}_vs_competitors"
    )
    ensure_dir(output_dir)
    print(f"\n[对比分析] 输出目录: {output_dir}")
    print(f"  对手公司: {[c.get('stock_name') for c in competitors]}")

    latest_year = args.years[-1]
    generated = []
    for group_name, group_config in METRIC_GROUPS.items():
        output_path = os.path.join(output_dir, f"{group_name}对比分析.png")
        success = draw_comparison_chart(
            target_name=args.name,
            target_code=args.code,
            competitors=competitors,
            latest_year=latest_year,
            input_dir=args.input_dir,
            metrics=group_config["metrics"],
            group_name=group_name,
            output_path=output_path,
        )
        if success:
            generated.append(output_path)

    return generated


def load_competitors(filepath: str) -> List[dict]:
    """加载竞争对手列表"""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        competitors = data.get("competitors", [])
        return [c for c in competitors if c.get("stock_code") and c.get("stock_name")]
    except Exception as e:
        print(f"[警告] 读取 competitors 失败: {e}")
        return []


def write_trend_report(args, chart_paths: List[str]) -> str:
    """写入单公司趋势 Markdown 报告"""
    output_dir = os.path.join(args.output_dir, f"{args.code}_{args.name}")
    report_path = os.path.join(output_dir, "最终分析报告.md")

    lines = [
        f"# {args.name}财务指标趋势分析报告",
        "",
        f"分析期间: {args.years[0]} - {args.years[-1]}",
        f"股票代码: {args.code}",
        "",
    ]

    section_map = {
        "盈利能力": "一、盈利能力",
        "偿债能力": "二、偿债能力",
        "运营能力": "三、运营能力",
        "现金流能力": "四、现金流能力",
    }

    for group_name, section_title in section_map.items():
        chart_filename = f"{args.name}{group_name}指标趋势分析.png"
        chart_path = os.path.join(output_dir, chart_filename)
        if chart_path in chart_paths:
            lines.append(f"## {section_title}指标趋势")
            lines.append(f"![{group_name}指标趋势分析](./{chart_filename})")
            lines.append("")
            lines.append(f"{GROUP_INTROS.get(group_name, '')}以下分析基于图表数据。")
            lines.append("")

    lines.append("## 五、数据来源")
    lines.append(f"- 数据来源: 东方财富-数据中心-年报季报-业绩快报")
    lines.append(f"- 数据加工: financial_ratio_calculation skill")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✅ 已生成: {report_path}")
    return report_path


def write_comparison_report(args, chart_paths: List[str]) -> str:
    """写入对比分析 Markdown 报告"""
    competitors = load_competitors(args.competitors)
    output_dir = os.path.join(
        args.compare_output_dir, f"{args.code}_{args.name}_vs_competitors"
    )
    report_path = os.path.join(output_dir, "最终分析报告.md")

    lines = [
        f"# {args.name}与竞争对手财务指标对比分析报告",
        "",
        f"对比年份: {args.years[-1]}",
        f"目标公司: {args.name} ({args.code})",
        f"对比公司: {', '.join([c.get('stock_name', '') for c in competitors])}",
        "",
    ]

    section_map = {
        "盈利能力": "一、盈利能力对比",
        "偿债能力": "二、偿债能力对比",
        "运营能力": "三、运营能力对比",
        "现金流能力": "四、现金流能力对比",
    }

    for group_name, section_title in section_map.items():
        chart_filename = f"{group_name}对比分析.png"
        chart_path = os.path.join(output_dir, chart_filename)
        if chart_path in chart_paths:
            lines.append(f"## {section_title}")
            lines.append(f"![{section_title}](./{chart_filename})")
            lines.append("")
            lines.append(f"{GROUP_INTROS.get(group_name, '')}以下分析基于图表数据。")
            lines.append("")

    lines.append("## 五、数据来源")
    lines.append(f"- 数据来源: 东方财富-数据中心-年报季报-业绩快报")
    lines.append(f"- 数据加工: financial_ratio_calculation skill")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✅ 已生成: {report_path}")
    return report_path


def main():
    args = parse_args()
    args.input_dir = os.path.abspath(args.input_dir)
    args.output_dir = os.path.abspath(args.output_dir)
    args.compare_output_dir = os.path.abspath(args.compare_output_dir)
    if args.competitors:
        args.competitors = os.path.abspath(args.competitors)

    print("=" * 60)
    print("财务可视化任务")
    print("=" * 60)
    print(f"目标公司: {args.name} ({args.code})")
    print(f"分析年份: {args.years}")
    print(f"输入目录: {args.input_dir}")
    print(f"输出模式: {args.mode}")
    print("=" * 60)

    setup_chinese_font()

    trend_charts = []
    compare_charts = []

    if args.mode in ("single", "both"):
        trend_charts = generate_trend_charts(args)
        if trend_charts:
            write_trend_report(args, trend_charts)

    if args.mode in ("compare", "both"):
        compare_charts = generate_comparison_charts(args)
        if compare_charts:
            write_comparison_report(args, compare_charts)

    print("\n" + "=" * 60)
    print("任务完成")
    print(f"单公司趋势图: {len(trend_charts)} 张")
    print(f"对比分析图: {len(compare_charts)} 张")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())