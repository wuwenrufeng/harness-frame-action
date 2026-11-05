---
name: valuation-modeling
description: |
  为中国上市公司构建估值与预测模型，输出包含 DCF 估值、相对估值（PE/PB）、行业对比的 Markdown 报告。
  当用户提到估值、估值模型、DCF、贴现现金流、相对估值、PE 估值、PB 估值、PS 估值、
  EV/EBITDA、内含价值、目标价、合理估值、股价预测、盈利预测、敏感性分析、
  估值与预测、估值分析报告、估值结论等任何与估值建模相关的需求时，务必使用此 skill。
  本 skill 输出标准化的估值 Markdown 报告，供最终研报直接使用。
compatibility: |
  - Python 3.9+
  - 依赖：pandas、numpy
  - 适用于 Claude Managed Agents 环境
  - 输入目录：/workspace/data/financial_statements 和 /workspace/data/report
  - 输出目录：/workspace/data/report
---

# 估值与预测模型技能 (Valuation Modeling)

## 用途

本 skill 用于为目标公司构建估值与预测模型，具体包括：

- **DCF 估值（绝对估值）**：基于历史现金流预测未来自由现金流并贴现
- **相对估值**：基于 PE、PB、PS、EV/EBITDA 等倍数与同行可比公司对比
- **行业对比估值**：结合行业均值和竞争对手估值水平给出合理区间
- **敏感性分析**：分析关键假设（WACC、增长率、永续增长率）对估值的影响
- **盈利预测**：基于历史增长率预测未来 3-5 年的收入和利润

## 何时使用此 skill

只要用户任务涉及以下内容，就应当使用本 skill：

- 估值、估值模型、估值分析
- DCF、贴现现金流、自由现金流
- PE 估值、PB 估值、PS 估值、相对估值
- 目标价、合理估值区间、内含价值
- 股价预测、盈利预测
- 估值敏感性分析
- 估值报告、估值与预测报告
- 投资价值评估

## 输入要求

本 skill 需要以下输入：

| 输入 | 必填 | 来源 |
|---|---|---|
| 目标公司股票代码 | 是 | 用户提供 |
| 目标公司名称 | 是 | 用户提供 |
| 行业 | 是 | 由 `competitor_research` 输出或用户提供 |
| 财务数据（资产负债表、利润表、现金流量表） | 是 | `financial_data_collection` 输出 |
| 竞争对手列表 | 是 | `competitor_research` 输出的 competitors.json |
| 主营业务描述 | 是 | `competitor_research` 输出的业务信息 |
| 行业均值数据 | 是 | `competitor_research` 输出的行业均值 |

调用主脚本时需要以下参数：

| 参数 | 必填 | 说明 |
|---|---|---|
| `--code` | 是 | 目标公司股票代码 |
| `--name` | 是 | 目标公司名称 |
| `--industry` | 否 | 所属行业，默认从 competitors.json 读取 |
| `--years` | 是 | 历史分析年份列表 |
| `--input-dir` | 否 | 财务报表目录，默认 `/workspace/data/financial_statements` |
| `--competitors-file` | 否 | 竞争对手 JSON，默认 `/workspace/data/report/competitors.json` |
| `--industry-info-file` | 否 | 行业均值文件，默认 `/workspace/data/report/竞争对手与行业均值数据.md` |
| `--output-dir` | 否 | 输出目录，默认 `/workspace/data/report` |

## 输出产物

```
/workspace/data/report/
└── 估值与预测模型.md
```

报告包含以下章节：

```markdown
# 贵州茅台（600519）估值与预测模型报告

## 一、公司基本面与估值假设
- 历史经营概况
- 关键财务预测假设
  - 未来 5 年收入增长率
  - 永续增长率
  - WACC（加权平均资本成本）

## 二、DCF 估值
- 自由现金流预测
- 贴现计算过程
- DCF 估值结果（每股价值、估值区间）

## 三、相对估值
- PE 估值
- PB 估值
- PS 估值
- EV/EBITDA 估值
- 与竞争对手对比

## 四、敏感性分析
- WACC 敏感性
- 增长率敏感性
- 估值结果区间

## 五、估值结论与投资建议
- 综合估值区间
- 投资评级（买入/增持/中性/减持）
- 主要风险提示

## 六、数据来源与免责声明
```

