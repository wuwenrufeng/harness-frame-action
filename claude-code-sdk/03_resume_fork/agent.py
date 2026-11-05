import argparse
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


# ---------- 系统提示词 ----------
SYSTEM_PROMPT = """\
你是一个资深投资分析师。必须使用子 agent 完成任务，**严禁自行调用 Skills**。
分析对象：燕京啤酒 2025 年年报 + 啤酒行业最新动态 + 个股风险信号。
输出格式：建议关注的核心风险点 / 关键财务异常 / 新增行业利好或利空。\
"""


# ---------- SubAgent 定义 ----------
def build_agents() -> dict[str, AgentDefinition]:
    """把三个 SubAgent 集中到一个工厂方法，方便 Fresh / Resume / Fork 三种模式复用。"""
    return {
        "financial-analyzer": AgentDefinition(
            description="财报分析助手",
            prompt="你是一个财报分析助手",
            tools=["Read", "Grep", "Glob", "Bash", "Write", "Edit"],
            skills=["financial-report-analyzer"],
        ),
        "industry-news-collector": AgentDefinition(
            description="行业信息收集助手",
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
            skills=["industry-news-collector"],
        ),
        "a-share-risk-alert": AgentDefinition(
            description="A股个股风险分析助手",
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
        ),
    }


# ---------- MCP / Bocha 搜索 ----------
@tool(
    "bochasearch",
    "使用 Bocha AI 进行网络搜索",
    {"query": str},
)
async def bochasearch(args) -> dict[str, Any]:
    bochakey = os.getenv("BOCHA_API_KEY")
    ep = "https://api.bochaai.com/v1/web-search"
    headers = {
        "Authorization": f"Bearer {bochakey}",
        "Content-Type": "application/json",
    }
    data = {
        "query": args["query"],
        "summary": True,
        "count": 10,
    }
    response = requests.post(ep, data=json.dumps(data), headers=headers)
    return {
        "content": [
            {
                "type": "text",
                "text": f"result: {response.json()}",
            }
        ]
    }


websearch_server = create_sdk_mcp_server(
    name="websearch",
    version="1.0.0",
    tools=[bochasearch],
)


# ---------- 默认首次提问 ----------
DEFAULT_PROMPT = """\
请完成以下三个任务：
1. 请使用 financial-analyzer agent，阅读 /Users/Admin/workspace/python/09fork/raw燕京啤酒财报.pdf，之后进行财务分析。
2. 请使用 a-share-risk-alert agent，对燕京啤酒进行风险分析。
3. 请使用 industry-news-collector agent，收集最近啤酒行业的新闻热点。

必须使用子 agent 完成任务，**不能自行调用 skills**。"""


# ============================================================
# 模式零：Fresh —— 从头开始的一次性分析
# ============================================================
async def run_fresh(prompt: str) -> str:
    """从头开始一次分析，跑完把 session_id 吐出来，方便后续 resume / fork。"""
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
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
        agents=build_agents(),
    )

    session_id = None
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for msg in client.receive_response():
            print(msg)
            if isinstance(msg, ResultMessage):
                session_id = msg.session_id
    return session_id


# ============================================================
# 模式一：Resume —— 接着上次聊
# ============================================================
async def run_resume(session_id: str, follow_up: str) -> None:
    """基于历史的 session_id 继续追问。SubAgent 状态、历史消息、Skills 缓存全部复用。"""
    options = ClaudeAgentOptions(
        resume=session_id,
        allowed_tools=[
            "Read",
            "Grep",
            "Glob",
            "Agent",
            "AskUserQuestion",
            "mcp__websearch__bochasearch",
        ],
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(follow_up)
        async for msg in client.receive_response():
            print(msg)


# ============================================================
# 模式二：Fork —— 在原会话上派生分支
# ============================================================
async def run_fork(session_id: str, alternative: str) -> str:
    """把当前会话完整复制一份给新分支，分支里随便试错，原会话纹丝不动。"""
    options = ClaudeAgentOptions(
        resume=session_id,
        fork_session=True,  # ★ 关键：派生分支
        max_turns=5,
    )
    forked_id = None
    async with ClaudeSDKClient(options=options) as client:
        await client.query(alternative)
        async for msg in client.receive_response():
            print(msg)
            if isinstance(msg, ResultMessage):
                forked_id = msg.session_id
    return forked_id


# ============================================================
# CLI 入口
# ============================================================
async def main():
    parser = argparse.ArgumentParser(
        description="燕京啤酒投研 Agent —— 支持 Fresh / Resume / Fork 三种会话模式"
    )
    parser.add_argument(
        "--resume",
        metavar="SESSION_ID",
        help="从已有 session_id 继续追问",
    )
    parser.add_argument(
        "--fork",
        metavar="SESSION_ID",
        help="基于已有 session_id 派生分支",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=DEFAULT_PROMPT,
        help="要发给主 Agent 的 prompt",
    )
    args = parser.parse_args()

    if args.fork:
        forked = await run_fork(args.fork, args.prompt)
        print(f"\n[FORK_SESSION_ID] {forked}")
        print("# 之后可以继续基于这个分支追问：")
        print(
            f'# python agent.py --resume {forked} "在 DCF 估值基础上，把永续增长率调到 1% 重新算一下"'
        )
    elif args.resume:
        await run_resume(args.resume, args.prompt)
    else:
        sid = await run_fresh(args.prompt)
        print(f"\n[SESSION_ID] {sid}")
        print("# 之后用：")
        print(f'# python agent.py --resume {sid} "请补充最新一周行业利空"')
        print("# 或者开分支探索不同投资逻辑：")
        print(
            f'# python agent.py --fork {sid} "请基于现有分析，额外用 DCF 模型重做估值"'
        )


if __name__ == "__main__":
    asyncio.run(main())
