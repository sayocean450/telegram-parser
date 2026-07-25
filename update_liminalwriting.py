#!/usr/bin/env python3
"""
Parse liminalwriting into liminalwriting_common.md (no knifing).

Usage:
    python3 update_liminalwriting.py
    python3 update_liminalwriting.py --dry-run
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from parser import fetch_and_export

load_dotenv()

API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")

CHANNEL   = "liminalwriting"
COMMON_MD = Path(
    "/Users/blacktrope/Library/CloudStorage/Dropbox/soshnikov-writing/channels"
    "/liminalwriting_common.md"
)


def main():
    argp = argparse.ArgumentParser(
        description="Parse liminalwriting into liminalwriting_common.md."
    )
    argp.add_argument(
        "--dry-run",
        action="store_true",
        help="Show target path without fetching or writing",
    )
    args = argp.parse_args()

    if not API_ID or not API_HASH:
        print("Error: TG_API_ID and TG_API_HASH must be set in .env")
        sys.exit(1)

    if args.dry_run:
        print(f"(dry-run) Would parse @{CHANNEL} → {COMMON_MD}")
        return

    asyncio.run(
        fetch_and_export(
            CHANNEL,
            str(COMMON_MD),
            limit=None,
            reverse=True,
            knife=False,
        )
    )


if __name__ == "__main__":
    main()
