#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""研报组装主脚本"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from typing import List, Optional

from markdown_helpers import (
    cut_at_heading,
    cut_before_trailing_sections,
    demote_headings,
    ensure_blank_lines,
    extract_images,
    get_md_files,
    list_images_in_dir,
    read_file,
    number_subsection_headings,
    remove_images,
    strip_heading_numbering,
)


def parse_args():
    parser = argparse.ArgumentParser(description="组装最终深度研报")
    parser.add_argument("--code", required=True, help="目标公司股票代码")
    parser.add_argument("--name", required=True, help="目标公司名称")
    parser.add_argument("--industry", default="", help="所属行业")
    parser.add_argument("--input-dir", default="/workspace",
                        help="中间报告根目录")
    parser.add_argument("--output-dir", default="/workspace/final_output",
                        help="最终输出目录")
    parser.add_argument("--no-docx", action="store_true",
                        help="跳过 Word 转换")
    parser.add_argument("--single-report", default="",
                        help="单公司分析报告路径（覆盖默认查找路径）")
    parser.add_argument("--compare-report", default="",
                        help="对比分析报告路径（覆盖默认查找路径）")
    parser.add_argument("--recommendation", default="",
                        help="投资建议 Markdown 路径（替代内置通用评价）")
    parser.add_argument("--rating", default="",
                        help="投资评级，写入报告封面")
    parser.add_argument("--exec-summary", default="",
                        help="摘要 Markdown 路径（置于报告开头）")
    parser.add_argument("--extra-image-dir", action="append", default=[],
                        help="额外的图片来源目录，可重复指定")
    return parser.parse_args()


def find_file(base_dir: str, candidates: List[str]) -> Optional[str]:
    """从候选路径中找到第一个存在的文件"""
    for candidate in candidates:
        path = os.path.join(base_dir, candidate)
        if os.path.exists(path):
            return path
    return None


def extract_clean_section(content: str, skip_top_heading: bool = True) -> str:
    """提取内容并去掉顶级标题"""
    if not content:
        return ""
    lines = content.split("\n")
    if skip_top_heading and lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def copy_images_to_output(
    images: List[str],
    output_images_dir: str,
) -> List[str]:
    """复制图片到输出目录，返回新的图片相对路径列表"""
    os.makedirs(output_images_dir, exist_ok=True)
    copied = []
    for src in images:
        if not os.path.exists(src):
            continue
        filename = os.path.basename(src)
        dst = os.path.join(output_images_dir, filename)
        try:
            shutil.copy2(src, dst)
            copied.append(f"./images/{filename}")
        except Exception as e:
            print(f"  [警告] 复制图片失败 {src}: {e}")
    return copied


def normalize_image_paths(content: str, output_dir: str) -> str:
    """把图片路径规范化为 ./images/xxx 格式"""

    def replace(match):
        alt = match.group(1)
        path = match.group(2).strip()
        suffix = match.group(3)

        if path.startswith("http://") or path.startswith("https://"):
            return match.group(0)

        filename = os.path.basename(path)
        if not filename:
            return match.group(0)

        return f"![{alt}](./images/{filename}){suffix}"



    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)(\s*)")
    return pattern.sub(replace, content)


def build_summary_report(
    args,
    files: dict,
) -> str:
    """生成第一阶段汇总报告（各章节要点汇编）"""
    lines = []
    lines.append(f"# {args.name}（{args.code}）财务研报汇总")
    lines.append("")
    lines.append(f"- 报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 所属行业：{args.industry or '未指定'}")
    lines.append(f"- 投资评级：{args.rating or '待定'}")
    lines.append("")
    sections = [
        ("一", "公司基础信息", "company_info", "(暂无公司基础信息)", ""),
        ("二", "股权信息", "shareholder_info", "(暂无股权信息)", ""),
        ("三", "行业与竞争对手", "industry_info", "(暂无行业信息)", ""),
        ("四", "财务趋势分析（单公司）", "single_analysis", "(暂无单公司分析报告)", ""),
        ("五", "财务对比分析（同业）", "compare_analysis", "(暂无对比分析报告)", ""),
        ("六", "估值与预测", "valuation", "(暂无估值报告)", "### 投资评级"),
        ("七", "投资建议", "recommendation", "(暂无投资建议)", ""),
    ]
    for num, heading, key, placeholder, cut_marker in sections:
        lines.append(f"## {num}、{heading}")
        lines.append("")
        body = embed_section(files.get(key) or "", args.output_dir,
                             levels=1, drop_trailing=True,
                             cut_marker=cut_marker,
                             number_prefix=CN.get(num, ""))
        lines.append(body or placeholder)
        lines.append("")
    return "\n".join(lines)


