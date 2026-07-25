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
from telethon.tl.types import MessageMediaWebPage
from telegraph import find_telegraph_url, fetch_telegraph
from knife_posts import write_individual_posts

load_dotenv()

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION_NAME = os.getenv("TG_SESSION", "tg_session")


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def resolve_post_text(msg) -> str:
    """Return post text, preferring full Telegraph article over Telegram caption.

    Media-only messages (photos, videos, etc. without caption) yield "".
    """
    wp_url = (
        getattr(msg.media.webpage, "url", None)
        if isinstance(msg.media, MessageMediaWebPage)
        else None
    )
    tg_url = find_telegraph_url(msg.text, wp_url)
    if tg_url:
        tg_content = fetch_telegraph(tg_url)
        if tg_content:
            return tg_content
    return msg.text or ""


async def fetch_and_export(
    channel: str,
    output: str,
    limit: int | None,
    reverse: bool,
    knife: bool = False,
):
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        print(f"Connecting to Telegram...")
        entity = await client.get_entity(channel)
        title = getattr(entity, "title", channel)
        username = getattr(entity, "username", None) or sanitize_filename(channel)

        print(f"Channel: {title} (@{username})")
        print("Fetching messages... (this may take a while for large channels)")

        messages = []
        async for msg in client.iter_messages(entity, limit=limit, reverse=reverse):
            messages.append(msg)
            if len(messages) % 200 == 0:
                print(f"  Fetched {len(messages)} messages...")

        print(f"Total messages fetched: {len(messages)}")

        # Sort oldest → newest for readable output
        if not reverse:
            messages.sort(key=lambda m: m.date)

        output_path = Path(output).expanduser() if output else Path(f"{sanitize_filename(username)}_common.md")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        posts: list[str] = []
        for msg in messages:
            post_text = resolve_post_text(msg)
            if not post_text:
                continue  # skip service / media-only messages (photos without caption, etc.)

            date_str = msg.date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            post_url = f"https://t.me/{username}/{msg.id}" if username else ""
            header = f"### [{date_str}]({post_url})\n\n" if post_url else f"### {date_str}\n\n"

            text = post_text.replace("\r\n", "\n").replace("\r", "\n")
            chunk = header + text + "\n"

            meta_parts = []
            if msg.views:
                meta_parts.append(f"👁 {msg.views:,}")
            if msg.forwards:
                meta_parts.append(f"🔁 {msg.forwards:,}")
            if meta_parts:
                chunk += f"\n*{' · '.join(meta_parts)}*"

            chunk += "\n\n---\n\n"
            posts.append(chunk)

        with output_path.open("w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            if username:
                f.write(f"**Channel:** [@{username}](https://t.me/{username})  \n")
            f.write(f"**Total posts exported:** {len(posts)}  \n")
            f.write(f"**Exported on:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}  \n\n")
            f.write("---\n\n")
            f.writelines(posts)

        print(f"\nDone! Exported {len(posts)} text posts to: {output_path.resolve()}")

        if knife:
            knife_dir = output_path.parent / f"{sanitize_filename(username)}_knifed"
            print(f"\nKnifing posts into: {knife_dir}")
            write_individual_posts(output_path, knife_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Export all posts from a Telegram channel to a single Markdown file."
    )
    parser.add_argument(
        "--channel", "-c",
        required=True,
        help="Channel username (e.g. durov) or invite link",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output *_common.md file path (e.g. ~/Dropbox/channels/durov_common.md)",
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
    parser.add_argument(
        "--knife",
        action="store_true",
        default=False,
        help="Also split posts into <channel>_knifed/ next to the common file",
    )
    args = parser.parse_args()

    if not API_ID or not API_HASH:
        print("Error: TG_API_ID and TG_API_HASH must be set in .env file.")
        print("Get your credentials at https://my.telegram.org/apps")
        raise SystemExit(1)

    asyncio.run(
        fetch_and_export(
            args.channel,
            args.output,
            args.limit,
            args.reverse,
            knife=args.knife,
        )
    )


if __name__ == "__main__":
    main()
