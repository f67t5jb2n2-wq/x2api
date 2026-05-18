import assert from "node:assert/strict";
import test from "node:test";

import { formatTarget, parseTarget, parseTargets } from "@/lib/targets";

test("parseTarget understands user targets", () => {
  assert.deepEqual(parseTarget("OpenAI"), {
    kind: "user",
    value: "OpenAI",
    normalizedValue: "openai",
  });
});

test("parseTarget understands keyword targets", () => {
  assert.deepEqual(parseTarget("search:AI Safety"), {
    kind: "keyword",
    value: "AI Safety",
    normalizedValue: "ai safety",
  });
});

test("parseTargets deduplicates normalized values", () => {
  const targets = parseTargets(["OpenAI", "openai", "search:AI", "search:ai"]);
  assert.equal(targets.length, 2);
  assert.equal(formatTarget(targets[0]), "OpenAI");
  assert.equal(formatTarget(targets[1]), "search:AI");
});
