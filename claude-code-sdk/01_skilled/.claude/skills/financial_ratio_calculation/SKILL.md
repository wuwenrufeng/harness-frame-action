---
name: financial-ratio-calculation
description: |
  从中国 A 股上市公司三大报表（资产负债表、利润表、现金流量表）计算关键财务比率。
  当用户提到财务指标计算、财务比率、毛利率、净利率、ROE、资产负债率、流动比率、速动比率、
  总资产周转率、应收账款周转天数、存货周转天数、现金流匹配度、权益乘数、财务分析指标等
  任何与财务比率计算相关的需求时，务必使用此 skill。
  本 skill 提供确定性脚本，读取 financial_data_collection 采集的 CSV，输出标准化财务比率 CSV。
compatibility: |
  - Python 3.9+
  - 依赖：pandas、numpy
  - 适用于 Claude Managed Agents 的 bash / code_execution 工具环境
  - 输入目录：/workspace/data/financial_statements
  - 输出目录：/workspace/data/financial_caculates
---

# 财务指标计算技能 (Financial Ratio Calculation)

## 用途

本 skill 用于从三大报表计算关键财务比率，具体包括：

### 盈利能力指标

- **毛利率** = (营业收入 - 营业成本) / 营业收入
- **净利率** = 净利润 / 营业收入

### 偿债能力指标

- **资产负债率** = 总负债 / 总资产
- **流动比率** = 流动资产 / 流动负债
- **速动比率** = (流动资产 - 存货 - 预付账款) / 流动负债

### 运营能力指标

- **总资产周转率** = 营业收入 / 平均总资产
- **应收账款周转天数** = 365 / (营业收入 / 平均应收账款)
- **存货周转天数** = 365 / (营业成本 / 平均存货)

### 现金流指标

- **现金流匹配度** = 经营活动现金流净额 / 净利润
- **销售现金比率** = 经营活动现金流净额 / 营业收入

### 杠杆指标

- **权益乘数** = 1 / (1 - 资产负债率)

## 何时使用此 skill

只要用户任务涉及以下内容，就应当使用本 skill：

- 计算财务比率、财务指标
- 毛利率、净利率、ROE、ROA
- 资产负债率、流动比率、速动比率
- 总资产周转率、应收账款周转天数、存货周转天数
- 现金流匹配度、销售现金比率
- 权益乘数、杜邦分析
- 从三大报表计算指标
- 财务数据分析前的指标加工

## 输入要求

本 skill 的输入是 `financial_data_collection` skill 采集的 CSV 文件：

```
/workspace/data/financial_statements/
├── {code}_{year}_资产负债表.csv
├── {code}_{year}_利润表.csv
├── {code}_{year}_现金流量表.csv
```

调用主脚本时需要以下参数：

| 参数 | 必填 | 说明 | 示例 |
|---|---|---|---|
| `--code` | 是 | 股票代码（纯数字） | `600519` |
| `--name` | 是 | 公司名称 | `贵州茅台` |
| `--year` | 是 | 计算年份 | `2024` |
| `--input-dir` | 否 | 输入目录 | 默认 `/workspace/data/financial_statements` |
| `--output-dir` | 否 | 输出目录 | 默认 `/workspace/data/financial_caculates` |

## 输出产物

脚本执行后生成：

```
{output_dir}/{code}_{year}年度财务计算结果.csv
```

例如：

```
600519_2024年度财务计算结果.csv
```

输出 CSV 为单行，包含所有计算指标：

| 指标名 | 值 |
|---|---|
| 毛利率 | 0.9192 |
| 净利率 | 0.5128 |
| 资产负债率 | 0.1889 |
| 流动比率 | 4.5231 |
| 速动比率 | 4.3125 |
| 总资产周转率 | 0.5823 |
| 应收账款周转天数 | 0.52 |
| 存货周转天数 | 1358.42 |
| 现金流匹配度 | 1.0348 |
| 销售现金比率 | 0.5407 |
| 权益乘数 | 1.2330 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r skills/financial_ratio_calculation/requirements.txt
```

### 2. 计算单年度指标

```bash
python skills/financial_ratio_calculation/scripts/calculate_ratios.py \
  --code 600519 \
  --name 贵州茅台 \
  --year 2024
```

### 3. 批量计算多年度指标

对每一年分别执行：

```bash
for year in 2022 2023 2024; do
  python skills/financial_ratio_calculation/scripts/calculate_ratios.py \
    --code 600519 \
    --name 贵州茅台 \
    --year $year
done
```

## 工作流

1. 确认 `financial_data_collection` 已生成三大报表 CSV
2. 调用本 skill 的脚本计算目标公司各年度指标
3. 对竞争对手公司重复步骤 2
4. 检查输出目录中的 CSV 是否完整
5. 将结果交给 `financial_visualization` 或 `report_writing` skill 进行分析和可视化

## 计算说明

### 平均值的计算

总资产周转率、应收账款周转天数、存货周转天数需要使用平均值：

- 平均总资产 = (本年总资产 + 上年总资产) / 2
- 平均应收账款 = (本年应收票据及应收账款 + 上年应收票据及应收账款) / 2
- 平均存货 = (本年存货 + 上年存货) / 2

脚本会自动尝试读取上一年度数据。如果上年数据不存在，则使用本年度数据作为平均值（会在日志中提示）。

### 数据字段映射

脚本使用 akshare 输出的英文列名直接读取：

| 中文概念 | 英文列名 |
|---|---|
| 营业收入 | TOTAL_OPERATE_INCOME / OPERATE_INCOME |
| 营业成本 | OPERATE_COST |
| 净利润 | NETPROFIT / PARENT_NETPROFIT |
| 总资产 | TOTAL_ASSETS |
| 总负债 | TOTAL_LIABILITIES |
| 流动资产 | TOTAL_CURRENT_ASSETS |
| 流动负债 | TOTAL_CURRENT_LIAB |
| 存货 | INVENTORY |
| 预付账款 | PREPAYMENT |
| 应收票据及应收账款 | NOTE_ACCOUNTS_RECE + ACCOUNTS_RECE |
| 经营活动现金流净额 | NETCASH_OPERATE |

### 特殊情况处理

1. 若分母为 0，则该指标返回空值并记录错误
2. 若某字段在报表中缺失，脚本会尝试多个等价列名
3. 若上年数据缺失，使用本年数据代替平均值
4. 所有计算保留 6 位小数

## 常见错误处理

| 问题 | 解决方案 |
|---|---|
| 找不到输入 CSV | 先运行 `financial_data_collection` skill 采集数据 |
| 某指标为空 | 检查对应字段是否在原始报表中存在；属于正常情况时跳过 |
| 上年数据缺失 | 脚本会自动使用本年数据代替；如需精确计算，确保采集上一年数据 |
| 计算结果异常 | 检查原始 CSV 中的数值是否为空或 0 |

## 文件结构

```
skills/financial_ratio_calculation/
├── SKILL.md                          # 本说明文件
├── requirements.txt                  # Python 依赖
└── scripts/
    └── calculate_ratios.py           # 财务比率计算主脚本
```

## 与上下游 skill 的协作

- **上游**：`financial_data_collection` 提供 `/workspace/data/financial_statements/*.csv`
- **下游**：`financial_visualization` 读取 `/workspace/data/financial_caculates/*.csv` 生成图表
- **下游**：`valuation_modeling` 使用指标数据进行估值

## 安全与合规

1. 只读取本地已采集的公开财务数据
2. 不访问外部网络
3. 输出文件仅包含计算后的财务比率，不包含敏感信息
