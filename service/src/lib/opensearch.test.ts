import assert from "node:assert/strict";
import test from "node:test";

import { assertOpenSearchFeedEnabled, getOpenSearchItemsIndex, isOpenSearchFeedEnabled } from "@/lib/opensearch";

test("isOpenSearchFeedEnabled accepts explicit truthy values", () => {
  const previous = process.env.OPENSEARCH_FEED_ENABLED;

  process.env.OPENSEARCH_FEED_ENABLED = "true";
  assert.equal(isOpenSearchFeedEnabled(), true);

  process.env.OPENSEARCH_FEED_ENABLED = "1";
  assert.equal(isOpenSearchFeedEnabled(), true);

  process.env.OPENSEARCH_FEED_ENABLED = "false";
  assert.equal(isOpenSearchFeedEnabled(), false);

  if (previous === undefined) {
    delete process.env.OPENSEARCH_FEED_ENABLED;
  } else {
    process.env.OPENSEARCH_FEED_ENABLED = previous;
  }
});

test("getOpenSearchItemsIndex defaults to x2_items", () => {
  const previous = process.env.OPENSEARCH_ITEMS_INDEX;

  delete process.env.OPENSEARCH_ITEMS_INDEX;
  assert.equal(getOpenSearchItemsIndex(), "x2_items");

  process.env.OPENSEARCH_ITEMS_INDEX = "custom_items";
  assert.equal(getOpenSearchItemsIndex(), "custom_items");

  if (previous === undefined) {
    delete process.env.OPENSEARCH_ITEMS_INDEX;
  } else {
    process.env.OPENSEARCH_ITEMS_INDEX = previous;
  }
});

test("assertOpenSearchFeedEnabled throws when feed flag is disabled", () => {
  const previousEnabled = process.env.OPENSEARCH_FEED_ENABLED;
  const previousUrl = process.env.OPENSEARCH_URL;

  process.env.OPENSEARCH_FEED_ENABLED = "false";
  process.env.OPENSEARCH_URL = "https://example.com";

  assert.throws(() => assertOpenSearchFeedEnabled("items"), /OPENSEARCH_FEED_ENABLED/);

  if (previousEnabled === undefined) {
    delete process.env.OPENSEARCH_FEED_ENABLED;
  } else {
    process.env.OPENSEARCH_FEED_ENABLED = previousEnabled;
  }

  if (previousUrl === undefined) {
    delete process.env.OPENSEARCH_URL;
  } else {
    process.env.OPENSEARCH_URL = previousUrl;
  }
});

test("assertOpenSearchFeedEnabled throws when OpenSearch URL is missing", () => {
  const previousEnabled = process.env.OPENSEARCH_FEED_ENABLED;
  const previousUrl = process.env.OPENSEARCH_URL;

  process.env.OPENSEARCH_FEED_ENABLED = "true";
  delete process.env.OPENSEARCH_URL;

  assert.throws(() => assertOpenSearchFeedEnabled("items"), /OPENSEARCH_URL/);

  if (previousEnabled === undefined) {
    delete process.env.OPENSEARCH_FEED_ENABLED;
  } else {
    process.env.OPENSEARCH_FEED_ENABLED = previousEnabled;
  }

  if (previousUrl === undefined) {
    delete process.env.OPENSEARCH_URL;
  } else {
    process.env.OPENSEARCH_URL = previousUrl;
  }
});
