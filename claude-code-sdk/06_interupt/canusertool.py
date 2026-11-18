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
    return {"continue_": True}


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
