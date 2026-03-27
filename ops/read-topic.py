#!/usr/bin/env python3
"""
Читает историю топика через Pyrogram userbot.
Использование: python3 read-topic.py <chat_id> <topic_id> [limit]

Примеры:
  python3 read-topic.py -1003596522926 406 200
  python3 read-topic.py -1003888103563 0 300
"""
import asyncio
import sys
sys.path.insert(0, '/home/dima/.openclaw/workspace/.venv/lib/python3.12/site-packages')
from pyrogram import Client

async def main():
    if len(sys.argv) < 3:
        print("Usage: python3 read-topic.py <chat_id> <topic_id> [limit]")
        print("  topic_id=0 для General топика или чата без топиков")
        sys.exit(1)
    
    chat_id = int(sys.argv[1])
    topic_id = int(sys.argv[2])
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    
    app = Client("userbot", workdir="/home/dima/.openclaw/workspace/ops")
    async with app:
        messages = []
        async for msg in app.get_chat_history(chat_id, limit=limit * 3):  # берём с запасом
            thread_id = getattr(msg, 'message_thread_id', None) or getattr(msg, 'reply_to_message_id', None)
            
            # Фильтр по топику
            if topic_id == 0:
                # General или чат без топиков — берём сообщения без thread_id
                if thread_id is not None and thread_id != 0:
                    continue
            else:
                if msg.id != topic_id and thread_id != topic_id:
                    continue
            
            text = msg.text or msg.caption or ""
            if not text and msg.media:
                text = f"[{msg.media}]"
            
            sender = "unknown"
            if msg.from_user:
                sender = msg.from_user.first_name or msg.from_user.username or str(msg.from_user.id)
            elif msg.sender_chat:
                sender = msg.sender_chat.title or "chat"
            
            messages.append((msg.date, msg.id, sender, text))
            
            if len(messages) >= limit:
                break
        
        messages.sort(key=lambda x: x[0])
        
        print(f"=== Топик {topic_id} в чате {chat_id} ({len(messages)} сообщений) ===\n")
        for date, mid, sender, text in messages:
            preview = text[:500].replace('\n', ' ')
            print(f"[{date.strftime('%d.%m %H:%M')}] {sender}: {preview}")
        print("\n=== END ===")

asyncio.run(main())
