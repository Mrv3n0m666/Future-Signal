
import asyncio
from telegram import Bot
import io

def make_bot(token):
    return Bot(token=token)

async def send_message_async(bot, chat_id, text):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, bot.send_message, chat_id, text, "Markdown")

async def send_photo_async(bot, chat_id, photo_bytesio, caption=None):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, bot.send_photo, chat_id, photo_bytesio, caption)
