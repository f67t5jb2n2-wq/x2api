import { NextResponse } from "next/server";

export function jsonOk(payload: unknown, init?: ResponseInit) {
  return NextResponse.json(payload, init);
}

export function jsonError(message: string, status = 400) {
  return NextResponse.json({ error: message }, { status });
}
