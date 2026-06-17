from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys
import types

fake_opensearchpy = types.ModuleType("opensearchpy")
fake_opensearchpy.OpenSearch = object
fake_opensearchpy.helpers = types.SimpleNamespace(bulk=None)
sys.modules.setdefault("opensearchpy", fake_opensearchpy)

from collector import sync_to_opensearch as sync


class SyncToOpenSearchTests(unittest.TestCase):
    def test_base_sync_sql_includes_active_non_video_items(self):
        self.assertIn("WHERE i.expires_at > NOW()", sync.BASE_SYNC_SQL)
        self.assertNotIn("WHERE i.video_url IS NOT NULL", sync.BASE_SYNC_SQL)
        self.assertIn("OR i.video_url_expires_at > NOW() + INTERVAL '10 minutes'", sync.BASE_SYNC_SQL)

    def test_base_sync_sql_keeps_video_url_field_in_projection(self):
        self.assertIn("i.video_url,", sync.BASE_SYNC_SQL)
        self.assertIn("has_video", sync.X2_ITEMS_MAPPING["mappings"]["properties"])

    def test_sync_items_uses_updated_at_checkpoint_and_persists_v2_meta(self):
        updated_at = datetime(2026, 6, 16, 21, 25, 54, 331546, tzinfo=timezone.utc)
        row = {
            "id": "item-2",
            "updated_at": updated_at,
            "stored_at": datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        }

        fake_cursor = MagicMock()
        fake_cursor.fetchmany.side_effect = [[row], []]
        fake_cursor.__enter__.return_value = fake_cursor
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        fake_conn.__enter__.return_value = fake_conn

        os_client = MagicMock()

        with patch.object(sync, "get_last_sync_checkpoint", return_value=("2026-06-16T21:21:44.020773+00:00", "item-1")) as get_checkpoint, \
             patch.object(sync.psycopg, "connect", return_value=fake_conn), \
             patch.object(sync, "build_document", return_value={"id": "item-2"}), \
             patch.object(sync.helpers, "bulk", return_value=(1, [])), \
             patch.object(sync, "set_last_sync_timestamp") as set_checkpoint:
            sync.sync_items(os_client, "postgres://example", full=False, limit=None, shard_index=1, shard_count=4)

        get_checkpoint.assert_called_once_with(os_client, meta_key="last_sync_v2_shard_1_of_4")
        executed_sql, executed_params = fake_cursor.execute.call_args.args
        self.assertIn("i.updated_at > %s OR (i.updated_at = %s AND i.id::text > %s)", executed_sql)
        self.assertIn("MOD(hashtext(i.id::text)::bigint + 2147483648, %s::int) = %s::int", executed_sql)
        self.assertIn("ORDER BY i.updated_at ASC, i.id ASC", executed_sql)
        self.assertEqual(
            executed_params,
            ["2026-06-16T21:21:44.020773+00:00", "2026-06-16T21:21:44.020773+00:00", "item-1", 4, 1],
        )
        set_checkpoint.assert_called_once_with(
            os_client,
            updated_at.isoformat(),
            meta_key="last_sync_v2_shard_1_of_4",
            item_id="item-2",
        )

    def test_sync_items_does_not_advance_checkpoint_when_bulk_has_errors(self):
        updated_at = datetime(2026, 6, 16, 21, 25, 54, 331546, tzinfo=timezone.utc)
        row = {
            "id": "item-2",
            "updated_at": updated_at,
            "stored_at": datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        }

        fake_cursor = MagicMock()
        fake_cursor.fetchmany.side_effect = [[row], []]
        fake_cursor.__enter__.return_value = fake_cursor
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        fake_conn.__enter__.return_value = fake_conn

        os_client = MagicMock()

        with patch.object(sync, "get_last_sync_checkpoint", return_value=("2026-06-16T21:21:44.020773+00:00", "item-1")), \
             patch.object(sync.psycopg, "connect", return_value=fake_conn), \
             patch.object(sync, "build_document", return_value={"id": "item-2"}), \
             patch.object(sync.helpers, "bulk", return_value=(0, [{"index": {"error": "boom"}}])), \
             patch.object(sync, "set_last_sync_timestamp") as set_checkpoint:
            sync.sync_items(os_client, "postgres://example", full=False, limit=None, shard_index=0, shard_count=1)

        set_checkpoint.assert_not_called()

    def test_stable_shard_is_deterministic(self):
        self.assertEqual(sync.stable_shard("item-123", 4), sync.stable_shard("item-123", 4))
        self.assertIn(sync.stable_shard("item-123", 4), {0, 1, 2, 3})

    def test_build_document_uses_projection_metadata_when_pg_fields_are_empty(self):
        row = {
            "id": "item-3",
            "target_id": "target-1",
            "guid": "guid-1",
            "video_url": "https://cdn.example.com/video.m3u8",
            "metadata": {
                "item_title": "Title from metadata",
                "item_content": "Content from metadata",
                "item_author": "author_from_metadata",
                "item_fullname": "Author From Metadata",
                "item_display_author": "Display Name",
                "item_display_handle": "@handle",
                "item_author_profile_url": "https://example.com/profile",
                "item_author_profile_platform": "Example",
                "item_link": "https://example.com/detail",
                "item_x_url": "https://x.com/example/status/1",
                "item_images": ["https://example.com/image.jpg"],
            },
            "playback_headers": None,
            "cover_url": "https://example.com/poster.jpg",
            "title": None,
            "caption": None,
            "content": None,
            "raw_content": None,
            "translated_content": None,
            "author": None,
            "fullname": None,
            "display_author": None,
            "display_handle": None,
            "author_profile_url": None,
            "author_profile_platform": None,
            "x_url": None,
            "link": None,
            "published_at": datetime(2026, 6, 16, 12, 0, 0, tzinfo=timezone.utc),
            "stored_at": datetime(2026, 6, 16, 12, 0, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 6, 16, 12, 0, 2, tzinfo=timezone.utc),
            "source": "badnews",
            "kind": "site",
            "target_value": "https://bad.news",
            "category": "adult",
            "is_public_pool": True,
            "is_retweet": False,
            "is_sensitive": True,
            "expires_at": datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc),
            "video_url_expires_at": datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc),
            "score": 3,
            "impressions": 1,
            "plays": 2,
            "finishes": 0,
            "likes": 0,
            "dislikes": 0,
            "skips": 0,
            "shares": 0,
            "images": [],
            "item_tags_array": [],
            "profile_tags": [],
        }

        doc = sync.build_document(row)
        self.assertEqual(doc["title"], "Title from metadata")
        self.assertEqual(doc["content"], "Content from metadata")
        self.assertEqual(doc["caption"], "Content from metadata")
        self.assertEqual(doc["author"], "author_from_metadata")
        self.assertEqual(doc["fullname"], "Author From Metadata")
        self.assertEqual(doc["display_author"], "Display Name")
        self.assertEqual(doc["display_handle"], "@handle")
        self.assertEqual(doc["author_profile_url"], "https://example.com/profile")
        self.assertEqual(doc["author_profile_platform"], "Example")
        self.assertEqual(doc["link"], "https://example.com/detail")
        self.assertEqual(doc["x_url"], "https://x.com/example/status/1")
        self.assertEqual(doc["images"], ["https://example.com/image.jpg"])


if __name__ == "__main__":
    unittest.main()
