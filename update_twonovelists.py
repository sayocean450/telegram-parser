#!/usr/bin/env python3
"""
Incremental updater for the twonovelists channel.

1. Parses twonovelists → twonovelists_common.md (full refresh)
2. Syncs individual post files in channels/twonovelists/:
   - Updates files whose content changed (edited posts)
   - Creates files for brand-new posts that don't exist yet

Usage:
    python3 update_twonovelists.py
    python3 update_twonovelists.py --dry-run
"""

import asyncio
import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaWebPage,
)
from datetime import timezone
from telegraph import find_telegraph_url, fetch_telegraph

load_dotenv()

API_ID       = int(os.getenv("TG_API_ID", "0"))
API_HASH     = os.getenv("TG_API_HASH", "")
SESSION_NAME = os.getenv("TG_SESSION", "tg_session")

CHANNEL   = "twonovelists"
COMMON_MD = Path("/Users/blacktrope/Library/CloudStorage/Dropbox/channels/twonovelists_common.md")
POSTS_DIR = Path("/Users/blacktrope/Library/CloudStorage/Dropbox/soshnikov-writing/channels/twonovelists")

# ── parser helpers ────────────────────────────────────────────────────────────

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
        url   = getattr(wp, "url",   "") or ""
        if title and url:
            return f"🔗 [{title}]({url})"
        if url:
            return f"🔗 {url}"
    return ""


async def parse_channel(dry_run: bool):
    """Fetch all posts from twonovelists and write to COMMON_MD."""
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        print("Connecting to Telegram...")
        entity   = await client.get_entity(CHANNEL)
        title    = getattr(entity, "title",    CHANNEL)
        username = getattr(entity, "username", CHANNEL)

        print(f"Channel: {title} (@{username})")
        print("Fetching messages...")

        messages = []
        async for msg in client.iter_messages(entity, reverse=True):
            messages.append(msg)
            if len(messages) % 200 == 0:
                print(f"  Fetched {len(messages)} messages...")

        total = len(messages)
        print(f"Total messages fetched: {total}")

        if dry_run:
            print(f"(dry-run) Would write {total} posts to {COMMON_MD}")
            return total

        COMMON_MD.parent.mkdir(parents=True, exist_ok=True)

        with COMMON_MD.open("w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            if username:
                f.write(f"**Channel:** [@{username}](https://t.me/{username})  \n")
            f.write(f"**Total posts exported:** {total}  \n")
            f.write(f"**Exported on:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}  \n\n")
            f.write("---\n\n")

            for msg in messages:
                if not msg.text and not msg.media:
                    continue

                date_str = msg.date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                post_url = f"https://t.me/{username}/{msg.id}" if username else ""
                if post_url:
                    f.write(f"### [{date_str}]({post_url})\n\n")
                else:
                    f.write(f"### {date_str}\n\n")

                # Detect Telegraph link and fetch full article text
                wp_url = (
                    getattr(msg.media.webpage, "url", None)
                    if isinstance(msg.media, MessageMediaWebPage)
                    else None
                )
                tg_url     = find_telegraph_url(msg.text, wp_url)
                tg_content = fetch_telegraph(tg_url) if tg_url else None

                if msg.media:
                    if tg_content and isinstance(msg.media, MessageMediaWebPage):
                        pass  # full content replaces the short preview
                    else:
                        media_str = media_type(msg)
                        if media_str:
                            f.write(f"> {media_str}\n\n")

                post_text = tg_content or msg.text or ""
                if post_text:
                    text = post_text.replace("\r\n", "\n").replace("\r", "\n")
                    f.write(text)
                    f.write("\n")

                meta_parts = []
                if msg.views:
                    meta_parts.append(f"👁 {msg.views:,}")
                if msg.forwards:
                    meta_parts.append(f"🔁 {msg.forwards:,}")
                if meta_parts:
                    f.write(f"\n*{' · '.join(meta_parts)}*")

                f.write("\n\n---\n\n")

        print(f"Saved to: {COMMON_MD}")
        return total

# ── knife helpers ─────────────────────────────────────────────────────────────

POST_SEPARATOR = re.compile(r'\n---\n')
POST_HEADER    = re.compile(r'^### \[')


def split_posts(md_path: Path) -> list[str]:
    text = md_path.read_text(encoding="utf-8")
    first_sep = text.find('\n---\n')
    if first_sep == -1:
        print("Error: no posts found in common file")
        sys.exit(1)
    body   = text[first_sep + 5:]
    chunks = POST_SEPARATOR.split(body)
    return [c.strip() for c in chunks if POST_HEADER.match(c.strip())]


def count_existing(out_dir: Path) -> int:
    if not out_dir.exists():
        return 0
    return sum(1 for f in out_dir.iterdir() if re.match(r'^\d{3}\.md$', f.name))


def sync_posts(dry_run: bool):
    """
    Sync individual post files with the freshly parsed common file:
      - Overwrite files whose content changed (edited posts in the channel)
      - Create files for brand-new posts that don't exist yet
    """
    posts    = split_posts(COMMON_MD)
    existing = count_existing(POSTS_DIR)

    print(f"\nSync step:")
    print(f"  Total posts in common file : {len(posts)}")
    print(f"  Already sliced             : {existing}")
    print(f"  New to write               : {max(0, len(posts) - existing)}")

    if not dry_run:
        POSTS_DIR.mkdir(parents=True, exist_ok=True)

    updated = 0
    created = 0

    for i, post in enumerate(posts, start=1):
        filename = f"{i:03d}.md"
        out_path = POSTS_DIR / filename
        new_content = post + '\n'

        if out_path.exists():
            old_content = out_path.read_text(encoding="utf-8")
            if old_content == new_content:
                continue  # unchanged — skip silently
            preview = post.splitlines()[0][:70]
            print(f"  UPDATED  {filename}  {preview}")
            if not dry_run:
                out_path.write_text(new_content, encoding="utf-8")
            updated += 1
        else:
            preview = post.splitlines()[0][:70]
            print(f"  NEW      {filename}  {preview}")
            if not dry_run:
                out_path.write_text(new_content, encoding="utf-8")
            created += 1

    if updated == 0 and created == 0:
        print("  All posts are up to date — nothing to do.")
    elif dry_run:
        print(f"\n(dry-run) Would update {updated} and create {created} file(s).")
    else:
        parts = []
        if updated:
            parts.append(f"{updated} updated")
        if created:
            parts.append(f"{created} created")
        print(f"\nDone! {', '.join(parts)}. Files in {POSTS_DIR}")


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Incremental updater: parse twonovelists, then sync post files."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without writing files")
    args = parser.parse_args()

    if not API_ID or not API_HASH:
        print("Error: TG_API_ID and TG_API_HASH must be set in .env")
        sys.exit(1)

    asyncio.run(parse_channel(args.dry_run))
    sync_posts(args.dry_run)


if __name__ == "__main__":
    main()
