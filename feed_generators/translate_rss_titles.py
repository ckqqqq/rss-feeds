"""Translate public RSS article titles only, caching each result without model tokens."""

import argparse
import json
import os
import re
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import requests
from lxml import etree

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


def save_cache(output, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=destination.parent, delete=False) as temporary:
        json.dump(output, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
    os.replace(temporary.name, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--article", type=Path, required=True)
    parser.add_argument("--engine", choices=["local", "mymemory"], default="local")
    args = parser.parse_args()
    local = None
    output = json.loads(args.output.read_text()) if args.output.exists() else {"provider": PROVIDER, "items": {}}
    output["provider"] = "Cached machine translation: MyMemory / Argos OPUS-MT"
    items = output["items"]
    feed = Path(__file__).resolve().parents[1] / "feeds/feed_darioamodei.xml"
    titles = {item.findtext("link"): item.findtext("title") for item in etree.parse(str(feed)).findall("channel/item")}
    for title, url, english in re.findall(
        r"^- \d{4}-\d{2}(?:-\d{2})? · \*\*[^*]+\*\* · \[([^\]]+)\]\((https?://[^)]+)\)(?:\uFF08([^\n]*)\uFF09)?",
        args.article.read_text(),
        re.M,
    ):
        titles.setdefault(url, english or title)
    for index, (url, title) in enumerate(titles.items(), 1):
        cached = items.get(url, {})
        if cached.get("title_en") == title:
            continue
        if args.engine == "local":
            if local is None:
                from local_title_translation import LocalTitleTranslator

                local = LocalTitleTranslator()
            translated = local.translate(title)
        else:
            translated = translate(title)
        items[url] = {
            "title_en": title,
            "title_zh": translated,
            "translated_at": datetime.now(UTC).isoformat(),
            "provider": "Argos OPUS-MT en_zh 1.9" if args.engine == "local" else PROVIDER,
        }
        # Save each success so a quota/network failure never repeats successful work.
        save_cache(output, args.output)
        print(f"Translated title {index}/{len(titles)}: {title}", flush=True)
        if args.engine == "mymemory":
            time.sleep(1)
    print(f"Verified {len(titles)} cached titles; no excerpts or full text sent")


if __name__ == "__main__":
    main()
