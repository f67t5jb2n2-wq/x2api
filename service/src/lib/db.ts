import { neon } from "@neondatabase/serverless";

import { getRequiredEnv } from "@/lib/env";

type SqlFunction = ReturnType<typeof neon>;

let sqlClient: SqlFunction | null = null;

export function getSql(): SqlFunction {
  if (!sqlClient) {
    sqlClient = neon(getRequiredEnv("DATABASE_URL"));
  }
  return sqlClient;
}
