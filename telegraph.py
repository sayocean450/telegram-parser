"""
Helpers for fetching full article text from telegra.ph via the Telegraph API.

API reference: https://telegra.ph/api#getPage
"""

import json
import re
import urllib.request

TELEGRAPH_RE = re.compile(r'https?://telegra\.ph/([\w-]+(?:/\d+)?)')


def find_telegraph_url(text: str | None, extra_url: str | None = None) -> str | None:
    """
    Return a telegra.ph URL, if any, from:
      - extra_url  (pre-extracted from MessageMediaWebPage.webpage.url)
      - msg.text   (fallback plain-text scan)
    """
    if extra_url and "telegra.ph" in extra_url:
        return extra_url
    if text:
        m = TELEGRAPH_RE.search(text)
        if m:
            return m.group(0)
    return None


# ── node → Markdown converters ────────────────────────────────────────────────

def _inline(children: list) -> str:
    parts = []
    for child in children:
        if isinstance(child, str):
            parts.append(child)
        elif isinstance(child, dict):
            tag   = child.get("tag", "")
            sub   = child.get("children", [])
            attrs = child.get("attrs", {})
            inner = _inline(sub)
            if tag == "a":
                href = attrs.get("href", "")
                parts.append(f"[{inner}]({href})")
            elif tag in ("b", "strong"):
                parts.append(f"**{inner}**")
            elif tag in ("i", "em"):
                parts.append(f"*{inner}*")
            elif tag in ("s", "del"):
                parts.append(f"~~{inner}~~")
            elif tag == "u":
                parts.append(inner)          # markdown has no underline; keep plain
            elif tag == "code":
                parts.append(f"`{inner}`")
            elif tag == "br":
                parts.append("\n")
            else:
                parts.append(inner)
    return "".join(parts)


def _blocks(nodes: list) -> list[str]:
    lines = []
    for node in nodes:
        if isinstance(node, str):
            if node.strip():
                lines.append(node)
        elif isinstance(node, dict):
            tag      = node.get("tag", "")
            children = node.get("children", [])

            if tag == "br":
                lines.append("")

            elif tag in ("h3", "h4"):
                level = 3 if tag == "h3" else 4
                lines.append(f"{'#' * level} {_inline(children)}")
                lines.append("")

            elif tag == "p":
                text = _inline(children)
                if text.strip():
                    lines.append(text)
                    lines.append("")

            elif tag == "blockquote":
                inner = _inline(children)
                for line in inner.split("\n"):
                    lines.append(f"> {line}")
                lines.append("")

            elif tag in ("ul", "ol"):
                for li in children:
                    if isinstance(li, dict) and li.get("tag") == "li":
                        item = _inline(li.get("children", []))
                        lines.append(f"- {item}")
                lines.append("")

            elif tag == "pre":
                code = _inline(children)
                lines.append(f"```\n{code}\n```")
                lines.append("")

            elif tag == "figure":
                # Show caption only; skip image (not downloadable here)
                for child in children:
                    if isinstance(child, dict) and child.get("tag") == "figcaption":
                        cap = _inline(child.get("children", []))
                        if cap.strip():
                            lines.append(f"*{cap}*")
                            lines.append("")

            else:
                text = _inline(children)
                if text.strip():
                    lines.append(text)
                    lines.append("")

    # Strip trailing blank lines
    while lines and not lines[-1].strip():
        lines.pop()

    return lines


# ── public API ────────────────────────────────────────────────────────────────

def fetch_telegraph(url: str) -> str | None:
    """
    Fetch the full text of a telegra.ph article.
    Returns a Markdown string (including the article title as ## heading),
    or None if the fetch / parse fails.
    """
    m = TELEGRAPH_RE.search(url)
    if not m:
        return None
    path    = m.group(1)
    api_url = f"https://api.telegra.ph/getPage/{path}?return_content=true"

    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; tg-parser/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data.get("ok"):
            print(f"  [telegraph] API error for {url}: {data.get('error')}")
            return None

        result  = data["result"]
        title   = result.get("title", "")
        content = result.get("content", [])

        lines = []
        if title:
            lines.append(f"## {title}")
            lines.append("")
        lines.extend(_blocks(content))

        return "\n".join(lines)

    except Exception as e:
        print(f"  [telegraph] fetch failed for {url}: {e}")
        return None
