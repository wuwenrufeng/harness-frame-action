import anyio
from claude_agent_sdk import query
from dotenv import load_dotenv

load_dotenv("/Users/wuwen/workspace/python/github/harness-frame-action/.env", override=True)



async def main():
    async for message in query(prompt="2+2=?"):
        print(message)


anyio.run(main)
