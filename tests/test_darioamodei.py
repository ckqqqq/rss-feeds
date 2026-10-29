"""A changed listing or unknown date must not silently damage a published feed."""

import unittest
from unittest.mock import patch

import darioamodei_blog as feed


class DarioTests(unittest.TestCase):
    def test_listing_deduplicates_and_excludes_external_links(self):
        html = (
            '<a href="/essay/example">Example</a>'
            '<a href="/essay/example">Example</a>'
            '<a href="https://other.test/post/example">Other</a>'
        )
        self.assertEqual(feed.parse_links(html), {"https://darioamodei.com/essay/example": "Example"})

    def test_month_precision_is_disclosed_and_guid_is_stable(self):
        post = feed.parse_article(
            '<div class="post-date">September 2026</div>', "https://darioamodei.com/post/example", "Example"
        )
        self.assertEqual(post["date"].isoformat(), "2026-09-01T00:00:00+00:00")
        self.assertIn("exact day is not supplied", post["description"])
        xml = feed.generate_rss_feed([post]).rss_str().decode()
        self.assertIn('<guid isPermaLink="false">https://darioamodei.com/post/example</guid>', xml)

    def test_empty_listing_and_bad_dates_fail_before_writing(self):
        with self.assertRaises(ValueError):
            feed.parse_links('<a href="/">Home</a>')
        for html in ["", '<div class="post-date">Tomorrow</div>']:
            with self.assertRaises(ValueError):
                feed.parse_article(html, "https://darioamodei.com/post/example", "Example")
        with patch.object(feed, "fetch_page", return_value=""), patch.object(feed, "save_rss_feed") as save:
            self.assertFalse(feed.main())
            save.assert_not_called()


class IncrementalTests(unittest.TestCase):
    def test_existing_entries_are_not_refetched_and_archive_is_preserved(self):
        import tempfile
        from datetime import UTC, datetime
        from pathlib import Path

        old = {
            "title": "Old article",
            "link": "https://darioamodei.com/essay/old",
            "description": "Historical item",
            "date": datetime(2024, 1, 1, tzinfo=UTC),
        }
        new = {
            "title": "New article",
            "link": "https://darioamodei.com/post/new",
            "description": "New item",
            "date": datetime(2026, 9, 1, tzinfo=UTC),
        }
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "feed_darioamodei.xml").write_bytes(feed.generate_rss_feed([old]).rss_str())
            with (
                patch.object(feed, "get_feeds_dir", return_value=Path(directory)),
                patch.object(feed, "fetch_page", return_value="page") as fetch,
                patch.object(feed, "parse_links", return_value={old["link"]: old["title"], new["link"]: new["title"]}),
                patch.object(feed, "parse_article", return_value=new) as parse,
                patch.object(feed, "save_rss_feed") as save,
            ):
                self.assertTrue(feed.main())
                self.assertEqual(fetch.call_count, 2)  # Homepage plus only the new article.
                parse.assert_called_once_with("page", new["link"], new["title"])
                xml = save.call_args.args[0].rss_str().decode()
                self.assertIn(old["link"], xml)
                self.assertIn(new["link"], xml)
