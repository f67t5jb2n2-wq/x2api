#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collector.opensearch_items import update_item_playback  # noqa: E402


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
      raise SystemExit("DATABASE_URL is required")

    updated = 0
    batch_size = 200
    last_entry_id = ""
    with psycopg.connect(database_url, row_factory=dict_row, prepare_threshold=None) as conn:
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM (
                        SELECT DISTINCT ON (entry.id)
                            entry.id::text AS entry_id,
                            variant.video_url,
                            variant.video_url_expires_at,
                            variant.variant_key,
                            variant.published_at,
                            variant.stored_at
                        FROM items entry
                        JOIN items variant
                          ON variant.parent_item_id = entry.id
                        WHERE entry.item_role = 'entry'
                          AND variant.item_role = 'video_variant'
                          AND variant.video_url IS NOT NULL
                          AND entry.id::text > %s
                        ORDER BY entry.id, variant.variant_index NULLS FIRST, variant.published_at DESC NULLS LAST, variant.stored_at DESC
                    ) batch
                    ORDER BY entry_id
                    LIMIT %s
                    """,
                    (last_entry_id, batch_size),
                )
                rows = cur.fetchall()

            if not rows:
                break

            for row in rows:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE items
                        SET video_url = %s,
                            video_url_expires_at = %s
                        WHERE id = %s
                        """,
                        (row["video_url"], row["video_url_expires_at"], row["entry_id"]),
                    )

                update_item_playback(
                    row["entry_id"],
                    video_url=row["video_url"],
                    video_url_expires_at=row["video_url_expires_at"],
                    video_key=row["variant_key"] or row["video_url"],
                    conn=conn,
                )
                updated += 1
                last_entry_id = row["entry_id"]

            conn.commit()
            print(f"updated_entries={updated}", flush=True)

    print(f"updated_entries={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
