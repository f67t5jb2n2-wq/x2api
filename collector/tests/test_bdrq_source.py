from __future__ import annotations

import unittest
from unittest.mock import patch

from Crypto.Cipher import AES

from collector.bdrq_source import (
    aes_iv_for_segment,
    clean_hls_playlist,
    decode_player_url,
    decrypt_aes128_chunk,
    extract_player_json,
    looks_like_media_segment,
    normalize_asset_url,
    parse_list_page,
    reject_ad_url,
)


class BdrqSourceTests(unittest.TestCase):
    def test_normalize_asset_url_preserves_root_relative_paths(self):
        self.assertEqual(
            normalize_asset_url("https://g3h4i5j6.bdrq45.cc/vodshow/181-----------.html", "/voddetail/769512.html"),
            "https://g3h4i5j6.bdrq45.cc/voddetail/769512.html",
        )

    def test_parse_list_page_reads_vod_cards(self):
        html = """
        <html><body>
          <ul class="stui-vodlist">
            <li>
              <a class="stui-vodlist__thumb" href="/voddetail/769512.html" title="Sample title" data-original="/upload/cover.jpg"></a>
              <div class="stui-vodlist__detail">
                <h4 class="title"><a href="/voddetail/769512.html" title="Sample title">Sample title</a></h4>
                <span class="pic-text1">中文字幕</span>
                <p>2026-06-09</p>
              </div>
            </li>
          </ul>
        </body></html>
        """
        with patch("collector.bdrq_source.fetch_html", return_value=html):
            items = parse_list_page("https://g3h4i5j6.bdrq45.cc", "/vodshow/181-----------.html", 1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["guid"], "bdrq:769512")
        self.assertEqual(items[0]["url"], "https://g3h4i5j6.bdrq45.cc/voddetail/769512.html")
        self.assertEqual(items[0]["title"], "Sample title")
        self.assertEqual(items[0]["image"], "https://g3h4i5j6.bdrq45.cc/upload/cover.jpg")

    def test_extract_player_json_decodes_percent_encoded_url(self):
        payload = extract_player_json(
            """
            <script>
            var player_aaaa={"encrypt":1,"url":"%68%74%74%70%73%3A%2F%2Fcdn.example%2Fvideo%2Findex.m3u8","nid":1}
            </script>
            """
        )

        self.assertEqual(decode_player_url(payload, "https://g3h4i5j6.bdrq45.cc/vodplay/1-1-1.html"), "https://cdn.example/video/index.m3u8")

    def test_clean_hls_playlist_removes_foreign_prefix_segments(self):
        cleaned, stats = clean_hls_playlist(
            "https://kjbwhcnao.com/20260608/g4jGnAUr/2000kb/hls/index.m3u8",
            """#EXTM3U
#EXT-X-VERSION:3
#EXTINF:4.0,
https://kjbwhcnao.com/20260604/I6vsA78Y/2000kb/hls/ad0.ts
#EXT-X-KEY:METHOD=AES-128,URI="https://tsbfask.com:65/20260608/g4jGnAUr/2000kb/hls/key.key",IV=0x00000000000000000000000000000007
#EXTINF:4.0,
https://tsbfask.com:65/20260608/g4jGnAUr/2000kb/hls/index0.ts
#EXT-X-ENDLIST
""",
            "/20260608/g4jGnAUr/2000kb/hls/",
        )

        self.assertEqual(stats["kept_segments"], 1)
        self.assertEqual(stats["removed_segments"], 1)
        self.assertIn("https://tsbfask.com:65/20260608/g4jGnAUr/2000kb/hls/key.key", cleaned)
        self.assertIn("https://tsbfask.com:65/20260608/g4jGnAUr/2000kb/hls/index0.ts", cleaned)
        self.assertNotIn("I6vsA78Y", cleaned)

    def test_aes_decrypt_probe_recognizes_encrypted_ts_bytes(self):
        key = b"0123456789abcdef"
        sequence = 7
        plain = bytearray(384)
        plain[0] = 0x47
        plain[188] = 0x47
        encrypted = AES.new(key, AES.MODE_CBC, aes_iv_for_segment(sequence, None)).encrypt(bytes(plain))

        self.assertTrue(looks_like_media_segment(decrypt_aes128_chunk(encrypted, key, sequence, None)))

    def test_reject_ad_url_blocks_known_ad_hosts(self):
        with self.assertRaisesRegex(ValueError, "ad host"):
            reject_ad_url("https://clickadu.example/video.mp4")


if __name__ == "__main__":
    unittest.main()
