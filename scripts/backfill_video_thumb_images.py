from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from collector.twitter_monitor import get_original_image_url  # noqa: E402


VIDEO_THUMB_PATTERNS = (
    "%amplify_video_thumb%",
    "%ext_tw_video_thumb%",
    "%tweet_video_thumb%",
)
NITTER_VIDEO_THUMB_PREFIXES = (
    "https://nitter.privacyredirect.com/pic/amplify_video_thumb",
    "https://nitter.privacyredirect.com/pic/ext_tw_video_thumb",
    "https://nitter.privacyredirect.com/pic/tweet_video_thumb",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rewrite stored Nitter/X video thumbnail image URLs to pbs.twimg.com URLs."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Update rows. Without this flag the script only reports what would change.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=10,
        help="Number of changed URL samples to print.",
    )
    return parser.parse_args()


def is_nitter_video_thumb_url(image_url: str) -> bool:
    return image_url.startswith(NITTER_VIDEO_THUMB_PREFIXES)


def main() -> int:
    args = parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("Missing DATABASE_URL environment variable.")

    sample_limit = max(args.sample_limit, 0)
    checked = 0
    changed_rows: list[tuple[list[str], object]] = []
    samples: list[dict[str, str]] = []

    with connect(database_url, row_factory=dict_row, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, guid, images
                FROM items
                WHERE EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(images) image_url(url)
                    WHERE image_url.url LIKE %s
                       OR image_url.url LIKE %s
                       OR image_url.url LIKE %s
                )
                ORDER BY stored_at DESC
                """,
                VIDEO_THUMB_PATTERNS,
            )
            rows = cur.fetchall()

        for row in rows:
            checked += 1
            images = row["images"] or []
            rewritten_images = [
                get_original_image_url(str(image_url))
                if is_nitter_video_thumb_url(str(image_url))
                else str(image_url)
                for image_url in images
            ]
            if rewritten_images == images:
                continue

            changed_rows.append((rewritten_images, row["id"]))
            if len(samples) < sample_limit:
                for before, after in zip(images, rewritten_images):
                    if before != after:
                        samples.append(
                            {
                                "guid": str(row["guid"]),
                                "before": str(before),
                                "after": after,
                            }
                        )
                        break

        if args.apply and changed_rows:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    UPDATE items
                    SET images = %s
                    WHERE id = %s
                    """,
                    [(Jsonb(images), item_id) for images, item_id in changed_rows],
                )
            conn.commit()
        else:
            conn.rollback()

    print(
        {
            "mode": "apply" if args.apply else "dry-run",
            "checked": checked,
            "updated": len(changed_rows) if args.apply else 0,
            "would_update": len(changed_rows),
            "samples": samples,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
