import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any

import requests
from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    ResultMessage,
    SystemMessage,
    create_sdk_mcp_server,
    tool,
)
from dotenv import load_dotenv

load_dotenv("/Users/wuwen/workspace/python/github/harness-frame-action/.env", override=True)


# ---------- 系统提示词 ----------
# SYSTEM_PROMPT = """\
# 你是燕京啤酒 (000729) 的资深投资分析师。必须使用子 agent 完成任务，**严禁自行调用 Skills**。
# 分析对象：燕京啤酒 2025 年年报 + 啤酒行业最新动态 + 个股风险信号。
# 输出格式：建议关注的核心风险点 / 关键财务异常 / 新增行业利好或利空。\
# """
SYSTEM_PROMPT = """\
你是燕京啤酒 (000729) 的资深投资分析师。
分析对象：燕京啤酒 2025 年年报 + 啤酒行业最新动态 + 个股风险信号。
输出格式：建议关注的核心风险点 / 关键财务异常 / 新增行业利好或利空。
行为边界：**严禁自行调用 Skills**。 \
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
            background=False,
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
            background=False,
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
            background=False,
        ),
    }


# AgentDefinition 只负责注册自定义 agent；内置 general-purpose 等仍然可被
# 主 agent 选择，因此另外维护一份真正用于安全校验的白名单。
ALLOWED_SUBAGENTS = frozenset(build_agents())


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
        "summary": False,  # ★ 官方推荐：禁用长摘要，只返回 snippet
        "freshness": "noLimit",
        "count": 5,  # ★ 官方推荐：减少返回数量到 5
    }
    response = requests.post(ep, data=json.dumps(data), headers=headers)
    result = response.json()

    # ★★★ 官方集成模式：只提取 webPages，丢弃 images/videos
    cleaned_result = {
        "webPages": {
            "value": [
                {
                    "name": item.get("name", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),  # 使用 snippet 而非 summary
                    "datePublished": item.get("datePublished", ""),
                }
                for item in result.get("webPages", {}).get("value", [])
            ]
        }
        # 完全移除 images、videos 等大字段
    }

    return {
        "content": [
            {
                "type": "text",
                "text": f"result: {json.dumps(cleaned_result, ensure_ascii=False)}",
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
1. 请使用 financial-analyzer agent，阅读 /Users/wuwen/workspace/python/github/harness-frame-action/claude-code-sdk/05_opentelemetry/raw/燕京啤酒财报.pdf，之后进行财务分析。
2. 请使用 a-share-risk-alert agent，对燕京啤酒进行风险分析。
3. 请使用 industry-news-collector agent，收集最近啤酒行业的新闻热点。

必须使用子 agent 完成任务，**不能自行调用 skills**。
调用 Agent 工具时必须设置 run_in_background=false
"""


# ============================================================
# Hooks：安全策略 + 审计日志 + 子 Agent 追踪 + 耗时统计
# ============================================================
AUDIT_LOG = "audit_log.jsonl"

# 用于记录子agent的启动时间和耗时统计
SUBAGENT_TIMING = {}  # {agent_id: {"start_time": datetime, "agent_type": str}}
SUBAGENT_STATS = []   # 存储完成的统计结果


async def pre_tool_guard(input_data, tool_use_id, context):
    """PreToolUse：只读自动放行，写操作检查路径，Bash 拒绝危险命令。"""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {}) or {}

    # 临时诊断日志：只记录工具和目标名称，不记录文件内容或完整命令，避免泄露密钥。
    if tool_name in {"Write", "Edit"}:
        target = tool_input.get("file_path", "")
        detail = f"target={target}"
    elif tool_name == "Bash":
        detail = "command_present=" + str(bool(tool_input.get("command")))
    else:
        detail = ""
    print(
        f"[PreToolUse] agent_id={input_data.get('agent_id')} "
        f"agent_type={input_data.get('agent_type')} tool={tool_name} "
        f"tool_use_id={tool_use_id} {detail}".rstrip()
    )

    # AgentDefinition 不会禁用内置 agent；在 Agent 工具真正执行前做白名单校验。
    if tool_name in {"Agent", "Task"}:
        subagent_type = tool_input.get("subagent_type") or tool_input.get("agent_type", "")
        if subagent_type not in ALLOWED_SUBAGENTS:
            return {
                "systemMessage": (
                    f"⚠️ 禁止使用未授权的子 agent：{subagent_type or '<missing>'}；"
                    f"允许的子 agent：{', '.join(sorted(ALLOWED_SUBAGENTS))}"
                ),
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Subagent type is not allowlisted",
                },
            }

    # 1. 只读工具自动放行
    if tool_name in {"Read", "Glob", "Grep"}:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Read-only tool auto-approved",
            }
        }

    # 2. 写操作保护 .env 与系统目录
    if tool_name in {"Write", "Edit"}:
        file_path = tool_input.get("file_path", "")
        file_name = file_path.split("/")[-1].split("\\")[-1]
        if file_name == ".env" or file_path.startswith(("/etc", "C:\\Windows")):
            return {
                "systemMessage": f"⚠️ 禁止修改受保护文件：{file_path}",
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Cannot modify protected files",
                },
            }

    # 3. Bash 危险命令拦截
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        dangerous = ["rm -rf", "mkfs", ":(){ :|:& };:", "> /dev/sda"]
        if any(d in command for d in dangerous):
            return {
                "systemMessage": f"⚠️ 检测到危险命令：{command}",
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Dangerous shell command blocked",
                },
            }

    # 其余工具走默认权限策略
    return {}


