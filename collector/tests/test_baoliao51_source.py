from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from collector import baoliao51_source as source


class Baoliao51SourceTests(unittest.TestCase):
    def test_normalize_target_defaults_to_latest_category(self):
        self.assertEqual(
            source.normalize_baoliao51_target_value("https://www.51baoliao01.com"),
            "https://www.51baoliao01.com/category/jrbl/",
        )
        self.assertEqual(
            source.normalize_baoliao51_target_value("www.51baoliao01.com/category/jrbl"),
            "https://www.51baoliao01.com/category/jrbl/",
        )

    def test_parse_list_page_reads_archive_cards(self):
        html = """
        <html><body>
          <article><a href="/archives/151218/"><h2>Real Title</h2></a><span>2026年6月10日</span></article>
          <article><a href="/other/1"><h2>Ignore</h2></a></article>
        </body></html>
        """
        with patch.object(source, "fetch_html", return_value=html):
            items, next_url = source.parse_list_page(
                "https://www.51baoliao01.com/category/jrbl/",
                "https://www.51baoliao01.com/category/jrbl/",
            )
        self.assertIsNone(next_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["page_id"], "151218")
        self.assertEqual(items[0]["url"], "https://www.51baoliao01.com/archives/151218/")
        self.assertEqual(items[0]["title"], "Real Title")

    def test_parse_detail_page_uses_real_video_url_not_ad_url(self):
        config = {
            "video": {"url": "https://hls.chxgdn.cn/videos5/real/real.m3u8?auth_key=1781068776-1-0-real", "type": "hls"},
            "video_player_ads": [{"src": "https://pic.myedua.cn/ad.gif", "link": "1"}],
        }
        html = f"""
        <html><body>
          <h1>Detail Title</h1>
          <script type="application/ld+json">{{"@type":"Article","datePublished":"2026-06-10T05:00:00+00:00"}}</script>
          <div class="dplayer" data-video_id="151218002" data-config='{json.dumps(config)}'></div>
        </body></html>
        """
        with patch.object(source, "fetch_html", return_value=html):
            detail = source.parse_detail_page("https://www.51baoliao01.com/archives/151218/")
        self.assertEqual(detail["title"], "Detail Title")
        self.assertEqual(len(detail["players"]), 1)
        self.assertEqual(detail["players"][0]["guid"], "baoliao51:151218:151218002")
        self.assertEqual(detail["players"][0]["video_url"], config["video"]["url"])

    def test_verify_hls_url_records_explicit_expiry_and_headers(self):
        playlist = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-KEY:METHOD=AES-128,URI="https://tts.doudou520.online/videos5/real/crypt.key?expires=1781068776"
#EXT-X-TARGETDURATION:5
#EXTINF:5.0,
https://tts.doudou520.online/videos5/real/seg0.ts?expires=1781068776
#EXT-X-ENDLIST
"""

        class FakeResponse:
            status_code = 206
            headers = {"Content-Type": "video/mp2t"}

        def fake_read_media_chunk(url, referer, size):
            if url.endswith("crypt.key?expires=1781068776"):
                return b"0123456789abcdef", FakeResponse()
            return b"x" * min(size, 512), FakeResponse()

        with patch.object(source, "fetch_hls_text", return_value=playlist), patch.object(source, "read_media_chunk", side_effect=fake_read_media_chunk):
            with patch.object(source, "now_utc", return_value=datetime(2026, 6, 10, 5, 0, tzinfo=timezone.utc)):
                verified = source.verify_hls_url(
                    "https://hls.chxgdn.cn/videos5/real/real.m3u8?expires=1781068776",
                    "https://www.51baoliao01.com/archives/151218/",
                )

        self.assertEqual(verified["media_format"], "hls")
        self.assertTrue(verified["playback_refresh_required"])
        self.assertEqual(verified["video_url_expires_at"], datetime(2026, 6, 10, 5, 19, 36, tzinfo=timezone.utc))
        self.assertEqual(verified["playback_headers"]["Referer"], "https://www.51baoliao01.com/archives/151218/")
        self.assertEqual(verified["playback_headers"]["Origin"], "https://www.51baoliao01.com")

    def test_parse_query_expiry_ignores_auth_key_timestamp(self):
        self.assertIsNone(source.parse_query_expiry("https://hls.chxgdn.cn/video.m3u8?auth_key=1781068776-1-0-real"))


if __name__ == "__main__":
    unittest.main()
