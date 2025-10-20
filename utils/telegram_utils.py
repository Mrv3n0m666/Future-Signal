import asyncio
from telegram import Bot
import io

def make_bot(token):
    """Membuat instance Telegram Bot."""
    return Bot(token=token)

async def send_message_async(bot, chat_id, text):
    """Kirim pesan teks ke Telegram secara asynchronous."""
    try:
        # Gunakan executor agar tetap non-blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: bot.send_message(chat_id=chat_id, text=text))
        print(f"✅ Message sent to {chat_id} successfully (message_id: {response.message_id})")
        return True
    except Exception as e:
        print(f"⚠️ Failed to send message to {chat_id}: {e}")
        return False

async def send_photo_async(bot, chat_id, photo_bytesio, caption=None):
    """Kirim foto/chart ke Telegram secara asynchronous."""
    try:
        loop = asyncio.get_event_loop()
        # Bungkus dalam lambda supaya argumen sesuai
        await loop.run_in_executor(None, lambda: bot.send_photo(chat_id=chat_id, photo=photo_bytesio, caption=caption))
        print(f"📸 Photo sent to {chat_id} successfully")
    except Exception as e:
        print(f"⚠️ Failed to send photo to {chat_id}: {e}")
