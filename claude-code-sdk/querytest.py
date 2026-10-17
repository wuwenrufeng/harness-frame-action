import anyio
from claude_agent_sdk import ClaudeAgentOptions, query
from dotenv import load_dotenv

load_dotenv("../.env", override=True)


async def main():

    options = ClaudeAgentOptions(
        system_prompt="你是一个有帮助的助手",  # 系统提示词
        max_turns=3,  # 循环次数
        allowed_tools=["Read", "Write", "Bash"],  # 允许使用的工具
        permission_mode="auto",  # 设置工具权限，允许不经过人类确认，直接进行文件编辑
        cwd="/Users/wuwen/workspace/python/github/harness-frame-action/claude-code-sdk",  # 工作目录
    )

    async for message in query(
        prompt="在当前目录下，新建一个test.txt文件，然后写入12345", options=options
    ):
        print(message)


anyio.run(main)
