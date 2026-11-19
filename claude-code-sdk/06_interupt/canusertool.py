import asyncio
import os

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage
from claude_agent_sdk.types import (
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)
from dotenv import load_dotenv

load_dotenv(
    "/Users/wuwen/workspace/python/github/harness-frame-action/.env", override=True
)


async def can_use_tool(
    tool_name: str, input_data: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    # Display the tool request
    print(f"\nTool: {tool_name}")
    if tool_name == "Bash":
        print(f"Command: {input_data.get('command')}")
        if input_data.get("description"):
            print(f"Description: {input_data.get('description')}")
    else:
        print(f"Input: {input_data}")

    # Get user approval
    response = input("Allow this action? (y/n): ")

    # Return allow or deny based on user's response
    if response.lower() == "y":
        # Allow: tool executes with the original (or modified) input
        return PermissionResultAllow(updated_input=input_data)
    else:
        # Deny: tool doesn't execute, Claude sees the message
        return PermissionResultDeny(message="User denied this action")


# Required workaround: dummy hook keeps the stream open for can_use_tool
async def dummy_hook(input_data, tool_use_id, context):
    """演示 PreToolUse 的权限决定对 can_use_tool 的影响。

    permissionDecision 为 deny 时，hook 已拒绝工具调用，无需询问用户；
    为 allow 时，hook 已批准该调用，同样不会进入 can_use_tool。
    为 ask 时，请求用户审批，由 can_use_tool 处理。
    仅返回 {"continue_": True} 不作权限决定，继续后续权限检查；
    如果该调用需要用户审批，才会进入 can_use_tool。
    """
    print('dummy_hook called')
    # return {
    #     "systemMessage": "⚠️ 禁止调用任何工具",
    #     "hookSpecificOutput": {
    #         "hookEventName": "PreToolUse",
    #         "permissionDecision": "deny",
    #         "permissionDecisionReason": "Cannot modify protected files",
    #     },
    # }
    # return {
    #     "continue_": True,
    #     "systemMessage": "可以调用任何工具",
    #     "hookSpecificOutput": {
    #         "hookEventName": "PreToolUse",
    #         "permissionDecision": "allow",
    #         "permissionDecisionReason": "approved",
    #     },
    # }
    # return {"continue_": True}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": "此操作需要用户审批",
        }
    }


async def prompt_stream():
    yield {
        "type": "user",
        "message": {
            "role": "user",
            "content": "Create a test file in /tmp and then delete it",
        },
    }


async def main():
    options = ClaudeAgentOptions(
        can_use_tool=can_use_tool,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        setting_sources=['local'],
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]},
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt=prompt_stream())
        async for message in client.receive_response():
            if isinstance(message, ResultMessage) and message.subtype == "success":
                print(message.result)


asyncio.run(main())
