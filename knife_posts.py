#!/usr/bin/env python3
"""
Splits a parsed channel .md file into individual post files: 001.md, 002.md, etc.

Usage:
    python3 knife_posts.py <path-to-channel.md> --out <output-dir>
    python3 knife_posts.py <path-to-channel.md> --out <output-dir> --dry-run
"""

import argparse
import re
import sys
from pathlib import Path


# Posts are separated by "---" lines; each starts with "### [date](url)"
POST_SEPARATOR = re.compile(r'\n---\n')
POST_HEADER    = re.compile(r'^### \[')


def split_posts(md_path: Path) -> list[str]:
    text = md_path.read_text(encoding='utf-8')

    # Drop the file-level header block (everything before the first ---)
    first_sep = text.find('\n---\n')
    if first_sep == -1:
        print("Error: no posts found (separator '---' not found)")
        sys.exit(1)

    body = text[first_sep + 5:]   # skip the first \n---\n

    # Split on --- separators
    chunks = POST_SEPARATOR.split(body)

    # Keep only chunks that start with a ### post header
    posts = [c.strip() for c in chunks if POST_HEADER.match(c.strip())]
    return posts


def count_existing(out_dir: Path) -> int:
    """Count how many NNN.md files already exist in out_dir."""
    if not out_dir.exists():
        return 0
    return sum(1 for f in out_dir.iterdir() if re.match(r'^\d{3}\.md$', f.name))


def write_individual_posts(
    md_path: Path,
    out_dir: Path,
    *,
    incremental: bool = False,
    dry_run: bool = False,
) -> int:
    """
    Split a common .md file into 001.md, 002.md, … in out_dir.
    Returns the number of files written (or that would be written in dry-run).
    """
    posts = split_posts(md_path)
    if not posts:
        print("No posts found.")
        return 0

    existing = count_existing(out_dir) if incremental else 0
    new_posts = posts[existing:]

    print(f"Channel file : {md_path}")
    print(f"Output folder: {out_dir}")
    print(f"Total posts  : {len(posts)}")
    if incremental:
        print(f"Already exist: {existing}")
        print(f"New posts    : {len(new_posts)}\n")
    else:
        print()

    if not new_posts:
        print("Nothing to do — all posts already exist.")
        return 0

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for i, post in enumerate(new_posts, start=existing + 1):
        filename = f"{i:03d}.md"
        out_path = out_dir / filename
        preview = post.splitlines()[0][:80]
        print(f"  {filename}  {preview}")
        if not dry_run:
            out_path.write_text(post + '\n', encoding='utf-8')

    if dry_run:
        print("\n(dry-run — no files written)")
    else:
        print(f"\nDone! {len(new_posts)} new files written to {out_dir}")

    return len(new_posts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='Path to the parsed channel .md file')
    parser.add_argument('--out', required=True, help='Output directory for individual post files')
    parser.add_argument('--incremental', action='store_true',
                        help='Skip posts that already have a file, add only new ones')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be created without writing files')
    args = parser.parse_args()

    md_path = Path(args.file).expanduser().resolve()
    if not md_path.exists():
        print(f"Error: file not found: {md_path}")
        sys.exit(1)

    out_dir = Path(args.out).expanduser().resolve()
    write_individual_posts(
        md_path,
        out_dir,
        incremental=args.incremental,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
