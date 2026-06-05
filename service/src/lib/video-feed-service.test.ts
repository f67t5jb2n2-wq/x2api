import assert from "node:assert/strict";
import test from "node:test";

import { decodeCursor, encodeCursor } from "@/lib/pagination";
import { mergeVideoFeedCandidatePools, selectDiverseVideoItems } from "@/lib/video-feed-service";

type FeedCursor = {
  sortTime: string;
  storedAt: string;
  id: string;
};

type RankedItem = FeedCursor & {
  score: number;
};

function isFeedCursor(value: unknown): value is FeedCursor {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  const candidate = value as Partial<FeedCursor>;
  return (
    typeof candidate.sortTime === "string" &&
    typeof candidate.storedAt === "string" &&
    typeof candidate.id === "string"
  );
}

function keysetAfter(items: RankedItem[], cursor: FeedCursor | null) {
  if (!cursor) {
    return items;
  }

  return items.filter((item) => {
    if (item.sortTime !== cursor.sortTime) {
      return item.sortTime < cursor.sortTime;
    }

    if (item.storedAt !== cursor.storedAt) {
      return item.storedAt < cursor.storedAt;
    }

    return item.id < cursor.id;
  });
}

test("video feed pagination remains stable when scores differ", () => {
  const items: RankedItem[] = [
    {
      id: "b",
      sortTime: "2026-05-21T10:00:00.000Z",
      storedAt: "2026-05-21T10:00:00.000Z",
      score: 1,
    },
    {
      id: "a",
      sortTime: "2026-05-21T10:00:00.000Z",
      storedAt: "2026-05-21T10:00:00.000Z",
      score: 999,
    },
    {
      id: "9",
      sortTime: "2026-05-21T09:59:00.000Z",
      storedAt: "2026-05-21T09:59:00.000Z",
      score: 0,
    },
  ].sort((left, right) => {
    if (left.sortTime !== right.sortTime) {
      return right.sortTime.localeCompare(left.sortTime);
    }

    if (left.storedAt !== right.storedAt) {
      return right.storedAt.localeCompare(left.storedAt);
    }

    return right.id.localeCompare(left.id);
  });

  const firstPage = items.slice(0, 2);
  const cursor = decodeCursor(
    encodeCursor({
      sortTime: firstPage[1]!.sortTime,
      storedAt: firstPage[1]!.storedAt,
      id: firstPage[1]!.id,
    }),
    isFeedCursor,
  );

  const secondPage = keysetAfter(items, cursor);

  assert.deepEqual(
    firstPage.map((item) => item.id),
    ["b", "a"],
  );
  assert.deepEqual(
    secondPage.map((item) => item.id),
    ["9"],
  );
  assert.equal(secondPage.some((item) => item.id === "b" || item.id === "a"), false);
});

test("selectDiverseVideoItems avoids consecutive authors and target flooding", () => {
  const selected = selectDiverseVideoItems({
    candidates: [
      { id: "1", guid: "g1", author: "alice", target: "search:ai" },
      { id: "2", guid: "g2", author: "alice", target: "search:ai" },
      { id: "3", guid: "g3", author: "alice", target: "search:ai" },
      { id: "4", guid: "g4", author: "bob", target: "search:design" },
      { id: "5", guid: "g5", author: "carol", target: "search:code" },
      { id: "6", guid: "g6", author: "dave", target: "search:ai" },
    ],
    limit: 5,
  });

  assert.deepEqual(
    selected.map((item) => item.id),
    ["1", "4", "5", "6"],
  );
});

test("selectDiverseVideoItems can relax page limits without repeating ids or guids", () => {
  const strictSelected = selectDiverseVideoItems({
    candidates: [
      { id: "1", guid: "same", author: "alice", target: "search:ai" },
      { id: "2", guid: "g2", author: "alice", target: "search:ai" },
      { id: "3", guid: "g3", author: "alice", target: "search:ai" },
      { id: "4", guid: "same", author: "bob", target: "search:design" },
    ],
    limit: 3,
  });
  const relaxedSelected = selectDiverseVideoItems({
    selected: strictSelected,
    candidates: [
      { id: "1", guid: "same", author: "alice", target: "search:ai" },
      { id: "2", guid: "g2", author: "alice", target: "search:ai" },
      { id: "3", guid: "g3", author: "alice", target: "search:ai" },
      { id: "4", guid: "same", author: "bob", target: "search:design" },
    ],
    limit: 3,
    enforceLimits: false,
    enforceConsecutive: false,
  });

  assert.deepEqual(
    strictSelected.map((item) => item.id),
    ["1"],
  );
  assert.deepEqual(
    relaxedSelected.map((item) => item.id),
    ["1", "2", "3"],
  );
});

test("mergeVideoFeedCandidatePools keeps single non-empty pool when the other is empty", () => {
  const merged = mergeVideoFeedCandidatePools([
    [],
    [
      {
        id: "public-1",
        guid: "guid-public-1",
        videoKey: "video-public-1",
        sortTime: "2026-06-04T10:00:00.000Z",
        storedAt: "2026-06-04T10:00:00.000Z",
      },
    ],
  ]);

  assert.deepEqual(
    merged.map((item) => item.id),
    ["public-1"],
  );
});

test("mergeVideoFeedCandidatePools sorts candidates and removes duplicates", () => {
  const merged = mergeVideoFeedCandidatePools([
    [
      {
        id: "user-old",
        guid: "guid-user-old",
        videoKey: "video-user-old",
        sortTime: "2026-06-04T09:00:00.000Z",
        storedAt: "2026-06-04T09:00:00.000Z",
      },
      {
        id: "same-id",
        guid: "guid-user-same",
        videoKey: "video-user-same",
        sortTime: "2026-06-04T08:00:00.000Z",
        storedAt: "2026-06-04T08:00:00.000Z",
      },
    ],
    [
      {
        id: "public-new",
        guid: "guid-public-new",
        videoKey: "video-public-new",
        sortTime: "2026-06-04T11:00:00.000Z",
        storedAt: "2026-06-04T11:00:00.000Z",
      },
      {
        id: "public-duplicate-video",
        guid: "guid-public-duplicate-video",
        videoKey: "video-user-old",
        sortTime: "2026-06-04T10:00:00.000Z",
        storedAt: "2026-06-04T10:00:00.000Z",
      },
      {
        id: "same-id",
        guid: "guid-public-same",
        videoKey: "video-public-same",
        sortTime: "2026-06-04T07:00:00.000Z",
        storedAt: "2026-06-04T07:00:00.000Z",
      },
    ],
  ]);

  assert.deepEqual(
    merged.map((item) => item.id),
    ["public-new", "public-duplicate-video", "same-id"],
  );
});
