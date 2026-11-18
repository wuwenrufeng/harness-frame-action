# -*- coding: utf-8 -*-
"""
akshare 财务数据采集工具函数
用于采集中国 A 股和港股上市公司的三大报表及财务指标
"""

import os
import time
from typing import Callable, Optional

import akshare as ak
import pandas as pd


def normalize_a_share_code(stock_code: str) -> str:
    """
    将纯数字 A 股代码转换为带市场前缀的格式（SH600519 / SZ000001）
    """
    code = str(stock_code).strip()
    if code.startswith(("SH", "SZ", "sh", "sz")):
        return code.upper()
    # 6 开头为沪市，其余为深市
    if code.startswith("6"):
        return f"SH{code}"
    return f"SZ{code}"


def clean_a_share_code(stock_code: str) -> str:
    """
    去掉 SH/SZ 前缀，返回纯数字代码
    """
    code = str(stock_code).strip().upper()
    if code.startswith(("SH", "SZ")):
        return code[2:]
    return code


def ensure_dir(path: str) -> None:
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def save_dataframe(df: pd.DataFrame, filepath: str) -> None:
    """保存 DataFrame 为 utf-8-sig 编码的 CSV"""
    df.to_csv(filepath, index=False, encoding="utf-8-sig")


def filter_annual_report(df: pd.DataFrame, year: str, date_column: str) -> pd.DataFrame:
    """
    从 DataFrame 中筛选出指定年份的年报数据
    兼容 akshare 不同接口返回的多种日期格式
    """
    if df is None or df.empty:
        return pd.DataFrame()

    if date_column not in df.columns:
        print(f"[警告] 数据中不存在日期列 '{date_column}'，可用列: {list(df.columns)}")
        return pd.DataFrame()

    target_patterns = [
        f"{year}-12-31 00:00:00",
        f"{year}-12-31",
    ]

    # 将日期列统一转为字符串
    date_values = df[date_column].astype(str)
    mask = date_values.isin(target_patterns)
    return df[mask].copy()


def retry_call(func: Callable, retries: int = 3, sleep_seconds: float = 0.5):
    """
    包装函数调用，失败时自动重试
    """
    last_exception = None
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            print(f"[重试 {attempt + 1}/{retries}] 调用失败: {e}")
            if attempt < retries - 1:
                time.sleep(sleep_seconds * (attempt + 1))
    raise last_exception


def get_balance_sheet(stock_code: str, year: str, retries: int = 3) -> Optional[pd.DataFrame]:
    """
    获取 A 股资产负债表
    :param stock_code: 带 SH/SZ 前缀的 A 股代码
    :param year: 年份，如 2024
    :return: DataFrame 或 None
    """
    try:
        df = retry_call(
            lambda: ak.stock_balance_sheet_by_yearly_em(symbol=stock_code),
            retries=retries,
        )
        return filter_annual_report(df, year, date_column="REPORT_DATE")
    except Exception as e:
        print(f"[错误] 获取资产负债表失败 ({stock_code}, {year}): {e}")
        return None


def get_income_statement(stock_code: str, year: str, retries: int = 3) -> Optional[pd.DataFrame]:
    """
    获取 A 股利润表
    """
    try:
        df = retry_call(
            lambda: ak.stock_profit_sheet_by_yearly_em(symbol=stock_code),
            retries=retries,
        )
        return filter_annual_report(df, year, date_column="REPORT_DATE")
    except Exception as e:
        print(f"[错误] 获取利润表失败 ({stock_code}, {year}): {e}")
        return None


def get_cash_flow_statement(stock_code: str, year: str, retries: int = 3) -> Optional[pd.DataFrame]:
    """
    获取 A 股现金流量表
    """
    try:
        df = retry_call(
            lambda: ak.stock_cash_flow_sheet_by_yearly_em(symbol=stock_code),
            retries=retries,
        )
        return filter_annual_report(df, year, date_column="REPORT_DATE")
    except Exception as e:
        print(f"[错误] 获取现金流量表失败 ({stock_code}, {year}): {e}")
        return None


