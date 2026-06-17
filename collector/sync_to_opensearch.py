#!/usr/bin/env python3
"""
Retired legacy PG->OpenSearch sync entrypoint.

The production architecture is now:
- PostgreSQL `items`: lightweight control/relationship fields only
- OpenSearch `x2_items`: heavy content source of truth

Heavy fields are written directly to OpenSearch at write time. The old
incremental/full sync flow is intentionally removed to prevent regressions.
"""

from __future__ import annotations

import argparse
import sys

RETIRED_MESSAGE = (
    "collector/sync_to_opensearch.py has been retired. "
    "Items are now double-written directly: PostgreSQL stores lightweight "
    "control fields and OpenSearch stores heavy content fields."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retired legacy PG->OpenSearch sync entrypoint")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--stats-only", action="store_true")
    parser.add_argument("--prune-deleted", action="store_true")
    parser.add_argument("--reset-checkpoint", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.parse_args([] if argv is None else argv)

    print(RETIRED_MESSAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
