#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required."
  exit 1
fi

echo "[verify] applying schema"
if command -v psql >/dev/null 2>&1; then
  psql "$DATABASE_URL" -f "$ROOT_DIR/shared/schema.sql"
else
  echo "psql not found; skipping schema apply."
fi

echo "[verify] registering client"
REGISTER_JSON="$(python3 "$ROOT_DIR/collector/twitter_monitor.py" register-client --label "verify-script")"
echo "$REGISTER_JSON"

API_KEY="$(printf '%s' "$REGISTER_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["apiKey"])')"
FEED_TOKEN="$(printf '%s' "$REGISTER_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["feedToken"])')"

echo "[verify] updating subscriptions"
python3 "$ROOT_DIR/collector/twitter_monitor.py" subscribe set \
  --api-key "$API_KEY" \
  --targets "OpenAI,search:AI safety"

echo "[verify] querying items"
python3 "$ROOT_DIR/collector/twitter_monitor.py" query --api-key "$API_KEY" --limit 5

echo "[verify] expected feed url path: /rss/${FEED_TOKEN}.xml"