## 估值方法说明

### 1. DCF 估值（核心方法）

DCF 估值的核心公式：

```
企业价值 = Σ(FCF_t / (1+WACC)^t) + TV / (1+WACC)^n
FCF = 息税前利润 × (1 - 税率) + 折旧摊销 - 资本支出 - 营运资本增加
TV = FCF_(n+1) / (WACC - g)
```

其中：

- `FCF`：自由现金流
- `WACC`：加权平均资本成本（建议 A 股 8-12%）
- `g`：永续增长率（建议不超过 GDP 长期增速，A 股 2-4%）
- `TV`：终值

### 2. 相对估值

| 倍数 | 公式 | 适用场景 |
|---|---|---|
| PE | 股价 / 每股收益 | 盈利稳定的成熟公司 |
| PB | 股价 / 每股净资产 | 资产密集型公司、银行、保险 |
| PS | 股价 / 每股营业收入 | 高成长亏损公司 |
| EV/EBITDA | 企业价值 / EBITDA | 跨资本结构比较 |

### 3. 敏感性分析

构建 WACC × 永续增长率的敏感性矩阵，得到估值区间。

## 快速开始

### 1. 安装依赖

```bash
pip install -r skills/valuation_modeling/requirements.txt
```

### 2. 准备输入文件

确保以下文件存在：

```bash
# 检查输入文件
ls -la /workspace/data/financial_statements/
ls -la /workspace/data/report/competitors.json
ls -la /workspace/data/report/竞争对手与行业均值数据.md
```

### 3. 生成估值报告

```bash
python skills/valuation_modeling/scripts/build_valuation.py \
  --code 600519 \
  --name 贵州茅台 \
  --industry 白酒 \
  --years 2022 2023 2024
```

## 工作流

1. 确认 `financial_data_collection` 已生成三大报表 CSV
2. 确认 `competitor_research` 已生成 competitors.json 和行业均值报告
3. 运行本 skill 脚本，让 LLM 基于财务数据和行业信息撰写估值报告
4. 检查输出的 Markdown 报告是否完整
5. 将报告交给 `report_assembly` skill 汇总到最终研报

## 估值假设的参考范围

| 公司类型 | 收入增长率 | 毛利率 | WACC | 永续增长率 |
|---|---|---|---|---|
| 成熟稳定型（白酒、家电） | 5-15% | 30-70% | 8-10% | 2-3% |
| 高成长型（科技、生物医药） | 20-50% | 50-80% | 10-15% | 3-5% |
| 周期型（化工、钢铁） | -5-15% | 10-25% | 9-12% | 2-3% |
| 防御型（公用事业） | 3-8% | 20-40% | 7-9% | 2-3% |

## 常见错误处理

| 问题 | 解决方案 |
|---|---|
| 缺少财务报表 | 先运行 `financial_data_collection` skill |
| 缺少竞争对手数据 | 先运行 `competitor_research` skill |
| 行业判断困难 | 根据公司主营产品和 akshare 行业分类判断 |
| 历史数据波动大 | 在估值假设中使用多年平均值 |
| 公司处于亏损状态 | 使用 PS、EV/Revenue 等替代倍数 |

## 文件结构

```
skills/valuation_modeling/
├── SKILL.md                          # 本说明文件
├── requirements.txt                  # Python 依赖
└── scripts/
    ├── build_valuation.py            # 估值建模主脚本
    └── valuation_helpers.py          # 估值计算辅助函数
```

## 与上下游 skill 的协作

- **上游**：`financial_data_collection` 提供财务报表
- **上游**：`competitor_research` 提供竞争对手和行业均值
- **下游**：`report_assembly` 读取估值报告并汇总到最终研报

## 安全与合规

1. 估值结论仅供参考，不构成投资建议
2. 所有计算结果必须基于公开披露数据
3. 报告必须包含数据来源说明
4. 涉及未来预测时必须标注不确定性