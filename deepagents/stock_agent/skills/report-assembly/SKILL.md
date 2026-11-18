---
name: report-assembly
description: |
  组装最终深度研报，合并所有上游 skill 的输出（数据采集、指标计算、可视化、竞争对手研究、估值、研报写作），
  输出完整 Markdown 研报和可选的 Word 版本。
  当用户提到组装研报、生成最终研报、汇总研报、合并分析报告、输出深度研报、
  最终交付报告、生成 Word 报告、生成 docx、研报排版、研报整合、最终交付等
  任何与最终研报组装相关的需求时，务必使用此 skill。
  本 skill 提供 Markdown 拼装、图片路径提取、格式化和可选的 Word 转换工具。
compatibility: |
  - Python 3.9+
  - 依赖：requests、beautifulsoup4、lxml（可选）
  - 可选 pandoc（用于 Word 转换）
  - 适用于 Claude Managed Agents 环境
  - 输出目录：/workspace/final_output
---

# 研报组装技能 (Report Assembly)

## 用途

本 skill 是研报生成流水线的**最终步骤**，负责把各上游 skill 产出的中间报告组装成完整的深度研究报告，具体包括：

- **汇总各章节报告**：公司概况、行业分析、财务分析、对比分析、估值与预测、投资建议
- **图片路径处理**：把各章节 PNG 图片路径规范化为最终报告的相对路径
- **生成完整 Markdown**：按标准研报结构合并为单一 Markdown 文件
- **格式化和校验**：去除冗余、检查图片引用、补全免责声明
- **可选 Word 转换**：调用 pandoc 生成 .docx 文件

## 何时使用此 skill

只要用户任务涉及以下内容，就应当使用本 skill：

- 合并各章节研报
- 生成最终深度研报
- 输出完整 Markdown 研报
- 转换 Markdown 为 Word
- 排版、整合研报
- 最终交付报告生成

## 输入要求

本 skill 收集以下上游产物：

| 输入 | 来源路径 |
|---|---|
| 公司基本信息 | `/workspace/data/report/公司信息数据.md` |
| 主营业务与核心竞争力 | `/workspace/data/report/主营业务与核心竞争力.md` |
| 股东信息 | `/workspace/data/report/股东信息数据.md` |
| 行业与竞争对手研究 | `/workspace/data/report/竞争对手与行业均值数据.md` |
| 单公司分析报告 | `/workspace/analyze_agent_outputs/{code}_{name}/最终分析报告.md` |
| 对比分析报告 | `/workspace/compare_company_report_outputs/{code}_{name}_vs_competitors/最终分析报告.md` |
| 估值报告 | `/workspace/data/report/估值与预测模型.md` |
| 单公司分析图表 | `/workspace/analyze_agent_outputs/{code}_{name}/*.png` |
| 对比分析图表 | `/workspace/compare_company_report_outputs/{code}_{name}_vs_competitors/*.png` |

调用主脚本需要以下参数：

| 参数 | 必填 | 说明 | 示例 |
|---|---|---|---|
| `--code` | 是 | 目标公司股票代码 | `600519` |
| `--name` | 是 | 目标公司名称 | `贵州茅台` |
| `--industry` | 否 | 所属行业 | `白酒` |
| `--input-dir` | 否 | 中间报告根目录 | 默认 `/workspace` |
| `--output-dir` | 否 | 输出目录 | 默认 `/workspace/final_output` |
| `--no-docx` | 否 | 跳过 Word 转换 | 默认关闭（生成 docx） |

## 输出产物

```
/workspace/final_output/
├── 财务研报汇总_{timestamp}.md           # 第一阶段汇总
├── 深度财务研报分析_{timestamp}.md       # 最终深度研报
├── 深度财务研报分析_{timestamp}_images.md # 处理图片路径后的版本
└── 深度财务研报分析_{timestamp}.docx       # Word 版本（可选）
```

## 标准研报章节顺序

