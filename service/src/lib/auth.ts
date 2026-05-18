import { headers } from "next/headers";

import { getSql } from "@/lib/db";
import { asRows } from "@/lib/sql-result";

export type AuthenticatedClient = {
  id: string;
  apiKey: string;
  feedToken: string;
  label: string | null;
  status: "active" | "disabled";
};

function extractApiKey(headerValue: string | null): string | null {
  if (!headerValue) {
    return null;
  }
  const bearerPrefix = "Bearer ";
  if (headerValue.startsWith(bearerPrefix)) {
    return headerValue.slice(bearerPrefix.length).trim() || null;
  }
  return headerValue.trim() || null;
}

export async function requireClient(): Promise<AuthenticatedClient> {
  const headersStore = await headers();
  const authorization = headersStore.get("authorization");
  const fallbackApiKey = headersStore.get("x-api-key");
  const apiKey = extractApiKey(authorization) ?? extractApiKey(fallbackApiKey);

  if (!apiKey) {
    throw new Error("Missing API key.");
  }

  const sql = getSql();
  const rows = asRows<AuthenticatedClient>(await sql`
    SELECT
      id,
      api_key AS "apiKey",
      feed_token AS "feedToken",
      label,
      status
    FROM clients
    WHERE api_key = ${apiKey}
    LIMIT 1
  `);

  const client = rows[0];
  if (!client || client.status !== "active") {
    throw new Error("Invalid API key.");
  }

  await sql`
    UPDATE clients
    SET last_seen_at = NOW()
    WHERE id = ${client.id}
  `;

  return client;
}
