import os
from typing import Any

import akshare as ak
import anyio
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    create_sdk_mcp_server,
    tool,
)
from dotenv import load_dotenv

load_dotenv("/Users/wuwen/workspace/python/github/harness-frame-action/.env", override=True)


async def main():
    @tool(
        "bochasearch",
        "使用 Bocha AI 进行网络搜索",
        {"query": str},
    )
    async def bochasearch(args) -> dict[str, Any]:
        # 从环境变量中获取 API 密钥
        bochakey = os.getenv("BOCHA_API_KEY")
        # Bocha AI 网络搜索 API 端点
        ep = "https://api.bochaai.com/v1/web-search"

        # 设置请求头
        headers = {
            "Authorization": f"Bearer {bochakey}",
            "Content-Type": "application/json",
        }

        # 构建请求数据
        data = {
            "query": args["query"],  # 搜索关键词
            "summary": True,  # 返回摘要
            "count": 10,  # 返回结果数量
        }

        # 发送 POST 请求到 API
        response = requests.post(ep, data=json.dumps(data), headers=headers)

        data = response.json()

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"result: {data}",
                }
            ]
        }

    websearch_server = create_sdk_mcp_server(
        name="websearch",
        version="1.0.0",
        tools=[bochasearch],
    )

    SYSTEM_PROMPT = """
你是一位金融研报项目协调员。用户会提供股票代码、公司名称、市场和分析年份。

你的工作流程（按顺序执行）：

## 阶段 1: 数据采集
- 调用 competitor_research skill 研究竞争对手和行业
- 调用 financial_data_collection skill 采集所有公司的财务报表

## 阶段 2: 指标计算
- 调用 financial_ratio_calculation skill 计算所有公司的财务比率

## 阶段 3: 分析与可视化
- 调用 financial_visualization skill 生成趋势图和对比图
- 调用 valuation_modeling skill 生成估值报告

## 阶段 4: 报告撰写
- 调用 report_writing skill（隐式遵循其写作规范）
- 调用 report_assembly skill 组装最终研报

## 状态管理
所有中间产物都保存在文件系统中，你通过 read/glob 工具检查产物是否存在。
如果某个 skill 失败，记录警告并尝试继续。
    """
    # Use it with Claude. allowed_tools pre-approves the tool so it runs
    # without a permission prompt; it does not control tool availability.
    options = ClaudeAgentOptions(
        cwd="/Users/wuwen/workspace/python/github/harness-frame-action/claude-code-sdk/01_skilled",
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"tools": websearch_server},
        skills="all",
        allowed_tools=["Read", "Write", "Bash", "Glob", "mcp__tools__bochasearch"],
    )

    async with ClaudeSDKClient(options=options) as client:
        # await client.query("生成青岛啤酒SH600600的2025年金融研报")
        await client.query("生成小米集团01810.HK的2025年金融研报")

        # Extract and print response
        async for msg in client.receive_response():
            print(msg)


anyio.run(main)
