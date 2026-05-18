import { getSql } from "@/lib/db";
import { asRows } from "@/lib/sql-result";
import { createOpaqueToken, maskToken } from "@/lib/tokens";

export type ClientRecord = {
  id: string;
  apiKey: string;
  feedToken: string;
  label: string | null;
  createdAt: string;
};

export async function registerClient(label?: string): Promise<ClientRecord> {
  const sql = getSql();
  const apiKey = createOpaqueToken("x2d");
  const feedToken = createOpaqueToken("feed");

  const rows = asRows<ClientRecord>(await sql`
    INSERT INTO clients (api_key, feed_token, label)
    VALUES (${apiKey}, ${feedToken}, ${label ?? null})
    RETURNING
      id,
      api_key AS "apiKey",
      feed_token AS "feedToken",
      label,
      created_at AS "createdAt"
  `);

  return rows[0];
}

export function publicClientView(record: ClientRecord) {
  return {
    id: record.id,
    label: record.label,
    apiKey: record.apiKey,
    apiKeyPreview: maskToken(record.apiKey),
    feedToken: record.feedToken,
    feedUrlPath: `/rss/${record.feedToken}.xml`,
    createdAt: record.createdAt,
  };
}
