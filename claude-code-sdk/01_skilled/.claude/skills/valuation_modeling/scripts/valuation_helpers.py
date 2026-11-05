# -*- coding: utf-8 -*-
"""估值计算辅助函数"""
from typing import Dict, List, Optional, Tuple

import pandas as pd


def load_statement(input_dir: str, code: str, year: str, statement_type: str) -> Optional[pd.DataFrame]:
    """加载单张报表"""
    import os

    filename = f"{code}_{year}_{statement_type}.csv"
    filepath = os.path.join(input_dir, filename)
    if not os.path.exists(filepath):
        return None
    try:
        return pd.read_csv(filepath, encoding="utf-8-sig")
    except Exception as e:
        print(f"[错误] 读取 {filepath} 失败: {e}")
        return None


def get_value(df: Optional[pd.DataFrame], aliases: List[str]) -> Optional[float]:
    """从 DataFrame 中按别名列表获取第一个非空值"""
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


def get_historical_metrics(
    code: str,
    years: List[str],
    input_dir: str,
) -> Dict[str, Dict[str, float]]:
    """
    提取历史财务指标
    :return: {"营业收入": {"2022": x, "2023": y, "2024": z}, ...}
    """
    metrics = {}

    for year in years:
        df_zcfz = load_statement(input_dir, code, year, "资产负债表")
        df_lrb = load_statement(input_dir, code, year, "利润表")
        df_xjll = load_statement(input_dir, code, year, "现金流量表")

        revenue = get_value(df_lrb, ["TOTAL_OPERATE_INCOME", "OPERATE_INCOME"])
        cost = get_value(df_lrb, ["OPERATE_COST"])
        net_profit = get_value(df_lrb, ["NETPROFIT", "PARENT_NETPROFIT"])
        total_assets = get_value(df_zcfz, ["TOTAL_ASSETS"])
        total_liabilities = get_value(df_zcfz, ["TOTAL_LIABILITIES"])
        equity = get_value(df_zcfz, ["TOTAL_EQUITY", "TOTAL_PARENT_EQUITY"])
        cash_flow_op = get_value(df_xjll, ["NETCASH_OPERATE"])

        def add(metric_name, value):
            if value is None:
                return
            if metric_name not in metrics:
                metrics[metric_name] = {}
            metrics[metric_name][year] = value

        add("营业收入", revenue)
        add("营业成本", cost)
        add("净利润", net_profit)
        add("总资产", total_assets)
        add("总负债", total_liabilities)
        add("股东权益", equity)
        add("经营活动现金流", cash_flow_op)

    return metrics


def calculate_growth_rates(values_by_year: Dict[str, float], years: List[str]) -> Dict[str, float]:
    """计算同比增长率"""
    growth = {}
    for i in range(1, len(years)):
        prev_year = years[i - 1]
        curr_year = years[i]
        prev = values_by_year.get(prev_year)
        curr = values_by_year.get(curr_year)
        if prev is not None and curr is not None and prev != 0:
            growth[curr_year] = (curr - prev) / prev
    return growth


def calculate_average(values: List[float]) -> Optional[float]:
    """计算平均值（忽略 None）"""
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def calculate_cagr(start_value: float, end_value: float, periods: int) -> Optional[float]:
    """计算复合增长率 (CAGR)"""
    if start_value is None or end_value is None or periods <= 0 or start_value <= 0:
        return None
    return (end_value / start_value) ** (1.0 / periods) - 1


def calculate_simple_dcf_valuation(
    base_fcf: float,
    growth_rate: float,
    wacc: float,
    terminal_growth: float,
    forecast_years: int = 5,
) -> Tuple[Optional[float], List[Dict[str, float]]]:
    """
    简单 DCF 估值
    :return: (企业价值, 现金流预测列表)
    """
    if base_fcf is None or wacc is None or wacc <= terminal_growth:
        return None, []

    projections = []
    pv_total = 0.0
    fcf = base_fcf

    for year in range(1, forecast_years + 1):
        fcf = fcf * (1 + growth_rate)
        discount_factor = (1 + wacc) ** year
        pv = fcf / discount_factor
        pv_total += pv
        projections.append({
            "year": year,
            "fcf": fcf,
            "discount_factor": discount_factor,
            "pv": pv,
        })

    # 终值
    terminal_fcf = fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** forecast_years)
    pv_total += pv_terminal

    projections.append({
        "year": forecast_years + 1,
        "fcf": None,
        "discount_factor": None,
        "pv": pv_terminal,
        "terminal_value": terminal_value,
    })

    return pv_total, projections


def build_sensitivity_matrix(
    base_fcf: float,
    base_growth: float,
    base_wacc: float,
    base_terminal_growth: float,
    wacc_range: List[float],
    growth_range: List[float],
    forecast_years: int = 5,
) -> Dict[str, Dict[str, float]]:
    """构建敏感性矩阵"""
    matrix = {}
    for wacc in wacc_range:
        matrix[f"{wacc:.2%}"] = {}
        for growth in growth_range:
            valuation, _ = calculate_simple_dcf_valuation(
                base_fcf=base_fcf,
                growth_rate=growth,
                wacc=wacc,
                terminal_growth=base_terminal_growth,
                forecast_years=forecast_years,
            )
            matrix[f"{wacc:.2%}"][f"{growth:.2%}"] = valuation
    return matrix


def format_currency(value: float, unit: str = "亿元") -> str:
    """格式化货币金额"""
    if value is None:
        return "N/A"
    if abs(value) >= 1e8:
        return f"{value / 1e8:.2f} {unit}"
    if abs(value) >= 1e4:
        return f"{value / 1e4:.2f} 万元"
    return f"{value:.2f} 元"


def load_competitors(filepath: str) -> List[dict]:
    """加载竞争对手 JSON"""
    import json
    import os

    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("competitors", [])
    except Exception as e:
        print(f"[警告] 读取 competitors 失败: {e}")
        return []