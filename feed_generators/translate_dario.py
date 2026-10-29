"""Cache Chinese machine translations of public Dario titles and short source excerpts."""

import argparse
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from lxml import etree

from utils import fetch_page

PROVIDER = "MyMemory / machine translation"


def translate(text):
    response = requests.get(
        "https://api.mymemory.translated.net/get", params={"q": text, "langpair": "en|zh-CN", "mt": "1"}, timeout=30
    )
    response.raise_for_status()
    result = response.json()
    translated = result.get("responseData", {}).get("translatedText", "")
    if str(result.get("responseStatus")) != "200" or result.get("quotaFinished") or not translated:
        raise ValueError("Machine translation unavailable or quota exceeded; keep previous cache")
    return translated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    previous = json.loads(args.output.read_text()) if args.output.exists() else {"provider": PROVIDER, "items": {}}
    items = dict(previous["items"])
    feed = Path(__file__).resolve().parents[1] / "feeds/feed_darioamodei.xml"
    for item in etree.parse(str(feed)).findall("channel/item"):
        url, title = item.findtext("link"), item.findtext("title")
        if not url.startswith(("https://darioamodei.com/post/", "https://darioamodei.com/essay/")):
            raise ValueError("Unexpected public article URL")
        soup = BeautifulSoup(fetch_page(url), "html.parser")
        meta = soup.select_one('meta[name="description"]')
        excerpt = meta.get("content", "").strip() if meta else ""
        if not excerpt:
            paragraph = soup.select_one(".rich-text p")
            if paragraph is None:
                raise ValueError("Source excerpt missing")
            excerpt = paragraph.get_text(" ", strip=True)
        excerpt = excerpt[:350].rsplit(" ", 1)[0] + "…" if len(excerpt) > 350 else excerpt
        cached = items.get(url, {})
        if cached.get("title_en") == title and cached.get("excerpt_en") == excerpt:
            continue
        title_zh = cached["title_zh"] if cached.get("title_en") == title else translate(title)
        time.sleep(1)
        excerpt_zh = cached["excerpt_zh"] if cached.get("excerpt_en") == excerpt else translate(excerpt)
        items[url] = {
            "title_en": title,
            "title_zh": title_zh,
            "excerpt_en": excerpt,
            "excerpt_zh": excerpt_zh,
            "translated_at": datetime.now(UTC).isoformat(),
        }
        print(f"Translated: {title}", flush=True)
        time.sleep(1)
    output = {"provider": PROVIDER, "items": items}
    if output != previous:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=args.output.parent, delete=False) as temporary:
            json.dump(output, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
        os.replace(temporary.name, args.output)
    print(f"Verified {len(items)} translation cache entries")


if __name__ == "__main__":
    main()
