---
name: competitor-research
description: |
  研究中国上市公司的竞争对手与行业均值数据。
  当用户提到竞争对手、行业对比、同业比较、行业均值、行业基准、竞争格局、竞品分析、
  市场份额、行业排名、可比公司、对标公司等任何与竞争研究相关的需求时，务必使用此 skill。
  本 skill 指导 Agent 使用网络搜索采集竞争对手信息和行业财务均值，输出结构化 Markdown 报告和 JSON  competitor 列表。
compatibility: |
  - 依赖工具：web_search、web_fetch、write、bash
  - 适用于 Claude Managed Agents 环境
  - 可选 Python 依赖：requests、beautifulsoup4（仅当需要解析 HTML 时使用）
  - 默认输出目录：/workspace/data/report
---

# 竞争对手与行业研究技能 (Competitor Research)

## 用途

本 skill 用于研究中国上市公司的竞争环境和行业基准数据，具体包括：

- **竞争对手识别**：同行业主要上市公司，按竞争程度排序
- **竞争对手基本信息**：股票代码、公司名称、所属市场（A股/港股）
- **行业均值数据**：行业平均毛利率、净利率、ROE、资产负债率、市盈率等关键指标
- **行业背景**：行业规模、增速、竞争格局、龙头公司市场份额

研究结果用于后续的财务对比分析和研报撰写。

## 何时使用此 skill

只要用户任务涉及以下内容，就应当使用本 skill：

- 竞争对手分析、同业对比
- 行业均值、行业基准、行业平均水平
- 竞争格局、市场份额、行业排名
- 可比公司、对标公司
- 竞争对手股票代码
- 行业财务指标对比

## 输入要求

开始研究前需要明确以下信息：

| 信息 | 必填 | 说明 | 示例 |
|---|---|---|---|
| 股票代码 | 是 | 目标公司纯数字代码 | `600519` |
| 公司名称 | 是 | 目标公司中文名称 | `贵州茅台` |
| 市场 | 是 | A股 或 港股 | `A股` |
| 行业 | 否 | 若不明确可自动判断 | `白酒` |

## 输出产物

本 skill 产出两个文件：

```
/workspace/data/report/
├── 竞争对手与行业均值数据.md
└── competitors.json
```

### 1. 竞争对手与行业均值数据.md

包含以下章节：

```markdown
# 贵州茅台（600519）竞争对手与行业均值分析

## 一、行业概况
- 行业名称：
- 行业特点：...
- 行业规模与增速：...

## 二、主要竞争对手

| 序号 | 股票代码 | 公司名称 | 市场 | 竞争关系说明 |
|---|---|---|---|---|

## 三、行业均值数据

| 指标 | 行业均值 | 数据来源/说明 |
|---|---|---|
| 毛利率 | XX% | ... |
| 净利率 | XX% | ... |
| ROE | XX% | ... |
| 资产负债率 | XX% | ... |
| 市盈率(PE-TTM) | XX | ... |

## 四、数据来源
1. ...
2. ...
```

### 2. competitors.json

结构化 competitor 列表，供下游 Agent 直接读取：

```json
{
  "competitors": [
    {
      "stock_code": "000858",
      "stock_name": "五粮液",
      "market": "A股"
    },
    {
      "stock_code": "000568",
      "stock_name": "泸州老窖",
      "market": "A股"
    }
  ],
  "industry": "白酒",
  "target_company": "贵州茅台",
  "target_code": "600519"
}
```

## 工作流

1. **判断行业**：根据公司名称和股票代码判断所属行业
2. **搜索竞争对手**：
   - 搜索 `"{公司名称} 竞争对手 上市公司"`
   - 搜索 `"{行业} 上市公司 排名"`
   - 搜索 `"{行业} 龙头企业"`
3. **搜索行业均值**：
   - 搜索 `"{行业} 行业平均毛利率 净利率 ROE {年份}"`
   - 搜索 `"{行业} 行业均值 资产负债率 市盈率"`
4. **整理 Markdown 报告**：按上方模板写入 `/workspace/data/report/竞争对手与行业均值数据.md`
5. **生成 JSON**：调用脚本 `scripts/parse_competitors.py` 从 Markdown 中提取结构化 competitor 列表

## 搜索策略

为了获得高质量结果，建议组合使用以下查询：

### 竞争对手相关

```
{公司名称} 竞争对手 上市公司
{行业} 主要上市公司 排名
{行业} 龙头企业 市场份额
{公司名称} 同业竞争 对标公司
```

### 行业均值相关

```
{行业} 行业平均毛利率 {年份}
{行业} 行业平均净利率 {年份}
{行业} 行业平均ROE {年份}
{行业} 行业平均资产负债率 {年份}
{行业} 行业市盈率 {年份}
```

### 注意事项

1. **竞争对手只关注 A 股或港股上市公司**，不关注美股或未上市公司
2. 优先选择 3-5 家最具竞争力的对手
3. 若搜索到未上市公司的信息，仅作参考，不纳入 `competitors.json`
4. 行业均值尽量使用最近财年的数据（优先 2024，其次 2023）
5. 所有数据标注来源

## 使用 parse_competitors.py

研究完成后，运行以下命令生成结构化 JSON：

```bash
python skills/competitor_research/scripts/parse_competitors.py \
  --input /workspace/data/report/竞争对手与行业均值数据.md \
  --output /workspace/data/report/competitors.json \
  --target-code 600519 \
  --target-name 贵州茅台
```

如果 Markdown 中已经包含 JSON 代码块，脚本会自动提取；否则会尝试从表格中解析。

## 与 financial_data_collection skill 的协作

1. 本 skill 先输出 `competitors.json`
2. 下游的 `financial_data_collection` skill 读取 `competitors.json`
3. 对 `competitors.json` 中的每家公司调用数据采集脚本
4. 最终形成目标公司 + 竞争对手的完整财务数据集

## 常见错误处理

| 问题 | 解决方案 |
|---|---|
| 搜索结果质量差 | 换用更具体的关键词，如加上 "上市公司" "股票代码" |
| 找不到行业均值 | 搜索 "{行业} 财务指标 行业平均" 或查找券商研报 |
| 竞争对手代码格式不统一 | 使用 `parse_competitors.py` 统一清洗为纯数字 |
| 行业判断错误 | 结合公司主营业务和搜索结果交叉验证 |

## 文件结构

```
skills/competitor_research/
├── SKILL.md                          # 本说明文件
├── requirements.txt                  # Python 依赖
└── scripts/
    └── parse_competitors.py          # 从 Markdown 提取结构化 competitor 列表
```

## 安全与合规

1. 只使用公开信息和公开财经数据
2. 不访问需要登录或付费才能查看的私有数据
3. 引用的网络内容标注来源链接
4. 不对竞争对手进行主观恶意评价
