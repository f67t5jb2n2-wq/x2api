from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from collector import missav_source as missav


class MissavSourceTests(unittest.TestCase):
    def test_parse_list_page_extracts_unique_vodplay_cards(self):
        html = """
        <html><body>
          <div class="thumbnail group">
            <a href="/vodplay/261745-1-1/">
              <img src="/static/images/lazyload.gif" data-src="https://img.example/cover.jpg" alt="Real Title">
            </a>
            <a href="/vodplay/261745-1-1/">duplicate</a>
          </div>
          <iframe src="https://go.rmhfrtnd.com/smartpop/ad"></iframe>
          <div class="thumbnail group">
            <a href="https://evil.example/vodplay/999-1-1/"><img alt="Ad"></a>
          </div>
        </body></html>
        """

        with patch.object(missav, "fetch_html", return_value=html):
            items = missav.parse_list_page("https://missav.app/vodtype/20/", 1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["guid"], "missav:261745")
        self.assertEqual(items[0]["url"], "https://missav.app/vodplay/261745-1-1/")
        self.assertEqual(items[0]["title"], "Real Title")
        self.assertEqual(items[0]["image"], "https://img.example/cover.jpg")

    def test_parse_detail_page_uses_player_url_and_ignores_iframe_ads(self):
        payload = {
            "encrypt": 0,
            "url": "https://2605.senlin2026.com/20260608/video/index.m3u8",
            "from": "slm3u8",
            "id": "261745",
            "nid": 1,
            "vod_data": {"vod_name": "Detail Title", "vod_class": "Category"},
        }
        html = f"""
        <html><body>
          <iframe src="https://go.rmhfrtnd.com/smartpop/ad"></iframe>
          <script>var player_aaaa={json.dumps(payload)}</script>
        </body></html>
        """

        with patch.object(missav, "fetch_html", return_value=html):
            detail = missav.parse_detail_page("https://missav.app/vodplay/261745-1-1/")

        self.assertEqual(detail["title"], "Detail Title")
        self.assertEqual(detail["category_name"], "Category")
        self.assertEqual(detail["players"][0]["video_url"], "https://2605.senlin2026.com/20260608/video/index.m3u8")
        self.assertEqual(detail["players"][0]["video_type"], "hls")

    def test_decode_player_url_supports_encoded_values(self):
        self.assertEqual(
            missav.decode_player_url({"encrypt": 1, "url": "https%3A%2F%2Fcdn.example%2Fvideo.m3u8"}, "https://missav.app/vodplay/1-1-1/"),
            "https://cdn.example/video.m3u8",
        )

    def test_verify_hls_url_accepts_master_variant_and_ts_segments(self):
        master = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1280x720
2000kb/hls/index.m3u8
"""
        media = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXTINF:6,
seg0.ts
#EXTINF:6,
seg1.ts
#EXT-X-ENDLIST
"""
        chunk = bytes([0x47]) + b"\x00" * 187 + bytes([0x47]) + b"\x00" * 187

        def fake_fetch_hls_text(url, referer):
            if url.endswith("index.m3u8") and "2000kb" not in url:
                return master
            return media

        def fake_read_media_chunk(url, referer, size):
            return chunk[:size], object()

        with patch.object(missav, "fetch_hls_text", side_effect=fake_fetch_hls_text), patch.object(missav, "read_media_chunk", side_effect=fake_read_media_chunk):
            with patch.object(missav, "now_utc", return_value=datetime(2026, 6, 10, 4, 0, tzinfo=timezone.utc)):
                verified = missav.verify_hls_url("https://2605.senlin2026.com/20260608/video/index.m3u8", "https://missav.app/vodplay/261745-1-1/")

        self.assertEqual(verified["media_format"], "hls")
        self.assertEqual(verified["variant_count"], 1)
        self.assertFalse(verified["playback_refresh_required"])
        self.assertEqual(verified["playback_headers"]["Referer"], "https://missav.app/vodplay/261745-1-1/")

    def test_reject_ad_url_rejects_known_ad_hosts(self):
        with self.assertRaisesRegex(ValueError, "ad host"):
            missav.reject_ad_url("https://go.rmhfrtnd.com/smartpop/ad")

    def test_parse_query_expiry_uses_explicit_expiry_key(self):
        self.assertEqual(
            missav.parse_query_expiry("https://cdn.example/video.m3u8?expires=1781061721"),
            datetime(2026, 6, 10, 3, 22, 1, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