def get_financial_indicator(stock_code: str, year: str, retries: int = 3) -> Optional[pd.DataFrame]:
    """
    获取 A 股财务指标
    :param stock_code: 纯数字 A 股代码
    :param year: 年份
    """
    clean_code = clean_a_share_code(stock_code)
    try:
        df = retry_call(
            lambda: ak.stock_financial_analysis_indicator(symbol=clean_code, start_year=year),
            retries=retries,
        )
        return filter_annual_report(df, year, date_column="日期")
    except Exception as e:
        print(f"[错误] 获取财务指标失败 ({clean_code}, {year}): {e}")
        return None


def save_statement_if_valid(
    df: Optional[pd.DataFrame],
    output_dir: str,
    clean_code: str,
    year: str,
    statement_name: str,
    results: dict,
) -> None:
    """
    如果 DataFrame 有效则保存，否则记录错误
    """
    if df is not None and not df.empty:
        path = os.path.join(output_dir, f"{clean_code}_{year}_{statement_name}.csv")
        save_dataframe(df, path)
        results["files"].append(path)
        print(f"  ✅ {statement_name}已保存: {path}")
    else:
        msg = f"{clean_code} {year} {statement_name}无数据"
        results["errors"].append(msg)
        print(f"  ⚠️ {msg}")


# ========== 港股支持 ==========
# akshare 港股报表为长表格式（STD_ITEM_CODE / STD_ITEM_NAME / AMOUNT），
# 下游计算脚本需要宽表 + 英文列名，故在此做科目映射与透视。

# 注意：港股报表的 STD_ITEM_CODE 在不同报表间会重复（如 004011999 在资产负债表为
# "流动负债合计"、在利润表为"除税前溢利"），因此必须按报表分别维护映射。
HK_ITEM_MAP = {
    "利润表": {
        "TOTAL_OPERATE_INCOME": ["004001001", "004001999"],  # 营业额 / 营运收入
        "OPERATE_COST": ["004005002"],                       # 销售成本
        "GROSS_PROFIT": ["004007999"],                       # 毛利
        "OPERATE_PROFIT": ["004010999"],                     # 经营溢利
        "TOTAL_PROFIT": ["004011999"],                       # 除税前溢利
        "NETPROFIT": ["004012999"],                          # 除税后溢利
        "PARENT_NETPROFIT": ["004025002"],                   # 股东应占溢利
        "RESEARCH_EXPENSE": ["004010010"],                   # 研发费用
        "SALE_EXPENSE": ["004010003"],                       # 销售及分销费用
        "MANAGE_EXPENSE": ["004010004"],                     # 行政开支
        "FINANCE_EXPENSE": ["004011201"],                    # 融资成本
        "INTEREST_INCOME": ["004011200"],                    # 利息收入
        "BASIC_EPS": ["004027002"],                          # 每股基本盈利
    },
    "资产负债表": {
        "TOTAL_ASSETS": ["004009999"],
        "TOTAL_LIABILITIES": ["004025999"],
        "TOTAL_CURRENT_ASSETS": ["004002999"],
        "TOTAL_CURRENT_LIAB": ["004011999"],
        "INVENTORY": ["004002001"],
        "ACCOUNTS_RECE": ["004002003"],
        "PREPAYMENT": ["004002005"],                         # 预付款按金及其他应收款
        "CASH_EQUIVALENTS": ["004002010"],                   # 现金及等价物
        "TOTAL_EQUITY": ["004028999"],                       # 净资产
        "TOTAL_PARENT_EQUITY": ["004030999"],                # 股东权益
        "SHORT_LOAN": ["004011010"],                         # 短期贷款
        "LONG_LOAN": ["004020001"],                          # 长期贷款
        "CONTRACT_LIAB": ["004011009"],                      # 预收款项
    },
    "现金流量表": {
        "NETCASH_OPERATE": ["003999"],                       # 经营业务现金净额
        "NETCASH_INVEST": ["005999"],                        # 投资业务现金净额
        "NETCASH_FINANCE": ["007999"],                       # 融资业务现金净额
        "CAPEX": ["005005"],                                 # 购建固定资产
        "DEPRECIATION": ["001009"],                          # 折旧及摊销
    },
}

