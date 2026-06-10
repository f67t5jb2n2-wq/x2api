from __future__ import annotations

import unittest
from unittest.mock import patch

from collector import xxxtik_source as xxxtik


class XxxTikSourceTests(unittest.TestCase):
    def test_parse_post_builds_hls_candidate_from_uid(self):
        detail = xxxtik.parse_post(
            {
                "id": 413593,
                "uuid": "cd5be922-9f39-4328-a2a9-2a10f0c8b947",
                "uid": "5AQM-T",
                "description": "Sample description",
                "status": "approved",
                "visible": True,
                "createdAt": "2026-06-06T10:10:58.733Z",
                "author": {"name": "creator"},
                "tags": [{"name": "sample"}, {"name": "Sample"}],
            }
        )

        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["guid"], "xxxtik:cd5be922-9f39-4328-a2a9-2a10f0c8b947")
        self.assertEqual(detail["title"], "Sample description")
        self.assertEqual(detail["image"], "https://p5rn.com/cdn/production/media/0312/5AQM-T/thumbnail.webp")
        self.assertEqual(detail["players"][0]["video_type"], "hls")
        self.assertIn("https://p5rn.com/cdn/production/media/0312/5AQM-T/master.m3u8", detail["players"][0]["video_url_candidates"])

    def test_parse_list_page_returns_next_cursor(self):
        posts = [
            {"id": 10, "uuid": "a", "uid": "uid-a", "description": "A", "status": "approved", "visible": True},
            {"id": 9, "uuid": "b", "uid": "uid-b", "description": "B", "status": "approved", "visible": True},
        ]

        with patch.object(xxxtik, "fetch_new_posts", return_value=posts):
            items, cursor = xxxtik.parse_list_page("https://xxxtik.com", 1, cursor=0, limit=2)

        self.assertEqual([item["guid"] for item in items], ["xxxtik:a", "xxxtik:b"])
        self.assertEqual(cursor, 9)

    def test_verify_hls_url_accepts_master_playlist_and_ts_segment(self):
        master_url = "https://p5rn.com/cdn/production/media/0312/5AQM-T/master.m3u8"
        media_url = "https://p5rn.com/cdn/production/media/0312/5AQM-T/1080-2M.m3u8"
        master = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1080x1810
1080-2M.m3u8
"""
        media = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:4
#EXTINF:4.0,
1080-2M0.ts
#EXTINF:4.0,
1080-2M1.ts
#EXT-X-ENDLIST
"""
        chunk = bytearray(188 * 2)
        chunk[0] = 0x47
        chunk[188] = 0x47

        def fake_fetch_media_text(url, page_url, allowed_hosts=None):
            return master if url == master_url else media

        def fake_read_media_chunk(url, page_url, size, allowed_hosts=None):
            return bytes(chunk[:size]), object()

        with patch.object(xxxtik, "fetch_media_text", side_effect=fake_fetch_media_text), patch.object(xxxtik, "read_media_chunk", side_effect=fake_read_media_chunk):
            verified = xxxtik.verify_hls_url(master_url, "https://xxxtik.com/post/example")

        self.assertEqual(verified["video_url"], master_url)
        self.assertEqual(verified["variant_url"], media_url)
        self.assertEqual(verified["media_format"], "hls")
        self.assertFalse(verified["playback_refresh_required"])
        self.assertEqual(verified["media_url_count"], 2)

    def test_video_name_posts_generate_direct_mp4_candidates(self):
        candidates = xxxtik.direct_candidates({"videoName": "sample", "count": 2})

        self.assertIn("https://p5rn.com/cdn/production/media/0312/videos/sample/sample-0.mp4", candidates)
        self.assertIn("https://xcdn.tv/cdn/production/media/0312/videos/sample/sample-1-480.mp4", candidates)

    def test_reject_ad_url_rejects_known_ad_hosts(self):
        with self.assertRaisesRegex(ValueError, "ad host"):
            xxxtik.reject_ad_url("https://a.crme7srv.com/ad-provider.js")

    def test_parse_query_expiry_uses_real_expiry_params_only(self):
        self.assertIsNone(xxxtik.parse_query_expiry("https://p5rn.com/video.m3u8?t=2026060919"))
        self.assertIsNotNone(xxxtik.parse_query_expiry("https://p5rn.com/video.m3u8?exp=1780000000"))


if __name__ == "__main__":
    unittest.main()
