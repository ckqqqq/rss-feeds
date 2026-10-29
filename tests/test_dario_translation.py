"""Translation errors must never be cached as successful Chinese output."""

import unittest
from unittest.mock import Mock, patch

from translate_rss_titles import translate


class TranslationTests(unittest.TestCase):
    def test_returns_service_translation(self):
        response = Mock()
        response.json.return_value = {
            "responseStatus": 200,
            "quotaFinished": False,
            "responseData": {"translatedText": "科技的青春期"},
        }
        with patch("translate_rss_titles.requests.get", return_value=response) as request:
            self.assertEqual(translate("The Adolescence of Technology"), "科技的青春期")
            self.assertEqual(request.call_args.kwargs["params"]["langpair"], "en|zh-CN")

    def test_quota_or_empty_output_is_rejected(self):
        for result in [
            {"responseStatus": 200, "quotaFinished": True, "responseData": {"translatedText": "Quota exceeded"}},
            {"responseStatus": 500, "responseData": {"translatedText": "Error"}},
            {"responseStatus": 200, "responseData": {"translatedText": ""}},
        ]:
            response = Mock()
            response.json.return_value = result
            with patch("translate_rss_titles.requests.get", return_value=response), self.assertRaises(ValueError):
                translate("Example")


class IncrementalTranslationTests(unittest.TestCase):
    def test_missing_translation_is_filled_once_then_cached(self):
        import json
        import tempfile
        from pathlib import Path

        from lxml import etree

        import translate_rss_titles as titles

        url = "https://example.com/post"
        with tempfile.TemporaryDirectory() as directory:
            article, cache = Path(directory, "article.md"), Path(directory, "cache.json")
            article.write_text(f"- 2026-10 · **Example** · [Example title]({url})\n")
            cache.write_text(json.dumps({"items": {url: {"title_en": "Example title", "title_zh": ""}}}))
            empty_feed = etree.ElementTree(etree.fromstring("<rss><channel/></rss>"))
            with (
                patch(
                    "sys.argv", ["translate", "--article", str(article), "--output", str(cache), "--engine", "mymemory"]
                ),
                patch.object(titles.etree, "parse", return_value=empty_feed),
                patch.object(titles, "translate", return_value="示例标题") as translate_call,
                patch.object(titles.time, "sleep"),
            ):
                titles.main()
                titles.main()
                translate_call.assert_called_once_with("Example title")
                self.assertEqual(json.loads(cache.read_text())["items"][url]["title_zh"], "示例标题")
