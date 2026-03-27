#!/usr/bin/env python3
"""Download media from Telegram topic messages."""
import asyncio
import sys
import os
sys.path.insert(0, '/home/dima/.openclaw/workspace/.venv/lib/python3.12/site-packages')
from pyrogram import Client

async def main():
    if len(sys.argv) < 4:
        print("Usage: download-topic-media.py <chat_id> <topic_id> <output_dir> [limit]")
        sys.exit(1)
    
    chat_id = int(sys.argv[1])
    topic_id = int(sys.argv[2])
    output_dir = sys.argv[3]
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 50
    
    os.makedirs(output_dir, exist_ok=True)
    
    app = Client("userbot", workdir="/home/dima/.openclaw/workspace/ops")
    async with app:
        count = 0
        async for msg in app.get_chat_history(chat_id, limit=limit * 3):
            thread_id = getattr(msg, 'message_thread_id', None) or getattr(msg, 'reply_to_message_id', None)
            
            # Фильтр по топику
            if topic_id == 0:
                if thread_id is not None and thread_id != 0:
                    continue
            else:
                if msg.id != topic_id and thread_id != topic_id:
                    continue
            
            if msg.photo:
                filename = f"{output_dir}/photo_{msg.id}.jpg"
                await msg.download(filename)
                sender = msg.from_user.first_name if msg.from_user else "unknown"
                print(f"Downloaded: {filename} (from {sender})")
                count += 1
            elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith('image'):
                ext = msg.document.file_name.split('.')[-1] if msg.document.file_name else 'bin'
                filename = f"{output_dir}/doc_{msg.id}.{ext}"
                await msg.download(filename)
                sender = msg.from_user.first_name if msg.from_user else "unknown"
                print(f"Downloaded: {filename} (from {sender})")
                count += 1
        
        print(f"\nTotal downloaded: {count} files")

if __name__ == "__main__":
    asyncio.run(main())
