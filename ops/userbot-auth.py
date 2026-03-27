#!/usr/bin/env python3
"""
Userbot auth — запускать один раз для создания сессии.
После успешной авторизации сессия сохранится в ~/.openclaw/workspace/ops/userbot.session
"""

import asyncio
import sys
sys.path.insert(0, '/home/dima/.openclaw/workspace/.venv/lib/python3.12/site-packages')

from pyrogram import Client

async def main():
    print("=== Telegram Userbot — первичная авторизация ===\n")
    api_id = int(input("api_id: ").strip())
    api_hash = input("api_hash: ").strip()

    app = Client(
        "userbot",
        api_id=api_id,
        api_hash=api_hash,
        workdir="/home/dima/.openclaw/workspace/ops"
    )

    async with app:
        me = await app.get_me()
        print(f"\n✅ Успешно! Авторизован как: {me.first_name} (@{me.username})")
        print(f"Сессия сохранена: ~/.openclaw/workspace/ops/userbot.session")

asyncio.run(main())
