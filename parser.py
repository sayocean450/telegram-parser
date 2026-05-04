#!/usr/bin/env python3
"""
Telegram Channel Parser
Fetches all posts from a Telegram channel and saves them as a Markdown file.

Requirements:
    pip install telethon python-dotenv

Setup:
    1. Get API credentials at https://my.telegram.org/apps
    2. Copy .env.example to .env and fill in the values
    3. Run: python parser.py --channel <channel_username>
"""

import asyncio
import argparse
import os
import re
from datetime import timezone
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaWebPage,
    PeerChannel,
)

load_dotenv()

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION_NAME = os.getenv("TG_SESSION", "tg_session")


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def media_type(message) -> str:
    if isinstance(message.media, MessageMediaPhoto):
        return "📷 Photo"
    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        for attr in doc.attributes:
            if hasattr(attr, "file_name"):
                return f"📎 {attr.file_name}"
        mime = getattr(doc, "mime_type", "")
        if mime.startswith("video"):
            return "🎥 Video"
        if mime.startswith("audio"):
            return "🎵 Audio"
        return f"📎 Document ({mime})"
    if isinstance(message.media, MessageMediaWebPage):
        wp = message.media.webpage
        title = getattr(wp, "title", "") or ""
        url = getattr(wp, "url", "") or ""
        if title and url:
            return f"🔗 [{title}]({url})"
        if url:
            return f"🔗 {url}"
    return ""


async def fetch_and_export(channel: str, output: str, limit: int | None, reverse: bool):
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        print(f"Connecting to Telegram...")
        entity = await client.get_entity(channel)
        title = getattr(entity, "title", channel)
        username = getattr(entity, "username", channel)

        print(f"Channel: {title} (@{username})")
        print("Fetching messages... (this may take a while for large channels)")

        messages = []
        async for msg in client.iter_messages(entity, limit=limit, reverse=reverse):
            messages.append(msg)
            if len(messages) % 200 == 0:
                print(f"  Fetched {len(messages)} messages...")

        total = len(messages)
        print(f"Total messages fetched: {total}")

        # Sort oldest → newest for readable output
        if not reverse:
            messages.sort(key=lambda m: m.date)

        output_path = Path(output or f"{sanitize_filename(title)}.md")

        with output_path.open("w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            if username:
                f.write(f"**Channel:** [@{username}](https://t.me/{username})  \n")
            f.write(f"**Total posts exported:** {total}  \n")
            f.write(f"**Exported on:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}  \n\n")
            f.write("---\n\n")

            for msg in messages:
                if not msg.text and not msg.media:
                    continue  # skip service messages

                # Header: date + link
                date_str = msg.date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                post_url = f"https://t.me/{username}/{msg.id}" if username else ""
                if post_url:
                    f.write(f"### [{date_str}]({post_url})\n\n")
                else:
                    f.write(f"### {date_str}\n\n")

                # Media attachment info
                if msg.media:
                    media_str = media_type(msg)
                    if media_str:
                        f.write(f"> {media_str}\n\n")

                # Message text
                if msg.text:
                    # Preserve line breaks, escape leading '#' to avoid unintended headers
                    text = msg.text.replace("\r\n", "\n").replace("\r", "\n")
                    f.write(text)
                    f.write("\n")

                # Views / forwards metadata
                meta_parts = []
                if msg.views:
                    meta_parts.append(f"👁 {msg.views:,}")
                if msg.forwards:
                    meta_parts.append(f"🔁 {msg.forwards:,}")
                if meta_parts:
                    f.write(f"\n*{' · '.join(meta_parts)}*")

                f.write("\n\n---\n\n")

        print(f"\nDone! Saved to: {output_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Export all posts from a Telegram channel to Markdown."
    )
    parser.add_argument(
        "--channel", "-c",
        required=True,
        help="Channel username (e.g. durov) or invite link",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output .md file path (default: <channel_title>.md)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Max number of messages to fetch (default: all)",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        default=False,
        help="Fetch in reverse order (newest first)",
    )
    args = parser.parse_args()

    if not API_ID or not API_HASH:
        print("Error: TG_API_ID and TG_API_HASH must be set in .env file.")
        print("Get your credentials at https://my.telegram.org/apps")
        raise SystemExit(1)

    asyncio.run(fetch_and_export(args.channel, args.output, args.limit, args.reverse))


if __name__ == "__main__":
    main()
