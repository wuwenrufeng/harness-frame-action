---
name: financial-visualization
description: |
  从财务比率 CSV 生成财务分析图表和 Markdown 分析报告。
  当用户提到财务分析图表、财务可视化、趋势图、对比图、财务指标图表、
  盈利能力分析图、偿债能力分析图、运营能力分析图、现金流分析图、
  单公司趋势分析、竞争对手对比分析、生成财务报告图表等任何与财务可视化相关的需求时，
  务必使用此 skill。
  本 skill 提供 matplotlib 脚本，输出 PNG 图表和 Markdown 报告，供最终研报使用。
compatibility: |
  - Python 3.9+
  - 依赖：pandas、numpy、matplotlib
  - 适用于 Claude Managed Agents 的 bash / code_execution 工具环境
  - 输入目录：/workspace/data/financial_caculates
  - 输出目录：/workspace/analyze_agent_outputs 和 /workspace/compare_company_report_outputs
---

# 财务可视化技能 (Financial Visualization)

## 用途

本 skill 用于将 `financial_ratio_calculation` 计算出的财务比率 CSV 转化为可视化图表和分析报告，具体包括：

- **单公司趋势分析**：展示一家公司多年度财务指标的变化趋势
- **多公司对比分析**：展示目标公司与竞争对手在同一时期的指标对比
- **分类图表**：按盈利能力、偿债能力、运营能力、现金流四大维度分别出图
- **Markdown 报告**：每张图表配文字解读，便于下游生成最终研报

## 何时使用此 skill

只要用户任务涉及以下内容，就应当使用本 skill：

- 财务分析图表、财务可视化
- 趋势图、折线图、柱状图、对比图
- 财务指标图表、财务比率图表
- 盈利能力分析图、偿债能力分析图
- 运营能力分析图、现金流分析图
- 单公司趋势分析、纵向分析
- 竞争对手对比、横向对比
- 生成图表附件、生成财务报告图片

## 输入要求

本 skill 的输入是 `financial_ratio_calculation` 生成的 CSV 文件：

```
/workspace/data/financial_caculates/
├── {code}_{year}年度财务计算结果.csv
```

以及可选的竞争对手信息 JSON：

```
/workspace/data/report/competitors.json
```

调用主脚本时需要以下参数：

| 参数 | 必填 | 说明 | 示例 |
|---|---|---|---|
| `--code` | 是 | 目标公司股票代码 | `600519` |
| `--name` | 是 | 目标公司名称 | `贵州茅台` |
| `--years` | 是 | 分析年份列表 | `2022 2023 2024` |
| `--input-dir` | 否 | 比率 CSV 输入目录 | 默认 `/workspace/data/financial_caculates` |
| `--output-dir` | 否 | 单公司分析输出目录 | 默认 `/workspace/analyze_agent_outputs` |
| `--compare-output-dir` | 否 | 对比分析输出目录 | 默认 `/workspace/compare_company_report_outputs` |
| `--competitors` | 否 | 竞争对手 JSON 文件路径 | 默认 `/workspace/data/report/competitors.json` |

## 输出产物

### 单公司趋势分析

```
/workspace/analyze_agent_outputs/{code}_{name}/
├── {name}盈利能力指标趋势分析.png
├── {name}偿债能力指标趋势分析.png
├── {name}运营能力指标趋势分析.png
├── {name}现金流指标趋势分析.png
└── 最终分析报告.md
```

### 多公司对比分析

```
/workspace/compare_company_report_outputs/{code}_{name}_vs_competitors/
├── 盈利能力对比分析.png
├── 偿债能力对比分析.png
├── 运营能力对比分析.png
├── 现金流能力对比分析.png
└── 最终分析报告.md
```

## 图表分类

### 1. 盈利能力指标

- 毛利率
- 净利率

### 2. 偿债能力指标

- 资产负债率
- 流动比率
- 速动比率

### 3. 运营能力指标