HK_STATEMENT_SYMBOL = {
    "资产负债表": "资产负债表",
    "利润表": "利润表",
    "现金流量表": "现金流量表",
}


def _hk_fetch_long(stock_code: str, statement_type: str, retries: int = 3) -> Optional[pd.DataFrame]:
    """获取港股单张报表的长表（含全部年度）"""
    clean = str(stock_code).strip().replace(".HK", "").zfill(5)
    try:
        return retry_call(
            lambda: ak.stock_financial_hk_report_em(
                stock=clean, symbol=statement_type, indicator="年度"
            ),
            retries=retries,
        )
    except Exception as e:
        print(f"[错误] 获取港股{statement_type}失败 ({clean}): {e}")
        return None


def hk_long_to_wide(df: pd.DataFrame, year: str, statement_type: str = "利润表") -> pd.DataFrame:
    """港股长表 -> 单年度宽表（英文列名 + 中文列名并存）"""
    if df is None or df.empty:
        return pd.DataFrame()

    # 优先匹配 12-31 年报；对 3 月等非自然年结的公司，退化为该年内最近一期年报
    target = f"{year}-12-31"
    sub = df[df["REPORT_DATE"].astype(str).str.startswith(target)].copy()
    if sub.empty:
        year_rows = df[df["REPORT_DATE"].astype(str).str.startswith(f"{year}-")].copy()
        if not year_rows.empty:
            latest = sorted(year_rows["REPORT_DATE"].astype(str).unique())[-1]
            sub = year_rows[year_rows["REPORT_DATE"].astype(str) == latest].copy()
            target = latest
    if sub.empty:
        return pd.DataFrame()

    amount_by_code = {}
    name_by_code = {}
    for _, row in sub.iterrows():
        code = str(row["STD_ITEM_CODE"])
        amount_by_code[code] = row["AMOUNT"]
        name_by_code[code] = row["STD_ITEM_NAME"]

    record = {
        "REPORT_DATE": target,
        "SECURITY_CODE": str(sub["SECURITY_CODE"].iloc[0]),
        "SECURITY_NAME_ABBR": sub["SECURITY_NAME_ABBR"].iloc[0],
        "FISCAL_YEAR": year,
    }
    for en_name, codes in HK_ITEM_MAP.get(statement_type, {}).items():
        for code in codes:
            if code in amount_by_code and pd.notna(amount_by_code[code]):
                record[en_name] = float(amount_by_code[code])
                record[f"{en_name}_CN"] = name_by_code.get(code, "")
                break

    # 港股部分公司不单列"销售成本"，用 营业额 - 毛利 倒推，保证毛利率可算
    if "OPERATE_COST" not in record and "GROSS_PROFIT" in record and "TOTAL_OPERATE_INCOME" in record:
        record["OPERATE_COST"] = record["TOTAL_OPERATE_INCOME"] - record["GROSS_PROFIT"]
        record["OPERATE_COST_CN"] = "推算值(营业额-毛利)"

    return pd.DataFrame([record])


def get_hk_financial_indicator(stock_code: str, year: str, retries: int = 3) -> Optional[pd.DataFrame]:
    """获取港股财务指标（东方财富港股 F10）"""
    clean = str(stock_code).strip().replace(".HK", "").zfill(5)
    try:
        df = retry_call(
            lambda: ak.stock_financial_hk_analysis_indicator_em(symbol=clean, indicator="年度"),
            retries=retries,
        )
        if df is None or df.empty:
            return None
        sub = df[df["REPORT_DATE"].astype(str).str.startswith(f"{year}-12-31")]
        if sub.empty:
            year_rows = df[df["REPORT_DATE"].astype(str).str.startswith(f"{year}-")]
            if not year_rows.empty:
                latest = sorted(year_rows["REPORT_DATE"].astype(str).unique())[-1]
                sub = year_rows[year_rows["REPORT_DATE"].astype(str) == latest]
        return sub.copy() if not sub.empty else None
    except Exception as e:
        print(f"[错误] 获取港股财务指标失败 ({clean}, {year}): {e}")
        return None


