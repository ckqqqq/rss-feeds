"""Dario's first-party essays and short posts, with explicit month precision."""

import sys
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from lxml import etree

from utils import fetch_page, get_feeds_dir, save_rss_feed, setup_feed_links, setup_logging

BLOG_URL = "https://darioamodei.com/"
FEED_NAME = "darioamodei"
logger = setup_logging()


def parse_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = {}
    for anchor in soup.select("a[href]"):
        url = urljoin(BLOG_URL, anchor["href"])
        parsed = urlparse(url)
        if parsed.netloc == "darioamodei.com" and parsed.path.startswith(("/essay/", "/post/")):
            title = anchor.get_text(" ", strip=True)
            if not title:
                raise ValueError(f"Missing title: {url}")
            links[url] = title
    if not links:
        raise ValueError("No Dario articles found; preserve existing feed")
    return links


def parse_article(html, url, title):
    soup = BeautifulSoup(html, "html.parser")
    date_element = soup.select_one(".post-date")
    if date_element is None:
        raise ValueError(f"Missing publication date: {url}")
    source_date = date_element.get_text(" ", strip=True)
    # The source supplies months only. RSS needs a day; disclose the normalization.
    date = datetime.strptime(source_date, "%B %Y").replace(tzinfo=UTC)
    return {
        "title": title,
        "link": url,
        "date": date,
        "description": f"By Dario Amodei. Source publication month: {source_date}. "
        "RSS date is normalized to the first day; the exact day is not supplied.",
    }


def generate_rss_feed(posts):
    feed = FeedGenerator()
    feed.title("Dario Amodei — Essays and Short Posts")
    feed.description("First-party articles by Dario Amodei. Publication dates have month precision.")
    feed.language("en")
    setup_feed_links(feed, BLOG_URL, FEED_NAME)
    for post in posts:
        entry = feed.add_entry()
        entry.id(post["link"])
        entry.link(href=post["link"])
        entry.title(post["title"])
        entry.description(post["description"])
        entry.published(post["date"])
    return feed


def main():
    try:
        posts = {}
        existing = get_feeds_dir() / f"feed_{FEED_NAME}.xml"
        # Keep historical entries if the home page later removes a link.
        if existing.exists():
            for item in etree.parse(str(existing)).findall("channel/item"):
                url = item.findtext("link")
                posts[url] = {
                    "link": url,
                    "title": item.findtext("title"),
                    "description": item.findtext("description"),
                    "date": parsedate_to_datetime(item.findtext("pubDate")),
                }
        for url, title in parse_links(fetch_page(BLOG_URL)).items():
            posts[url] = parse_article(fetch_page(url), url, title)
        save_rss_feed(generate_rss_feed(list(posts.values())), FEED_NAME)
        logger.info("Verified %s Dario articles", len(posts))
        return True
    except Exception:
        logger.exception("Dario refresh failed; existing feed preserved")
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
