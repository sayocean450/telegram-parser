#!/usr/bin/env python3
"""
Renumber all "Ночной пост" posts in a channel sequentially starting from no.1.

- Finds all posts matching "Ночной пост no.X" (any number)
- Sorts them chronologically (oldest = no.1)
- Assigns clean sequential numbers: no.1, no.2, no.3 …
- Strips ** markdown artifacts from header; uses only bold entity
- Handles both regular posts and Telegraph-embed posts

Usage:
    python3 renumber.py --channel artem_soshnikov --dry-run
    python3 renumber.py --channel artem_soshnikov
"""

import asyncio, argparse, copy, os, re
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import MessageEntityBold
from telethon.errors import FloodWaitError, MessageNotModifiedError

load_dotenv()
API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION  = os.getenv("TG_SESSION", "tg_session")

# Matches corrupted/clean header at start of text
HEADER_RE = re.compile(
    r'^[\*\s]*Ночной пост[\*,\s]*no[\*\.\s]*(\d+)[\*\n\r\s]*(?=\S)',
    re.IGNORECASE,
)
# Matches inline "**Ночной пост no.X**" (Telegraph posts)
INLINE_RE = re.compile(r'\*{0,2}Ночной пост(?:,)? no\.(\d+)\*{0,2}')


def build_edit(msg, new_num: int):
    """
    Returns (new_text, new_entities) with a clean header 'Ночной пост no.X'
    (no ** markers in text, only a bold entity).
    Returns None if the post already has the correct number and clean text.
    """
    text = msg.text

    # --- Case 1: header at start of text (regular posts) ---
    m = HEADER_RE.search(text)
    if m:
        new_header   = f"Ночной пост no.{new_num}"
        header_start = m.start()
        header_end   = m.end()

        # Check if already correct (clean text + right number)
        current_num = int(m.group(1))
        clean_already = (
            current_num == new_num
            and text[header_start:header_end].rstrip() == new_header
        )
        if clean_already:
            return None

        new_text = text[:header_start] + new_header + "\n\n" + text[header_end:]
        diff     = len(new_header) + 2 - (header_end - header_start)

        new_entities = [MessageEntityBold(offset=header_start, length=len(new_header))]
        for ent in (msg.entities or []):
            if ent.offset >= header_end:
                e = copy.copy(ent)
                e.offset += diff
                new_entities.append(e)
            elif ent.offset + ent.length <= header_start:
                new_entities.append(copy.copy(ent))

        return new_text, new_entities

    # --- Case 2: inline title (Telegraph posts) ---
    m2 = INLINE_RE.search(text)
    if m2:
        current_num = int(m2.group(1))
        old_frag    = m2.group(0)
        new_frag    = f"**Ночной пост no.{new_num}**"

        if old_frag == new_frag:
            return None

        diff     = len(new_frag) - len(old_frag)
        new_text = text[:m2.start()] + new_frag + text[m2.end():]

        new_entities = []
        for ent in (msg.entities or []):
            e = copy.copy(ent)
            if ent.offset >= m2.end():
                e.offset += diff
            new_entities.append(e)

        return new_text, new_entities

    return None


async def run(channel: str, dry_run: bool):
    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        entity = await client.get_entity(channel)
        title  = getattr(entity, "title", channel)
        print(f"Channel: {title} (@{channel})")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}\n")

        # Collect all matching posts
        posts = []
        async for msg in client.iter_messages(entity):
            if not msg.text:
                continue
            if HEADER_RE.search(msg.text) or INLINE_RE.search(msg.text):
                posts.append(msg)

        # Sort oldest → newest
        posts.sort(key=lambda m: m.date)
        print(f"Found {len(posts)} 'Ночной пост' posts\n")

        edited = 0
        for new_num, msg in enumerate(posts, start=1):
            result = build_edit(msg, new_num)

            # Determine current number for display
            m = HEADER_RE.search(msg.text) or INLINE_RE.search(msg.text)
            cur_num = int(m.group(1)) if m else "?"

            if result is None:
                print(f"  ID {msg.id:4d}: no.{cur_num} → no.{new_num}  (already correct)")
                continue

            new_text, new_entities = result
            print(f"  ID {msg.id:4d}: no.{cur_num} → no.{new_num}")

            if not dry_run:
                while True:
                    try:
                        await client.edit_message(
                            entity, msg.id,
                            new_text,
                            formatting_entities=new_entities or None,
                        )
                        await asyncio.sleep(0.5)
                        break
                    except MessageNotModifiedError:
                        break
                    except FloodWaitError as e:
                        print(f"    FloodWait {e.seconds}s — waiting...")
                        await asyncio.sleep(e.seconds + 2)

            edited += 1

        print(f"\n{'Would edit' if dry_run else 'Edited'}: {edited} post(s)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", "-c", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not API_ID or not API_HASH:
        raise SystemExit("Error: set TG_API_ID / TG_API_HASH in .env")
    asyncio.run(run(args.channel, args.dry_run))


if __name__ == "__main__":
    main()
