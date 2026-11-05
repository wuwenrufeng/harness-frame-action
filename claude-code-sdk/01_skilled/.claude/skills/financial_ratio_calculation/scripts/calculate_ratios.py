#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务比率计算主脚本

用法示例：
    python skills/financial_ratio_calculation/scripts/calculate_ratios.py \
        --code 600519 \
        --name 贵州茅台 \
        --year 2024 \
        --input-dir /workspace/data/financial_statements \
        --output-dir /workspace/data/financial_caculates
"""

import argparse
import json
import os
import sys
from typing import Optional

import pandas as pd


# ========== 字段映射配置 ==========
# 每个概念对应多个可能的列名，按优先级排列
FIELD_ALIASES = {
    # 利润表
    "operate_income": ["TOTAL_OPERATE_INCOME", "OPERATE_INCOME"],
    "operate_cost": ["OPERATE_COST"],
    "net_profit": ["NETPROFIT", "PARENT_NETPROFIT", "TOTAL_PROFIT"],

    # 资产负债表
    "total_assets": ["TOTAL_ASSETS"],
    "total_liabilities": ["TOTAL_LIABILITIES"],
    "current_assets": ["TOTAL_CURRENT_ASSETS"],
    "current_liabilities": ["TOTAL_CURRENT_LIAB"],
    "inventory": ["INVENTORY"],
    "prepayment": ["PREPAYMENT"],
    "accounts_rece": ["ACCOUNTS_RECE"],
    "notes_rece": ["NOTE_ACCOUNTS_RECE", "NOTE_RECE"],

    # 现金流量表
    "net_cash_operate": ["NETCASH_OPERATE"],
}


# ========== 计算公式 ==========

def calculate_gross_profit_margin(operating_income: float, operating_cost: float) -> Optional[float]:
    """毛利率 = (营业收入 - 营业成本) / 营业收入"""
    if operating_income == 0:
        return None
    return (operating_income - operating_cost) / operating_income


def calculate_net_profit_margin(net_profit: float, operating_income: float) -> Optional[float]:
    """净利率 = 净利润 / 营业收入"""
    if operating_income == 0:
        return None
    return net_profit / operating_income


def calculate_debt_to_asset_ratio(total_liabilities: float, total_assets: float) -> Optional[float]:
    """资产负债率 = 总负债 / 总资产"""
    if total_assets == 0:
        return None
    return total_liabilities / total_assets


def calculate_current_ratio(current_assets: float, current_liabilities: float) -> Optional[float]:
    """流动比率 = 流动资产 / 流动负债"""
    if current_liabilities == 0:
        return None
    return current_assets / current_liabilities


def calculate_quick_ratio(
    current_assets: float,
    inventory: float,
    prepayment: float,
    current_liabilities: float,
) -> Optional[float]:
    """速动比率 = (流动资产 - 存货 - 预付账款) / 流动负债"""
    if current_liabilities == 0:
        return None
    return (current_assets - inventory - prepayment) / current_liabilities


def calculate_total_asset_turnover(operating_income: float, average_total_assets: float) -> Optional[float]:
    """总资产周转率 = 营业收入 / 平均总资产"""
    if average_total_assets == 0:
        return None
    return operating_income / average_total_assets


def calculate_receivables_turnover_days(
    operating_income: float, average_net_receivables: float
) -> Optional[float]:
    """应收账款周转天数 = 365 / (营业收入 / 平均应收账款)"""
    if average_net_receivables == 0:
        return None
    turnover_ratio = operating_income / average_net_receivables
    if turnover_ratio == 0:
        return None
    return 365 / turnover_ratio


def calculate_inventory_turnover_days(
    cost_of_goods_sold: float, average_inventory: float
) -> Optional[float]:
    """存货周转天数 = 365 / (营业成本 / 平均存货)"""
    if average_inventory == 0:
        return None
    turnover_ratio = cost_of_goods_sold / average_inventory
    if turnover_ratio == 0:
        return None
    return 365 / turnover_ratio


def calculate_cash_flow_matching_ratio(
    net_cash_flow_from_operating_activities: float, net_profit: float
) -> Optional[float]:
    """现金流匹配度 = 经营活动现金流净额 / 净利润"""
    if net_profit == 0:
        return None
    return net_cash_flow_from_operating_activities / net_profit


def calculate_sales_cash_ratio(
    net_cash_flow_from_operating_activities: float, operating_income: float
) -> Optional[float]:
    """销售现金比率 = 经营活动现金流净额 / 营业收入"""
    if operating_income == 0:
        return None
    return net_cash_flow_from_operating_activities / operating_income


def calculate_equity_multiplier(asset_liability_ratio: float) -> Optional[float]:
    """权益乘数 = 1 / (1 - 资产负债率)"""
    if asset_liability_ratio is None or asset_liability_ratio >= 1:
        return None
    return 1 / (1 - asset_liability_ratio)


# ========== 数据读取 ==========

def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def load_statement(input_dir: str, code: str, year: str, statement_type: str) -> Optional[pd.DataFrame]:
    """
    加载单张报表 CSV
    statement_type: 资产负债表 / 利润表 / 现金流量表
    """
    filename = f"{code}_{year}_{statement_type}.csv"
    filepath = os.path.join(input_dir, filename)
    if not os.path.exists(filepath):
        return None
    try:
        return pd.read_csv(filepath, encoding="utf-8-sig")
    except Exception as e:
        print(f"[错误] 读取 {filepath} 失败: {e}")
        return None


def get_value(df: Optional[pd.DataFrame], aliases: list[str]) -> Optional[float]:
    """
    从 DataFrame 中按别名列表获取第一个非空值
    """
    if df is None or df.empty:
        return None

    for alias in aliases:
        if alias in df.columns:
            value = df[alias].iloc[0]
            if pd.notna(value):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
    return None


def get_value_with_fallback(values: dict, key: str, fallback_keys: list[str]) -> Optional[float]:
    """从 values 字典中获取值，支持 fallback"""
    keys = [key] + fallback_keys
    for k in keys:
        if k in values and values[k] is not None:
            return values[k]
    return None


# ========== 主计算逻辑 ==========

def calculate_financial_ratios(
    code: str,
    name: str,
    year: str,
    input_dir: str,
    output_dir: str,
) -> dict:
    """
    计算一家公司单年度的财务比率
    """
    ensure_dir(output_dir)
    results = {"success": False, "ratios": {}, "errors": [], "warnings": []}

    # 加载本年报表
    df_zcfz = load_statement(input_dir, code, year, "资产负债表")
    df_lrb = load_statement(input_dir, code, year, "利润表")
    df_xjll = load_statement(input_dir, code, year, "现金流量表")

    if df_zcfz is None:
        results["errors"].append(f"缺少资产负债表: {code}_{year}")
    if df_lrb is None:
        results["errors"].append(f"缺少利润表: {code}_{year}")
    if df_xjll is None:
        results["errors"].append(f"缺少现金流量表: {code}_{year}")

    if results["errors"]:
        return results

    # 尝试加载上年报表（用于计算平均值）
    prev_year = str(int(year) - 1)
    df_zcfz_prev = load_statement(input_dir, code, prev_year, "资产负债表")
    df_lrb_prev = load_statement(input_dir, code, prev_year, "利润表")

    if df_zcfz_prev is None:
        results["warnings"].append(f"缺少上年({prev_year})资产负债表，平均值使用本年数据")
    if df_lrb_prev is None:
        results["warnings"].append(f"缺少上年({prev_year})利润表，平均值使用本年数据")

    # 提取本年数值
    values = {
        "operate_income": get_value(df_lrb, FIELD_ALIASES["operate_income"]),
        "operate_cost": get_value(df_lrb, FIELD_ALIASES["operate_cost"]),
        "net_profit": get_value(df_lrb, FIELD_ALIASES["net_profit"]),
        "total_assets": get_value(df_zcfz, FIELD_ALIASES["total_assets"]),
        "total_liabilities": get_value(df_zcfz, FIELD_ALIASES["total_liabilities"]),
        "current_assets": get_value(df_zcfz, FIELD_ALIASES["current_assets"]),
        "current_liabilities": get_value(df_zcfz, FIELD_ALIASES["current_liabilities"]),
        "inventory": get_value(df_zcfz, FIELD_ALIASES["inventory"]),
        "prepayment": get_value(df_zcfz, FIELD_ALIASES["prepayment"]),
        "accounts_rece": get_value(df_zcfz, FIELD_ALIASES["accounts_rece"]),
        "notes_rece": get_value(df_zcfz, FIELD_ALIASES["notes_rece"]),
        "net_cash_operate": get_value(df_xjll, FIELD_ALIASES["net_cash_operate"]),
    }

    # 提取上年数值
    prev_values = {
        "total_assets": get_value(df_zcfz_prev, FIELD_ALIASES["total_assets"]),
        "inventory": get_value(df_zcfz_prev, FIELD_ALIASES["inventory"]),
        "accounts_rece": get_value(df_zcfz_prev, FIELD_ALIASES["accounts_rece"]),
        "notes_rece": get_value(df_zcfz_prev, FIELD_ALIASES["notes_rece"]),
    }

    # 默认值处理
    values["inventory"] = values["inventory"] or 0
    values["prepayment"] = values["prepayment"] or 0
    values["accounts_rece"] = values["accounts_rece"] or 0
    values["notes_rece"] = values["notes_rece"] or 0

    # 检查必要字段
    required_fields = ["operate_income", "operate_cost", "net_profit", "total_assets"]
    for field in required_fields:
        if values.get(field) is None:
            results["errors"].append(f"缺少必要字段: {field}")

    if results["errors"]:
        return results

    # 计算平均值
    avg_total_assets = values["total_assets"]
    if prev_values["total_assets"] is not None:
        avg_total_assets = (values["total_assets"] + prev_values["total_assets"]) / 2
    else:
        results["warnings"].append("使用本年总资产作为平均总资产")

    avg_inventory = values["inventory"]
    if prev_values["inventory"] is not None:
        avg_inventory = (values["inventory"] + prev_values["inventory"]) / 2

    receivables_current = values["accounts_rece"] + values["notes_rece"]
    receivables_prev = prev_values["accounts_rece"] or 0
    if prev_values["notes_rece"] is not None:
        receivables_prev += prev_values["notes_rece"]

    avg_receivables = receivables_current
    if prev_values["accounts_rece"] is not None or prev_values["notes_rece"] is not None:
        avg_receivables = (receivables_current + receivables_prev) / 2

    # 计算比率
    ratios = {}

    ratios["毛利率"] = calculate_gross_profit_margin(
        values["operate_income"], values["operate_cost"]
    )
    ratios["净利率"] = calculate_net_profit_margin(
        values["net_profit"], values["operate_income"]
    )
    ratios["资产负债率"] = calculate_debt_to_asset_ratio(
        values["total_liabilities"], values["total_assets"]
    )
    ratios["流动比率"] = calculate_current_ratio(
        values["current_assets"], values["current_liabilities"]
    )
    ratios["速动比率"] = calculate_quick_ratio(
        values["current_assets"],
        values["inventory"],
        values["prepayment"],
        values["current_liabilities"],
    )
    ratios["总资产周转率"] = calculate_total_asset_turnover(
        values["operate_income"], avg_total_assets
    )
    ratios["应收账款周转天数"] = calculate_receivables_turnover_days(
        values["operate_income"], avg_receivables
    )
    ratios["存货周转天数"] = calculate_inventory_turnover_days(
        values["operate_cost"], avg_inventory
    )
    ratios["现金流匹配度"] = calculate_cash_flow_matching_ratio(
        values["net_cash_operate"], values["net_profit"]
    )
    ratios["销售现金比率"] = calculate_sales_cash_ratio(
        values["net_cash_operate"], values["operate_income"]
    )
    ratios["权益乘数"] = calculate_equity_multiplier(ratios["资产负债率"])

    # 记录 None 值
    for metric, value in ratios.items():
        if value is None:
            results["warnings"].append(f"指标 '{metric}' 计算失败（分母为 0 或缺少数据）")
        else:
            ratios[metric] = round(value, 6)

    results["ratios"] = ratios
    results["success"] = any(v is not None for v in ratios.values())

    # 保存为 CSV
    output_df = pd.DataFrame([ratios])
    output_df.insert(0, "公司名称", name)
    output_df.insert(1, "股票代码", code)
    output_df.insert(2, "年份", year)

    output_filename = f"{code}_{year}年度财务计算结果.csv"
    output_path = os.path.join(output_dir, output_filename)
    output_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    results["output_path"] = output_path
    return results


# ========== CLI ==========

def parse_args():
    parser = argparse.ArgumentParser(description="计算财务比率")
    parser.add_argument("--code", required=True, help="股票代码，例如 600519")
    parser.add_argument("--name", required=True, help="公司名称，例如 贵州茅台")
    parser.add_argument("--year", required=True, help="计算年份，例如 2024")
    parser.add_argument(
        "--input-dir",
        default="/workspace/data/financial_statements",
        help="输入目录",
    )
    parser.add_argument(
        "--output-dir",
        default="/workspace/data/financial_caculates",
        help="输出目录",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)

    print("=" * 60)
    print("财务比率计算任务")
    print("=" * 60)
    print(f"股票代码: {args.code}")
    print(f"公司名称: {args.name}")
    print(f"计算年份: {args.year}")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    print("=" * 60)

    results = calculate_financial_ratios(
        code=args.code,
        name=args.name,
        year=args.year,
        input_dir=input_dir,
        output_dir=output_dir,
    )

    print("\n计算结果:")
    for metric, value in results["ratios"].items():
        print(f"  {metric}: {value}")

    if results["warnings"]:
        print("\n警告:")
        for w in results["warnings"]:
            print(f"  ⚠️ {w}")

    if results["errors"]:
        print("\n错误:")
        for e in results["errors"]:
            print(f"  ❌ {e}")
        return 1

    print(f"\n✅ 结果已保存: {results['output_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
