import asyncio
from my_copybot import bot
from http_srv import api
import os

async def http_app():
    api.run(host='0.0.0.0', port=os.environ["port"])

if __name__ == "__main__":

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.gather(
        bot.start(os.environ["BOT_TOKEN"]),
        http_app()
    ))