from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from collector import influencersgonewild_source as igw


class FakeResponse:
    status_code = 206

    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.headers = headers or {"Content-Type": "video/mp4", "Content-Range": "bytes 0-4095/123456"}


class InfluencersGoneWildSourceTests(unittest.TestCase):
    def test_parse_list_page_extracts_article_cards(self):
        html = """
        <html><body>
          <article>
            <h3 class="entry-title"><a href="/sample-post/">Sample Title</a></h3>
            <a class="g1-frame" href="/sample-post/"><img data-src="/thumb.jpg"></a>
            <time datetime="2026-06-10T01:02:03+00:00"></time>
            <a class="entry-category">Category</a>
          </article>
        </body></html>
        """

        with patch.object(igw, "fetch_text", return_value=html):
            items = igw.parse_list_page("https://influencersgonewild.com", 1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["guid"], "influencersgonewild:sample-post")
        self.assertEqual(items[0]["url"], "https://influencersgonewild.com/sample-post/")
        self.assertEqual(items[0]["title"], "Sample Title")
        self.assertEqual(items[0]["image"], "https://influencersgonewild.com/thumb.jpg")
        self.assertEqual(items[0]["published_at"], datetime(2026, 6, 10, 1, 2, 3, tzinfo=timezone.utc))
        self.assertEqual(items[0]["tags"], ["Category"])

    def test_media_candidates_from_html_extracts_video_and_escaped_player_config(self):
        html = """
        <video><source src="https://cdn04.influencersgonewild.net/video/sample.mp4"></video>
        <script>
          var player = {"src":"https:\\/\\/cdn05.influencersgonewild.net\\/video\\/alt.m3u8"};
        </script>
        """

        candidates = igw.media_candidates_from_html(html, "https://influencersgonewild.com/sample-post/")

        self.assertEqual(candidates[0]["video_url"], "https://cdn04.influencersgonewild.net/video/sample.mp4")
        self.assertEqual(candidates[0]["video_type"], "direct")
        self.assertIn(
            {"video_url": "https://cdn05.influencersgonewild.net/video/alt.m3u8", "video_type": "hls", "source": "player-config"},
            candidates,
        )

    def test_verify_direct_video_url_requires_playable_media_and_returns_playback_headers(self):
        page_url = "https://influencersgonewild.com/sample-post/"
        video_url = "https://cdn04.influencersgonewild.net/video/sample.mp4"

        def fake_read_media_chunk(url, referer, size):
            self.assertEqual(url, video_url)
            self.assertEqual(referer, page_url)
            self.assertEqual(size, 4096)
            return b"\x00\x00\x00 ftypisom" + (b"\x00" * 64), FakeResponse()

        with patch.object(igw, "read_media_chunk", side_effect=fake_read_media_chunk):
            verified = igw.verify_direct_video_url(video_url, page_url)

        self.assertEqual(verified["video_url"], video_url)
        self.assertEqual(verified["media_format"], "direct")
        self.assertFalse(verified["playback_refresh_required"])
        self.assertEqual(verified["playback_headers"], {"Referer": page_url, "Origin": "https://influencersgonewild.com"})

    def test_reject_ad_url_rejects_known_ad_hosts(self):
        with self.assertRaisesRegex(ValueError, "ad host"):
            igw.reject_ad_url("https://a.realsrv.com/video.mp4")

    def test_parse_query_expiry_uses_real_expiry_params_only(self):
        self.assertIsNone(igw.parse_query_expiry("https://cdn04.influencersgonewild.net/video.mp4?t=2026061012"))
        self.assertIsNotNone(igw.parse_query_expiry("https://cdn04.influencersgonewild.net/video.mp4?exp=1780000000"))


if __name__ == "__main__":
    unittest.main()
