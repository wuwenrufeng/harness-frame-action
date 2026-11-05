import anyio
from claude_agent_sdk import ClaudeSDKClient
from dotenv import load_dotenv

load_dotenv("../.env", override=True)

async def main():
    async with ClaudeSDKClient() as client:
        await client.query('2+3=?')

        # Extract and print msg
        async for msg in client.receive_response():
            print(msg)

if __name__ == "__main__":
    anyio.run(main)
