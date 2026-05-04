# Telegram Channel Parser

Exports all posts from a Telegram channel into a single Markdown file.

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
# Export all posts from a public channel
python parser.py --channel durov

# Export to a specific file
python parser.py --channel durov --output durov_posts.md

# Export only the latest 500 messages
python parser.py --channel durov --limit 500
```

### Arguments

| Argument | Short | Description |
|---|---|---|
| `--channel` | `-c` | Channel username or invite link (**required**) |
| `--output` | `-o` | Output file path (default: `<channel_title>.md`) |
| `--limit` | `-l` | Max messages to fetch (default: all) |
| `--reverse` | | Fetch newest-first |

## Output format

Each post in the Markdown file looks like:

```markdown
### [2024-01-15 10:30 UTC](https://t.me/channel/123)

> 📷 Photo

Post text goes here...

*👁 12,345 · 🔁 678*

---
```

## First run — authentication

On the first run Telethon will ask for your phone number and a confirmation code from Telegram. A `.session` file is created locally — subsequent runs won't ask again.

> **Never commit `.env` or `*.session` files — they're in `.gitignore`.**
