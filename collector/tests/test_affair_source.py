from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from Crypto.Cipher import AES

from collector import affair_source as affair


class AffairSourceTests(unittest.TestCase):
    def test_parse_list_page_skips_sponsored_cards_and_extracts_real_articles(self):
        html = """
        <html><body>
          <article class="no-mask">
            <a href="/archives/100/" rel="sponsored nofollow">
              <div class="post-card"><div class="post-card-mask post-card-ads"></div></div>
            </a>
          </article>
          <article>
            <a href="/archives/188412/">
              <div class="post-card" id="post-card-188412">
                <script>loadBannerDirect('https://pic.example.test/cover.jpeg', '', document.querySelector('#post-card-188412'), '-1', 1, 1);</script>
                <h2 class="post-card-title">Real Title</h2>
                <div class="post-card-info">
                  <span>作者 •</span>
                  <span content="2026-06-10T02:30:00+00:00" itemprop="datePublished">date •</span>
                  <span>今日大瓜, 福利视频</span>
                </div>
              </div>
            </a>
          </article>
        </body></html>
        """

        with patch.object(affair, "fetch_html", return_value=html):
            items = affair.parse_list_page("https://affair.zhkrsawaw.cc/category/jrgb/", 1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["guid"], "affair:188412")
        self.assertEqual(items[0]["url"], "https://affair.zhkrsawaw.cc/archives/188412/")
        self.assertEqual(items[0]["title"], "Real Title")
        self.assertEqual(items[0]["image"], "https://pic.example.test/cover.jpeg")
        self.assertEqual(items[0]["published_at"], datetime(2026, 6, 10, 2, 30, tzinfo=timezone.utc))
        self.assertEqual(items[0]["tags"], ["今日大瓜", "福利视频"])

    def test_parse_detail_page_uses_video_url_and_ignores_ad_urls(self):
        config = {
            "video_ads_url": "https://hls.chxgdn.cn/videos5/ad/ad.m3u8?auth_key=1781061721-1-0-ad",
            "backend_video_ads_url": "https://hls.chxgdn.cn/videos5/ad/backend.m3u8?auth_key=1781061721-1-0-ad",
            "video": {
                "url": "https://hls.chxgdn.cn/videos5/real/real.m3u8?auth_key=1781061721-1-0-real",
                "type": "hls",
            },
        }
        html = f"""
        <html>
          <head>
            <script type="application/ld+json">
              {{"@type":"Article","headline":"Detail Title","datePublished":"2026-06-10T02:30:00+00:00","keywords":["tag-a"]}}
            </script>
          </head>
          <body>
            <h1>Fallback</h1>
            <div class="dplayer" data-video_id="188412002" data-video_title="Player Title" data-video_tag_name="tag-b,tag-c" data-config='{json.dumps(config)}'></div>
          </body>
        </html>
        """

        with patch.object(affair, "fetch_html", return_value=html):
            detail = affair.parse_detail_page("https://affair.zhkrsawaw.cc/archives/188412/")

        self.assertEqual(detail["title"], "Detail Title")
        self.assertEqual(len(detail["players"]), 1)
        self.assertEqual(detail["players"][0]["guid"], "affair:188412:188412002")
        self.assertEqual(detail["players"][0]["video_url"], "https://hls.chxgdn.cn/videos5/real/real.m3u8?auth_key=1781061721-1-0-real")
        self.assertEqual(detail["players"][0]["video_type"], "hls")
        self.assertEqual(detail["players"][0]["tags"], ["tag-b", "tag-c"])

    def test_verify_hls_url_accepts_encrypted_segments_after_decrypting_probe(self):
        key = b"0123456789abcdef"
        iv = bytes.fromhex("762d6e9771693490b6ba7dd8960d9631")
        plaintext = bytearray(188 * 4)
        plaintext[0] = 0x47
        plaintext[188] = 0x47
        encrypted = AES.new(key, AES.MODE_CBC, iv).encrypt(bytes(plaintext))
        playlist = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-KEY:METHOD=AES-128,URI="https://tts.doudou520.online/videos5/real/crypt.key?auth_key=1781061746-1-0-key",IV=0x762d6e9771693490b6ba7dd8960d9631
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-TARGETDURATION:5
#EXTINF:5.0,
https://tts.doudou520.online/videos5/real/seg0.ts?auth_key=1781061746-1-0-seg
#EXT-X-ENDLIST
"""

        def fake_read_media_chunk(url, referer, size):
            if "crypt.key" in url:
                return key, object()
            return encrypted[:size], object()

        with patch.object(affair, "fetch_hls_text", return_value=playlist), patch.object(affair, "read_media_chunk", side_effect=fake_read_media_chunk):
            with patch.object(affair, "now_utc", return_value=datetime(2026, 6, 10, 3, 0, tzinfo=timezone.utc)):
                verified = affair.verify_hls_url("https://hls.chxgdn.cn/videos5/real/real.m3u8?auth_key=1781061721-1-0-real", "https://affair.zhkrsawaw.cc/archives/188412/")

        self.assertEqual(verified["media_format"], "hls")
        self.assertTrue(verified["encrypted"])
        self.assertFalse(verified["playback_refresh_required"])
        self.assertEqual(verified["playback_headers"]["Referer"], "https://affair.zhkrsawaw.cc/archives/188412/")

    def test_reject_ad_url_rejects_known_ad_hosts(self):
        with self.assertRaisesRegex(ValueError, "ad host"):
            affair.reject_ad_url("https://a.adtng.com/video.m3u8")

    def test_parse_query_expiry_uses_explicit_expiry_key(self):
        self.assertEqual(
            affair.parse_query_expiry("https://hls.chxgdn.cn/video.m3u8?expires=1781061721"),
            datetime(2026, 6, 10, 3, 22, 1, tzinfo=timezone.utc),
        )

    def test_parse_query_expiry_ignores_affair_auth_key_timestamp(self):
        self.assertIsNone(affair.parse_query_expiry("https://hls.chxgdn.cn/video.m3u8?auth_key=1781061721-1-0-real"))


if __name__ == "__main__":
    unittest.main()
