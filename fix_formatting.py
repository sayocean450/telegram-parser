#!/usr/bin/env python3
"""
Fixes corrupted "Ночной пост" headers caused by double-editing.

Two problems to fix:
  1. Text corrupted: "****Ночной пост no.**23**" → "Ночной пост no.23" (clean entity)
  2. Number incremented twice (posts 235, 178, 177, 157) → subtract 2

Usage:
    python3 fix_formatting.py --channel artem_soshnikov --dry-run
    python3 fix_formatting.py --channel artem_soshnikov
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

# Posts that got double-incremented → reduce number by 2
NUMBER_FIX = {235: 26, 178: 25, 177: 24, 157: 6}

# Matches corrupted/clean header at start of text (most posts)
HEADER_RE = re.compile(
    r'^[\*\s]*Ночной пост[\*,\s]*no[\*\.\s]*(\d+)[\*\n\r\s]*(?=\S)',
    re.IGNORECASE,
)

# Fallback: matches "**Ночной пост no.X**" anywhere in text (Telegraph posts)
TITLE_INLINE_RE = re.compile(r'\*\*Ночной пост no\.(\d+)\*\*')


def fix_message(msg) -> tuple[str, list, int, int] | None:
    """
    Returns (new_text, new_entities, old_number, new_number) or None if no fix needed.
    """
    if not msg.text:
        return None

    # --- Case 1: corrupted/old-style header at start of text ---
    m = HEADER_RE.search(msg.text)
    if m:
        current_num = int(m.group(1))
        final_num   = NUMBER_FIX.get(msg.id, current_num)

        new_header   = f"Ночной пост no.{final_num}"
        header_start = m.start()
        header_end   = m.end()

        new_text = msg.text[:header_start] + new_header + "\n\n" + msg.text[header_end:]

        old_block_len = header_end - header_start
        new_block_len = len(new_header) + 2
        diff          = new_block_len - old_block_len

        new_entities = [MessageEntityBold(offset=header_start, length=len(new_header))]
        for ent in (msg.entities or []):
            if ent.offset >= header_end:
                e = copy.copy(ent)
                e.offset += diff
                new_entities.append(e)
            elif ent.offset + ent.length <= header_start:
                new_entities.append(copy.copy(ent))

        return new_text, new_entities, current_num, final_num

    # --- Case 2: clean "**Ночной пост no.X**" inline (Telegraph posts) ---
    if msg.id in NUMBER_FIX:
        m2 = TITLE_INLINE_RE.search(msg.text)
        if m2:
            current_num = int(m2.group(1))
            final_num   = NUMBER_FIX[msg.id]

            old_frag = m2.group(0)                          # **Ночной пост no.26**
            new_frag = f"**Ночной пост no.{final_num}**"
            diff     = len(new_frag) - len(old_frag)

            new_text = msg.text[:m2.start()] + new_frag + msg.text[m2.end():]

            new_entities = []
            for ent in (msg.entities or []):
                e = copy.copy(ent)
                if ent.offset >= m2.end():
                    e.offset += diff
                new_entities.append(e)

            return new_text, new_entities, current_num, final_num

    return None


async def run(channel: str, dry_run: bool):
    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        entity = await client.get_entity(channel)
        title  = getattr(entity, "title", channel)
        print(f"Channel: {title} (@{channel})")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}\n")

        fixed = 0
        async for msg in client.iter_messages(entity):
            result = fix_message(msg)
            if result is None:
                continue

            new_text, new_entities, old_num, new_num = result
            note = f"  (number: {old_num}→{new_num})" if old_num != new_num else ""
            print(f"  ID {msg.id:4d}: no.{old_num} → no.{new_num}{note}")

            if not dry_run:
                while True:
                    try:
                        await client.edit_message(
                            entity, msg.id,
                            new_text,
                            formatting_entities=new_entities,
                        )
                        await asyncio.sleep(0.5)
                        break
                    except MessageNotModifiedError:
                        print(f"    (already up to date, skipping)")
                        break
                    except FloodWaitError as e:
                        print(f"    FloodWait {e.seconds}s — waiting...")
                        await asyncio.sleep(e.seconds + 2)

            fixed += 1

        print(f"\n{'Would fix' if dry_run else 'Fixed'}: {fixed} post(s)")


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
