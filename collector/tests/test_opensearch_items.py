from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from collector import opensearch_items


class OpenSearchItemsTest(unittest.TestCase):
    def test_update_item_document_sends_tags_and_images(self):
        fake_client = MagicMock()

        with patch.object(opensearch_items, "is_opensearch_write_enabled", return_value=True), \
             patch.object(opensearch_items, "get_client", return_value=fake_client):
            updated = opensearch_items.update_item_document(
                "item-1",
                title="Title",
                tags=["News", "news", " Video "],
                images=["https://example.com/1.jpg", "", None],
            )

        self.assertTrue(updated)
        fake_client.update.assert_called_once()
        payload = fake_client.update.call_args.kwargs["body"]["doc"]
        self.assertEqual(payload["title"], "Title")
        self.assertEqual(payload["tags"], ["news", "video"])
        self.assertEqual(payload["images"], ["https://example.com/1.jpg"])

    def test_update_parent_entry_playback_uses_parent_item_id(self):
        fake_conn = MagicMock()
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {"parent_item_id": "entry-1", "primary_item_id": "variant-1"}
        fake_conn.cursor.return_value.__enter__.return_value = fake_cursor

        with patch.object(opensearch_items, "update_item_playback", return_value=True) as mocked_update:
            updated = opensearch_items._update_parent_entry_playback(
                fake_conn,
                item_id="variant-1",
                video_url="https://cdn.example.com/video.m3u8",
                video_url_expires_at="2099-12-31T23:59:59Z",
                playback_headers={"Referer": "https://example.com"},
                cover_url="https://example.com/poster.jpg",
                video_key="video-key-1",
            )

        self.assertTrue(updated)
        mocked_update.assert_called_once_with(
            "entry-1",
            video_url="https://cdn.example.com/video.m3u8",
            video_url_expires_at="2099-12-31T23:59:59Z",
            video_key="video-key-1",
            playback_headers={"Referer": "https://example.com"},
            cover_url="https://example.com/poster.jpg",
            conn=fake_conn,
        )

    def test_refresh_item_playback_updates_variant_and_parent_entry(self):
        fake_conn = MagicMock()
        fake_cursor = MagicMock()
        fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
        fake_cursor.fetchone.side_effect = [
            {"parent_item_id": "entry-1", "primary_item_id": "variant-1"},
        ]

        with patch.object(opensearch_items, "update_item_playback", return_value=True) as mocked_update, \
             patch.object(opensearch_items, "_update_parent_entry_playback", return_value=True) as mocked_parent:
            updated = opensearch_items.refresh_item_playback(
                fake_conn,
                item_id="variant-1",
                video_url="https://cdn.example.com/video.m3u8",
                video_url_expires_at="2099-12-31T23:59:59Z",
                metadata={"variant_key": "video-key-1"},
                playback_headers={"Referer": "https://example.com"},
                cover_url="https://example.com/poster.jpg",
            )

        self.assertTrue(updated)
        mocked_update.assert_called_once()
        mocked_parent.assert_called_once_with(
            fake_conn,
            item_id="variant-1",
            video_url="https://cdn.example.com/video.m3u8",
            video_url_expires_at="2099-12-31T23:59:59Z",
            playback_headers={"Referer": "https://example.com"},
            cover_url="https://example.com/poster.jpg",
            video_key="https://cdn.example.com/video.m3u8",
        )

    def test_update_parent_entry_playback_ignores_non_primary_variants(self):
        fake_conn = MagicMock()
        fake_cursor = MagicMock()
        fake_cursor.fetchone.side_effect = [
            {"parent_item_id": "entry-1", "primary_item_id": "variant-1"},
        ]
        fake_conn.cursor.return_value.__enter__.return_value = fake_cursor

        with patch.object(opensearch_items, "update_item_playback", return_value=True) as mocked_update:
            updated = opensearch_items._update_parent_entry_playback(
                fake_conn,
                item_id="variant-2",
                video_url="https://cdn.example.com/video-2.m3u8",
                video_url_expires_at="2099-12-31T23:59:59Z",
            )

        self.assertFalse(updated)
        mocked_update.assert_not_called()


if __name__ == "__main__":
    unittest.main()
