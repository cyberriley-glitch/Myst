import asyncio
from my_copybot import bot
import os
from dotenv import load_dotenv

async def main():
    print("Starting bot")
    async with bot:
        await bot.start(os.environ["BOT_TOKEN"])


if __name__ == "__main__":
    load_dotenv()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