async def audit_logger(input_data, tool_use_id, context):
    """PostToolUse：把工具调用记录到审计日志。"""
    record = {
        "ts": datetime.now().isoformat(),
        "session_id": input_data.get("session_id"),
        "agent_id": input_data.get("agent_id"),
        "hook": input_data.get("hook_event_name"),
        "tool_name": input_data.get("tool_name"),
        "tool_use_id": tool_use_id,
        "tool_input": input_data.get("tool_input"),
        "tool_output_summary": str(input_data.get("tool_response", ""))[:500],
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {}


async def subagent_tracker(input_data, tool_use_id, context):
    """SubagentStart / SubagentStop：记录子 Agent 的启停与产物路径 + 耗时统计。"""
    event = input_data.get("hook_event_name")
    agent_id = input_data.get("agent_id", "unknown")
    agent_type = input_data.get("agent_type", "unknown")
    transcript = input_data.get("agent_transcript_path", "")

    if event == "SubagentStart":
        # 记录开始时间
        SUBAGENT_TIMING[agent_id] = {
            "start_time": datetime.now(),
            "agent_type": agent_type,
            "transcript": transcript,
        }
        print(f"[{event}] agent_id={agent_id} agent_type={agent_type} 开始执行")

    elif event == "SubagentStop":
        # 计算耗时
        if agent_id in SUBAGENT_TIMING:
            start_info = SUBAGENT_TIMING.pop(agent_id)
            duration = (datetime.now() - start_info["start_time"]).total_seconds()

            stat = {
                "agent_id": agent_id,
                "agent_type": start_info["agent_type"],
                "duration_seconds": round(duration, 2),
                "transcript": transcript,
                "start_time": start_info["start_time"].isoformat(),
                "end_time": datetime.now().isoformat(),
            }
            SUBAGENT_STATS.append(stat)

            print(f"[{event}] agent_id={agent_id} agent_type={start_info['agent_type']} "
                  f"耗时={duration:.2f}秒")
        else:
            print(f"[{event}] agent_id={agent_id} (未找到启动记录)")

    return {}


async def session_archiver(input_data, tool_use_id, context):
    """Stop：会话结束时打印归档信息 + 子agent耗时统计报告。"""
    session_id = input_data.get("session_id", "unknown")

    print(f"\n{'='*60}")
    print(f"[SESSION_END] {session_id}")
    print(f"{'='*60}")

    # 打印子agent耗时统计
    if SUBAGENT_STATS:
        print("\n📊 子Agent执行耗时统计:")
        print(f"{'Agent类型':<30} {'耗时(秒)':<15} {'Agent ID'}")
        print("-" * 60)

        total_time = 0
        for stat in SUBAGENT_STATS:
            print(f"{stat['agent_type']:<30} {stat['duration_seconds']:<15.2f} {stat['agent_id'][:12]}")
            total_time += stat['duration_seconds']

        print("-" * 60)
        print(f"{'总计':<30} {total_time:<15.2f}")

        # 按耗时排序显示TOP消耗
        print("\n⏱️  耗时排行:")
        sorted_stats = sorted(SUBAGENT_STATS, key=lambda x: x['duration_seconds'], reverse=True)
        for i, stat in enumerate(sorted_stats[:3], 1):
            print(f"  {i}. {stat['agent_type']}: {stat['duration_seconds']:.2f}秒")
    else:
        print("\n(未检测到子Agent执行)")

    print(f"\n📝 审计日志已写入: {AUDIT_LOG}")
    print(f"{'='*60}\n")

    # 可选：保存统计到文件
    if SUBAGENT_STATS:
        stats_file = f"subagent_stats_{session_id}.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(SUBAGENT_STATS, f, ensure_ascii=False, indent=2)
        print(f"📈 耗时统计已保存: {stats_file}\n")

    return {}


# 集中注册所有 hooks
BUILD_HOOKS = lambda: {
    "PreToolUse": [
        HookMatcher(hooks=[pre_tool_guard]),
    ],
    "PostToolUse": [
        HookMatcher(hooks=[audit_logger]),
    ],
    "PostToolUseFailure": [
        HookMatcher(hooks=[audit_logger]),
    ],
    "SubagentStart": [
        HookMatcher(hooks=[subagent_tracker]),
    ],
    "SubagentStop": [
        HookMatcher(hooks=[subagent_tracker]),
    ],
    "Stop": [
        HookMatcher(hooks=[session_archiver]),
    ],
}

def build_otel_env(
    service_name: str = "yanjing-research-agent",
    enduser_id: str = "",
    tenant_id: str = "",
) -> dict[str, str]:
    """构造 OpenTelemetry 环境变量，可传入服务名、用户、租户等标签。"""
    attrs = [
        "service.version=1.0.0",
        "deployment.environment=development",
    ]
    if enduser_id:
        from urllib.parse import quote
        attrs.append(f"enduser.id={quote(enduser_id)}")
    if tenant_id:
        from urllib.parse import quote
        attrs.append(f"tenant.id={quote(tenant_id)}")

    return {
        # 1. 总开关
        "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
        # 2. Traces 需要 beta 开关
        "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "1",
        # 3. 为三种信号各选一个 exporter
        "OTEL_TRACES_EXPORTER": "otlp",
        "OTEL_METRICS_EXPORTER": "otlp",
        "OTEL_LOGS_EXPORTER": "otlp",
        # 4. OTLP 传输配置
        "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
        "OTEL_EXPORTER_OTLP_ENDPOINT": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318"),
        "OTEL_EXPORTER_OTLP_HEADERS": os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""),
        # 5. 服务名与资源属性
        "OTEL_SERVICE_NAME": service_name,
        "OTEL_RESOURCE_ATTRIBUTES": ",".join(attrs),
        # 6. 短任务调低导出间隔，避免数据丢失
        "OTEL_METRIC_EXPORT_INTERVAL": "1000",
        "OTEL_LOGS_EXPORT_INTERVAL": "1000",
        "OTEL_TRACES_EXPORT_INTERVAL": "1000",
    }