```
# [公司名称]（股票代码）深度财务研报分析

## 一、公司概况
   1.1 公司简介
   1.2 主营业务与核心竞争力
   1.3 股权结构

## 二、行业分析
   2.1 行业概况
   2.2 竞争对手

## 三、财务分析
   3.1 盈利能力
   3.2 偿债能力
   3.3 运营能力
   3.4 现金流

## 四、对比分析
   与主要竞争对手对比

## 五、估值与预测

## 六、投资建议

## 七、数据来源与免责声明
```

## 工作流

1. 收集所有上游报告文件
2. 提取各报告的章节内容
3. 复制 PNG 图片到最终输出目录的 `images/` 子目录
4. 重写 Markdown 中的图片路径为相对路径
5. 按标准结构拼装最终 Markdown 研报
6. 调用 pandoc 生成 .docx（如可用）

## 快速开始

### 1. 安装依赖

```bash
pip install -r skills/report_assembly/requirements.txt
```

### 2. 组装研报

```bash
python skills/report_assembly/scripts/assemble_report.py \
  --code 600519 \
  --name 贵州茅台 \
  --industry 白酒
```

### 3. 仅生成 Markdown（不生成 docx）

```bash
python skills/report_assembly/scripts/assemble_report.py \
  --code 600519 \
  --name 贵州茅台 \
  --no-docx
```

## 图片路径处理

研报组装时会执行以下图片路径处理：

1. 查找每个子报告中的 `![alt](path)` 引用
2. 复制被引用的 PNG 到 `final_output/images/` 目录
3. 如果图片不存在则删除该引用
4. 重新写图片路径为 `./images/{filename}.png`

### 示例

```markdown
原引用：![公司盈利能力分析](./600519盈利能力指标趋势分析.png)
处理后：![公司盈利能力分析](./images/公司盈利能力指标趋势分析.png)
```

## 常见错误处理

| 问题 | 解决方案 |
|---|---|
| 缺少公司信息文件 | 检查 `competitor_research` skill 是否成功运行 |
| 缺少单公司分析报告 | 检查 `financial_visualization` skill 是否成功运行 |
| 缺少对比分析报告 | 检查 `financial_visualization` 是否生成对比图 |
| 缺少估值报告 | 检查 `valuation_modeling` 是否运行 |
| 图片不存在 | 自动删除该图片引用 |
| pandoc 不可用 | 仅生成 Markdown，跳过 docx |

## 输出 Markdown 结构示例

```markdown
# 贵州茅台（600519）深度财务研报分析

## 一、公司概况

[摘自 公司信息数据.md]

### 1.2 主营业务与核心竞争力

[摘自 主营业务与核心竞争力.md]

## 二、行业分析

[摘自 竞争对手与行业均值数据.md]

## 三、财务分析

### 3.1 盈利能力

[摘自 单公司分析报告]

![贵州茅台盈利能力指标趋势分析](./images/贵州茅台盈利能力指标趋势分析.png)

## 四、对比分析

[摘自 对比分析报告]

![盈利能力对比分析](./images/盈利能力对比分析.png)

## 五、估值与预测

[摘自 估值与预测模型.md]

## 六、投资建议

[综合所有分析]

## 七、数据来源与免责声明

### 数据来源
...

### 免责声明
...
```

## 文件结构

```
skills/report_assembly/
├── SKILL.md                          # 本说明文件
├── requirements.txt                  # Python 依赖
└── scripts/
    ├── assemble_report.py            # 研报组装主脚本
    └── markdown_helpers.py           # Markdown 处理辅助函数
```

## 与上下游 skill 的协作

| 上游 skill | 提供内容 |
|---|---|
| `competitor_research` | 公司信息、主营业务、股东信息、行业与竞争对手 |
| `financial_data_collection` | 财务三大报表（用于估值复核） |
| `financial_ratio_calculation` | 财务比率 CSV（用于估值复核） |
| `financial_visualization` | 单公司趋势图、对比分析图 |
| `valuation_modeling` | 估值与预测报告 |
| `report_writing` | 写作规范（本 skill 隐式遵循） |

## 安全与合规

1. 仅汇总已生成的中间报告
2. 不修改原始数据
3. 所有数据来源标注完整
4. 包含必要的免责声明