- 总资产周转率
- 应收账款周转天数
- 存货周转天数

### 4. 现金流指标

- 现金流匹配度
- 销售现金比率

## 快速开始

### 1. 安装依赖

```bash
pip install -r skills/financial_visualization/requirements.txt
```

### 2. 生成单公司趋势分析

```bash
python skills/financial_visualization/scripts/visualize_financial.py \
  --code 600519 \
  --name 贵州茅台 \
  --years 2022 2023 2024
```

### 3. 生成对比分析

```bash
python skills/financial_visualization/scripts/visualize_financial.py \
  --code 600519 \
  --name 贵州茅台 \
  --years 2022 2023 2024 \
  --competitors /workspace/data/report/competitors.json
```

## 工作流

1. 确认 `financial_ratio_calculation` 已为目标公司和竞争对手生成各年度比率 CSV
2. 运行本 skill 脚本生成单公司趋势图和 Markdown 报告
3. 提供 `competitors.json` 生成多公司对比图和 Markdown 报告
4. 检查输出目录中的 PNG 和 Markdown 是否完整
5. 将 Markdown 报告交给 `report_assembly` skill 汇总到最终研报

## 图表设计规范

1. 图表尺寸：figsize=(12, 6) 或 (14, 7)
2. 中文字体：自动尝试 SimHei、Noto Sans CJK JP、DejaVu Sans 等字体
3. 标题：使用 `{公司名称} {指标类别} {分析类型}` 格式
4. 坐标轴标签：中文，数值过大时自动转换为亿元/万元
5. 图例：位于右上角或图表外侧
6. 网格线：开启浅色网格线提高可读性
7. 保存格式：PNG，dpi=150，bbox_inches='tight'
8. 每个图表保存后调用 `plt.close()` 释放内存

## Markdown 报告格式

### 单公司报告

```markdown
# 贵州茅台财务指标趋势分析报告

## 一、盈利能力指标趋势
![盈利能力指标趋势分析](./贵州茅台盈利能力指标趋势分析.png)

2022-2024 年，贵州茅台毛利率维持在 91% 以上，净利率...

## 二、偿债能力指标趋势
...

## 三、运营能力指标趋势
...

## 四、现金流指标趋势
...
```

### 对比报告

```markdown
# 贵州茅台与竞争对手财务指标对比分析报告

## 一、盈利能力对比
![盈利能力对比分析](./盈利能力对比分析.png)

2024 年，贵州茅台毛利率为 91.92%，高于五粮液的 75....

## 二、偿债能力对比
...

## 三、运营能力对比
...

## 四、现金流能力对比
...
```

## 常见错误处理

| 问题 | 解决方案 |
|---|---|
| 找不到比率 CSV | 先运行 `financial_ratio_calculation` skill |
| 中文字体显示乱码 | 脚本会自动尝试多种字体；可在系统中安装 SimHei 或 Noto Sans CJK |
| 图表为空 | 检查输入 CSV 中对应指标是否为 None 或 0 |
| 竞争对手对比缺少公司 | 检查 `competitors.json` 和对应公司的比率 CSV 是否存在 |

## 文件结构

```
skills/financial_visualization/
├── SKILL.md                          # 本说明文件
├── requirements.txt                  # Python 依赖
└── scripts/
    ├── visualize_financial.py        # 可视化主入口
    └── chart_generator.py            # 图表生成工具函数
```

## 与上下游 skill 的协作

- **上游**：`financial_ratio_calculation` 提供 `/workspace/data/financial_caculates/*.csv`
- **上游**：`competitor_research` 提供 `/workspace/data/report/competitors.json`
- **下游**：`report_assembly` 读取本 skill 的 Markdown 报告和 PNG 图片，汇总到最终研报

## 安全与合规

1. 只读取本地已计算的财务比率数据
2. 不访问外部网络
3. 输出文件为图表和文本报告，不包含敏感信息
