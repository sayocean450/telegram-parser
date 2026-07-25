#!/usr/bin/env python3
"""
Restores corrupted posts 170, 177, 178, 235 from the backup .md file.

Strategy:
  - Take the original body text from backup (correct entities, correct structure)
  - Replace only the post number in the header
  - Send via Telethon parse_mode='md' — it strips markdown markers and builds
    clean entities (Bold, TextUrl, Italic, Strike) from scratch

Usage:
    python3 restore_posts.py --dry-run   # preview extracted text
    python3 restore_posts.py             # apply
"""

import asyncio, argparse, os, re
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError, MessageNotModifiedError

load_dotenv()
API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION  = os.getenv("TG_SESSION", "tg_session")

BACKUP   = "/Users/blacktrope/Library/CloudStorage/Dropbox/channels/artem_soshnikov_backup.md"
CHANNEL  = "artem_soshnikov"

# post_id → correct final number
POSTS = {170: 19, 177: 25, 178: 26, 235: 27}

NUM_RE = re.compile(r'(Ночной пост(?:,)? no)\.\d+')


def extract_from_backup(post_id: int) -> str:
    """
    Extracts post text from backup, stripping parser.py metadata
    (media descriptions "> ...", view counts "*👁 ...*").
    """
    with open(BACKUP, encoding='utf-8') as f:
        content = f.read()

    # Find the section using simple string search (avoids re.escape locale issues)
    url = f"https://t.me/artem_soshnikov/{post_id}"
    anchor = f"]({url})\n\n"
    pos = content.find(anchor)
    if pos == -1:
        raise ValueError(f"Post {post_id} not found in backup")

    start = pos + len(anchor)
    end_pos = content.find('\n\n---\n', start)
    section = content[start : end_pos if end_pos != -1 else len(content)]

    lines = section.split('\n')

    # Strip trailing blank lines + *👁...* metadata
    while lines and (lines[-1].strip() == '' or lines[-1].startswith('*👁')):
        lines.pop()

    # Strip leading media description lines ("> 📷", "> 🔗", etc.) + blank lines
    while lines and (lines[0].strip() == '' or lines[0].startswith('> ')):
        lines.pop(0)

    # Strip any remaining leading/trailing blank lines
    while lines and lines[0].strip() == '':
        lines.pop(0)
    while lines and lines[-1].strip() == '':
        lines.pop()

    return '\n'.join(lines)


def apply_new_number(text: str, new_num: int) -> str:
    return NUM_RE.sub(rf'\g<1>.{new_num}', text, count=1)


async def run(dry_run: bool):
    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        entity = await client.get_entity(CHANNEL)

        for post_id, new_num in POSTS.items():
            print(f"\n{'='*50}")
            print(f"Post {post_id}  →  no.{new_num}")

            try:
                backup_text = extract_from_backup(post_id)
            except ValueError as e:
                print(f"  ERROR: {e}")
                continue

            new_text = apply_new_number(backup_text, new_num)

            # Show first line and last line for verification
            lines = new_text.splitlines()
            print(f"  Header : {lines[0]!r}")
            print(f"  Last   : {lines[-1]!r}")
            print(f"  Length : {len(new_text)} chars, {len(lines)} lines")

            if dry_run:
                print("  (dry-run, not editing)")
                continue

            while True:
                try:
                    await client.edit_message(
                        entity, post_id,
                        new_text,
                        parse_mode='md',
                    )
                    print("  ✓ restored")
                    await asyncio.sleep(1)
                    break
                except MessageNotModifiedError:
                    print("  already correct, skipping")
                    break
                except FloodWaitError as e:
                    print(f"  FloodWait {e.seconds}s — waiting...")
                    await asyncio.sleep(e.seconds + 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    asyncio.run(run(args.dry_run))


if __name__ == '__main__':
    main()
