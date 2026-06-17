from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

fake_opensearchpy = types.ModuleType("opensearchpy")
fake_opensearchpy.OpenSearch = object
fake_opensearchpy.helpers = types.SimpleNamespace(bulk=None)
sys.modules.setdefault("opensearchpy", fake_opensearchpy)

from collector import opensearch_items


class OpenSearchItemsTest(unittest.TestCase):
    def test_sync_item_indexes_document_for_existing_row(self):
        fake_conn = MagicMock()
        fake_client = MagicMock()

        with patch.object(opensearch_items, "is_opensearch_write_enabled", return_value=True), \
             patch.object(opensearch_items, "get_client", return_value=fake_client), \
             patch.object(opensearch_items, "fetch_item_row", return_value={"id": "item-1"}), \
             patch.object(opensearch_items, "build_document", return_value={"id": "item-1"}):
            synced = opensearch_items.sync_item(fake_conn, "item-1")

        self.assertTrue(synced)
        fake_client.index.assert_called_once()


if __name__ == "__main__":
    unittest.main()
