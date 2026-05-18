import { getSql } from "@/lib/db";
import { asRows } from "@/lib/sql-result";
import { formatTarget, parseTargets, type ParsedTarget } from "@/lib/targets";

type DbSubscriptionRow = {
  subscriptionId: string;
  targetId: string;
  kind: "user" | "keyword";
  value: string;
  createdAt: string;
};

async function ensureTargets(targets: ParsedTarget[]) {
  if (targets.length === 0) {
    return [];
  }

  const sql = getSql();

  for (const target of targets) {
    await sql`
      INSERT INTO targets (kind, value, normalized_value)
      VALUES (${target.kind}, ${target.value}, ${target.normalizedValue})
      ON CONFLICT (kind, normalized_value)
      DO UPDATE SET value = EXCLUDED.value
    `;
  }

  const ensuredTargets: { id: string; kind: "user" | "keyword"; value: string; normalizedValue: string }[] = [];
  for (const target of targets) {
    const rows = asRows<{ id: string; kind: "user" | "keyword"; value: string; normalizedValue: string }>(await sql`
      SELECT
        id,
        kind,
        value,
        normalized_value AS "normalizedValue"
      FROM targets
      WHERE kind = ${target.kind}
        AND normalized_value = ${target.normalizedValue}
      LIMIT 1
    `);
    if (rows[0]) {
      ensuredTargets.push(rows[0]);
    }
  }

  return ensuredTargets;
}

export async function listSubscriptions(clientId: string) {
  const sql = getSql();
  const rows = asRows<DbSubscriptionRow>(await sql`
    SELECT
      s.id AS "subscriptionId",
      t.id AS "targetId",
      t.kind,
      t.value,
      s.created_at AS "createdAt"
    FROM subscriptions s
    INNER JOIN targets t ON t.id = s.target_id
    WHERE s.client_id = ${clientId}
    ORDER BY t.kind, LOWER(t.value)
  `);

  return rows.map((row) => ({
    id: row.subscriptionId,
    targetId: row.targetId,
    target: formatTarget({ kind: row.kind, value: row.value }),
    kind: row.kind,
    value: row.value,
    createdAt: row.createdAt,
  }));
}

export async function replaceSubscriptions(clientId: string, rawTargets: unknown) {
  const sql = getSql();
  const targets = parseTargets(rawTargets);
  const ensuredTargets = await ensureTargets(targets);

  await sql`
    DELETE FROM subscriptions
    WHERE client_id = ${clientId}
  `;

  for (const target of ensuredTargets) {
    await sql`
      INSERT INTO subscriptions (client_id, target_id)
      VALUES (${clientId}, ${target.id})
      ON CONFLICT (client_id, target_id) DO NOTHING
    `;
  }

  return listSubscriptions(clientId);
}

export async function addSubscriptions(clientId: string, rawTargets: unknown) {
  const targets = parseTargets(rawTargets);
  const ensuredTargets = await ensureTargets(targets);
  const sql = getSql();

  for (const target of ensuredTargets) {
    await sql`
      INSERT INTO subscriptions (client_id, target_id)
      VALUES (${clientId}, ${target.id})
      ON CONFLICT (client_id, target_id) DO NOTHING
    `;
  }

  return listSubscriptions(clientId);
}

export async function removeSubscriptions(clientId: string, rawTargets: unknown) {
  const targets = parseTargets(rawTargets);
  if (targets.length === 0) {
    return listSubscriptions(clientId);
  }

  const sql = getSql();
  for (const target of targets) {
    await sql`
      DELETE FROM subscriptions
      WHERE client_id = ${clientId}
        AND target_id IN (
          SELECT id
          FROM targets
          WHERE kind = ${target.kind}
            AND normalized_value = ${target.normalizedValue}
        )
    `;
  }

  return listSubscriptions(clientId);
}
