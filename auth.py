#!/usr/bin/env python3
"""
Run this script once to authorize Telethon and create a session file.
After that, parser.py will work without asking for credentials.
"""

import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION_NAME = os.getenv("TG_SESSION", "tg_session")


async def main():
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        me = await client.get_me()
        print(f"\nSuccess! Logged in as: {me.first_name} (@{me.username})")
        print(f"Session saved to: {SESSION_NAME}.session")
        print("\nYou can now run parser.py without re-authorization.")


asyncio.run(main())
