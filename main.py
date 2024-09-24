import asyncio
from my_copybot import bot
import os
from dotenv import load_dotenv

async def bot_app():
    print("Starting bot")
    await bot.start(os.environ["BOT_TOKEN"]),


if __name__ == "__main__":
    load_dotenv()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
#        await bot.start(os.environ["BOT_TOKEN"])
    loop.run_until_complete(asyncio.gather(
        bot_app()
    ))