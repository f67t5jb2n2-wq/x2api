import { requireClient } from "@/lib/auth";
import { jsonError, jsonOk } from "@/lib/http";
import {
  addSubscriptions,
  listSubscriptions,
  removeSubscriptions,
  replaceSubscriptions,
} from "@/lib/subscription-service";

export async function GET() {
  try {
    const client = await requireClient();
    const subscriptions = await listSubscriptions(client.id);
    return jsonOk({ subscriptions });
  } catch (error) {
    return jsonError(error instanceof Error ? error.message : "Unauthorized.", 401);
  }
}

export async function PUT(request: Request) {
  try {
    const client = await requireClient();
    const body = (await request.json()) as { targets?: unknown };
    const subscriptions = await replaceSubscriptions(client.id, body.targets ?? []);
    return jsonOk({ subscriptions });
  } catch (error) {
    return jsonError(error instanceof Error ? error.message : "Failed to replace subscriptions.");
  }
}

export async function POST(request: Request) {
  try {
    const client = await requireClient();
    const body = (await request.json()) as { targets?: unknown };
    const subscriptions = await addSubscriptions(client.id, body.targets ?? []);
    return jsonOk({ subscriptions });
  } catch (error) {
    return jsonError(error instanceof Error ? error.message : "Failed to add subscriptions.");
  }
}

export async function DELETE(request: Request) {
  try {
    const client = await requireClient();
    const body = (await request.json()) as { targets?: unknown };
    const subscriptions = await removeSubscriptions(client.id, body.targets ?? []);
    return jsonOk({ subscriptions });
  } catch (error) {
    return jsonError(error instanceof Error ? error.message : "Failed to remove subscriptions.");
  }
}
