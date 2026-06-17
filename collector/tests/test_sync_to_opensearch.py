from __future__ import annotations

import unittest

from collector import sync_to_opensearch as sync


class SyncToOpenSearchTests(unittest.TestCase):
    def test_sync_module_is_explicitly_retired(self):
        self.assertIn("retired", sync.RETIRED_MESSAGE.lower())
        self.assertIn("double-written directly", sync.RETIRED_MESSAGE.lower())

    def test_main_returns_failure_to_block_legacy_usage(self):
        self.assertEqual(sync.main([]), 1)


if __name__ == "__main__":
    unittest.main()
