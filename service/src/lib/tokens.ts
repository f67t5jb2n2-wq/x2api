import crypto from "node:crypto";

export function createOpaqueToken(prefix: string): string {
  return `${prefix}_${crypto.randomBytes(18).toString("base64url")}`;
}

export function maskToken(token: string): string {
  if (token.length <= 10) {
    return token;
  }
  return `${token.slice(0, 6)}...${token.slice(-4)}`;
}
