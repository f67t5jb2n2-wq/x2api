import assert from "node:assert/strict";
import test from "node:test";

import { buildFeedXml } from "@/lib/rss";

test("buildFeedXml creates RSS output", () => {
  const xml = buildFeedXml("feed_1234567890", [
    {
      id: "item-1",
      target: "OpenAI",
      kind: "user",
      author: "OpenAI",
      title: "New post",
      content: "Hello RSS",
      rawContent: null,
      translatedContent: null,
      link: "https://example.com/nitter",
      xUrl: "https://x.com/openai/status/1",
      images: [],
      videoUrl: null,
      publishedAt: "2026-05-18T10:00:00.000Z",
      storedAt: "2026-05-18T10:00:10.000Z",
      guid: "1",
      isRetweet: false,
    },
  ]);

  assert.match(xml, /<rss version="2.0">/);
  assert.match(xml, /<title>New post<\/title>/);
  assert.match(xml, /<guid isPermaLink="false">OpenAI:1<\/guid>/);
});
