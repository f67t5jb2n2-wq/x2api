import { publicClientView, registerClient } from "@/lib/client-service";
import { jsonError, jsonOk } from "@/lib/http";

export async function POST(request: Request) {
  try {
    const body = (await request.json().catch(() => ({}))) as { label?: string };
    const client = await registerClient(body.label);
    return jsonOk(publicClientView(client), { status: 201 });
  } catch (error) {
    return jsonError(error instanceof Error ? error.message : "Failed to register client.", 500);
  }
}
