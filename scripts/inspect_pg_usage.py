from __future__ import annotations

import json
import os

from psycopg import connect
from psycopg.rows import dict_row


SIZE_SQL = """
SELECT
  current_database() AS database_name,
  pg_size_pretty(pg_database_size(current_database())) AS database_size
"""

TABLE_SQL = """
SELECT
  c.relname AS table_name,
  pg_total_relation_size(c.oid) AS total_bytes,
  pg_relation_size(c.oid) AS heap_bytes,
  pg_indexes_size(c.oid) AS index_bytes,
  COALESCE(pg_total_relation_size(c.reltoastrelid), 0) AS toast_bytes,
  COALESCE(s.n_live_tup, 0)::bigint AS estimated_rows
FROM pg_class c
LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
WHERE c.relkind = 'r'
  AND c.relnamespace = 'public'::regnamespace
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 25
"""

INDEX_SQL = """
SELECT
  c.relname AS index_name,
  t.relname AS table_name,
  pg_relation_size(c.oid) AS index_bytes
FROM pg_class c
INNER JOIN pg_index i ON i.indexrelid = c.oid
INNER JOIN pg_class t ON t.oid = i.indrelid
WHERE c.relkind = 'i'
  AND c.relnamespace = 'public'::regnamespace
ORDER BY pg_relation_size(c.oid) DESC
LIMIT 25
"""

ITEMS_COLUMN_SQL = """
SELECT
  column_name,
  data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'items'
ORDER BY ordinal_position
"""


def require_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("Missing DATABASE_URL environment variable.")
    return database_url


def main() -> int:
    with connect(require_database_url(), row_factory=dict_row, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute(SIZE_SQL)
            db_info = dict(cur.fetchone())

            cur.execute(TABLE_SQL)
            tables = [dict(row) for row in cur.fetchall()]

            cur.execute(INDEX_SQL)
            indexes = [dict(row) for row in cur.fetchall()]

            cur.execute(ITEMS_COLUMN_SQL)
            items_columns = [dict(row) for row in cur.fetchall()]

        payload = {
            "database": db_info,
            "tables": tables,
            "indexes": indexes,
            "itemsColumns": items_columns,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
