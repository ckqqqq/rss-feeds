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
