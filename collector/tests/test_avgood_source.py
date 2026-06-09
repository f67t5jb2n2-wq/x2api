import unittest
from datetime import timezone
from unittest.mock import patch

from Crypto.Cipher import AES

from collector import avgood_source as avgood


class AvGoodSourceTests(unittest.TestCase):
    def test_parse_list_page_extracts_cards(self):
        html = """
        <div class="list-grid-container">
          <div class="grid-item">
            <a class="card" href="/c/663855.html">
              <div class="card-image"><img data-original="/remote/thumb/sample.jpg"></div>
              <div class="card-title">Sample Video</div>
              <div class="card-tags"><span class="tag-category">Category</span></div>
            </a>
          </div>
        </div>
        """
        with patch.object(avgood, "fetch_html", return_value=html):
            items = avgood.parse_list_page("https://avgood.com/c/664/", 1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["guid"], "avgood:663855")
        self.assertEqual(items[0]["title"], "Sample Video")
        self.assertEqual(items[0]["image"], "https://avgood.com/remote/thumb/sample.jpg")
        self.assertEqual(items[0]["category_name"], "Category")

    def test_parse_detail_page_uses_iframe_ajax_playlink(self):
        detail_html = """
        <html>
          <head><meta name="description" content="发行日期:2026-06-09, 其他信息"></head>
          <body>
            <h1 class="content-title">Detail Title</h1>
            <div class="description-section content-info">类别：Category 时长：00:35</div>
            <div class="description-images"><img src="/pic/poster.jpg"></div>
            <iframe id="video-player" src="/remote_play/video/play/213646.html"></iframe>
          </body>
        </html>
        """
        iframe_html = """
        <script>
          var player_id='213646';
          var ajax_url="/remote_play/index.php/play/ajax/213646.html";
        </script>
        """
        payload = {
            "zt": 0,
            "playlink": "/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fd7100b5fc0e845fc%2Fts%2Findex.m3u8?t=2026060919",
            "piclink": "/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fd7100b5fc0e845fc%2Fjpg%2Fvod.jpg",
        }

        def fake_fetch_html(url, referer=None):
            if "remote_play/video/play" in url:
                return iframe_html
            return detail_html

        with patch.object(avgood, "fetch_html", side_effect=fake_fetch_html), patch.object(avgood, "fetch_json", return_value=payload):
            detail = avgood.parse_detail_page("https://avgood.com/c/663855.html")

        self.assertEqual(detail["guid"], "avgood:663855")
        self.assertEqual(detail["title"], "Detail Title")
        self.assertEqual(detail["duration"], 35)
        self.assertEqual(detail["published_at"].tzinfo, timezone.utc)
        self.assertEqual(detail["players"][0]["player_id"], "213646")
        self.assertEqual(detail["players"][0]["video_type"], "hls")
        self.assertNotIn("?t=", detail["players"][0]["video_url"])
        self.assertEqual(detail["players"][0]["referer"], "https://avgood.com/remote_play/video/play/213646.html")

    def test_encoded_hls_uri_resolver_preserves_virtual_directory(self):
        media_url = "https://avgood.com/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fabcd%2Fts%2Findex.m3u8"

        self.assertEqual(
            avgood.media_playlist_content_prefix(media_url),
            "/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fabcd%2Fts%2F",
        )
        self.assertEqual(
            avgood.resolve_hls_uri(media_url, "key_1.key"),
            "https://avgood.com/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fabcd%2Fts%2Fkey_1.key",
        )
        self.assertEqual(
            avgood.resolve_hls_uri(media_url, "0000.ts"),
            "https://avgood.com/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fabcd%2Fts%2F0000.ts",
        )

    def test_decrypt_aes128_chunk_can_reveal_ts_sync_bytes(self):
        key = bytes(range(16))
        plaintext = bytearray(188 * 4)
        plaintext[0] = 0x47
        plaintext[188] = 0x47
        plaintext[376] = 0x47
        plaintext[564] = 0x47
        encrypted = AES.new(key, AES.MODE_CBC, bytes(16)).encrypt(bytes(plaintext))

        decrypted = avgood.decrypt_aes128_chunk(encrypted, key, 0, "0x00000000000000000000000000000000")

        self.assertTrue(avgood.looks_like_mpeg_ts(decrypted))

    def test_reject_ad_url_rejects_ad_hosts(self):
        with self.assertRaises(ValueError):
            avgood.reject_ad_url("https://ads.example.com/video.mp4")

    def test_strip_cache_only_query_keeps_real_expiry_params(self):
        self.assertEqual(
            avgood.strip_cache_only_query("https://avgood.com/video/index.m3u8?t=2026060919"),
            "https://avgood.com/video/index.m3u8",
        )
        self.assertEqual(
            avgood.strip_cache_only_query("https://avgood.com/video/index.m3u8?t=2026060919&exp=1780000000"),
            "https://avgood.com/video/index.m3u8?exp=1780000000",
        )


if __name__ == "__main__":
    unittest.main()