def embed_section(
    filepath: str,
    output_dir: str,
    levels: int = 1,
    drop_top_heading: bool = True,
    drop_trailing: bool = False,
    cut_marker: str = "",
    number_prefix: str = "",
) -> str:
    """把子报告嵌入主报告：去顶级标题、降级标题、去序号、规范化图片路径"""
    content = read_file(filepath)
    if not content:
        return ""
    if drop_top_heading:
        content = extract_clean_section(content)
    if cut_marker:
        content = cut_at_heading(content, cut_marker)
    if drop_trailing:
        content = cut_before_trailing_sections(content)
    content = strip_heading_numbering(content)
    if number_prefix:
        content = number_subsection_headings(content, number_prefix)
    content = demote_headings(content, levels)
    content = normalize_image_paths(content, output_dir)
    # 图片路径规范化后需要与正文间留空行
    content = re.sub(r"(?<!\n)\n(!\[)", r"\n\n\1", content)
    content = re.sub(r"(\]\([^)]*\))\n(?!\n)", r"\1\n\n", content)
    return content.strip()


CN = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7"}


def build_deep_report(
    args,
    files: dict,
    output_dir: str,
) -> str:
    """生成最终深度研报"""
    lines = []
    lines.append(f"# {args.name}（{args.code}）深度财务研究报告")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("|---|---|")
    lines.append(f"| 证券代码 | {args.code} |")
    lines.append(f"| 所属行业 | {args.industry or '未指定'} |")
    lines.append(f"| 投资评级 | **{args.rating or '待综合分析后给出'}** |")
    lines.append(f"| 报告日期 | {datetime.now().strftime('%Y-%m-%d')} |")
    lines.append(f"| 分析框架 | 基本面 → 行业竞争 → 财务质量 → 同业对比 → 绝对/相对估值 |")
    lines.append("")
    lines.append("---")
    lines.append("")

    if files.get("exec_summary"):
        lines.append("## 摘要")
        lines.append("")
        body = embed_section(files["exec_summary"], output_dir, levels=1)
        if body:
            lines.append(body)
            lines.append("")

    # 一、公司概况
    lines.append("## 一、公司概况")
    lines.append("")
    for idx, (key, title, placeholder) in enumerate([
        ("company_info", "公司简介", "(暂无公司基础信息)"),
        ("business_info", "主营业务与核心竞争力", "(暂无主营业务信息)"),
        ("shareholder_info", "股权结构", "(暂无股权信息)"),
    ], start=1):
        lines.append(f"### 1.{idx} {title}")
        lines.append("")
        body = embed_section(files.get(key) or "", output_dir, levels=2)
        lines.append(body or placeholder)
        lines.append("")

    # 二、行业与竞争格局
    sections = [
        # (章序号, 章标题, 文件键, 占位文本, 截断标记)
        ("二", "行业与竞争格局", "industry_info", "(暂无行业信息)", ""),
        ("三", "财务分析", "single_analysis", "(暂无单公司分析报告)", ""),
        ("四", "同业对比分析", "compare_analysis", "(暂无对比分析报告)", ""),
        # 估值章只保留到"综合估值区间"，评级/风险/跟踪指标统一放在第六章
        ("五", "估值与预测", "valuation", "(暂无估值报告)", "### 投资评级"),
        ("六", "投资建议与风险提示", "recommendation", "(暂无投资建议)", ""),
    ]
    for num, heading, key, placeholder, cut_marker in sections:
        lines.append(f"## {num}、{heading}")
        lines.append("")
        body = embed_section(files.get(key) or "", output_dir, levels=1,
                             drop_trailing=True, cut_marker=cut_marker,
                             number_prefix=CN.get(num, ""))
        if body:
            lines.append(body)
        else:
            lines.append(placeholder)
            if key == "recommendation":
                lines.append("")
                lines.append(f"**评级**：{args.rating or '待定'}")
        lines.append("")

    # 七、数据来源与免责声明
    lines.append("## 七、数据来源与免责声明")
    lines.append("")
    lines.append("### 7.1 数据来源")
    lines.append("")
    lines.append("1. **财务报表**：公司 2020—2025 年年度报告及 2025/2026 年中期报告，经东方财富港股 F10（akshare `stock_financial_hk_report_em` / `stock_financial_hk_analysis_indicator_em`）采集")
    lines.append("2. **财务比率**：由 `financial_ratio_calculation` skill 基于三大报表计算，明细见 `data/financial_ratios/`")
    lines.append("3. **估值数据**：百度股市通（akshare `stock_hk_valuation_baidu`）")
    lines.append("4. **可比公司**：各公司年度报告，东方财富港股 F10")
    lines.append("5. **公司资料与分部数据**：同花顺港股 F10、东方财富港股 F10 公司概况")
    lines.append("")
    lines.append("### 7.2 口径说明与数据缺口")
    lines.append("")
    lines.append("- 金额单位统一为**人民币亿元**（1 亿元 = 1e8 元），估值指标以**港元**计价，换算采用 1 HKD ≈ 0.914 CNY 的近似汇率。")
    lines.append("- 本报告将**投资重估盈余**（2025 年 133.12 亿元、2026H1 73.06 亿元）视为非经常性损益，在估值与同口径盈利指标中予以剔除，详见第五章口径说明。")
    lines.append("- **数据缺口**：全球智能手机出货量与市场份额的第三方统计（IDC / Counterpoint）及港股 F10 股东名册明细在本次采集环境中无法访问，报告中未引用相关具体数字，第五章与第一章相关位置已作说明。")
    lines.append("")
    lines.append("### 7.3 免责声明")
    lines.append("")
    lines.append("本报告由自动化分析流程基于公开披露数据生成，仅供参考，不构成任何投资建议、买卖要约或收益承诺。报告中的评级、目标价与估值区间均为基于特定模型与假设的技术性结论，存在重大不确定性。历史数据不代表未来表现，预测数据可能因宏观环境、行业竞争、公司经营等因素发生重大偏差。投资者应结合自身风险承受能力与投资目标独立判断，并自行承担全部投资风险。")
    lines.append("")

    return "\n".join(lines)


