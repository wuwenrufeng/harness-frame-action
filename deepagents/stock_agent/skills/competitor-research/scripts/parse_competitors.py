#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从竞争对手研究 Markdown 报告中提取结构化 competitor 列表

用法示例：
    python skills/competitor_research/scripts/parse_competitors.py \
        --input /workspace/data/report/竞争对手与行业均值数据.md \
        --output /workspace/data/report/competitors.json \
        --target-code 600519 \
        --target-name 贵州茅台
"""

import argparse
import json
import os
import re
import sys
from typing import Optional


def extract_json_block(content: str) -> Optional[dict]:
    """
    尝试从 Markdown 内容中提取 ```json 代码块
    """
    pattern = re.compile(r"```json\s*([\s\S]*?)\s*```", re.IGNORECASE)
    matches = pattern.findall(content)

    for match in matches:
        try:
            data = json.loads(match.strip())
            if "competitors" in data:
                return data
        except json.JSONDecodeError:
            continue
    return None


def clean_stock_code(code: str) -> str:
    """
    清洗股票代码：去掉 SH/SZ/HK 前缀和空格，返回纯数字
    """
    code = str(code).strip().upper()
    code = re.sub(r"^(SH|SZ|HK)", "", code)
    code = re.sub(r"[^0-9]", "", code)
    return code


def normalize_market(market: str) -> str:
    """
    标准化市场名称
    """
    market = str(market).strip()
    if "港" in market:
        return "港股"
    return "A股"


def extract_competitors_from_table(content: str) -> list[dict]:
    """
    从 Markdown 表格中提取 competitor 列表
    支持多种表头写法
    """
    competitors = []

    # 查找包含股票代码和公司名称的表格
    table_pattern = re.compile(
        r"\|([^\n]+)\|\n\|[-:\|\s]+\|\n((?:\|[^\n]+\|\n?)+)",
        re.MULTILINE,
    )

    for header, body in table_pattern.findall(content):
        headers = [h.strip() for h in header.split("|") if h.strip()]
        header_lower = [h.lower() for h in headers]

        # 判断是否为目标表格：包含股票代码/公司名称相关列
        has_code = any(
            keyword in " ".join(header_lower)
            for keyword in ["股票代码", "代码", "stock_code", "股票代码"]
        )
        has_name = any(
            keyword in " ".join(header_lower)
            for keyword in ["公司名称", "公司", "stock_name", "名称", "简称"]
        )

        if not (has_code or has_name):
            continue

        code_idx = None
        name_idx = None
        market_idx = None

        for i, h in enumerate(headers):
            h_lower = h.lower()
            if code_idx is None and any(
                kw in h_lower for kw in ["代码", "code", "股票代码"]
            ):
                code_idx = i
            if name_idx is None and any(
                kw in h_lower for kw in ["公司", "name", "名称", "简称"]
            ):
                name_idx = i
            if market_idx is None and any(
                kw in h_lower for kw in ["市场", "market", "交易所"]
            ):
                market_idx = i

        for line in body.strip().split("\n"):
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]  # 去掉空单元格

            if not cells:
                continue

            code = ""
            name = ""
            market = "A股"

            if code_idx is not None and code_idx < len(cells):
                code = clean_stock_code(cells[code_idx])
            if name_idx is not None and name_idx < len(cells):
                name = cells[name_idx]
            if market_idx is not None and market_idx < len(cells):
                market = normalize_market(cells[market_idx])

            # 如果没有代码但有公司名称，尝试从单元格内容提取 6 位数字代码
            if not code and name:
                code_match = re.search(r"\b(\d{5,6})\b", " ".join(cells))
                if code_match:
                    code = code_match.group(1)

            if code and name and len(code) >= 5:
                competitors.append(
                    {
                        "stock_code": code,
                        "stock_name": name,
                        "market": market,
                    }
                )

    return competitors


def extract_competitors_from_lists(content: str) -> list[dict]:
    """
    从 Markdown 列表中提取 competitor（兜底方案）
    例如：- 五粮液（000858.SZ）
    """
    competitors = []
    seen = set()

    # 匹配模式：公司名称（代码） 或 代码 公司名称
    patterns = [
        r"[-*]\s*([^（\(\n]+?)\s*[（(](\d{5,6})[）)]",
        r"[-*]\s*(\d{5,6})\s*[：:]\s*([^\n]+)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            if "（" in match.group(0) or "(" in match.group(0):
                name = match.group(1).strip()
                code = match.group(2).strip()
            else:
                code = match.group(1).strip()
                name = match.group(2).strip()

            code = clean_stock_code(code)
            name = re.split(r"[，,。；;]", name)[0].strip()

            if code and name and code not in seen and len(code) >= 5:
                seen.add(code)
                competitors.append(
                    {
                        "stock_code": code,
                        "stock_name": name,
                        "market": "A股",
                    }
                )

    return competitors


def extract_industry(content: str) -> str:
    """
    尝试提取行业名称
    """
    patterns = [
        r"行业名称[：:]\s*([^\n]+)",
        r"所属行业[：:]\s*([^\n]+)",
        r"行业[：:]\s*([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
    return ""


def deduplicate_competitors(competitors: list[dict]) -> list[dict]:
    """
    按股票代码去重
    """
    seen = set()
    result = []
    for c in competitors:
        code = c.get("stock_code", "")
        if code and code not in seen:
            seen.add(code)
            result.append(c)
    return result


def parse_competitors(
    input_path: str,
    output_path: str,
    target_code: str,
    target_name: str,
) -> dict:
    """
    主解析函数
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 优先尝试提取 JSON 代码块
    result = extract_json_block(content)

    if result:
        competitors = result.get("competitors", [])
        industry = result.get("industry", "")
    else:
        # 从表格提取
        competitors = extract_competitors_from_table(content)
        if not competitors:
            # 兜底：从列表提取
            competitors = extract_competitors_from_lists(content)
        industry = extract_industry(content)

    # 清洗和去重
    cleaned = []
    for c in competitors:
        code = clean_stock_code(c.get("stock_code", ""))
        name = c.get("stock_name", "").strip()
        market = normalize_market(c.get("market", "A股"))

        # 排除目标公司自己
        if code == clean_stock_code(target_code):
            continue
        if not code or not name:
            continue

        cleaned.append(
            {
                "stock_code": code,
                "stock_name": name,
                "market": market,
            }
        )

    cleaned = deduplicate_competitors(cleaned)

    output = {
        "competitors": cleaned,
        "industry": industry,
        "target_company": target_name,
        "target_code": clean_stock_code(target_code),
    }

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output


def parse_args():
    parser = argparse.ArgumentParser(
        description="从竞争对手研究 Markdown 中提取结构化 competitor 列表"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="输入的 Markdown 文件路径",
    )
    parser.add_argument(
        "--output",
        default="/workspace/data/report/competitors.json",
        help="输出的 JSON 文件路径，默认 /workspace/data/report/competitors.json",
    )
    parser.add_argument(
        "--target-code",
        required=True,
        help="目标公司股票代码，例如 600519",
    )
    parser.add_argument(
        "--target-name",
        required=True,
        help="目标公司名称，例如 贵州茅台",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"[开始] 解析竞争对手报告: {args.input}")

    try:
        result = parse_competitors(
            input_path=args.input,
            output_path=args.output,
            target_code=args.target_code,
            target_name=args.target_name,
        )

        print(f"[完成] 共提取 {len(result['competitors'])} 家竞争对手")
        for c in result["competitors"]:
            print(f"  - {c['stock_name']} ({c['stock_code']}, {c['market']})")
        print(f"[保存] {args.output}")
        return 0

    except Exception as e:
        print(f"[错误] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
