# Telegram Channel Parser

Exports all text posts from a Telegram channel into a single `*_common.md` file.
By default posts are **not** split into individual files.

## Setup

### 1. Get API credentials
Go to [my.telegram.org/apps](https://my.telegram.org/apps), log in and create an app — you'll get `api_id` and `api_hash`.

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in TG_API_ID and TG_API_HASH
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

```bash
# Export all posts into one common Markdown file
python parser.py --channel durov --output durov_common.md

# Same, then also split into individual files under durov_knifed/
python parser.py --channel durov --output durov_common.md --knife

# Export only the latest 500 messages
python parser.py --channel durov --output durov_common.md --limit 500
```

With `--knife`, the script creates `<channel>_knifed/` **next to** the common file
(e.g. `./durov_common.md` → `./durov_knifed/001.md`, `002.md`, …).

You can still knife an existing common file separately:

```bash
python knife_posts.py durov_common.md --out durov_knifed
```

### Arguments

| Argument | Short | Description |
|---|---|---|
| `--channel` | `-c` | Channel username or invite link (**required**) |
| `--output` | `-o` | Path to the `*_common.md` file (**required**) |
| `--limit` | `-l` | Max messages to fetch (default: all) |
| `--reverse` | | Fetch newest-first |
| `--knife` | | Also split posts into `<channel>_knifed/` beside the common file |

## Output format

Only text posts are exported (photo/video-only messages without a caption are skipped).
Posts with both an image and a caption keep the text only — no media stubs.

```markdown
### [2024-01-15 10:30 UTC](https://t.me/channel/123)

Post text goes here...

*👁 12,345 · 🔁 678*

---
```

## First run — authentication

On the first run Telethon will ask for your phone number and a confirmation code from Telegram. A `.session` file is created locally — subsequent runs won't ask again.

> **Never commit `.env` or `*.session` files — they're in `.gitignore`.**