def generate_docx(md_path: str, docx_path: str) -> bool:
    """调用 pandoc 生成 docx"""
    try:
        cmd = [
            "pandoc",
            md_path,
            "-o",
            docx_path,
            "--standalone",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ Word 文档已生成: {docx_path}")
            return True
        else:
            print(f"  [警告] pandoc 转换失败: {result.stderr}")
            return False
    except FileNotFoundError:
        print("  [警告] 未安装 pandoc，跳过 Word 转换")
        return False


def main():
    args = parse_args()
    args.input_dir = os.path.abspath(args.input_dir)
    args.output_dir = os.path.abspath(args.output_dir)

    os.makedirs(args.output_dir, exist_ok=True)
    images_dir = os.path.join(args.output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    print("=" * 60)
    print("研报组装任务")
    print("=" * 60)
    print(f"目标公司: {args.name} ({args.code})")
    print(f"所属行业: {args.industry}")
    print(f"输入目录: {args.input_dir}")
    print(f"输出目录: {args.output_dir}")
    print("=" * 60)

    # 1. 定位所有输入文件
    print("\n[1/4] 定位输入文件...")
    files = {
        "company_info": find_file(args.input_dir, [
            f"data/report/公司信息数据.md",
            "data/report/公司信息.md",
        ]),
        "business_info": find_file(args.input_dir, [
            "data/report/主营业务与核心竞争力.md",
            "data/report/主营业务.md",
        ]),
        "shareholder_info": find_file(args.input_dir, [
            "data/report/股东信息数据.md",
            "data/report/股东信息.md",
        ]),
        "industry_info": find_file(args.input_dir, [
            "data/report/竞争对手与行业均值数据.md",
            "data/report/行业分析.md",
        ]),
        "single_analysis": (args.single_report
                            if args.single_report and os.path.exists(args.single_report)
                            else find_file(args.input_dir, [
                                f"analyze_agent_outputs/{args.code}_{args.name}/最终分析报告.md",
                            ])),
        "compare_analysis": (args.compare_report
                             if args.compare_report and os.path.exists(args.compare_report)
                             else find_file(args.input_dir, [
                                 f"compare_company_report_outputs/{args.code}_{args.name}_vs_competitors/最终分析报告.md",
                             ])),
        "valuation": find_file(args.input_dir, [
            "data/report/估值与预测模型.md",
            "data/report/估值报告.md",
        ]),
        "exec_summary": (args.exec_summary
                         if args.exec_summary and os.path.exists(args.exec_summary)
                         else None),
        "recommendation": (args.recommendation
                           if args.recommendation and os.path.exists(args.recommendation)
                           else find_file(args.input_dir, [
                               "data/report/投资建议.md",
                           ])),
    }
    for key, path in files.items():
        if path:
            print(f"  ✅ {key}: {path}")
        else:
            print(f"  ⚠️ {key}: 未找到")

    # 2. 复制所有图片
    print("\n[2/4] 复制图片...")
    all_images = []
    image_dirs = [
        f"analyze_agent_outputs/{args.code}_{args.name}",
        f"compare_company_report_outputs/{args.code}_{args.name}_vs_competitors",
    ] + list(args.extra_image_dir)
    for d in image_dirs:
        full_path = os.path.join(args.input_dir, d)
        if os.path.exists(full_path):
            all_images.extend(list_images_in_dir(full_path))
    copied = copy_images_to_output(all_images, images_dir)
    print(f"  复制了 {len(copied)} 张图片到 {images_dir}")

    # 3. 生成汇总报告和深度研报
    print("\n[3/4] 生成 Markdown 研报...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    summary_md = build_summary_report(args, files)
    summary_path = os.path.join(args.output_dir, f"财务研报汇总_{timestamp}.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_md)
    print(f"  ✅ 汇总报告: {summary_path}")

    deep_md = build_deep_report(args, files, args.output_dir)
    deep_path = os.path.join(args.output_dir, f"深度财务研报分析_{timestamp}.md")
    with open(deep_path, "w", encoding="utf-8") as f:
        f.write(deep_md)
    print(f"  ✅ 深度研报: {deep_path}")

    # 4. 可选：转换为 Word
    if not args.no_docx:
        print("\n[4/4] 转换为 Word...")
        docx_path = deep_path.replace(".md", ".docx")
        generate_docx(deep_path, docx_path)
    else:
        print("\n[4/4] 跳过 Word 转换")

    print("\n" + "=" * 60)
    print("✅ 研报组装完成")
    print(f"输出目录: {args.output_dir}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())