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
