from __future__ import annotations

import unittest
from unittest.mock import patch

from Crypto.Cipher import AES

from collector import hs705_source as hs705


class Hs705SourceTests(unittest.TestCase):
    def test_parse_list_page_extracts_latest_cards(self):
        html = """
        <html><body>
          <li class="list1_obxobx">
            <a href="/Html/91/50710.html">
              <script>get_img_url("/Uploads/vod/2026-06-08/911.mp4.gif.webp")</script>
              <p>Sample Title</p>
              <span class="timeobxobx">2026-06-08</span>
            </a>
          </li>
        </body></html>
        """

        with patch.object(hs705, "fetch_html", return_value=html):
            items = hs705.parse_list_page("https://705hs.com/Html/60/index-1.html", 1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["guid"], "705hs:50710")
        self.assertEqual(items[0]["url"], "https://705hs.com/Html/91/50710.html")
        self.assertEqual(items[0]["title"], "Sample Title")
        self.assertEqual(items[0]["image"], "https://kp-i25977.com/Uploads/vod/2026-06-08/911.mp4.gif.webp")

    def test_parse_detail_page_builds_hls_candidates_from_player_page(self):
        detail_html = """
        <html><body>
          <div class="film_title"><h4>Detail Title</h4></div>
          <script>get_img_url("/Uploads/vod/2026-06-08/911.mp4.gif.webp")</script>
          <script>var down_url = 'https://d.220zx.com/20260608/91/911/911.mp4';</script>
          <p>情色分類：中文字幕</p>
          <p>更新時間：2026-06-08</p>
        </body></html>
        """
        play_html = """<script>u2_initPlayer({}, 'mp4("/20260608/91/911/911.mp4.m3u8")')</script>"""

        def fake_fetch_html(url, referer=None):
            if url.endswith("/js/u.js"):
                return "var a='https://kp-p29999.com';"
            if "/Html/player/play-" in url:
                return play_html
            return detail_html

        with patch.object(hs705, "fetch_html", side_effect=fake_fetch_html):
            detail = hs705.parse_detail_page("https://705hs.com/Html/91/50710.html")

        self.assertEqual(detail["guid"], "705hs:50710")
        self.assertEqual(detail["title"], "Detail Title")
        self.assertEqual(detail["category_name"], "中文字幕")
        self.assertEqual(detail["players"][0]["video_type"], "hls")
        self.assertTrue(detail["players"][0]["video_url"].endswith("/20260608/91/911/911.mp4.m3u8"))
        self.assertIn("https://d.220zx.com/20260608/91/911/911.mp4", detail["players"][0]["video_url_candidates"])

    def test_verify_hls_url_accepts_encrypted_ts_segments(self):
        key = b"0123456789abcdef"
        plain = bytearray(188 * 4)
        plain[0] = 0x47
        plain[188] = 0x47
        encrypted = AES.new(key, AES.MODE_CBC, bytes(16)).encrypt(bytes(plain))
        playlist = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
#EXT-X-KEY:METHOD=AES-128,URI="enc.key"
seg0.ts
#EXT-X-ENDLIST
"""

        def fake_read_media_chunk(url, page_url, size, allowed_hosts=None):
            if url.endswith("enc.key"):
                return key, object()
            return encrypted[:size], object()

        with patch.object(hs705, "fetch_media_text", return_value=playlist), patch.object(hs705, "read_media_chunk", side_effect=fake_read_media_chunk):
            verified = hs705.verify_hls_url("https://kp-p25277.com/20260608/91/911/911.mp4.m3u8", "https://705hs.com/Html/player/play-50710-0-1.html")

        self.assertEqual(verified["media_format"], "hls")
        self.assertFalse(verified["playback_refresh_required"])
        self.assertTrue(verified["encrypted"])
        self.assertEqual(verified["media_url_count"], 1)

    def test_reject_ad_url_rejects_known_ad_hosts(self):
        with self.assertRaisesRegex(ValueError, "ad host"):
            hs705.reject_ad_url("https://ads.example.com/video.mp4")

    def test_parse_query_expiry_uses_real_expiry_params_only(self):
        self.assertIsNone(hs705.parse_query_expiry("https://kp-p25277.com/index.m3u8?t=2026060919"))
        self.assertIsNotNone(hs705.parse_query_expiry("https://kp-p25277.com/index.m3u8?exp=1780000000"))


if __name__ == "__main__":
    unittest.main()
