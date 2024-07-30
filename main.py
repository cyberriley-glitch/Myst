import asyncio
from my_copybot import bot
from http_srv import api
import os

async def http_app():
    port = os.environ["PORT"]
    api.run(host='0.0.0.0', port=port)

async def bot_app():
    print("Starting bot")
    await bot.start(os.environ["BOT_TOKEN"]),


if __name__ == "__main__":

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
#        await bot.start(os.environ["BOT_TOKEN"])
    loop.run_until_complete(asyncio.gather(
        bot_app(),
        http_app()
    ))