# ============================================================
# 模式零：Fresh —— 从头开始的一次性分析
# ============================================================
async def run_fresh(prompt: str , otel_env: dict[str, str] | None = None) -> str:
    """从头开始一次分析，跑完把 session_id 吐出来，方便后续 resume / fork。"""
    # 清空上次的统计数据
    SUBAGENT_TIMING.clear()
    SUBAGENT_STATS.clear()

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
        hooks=BUILD_HOOKS(),
        setting_sources=['project'], # 只加载 .claude配置，为空时skills将被忽略
        env=otel_env or build_otel_env(),
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
async def run_resume(session_id: str, follow_up: str, otel_env: dict[str, str] | None = None) -> None:
    """基于历史的 session_id 继续追问。SubAgent 状态、历史消息、Skills 缓存全部复用。"""
    # 清空上次的统计数据
    SUBAGENT_TIMING.clear()
    SUBAGENT_STATS.clear()

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
        hooks=BUILD_HOOKS(),
        setting_sources=['local'],
        env=otel_env or build_otel_env(),
        # 🔧 修复：指定项目根目录，让 SDK 能找到 .claude/skills/
        cwd=os.path.dirname(os.path.abspath(__file__)),
        # 🔧 修复：显式指定全局可用的 skills
        skills="all",
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(follow_up)
        async for msg in client.receive_response():
            print(msg)


# ============================================================
# 模式二：Fork —— 在原会话上派生分支
# ============================================================
async def run_fork(session_id: str, alternative: str, otel_env: dict[str, str] | None = None) -> str:
    """把当前会话完整复制一份给新分支，分支里随便试错，原会话纹丝不动。"""
    # 清空上次的统计数据
    SUBAGENT_TIMING.clear()
    SUBAGENT_STATS.clear()

    options = ClaudeAgentOptions(
        resume=session_id,
        fork_session=True,  # ★ 关键：派生分支
        max_turns=5,
        hooks=BUILD_HOOKS(),
        setting_sources=['local'],
        env=otel_env or build_otel_env(),
        # 🔧 修复：指定项目根目录，让 SDK 能找到 .claude/skills/
        cwd=os.path.dirname(os.path.abspath(__file__)),
        # 🔧 修复：显式指定全局可用的 skills
        skills="all",
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
        description="燕京啤酒投研 Agent —— 支持 Fresh / Resume / Fork + Hooks"
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

    otel_env = build_otel_env(
        service_name="yanjing-research-agent",
        enduser_id='',
        tenant_id="",
    )

    if args.fork:
        forked = await run_fork(args.resume or args.prompt, args.prompt, otel_env)
        print(f"\n[FORK_SESSION_ID] {forked}")
        print("# 之后可以继续基于这个分支追问：")
        print(
            f'# python agent.py --resume {forked} "在 DCF 估值基础上，把永续增长率调到 1% 重新算一下"'
        )
    elif args.resume:
        await run_resume(args.resume, args.prompt, otel_env)
    else:
        sid = await run_fresh(args.prompt, otel_env)
        print(f"\n[SESSION_ID] {sid}")
        print("# 之后用：")
        print(f'# python agent.py --resume {sid} "请补充最新一周行业利空"')
        print("# 或者开分支探索不同投资逻辑：")
        print(
            f'# python agent.py --fork {sid} "请基于现有分析，额外用 DCF 模型重做估值"'
        )


if __name__ == "__main__":
    asyncio.run(main())
