
import asyncio
from telegram import Bot
import io

def make_bot(token):
    return Bot(token=token)

async def send_message_async(bot, chat_id, text):
    try:
        response = await bot.send_message(chat_id=chat_id, text=text, timeout=10)
        print(f"Message sent to {chat_id} successfully, message_id: {response.message_id}")
        return True
    except Exception as e:
        print(f"Failed to send message to {chat_id}: {e}")
        return False

async def send_photo_async(bot, chat_id, photo_bytesio, caption=None):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, bot.send_photo, chat_id, photo_bytesio, caption)