def collect_hk_company_financial_data(
    stock_code: str,
    stock_name: str,
    years: list[str],
    output_dir: str,
    retries: int = 3,
) -> dict:
    """采集港股公司财务数据（一次抓取，多年度切分）"""
    ensure_dir(output_dir)
    results = {"success": True, "files": [], "errors": []}
    clean_code = str(stock_code).strip().replace(".HK", "").zfill(5)

    long_tables = {}
    for stmt in HK_STATEMENT_SYMBOL:
        print(f"\n[港股] 抓取 {stock_name}({clean_code}) {stmt} ...")
        long_tables[stmt] = _hk_fetch_long(clean_code, stmt, retries=retries)

    for year in years:
        print(f"\n[开始] 处理 {stock_name}({clean_code}) {year} 年度...")
        for stmt in HK_STATEMENT_SYMBOL:
            wide = hk_long_to_wide(long_tables.get(stmt), year, stmt)
            save_statement_if_valid(wide, output_dir, clean_code, year, stmt, results)

        ind = get_hk_financial_indicator(clean_code, year, retries=retries)
        save_statement_if_valid(ind, output_dir, clean_code, year, "财务指标", results)

    if results["errors"]:
        results["success"] = False
    return results


def collect_company_financial_data(
    stock_code: str,
    stock_name: str,
    market: str,
    years: list[str],
    output_dir: str,
    sleep_seconds: float = 0.5,
    retries: int = 3,
) -> dict:
    """
    采集一家公司的全部财务数据
    :return: {"success": bool, "files": list, "errors": list}
    """
    ensure_dir(output_dir)
    results = {"success": True, "files": [], "errors": []}
    clean_code = clean_a_share_code(stock_code)

    for year in years:
        print(f"\n[开始] 采集 {stock_name}({clean_code}) {year} 年度财务数据...")

        if market == "A股":
            prefixed_code = normalize_a_share_code(stock_code)

            # 资产负债表
            df_zcfz = get_balance_sheet(prefixed_code, year, retries=retries)
            save_statement_if_valid(df_zcfz, output_dir, clean_code, year, "资产负债表", results)
            time.sleep(sleep_seconds)

            # 利润表
            df_lrb = get_income_statement(prefixed_code, year, retries=retries)
            save_statement_if_valid(df_lrb, output_dir, clean_code, year, "利润表", results)
            time.sleep(sleep_seconds)

            # 现金流量表
            df_xjll = get_cash_flow_statement(prefixed_code, year, retries=retries)
            save_statement_if_valid(df_xjll, output_dir, clean_code, year, "现金流量表", results)
            time.sleep(sleep_seconds)

            # 财务指标
            df_zb = get_financial_indicator(clean_code, year, retries=retries)
            save_statement_if_valid(df_zb, output_dir, clean_code, year, "财务指标", results)
            time.sleep(sleep_seconds)

        elif market == "港股":
            return collect_hk_company_financial_data(
                stock_code=stock_code,
                stock_name=stock_name,
                years=years,
                output_dir=output_dir,
                retries=retries,
            )
        else:
            msg = f"不支持的市场类型: {market}"
            results["errors"].append(msg)
            print(f"  ❌ {msg}")

    if results["errors"]:
        results["success"] = False

    return results


def read_csv_as_text(filepath: str, max_rows: Optional[int] = None) -> str:
    """
    读取 CSV 并格式化为 LLM 易读的文本
    """
    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        if max_rows:
            df = df.head(max_rows)
        return df.to_string(index=False)
    except Exception as e:
        return f"[读取失败] {filepath}: {e}"
