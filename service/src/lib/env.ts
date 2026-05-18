const requiredServerEnv = ["DATABASE_URL"] as const;

export function getRequiredEnv(name: (typeof requiredServerEnv)[number]): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}
