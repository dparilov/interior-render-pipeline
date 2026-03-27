#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/home/dima/.openclaw/workspace/.venv/lib/python3.12/site-packages')
from pyrogram import Client

CHAT_ID = -1003596522926
TOPIC_ID = 406

async def main():
    app = Client("userbot", workdir="/home/dima/.openclaw/workspace/ops")
    async with app:
        messages = []
        async for msg in app.get_chat_history(CHAT_ID, limit=500):
            thread_id = getattr(msg, 'message_thread_id', None) or getattr(msg, 'reply_to_message_id', None)
            if msg.id == TOPIC_ID or thread_id == TOPIC_ID:
                text = msg.text or msg.caption or ""
                if not text and msg.media:
                    text = f"[{msg.media}]"
                sender = "unknown"
                if msg.from_user:
                    sender = msg.from_user.first_name or msg.from_user.username or str(msg.from_user.id)
                elif msg.sender_chat:
                    sender = msg.sender_chat.title or "chat"
                messages.append((msg.date, msg.id, sender, text))

        messages.sort(key=lambda x: x[0])
        # Показываем только сообщения после #559
        recent = [(d, mid, s, t) for d, mid, s, t in messages if mid > 559]
        print(f"Всего в топике: {len(messages)}, после #559: {len(recent)}\n{'='*60}")
        for date, mid, sender, text in recent:
            print(f"[{date.strftime('%d.%m %H:%M')}] #{mid} {sender}: {text[:600]}")
        print("=" * 60)

asyncio.run(main())
