import asyncio
import json
import os
from typing import Any

import requests
from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import (
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    StreamEvent,
    ToolPermissionContext,
)
from dotenv import load_dotenv

load_dotenv("../../.env", override=True)


# Factory function that returns an AgentDefinition
# This pattern lets you customize agents based on runtime conditions
def financial_analyzer_agent() -> AgentDefinition:
    return AgentDefinition(
        description="财报分析助手",
        # Customize the prompt based on strictness level
        prompt="你是一个财报分析助手",
        tools=[
            "Read",
            "Grep",
            "Glob",
            "Bash",
            "Write",
            "Edit",
            "mcp__websearch__bochasearch",
        ],
        skills=["financial-report-analyzer"],
        # Key insight: use a more capable model for high-stakes reviews
        # model="MiniMax-M3",
    )


def industry_news_collector_agent() -> AgentDefinition:
    return AgentDefinition(
        description="行业信息收集助手",
        # Customize the prompt based on strictness level
        prompt="你是一个行业信息收集助手",
        tools=[
            "Read",
            "Grep",
            "Glob",
            "Bash",
            "Write",
            "Edit",
            "WebFetch",
            "mcp__websearch__bochasearch",
        ],
        skills=["industry_news_collector"],
        # Key insight: use a more capable model for high-stakes reviews
        # model="MiniMax-M3",
    )


def risk_alert_agent() -> AgentDefinition:
    return AgentDefinition(
        description="A股个股风险分析助手",
        # Customize the prompt based on strictness level
        prompt="你是一个A股个股风险分析助手",
        tools=[
            "Read",
            "Grep",
            "Glob",
            "Bash",
            "Write",
            "Edit",
            "mcp__websearch__bochasearch",
        ],
        skills=["a-share-risk-alert"],
        # Key insight: use a more capable model for high-stakes reviews
        # model="MiniMax-M3",
    )


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

prompt = """
请完成以下三个任务：
1. 请使用financial-analyzer agent，阅读/Users/wuwen/workspace/python/github/harness-frame-action/claude-code-sdk/subagent/raw/燕京啤酒财报.pdf，之后进行财务分析。
2. 请使用a-share-risk-alert agent，对燕京啤酒进行风险分析。
3. 请使用industry_news_collector agent，收集最近啤酒行业的新闻热点。

必须使用子agent完成任务，不能自行调用skills
"""

prompt2 = """
请完成以下任务：
1. 请使用financial-analyzer agent，阅读/Users/wuwen/workspace/python/github/harness-frame-action/claude-code-sdk/subagent/raw/燕京啤酒财报.pdf，之后进行财务分析。

必须使用子agent完成任务，不能自行调用skills
"""


async def main():
    in_tool = False
    agent_map = {}  # tool_use_id -> agent_name
    tool_inputs = {}  # tool_use_id -> accumulated JSON input
    current_tool_id = None

    agents_config = {
        "financial-analyzer": financial_analyzer_agent(),
        "industry_news_collector": industry_news_collector_agent(),
        "a-share-risk-alert": risk_alert_agent(),
    }

    options = ClaudeAgentOptions(
        # 开启了流式输出
        include_partial_messages=True,
        mcp_servers={"websearch": websearch_server},
        allowed_tools=[
            "Read",
            "Grep",
            "Glob",
            "Agent",
            "AskUserQuestion",
            "mcp__websearch__bochasearch",
        ],
        agents=agents_config,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt2)

        # Extract and print response
        async for msg in client.receive_response():
            print(msg)


asyncio.run(main())
