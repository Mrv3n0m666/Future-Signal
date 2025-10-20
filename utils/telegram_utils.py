import asyncio
from telegram import Bot
import io

def make_bot(token):
    """Membuat instance Telegram Bot."""
    return Bot(token=token)

async def send_message_async(bot, chat_id, text):
    """Kirim pesan teks ke Telegram secara aman (support async & sync)."""
    try:
        loop = asyncio.get_event_loop()

        # Jalankan fungsi send_message di executor biar blocking-safe
        def _send():
            resp = bot.send_message(chat_id=chat_id, text=text)
            # handle kalau hasilnya coroutine
            if asyncio.iscoroutine(resp):
                return asyncio.run(resp)
            return resp

        response = await loop.run_in_executor(None, _send)

        print(f"✅ Message sent to {chat_id} successfully (message_id: {getattr(response, 'message_id', 'N/A')})")
        return True
    except Exception as e:
        print(f"⚠️ Failed to send message to {chat_id}: {e}")
        return False

async def send_photo_async(bot, chat_id, photo_bytesio, caption=None):
    """Kirim foto/chart ke Telegram."""
    try:
        loop = asyncio.get_event_loop()

        def _send_photo():
            resp = bot.send_photo(chat_id=chat_id, photo=photo_bytesio, caption=caption)
            if asyncio.iscoroutine(resp):
                return asyncio.run(resp)
            return resp

        await loop.run_in_executor(None, _send_photo)
        print(f"📸 Photo sent to {chat_id} successfully")
    except Exception as e:
        print(f"⚠️ Failed to send photo to {chat_id}: {e}")
