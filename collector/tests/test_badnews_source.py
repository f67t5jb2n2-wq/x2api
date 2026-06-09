from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from collector.badnews_source import (
    media_referer_for_url,
    parse_list_page,
    parse_query_expiry,
    reject_ad_url,
)


class BadNewsSourceTest(unittest.TestCase):
    def test_parse_list_page_extracts_video_data_source(self):
        html = """
        <html>
          <body>
            <div class="entry">
              <h3 class="title"><a class="title" href="/search/t-all/q-user:author">Watch video</a></h3>
              <div class="tagline">
                <a class="dateline" href="/t/6227046"><time datetime="2026-06-09 15:31:32">19分钟前</time></a>
                <a class="author" href="/search/t-all/q-user:author">Author Name</a>
              </div>
              <video class="my-videos"
                poster="https://pbs.twimg.com/thumb.jpg"
                data-id="6227046"
                data-source="https://video.twimg.com/amplify_video/1/pl/master.m3u8?tag=27"
                data-type="m3u8"></video>
              <div class="ct-time"><span>00:05:29</span></div>
            </div>
          </body>
        </html>
        """

        with patch("collector.badnews_source.fetch_html", return_value=html):
            items = parse_list_page("https://bad.news/sort-new/page-1", 1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["guid"], "badnews:6227046")
        self.assertEqual(items[0]["title"], "Author Name video")
        self.assertEqual(items[0]["duration"], 329)
        self.assertEqual(items[0]["published_at"], datetime(2026, 6, 9, 7, 31, 32, tzinfo=timezone.utc))
        self.assertEqual(items[0]["players"][0]["video_type"], "hls")

    def test_twitter_cdn_media_uses_no_badnews_referer(self):
        self.assertIsNone(media_referer_for_url("https://video.twimg.com/ext_tw_video/1/vid/a.mp4", "https://bad.news/t/1"))
        self.assertEqual(media_referer_for_url("https://cdn.example/video.mp4", "https://bad.news/t/1"), "https://bad.news/t/1")

    def test_parse_query_expiry_reads_epoch_query(self):
        self.assertEqual(
            parse_query_expiry("https://cdn.example/video.mp4?e=1780987773"),
            datetime(2026, 6, 9, 6, 49, 33, tzinfo=timezone.utc),
        )

    def test_reject_ad_url_blocks_known_ad_hosts(self):
        with self.assertRaisesRegex(ValueError, "ad host"):
            reject_ad_url("https://ads.trafficstars.com/video.mp4")


if __name__ == "__main__":
    unittest.main()
