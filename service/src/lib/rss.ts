import type { ItemRecord } from "@/lib/item-service";

function escapeXml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function buildDescription(item: ItemRecord) {
  const lines = [
    item.author ? `Author: ${item.author}` : null,
    `Target: ${item.target}`,
    item.content || item.rawContent || item.translatedContent || "",
  ].filter(Boolean);

  return escapeXml(lines.join("\n\n"));
}

export function buildFeedXml(feedToken: string, items: ItemRecord[]) {
  const channelTitle = `x2ding feed ${feedToken.slice(0, 10)}`;
  const latestDate = items[0]?.publishedAt ?? items[0]?.storedAt ?? new Date().toISOString();

  const itemXml = items
    .map((item) => {
      const link = item.xUrl || item.link || `urn:x2ding:item:${item.id}`;
      const pubDate = new Date(item.publishedAt ?? item.storedAt).toUTCString();
      const title = escapeXml(item.title || `${item.target} update`);
      const description = buildDescription(item);

      return `<item>
  <title>${title}</title>
  <link>${escapeXml(link)}</link>
  <guid isPermaLink="false">${escapeXml(`${item.target}:${item.guid}`)}</guid>
  <pubDate>${escapeXml(pubDate)}</pubDate>
  <description>${description}</description>
</item>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>${escapeXml(channelTitle)}</title>
  <description>${escapeXml("x2ding aggregated subscription feed")}</description>
  <lastBuildDate>${escapeXml(new Date(latestDate).toUTCString())}</lastBuildDate>
  <generator>x2ding</generator>
${itemXml}
</channel>
</rss>`;
}
