import { requireClient } from "@/lib/auth";
import { jsonError, jsonOk } from "@/lib/http";
import { listItems } from "@/lib/item-service";

export async function GET(request: Request) {
  try {
    const client = await requireClient();
    const { searchParams } = new URL(request.url);
    const items = await listItems({
      clientId: client.id,
      limit: searchParams.get("limit") ? Number(searchParams.get("limit")) : undefined,
      keyword: searchParams.get("keyword"),
      target: searchParams.get("target"),
      since: searchParams.get("since"),
    });

    return jsonOk({ items });
  } catch (error) {
    return jsonError(error instanceof Error ? error.message : "Unauthorized.", 401);
  }
}
