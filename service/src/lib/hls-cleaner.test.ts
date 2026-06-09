import assert from "node:assert/strict";
import test from "node:test";

import { buildCleanHlsPath, cleanHlsPlaylist } from "@/lib/hls-cleaner";

test("cleanHlsPlaylist removes non-content segments and rewrites URLs", () => {
  const result = cleanHlsPlaylist({
    sourceUrl: "https://m3u8.cdn202511.com/videos/202606/07/abc123/869be4/index.m3u8",
    contentPathPrefix: "/videos/202606/07/abc123/",
    playlist: `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:4
#EXTINF:4.0,
https://video.cdn202528.com/stream/202606/05/ad/index0.ts
#EXT-X-DISCONTINUITY
#EXT-X-KEY:METHOD=AES-128,URI="/videos/202606/07/abc123/ts.key",IV=0x00000000000000000000000000000000
#EXTINF:4.0,
https://video.cdn202528.com/videos/202606/07/abc123/869be4/index0.ts
#EXT-X-ENDLIST
`,
  });

  assert.equal(result.keptSegments, 1);
  assert.equal(result.removedSegments, 1);
  assert.match(result.playlist, /https:\/\/m3u8\.cdn202511\.com\/videos\/202606\/07\/abc123\/ts\.key/);
  assert.match(result.playlist, /https:\/\/video\.cdn202528\.com\/videos\/202606\/07\/abc123\/869be4\/index0\.ts/);
  assert.doesNotMatch(result.playlist, /\/stream\//);
  assert.doesNotMatch(result.playlist, /DISCONTINUITY/);
});

test("buildCleanHlsPath produces a relative service URL", () => {
  const path = buildCleanHlsPath({
    sourceUrl: "https://m3u8.cdn202511.com/videos/202606/07/abc123/869be4/index.m3u8",
    referer: "https://18j.tv/v/1/",
    contentPathPrefix: "/videos/202606/07/abc123/",
  });

  assert.match(path, /^\/api\/hls\/clean\?/);
});

test("buildCleanHlsPath supports rewrite-only mode", () => {
  const path = buildCleanHlsPath({
    sourceUrl: "https://avgood.com/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fd7100b5fc0e845fc%2Fts%2Findex.m3u8",
    referer: "https://avgood.com/remote_play/video/play/213646.html",
    contentPathPrefix: "/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fd7100b5fc0e845fc%2Fts%2F",
    rewriteOnly: true,
  });

  assert.match(path, /[?&]rw=1(?:&|$)/);
});

test("cleanHlsPlaylist keeps bdrq CDN content and removes injected paths", () => {
  const result = cleanHlsPlaylist({
    sourceUrl: "https://kjbwhcnao.com/20260608/g4jGnAUr/2000kb/hls/index.m3u8",
    contentPathPrefix: "/20260608/g4jGnAUr/2000kb/hls/",
    playlist: `#EXTM3U
#EXT-X-VERSION:3
#EXTINF:4.0,
https://kjbwhcnao.com/20260604/I6vsA78Y/2000kb/hls/ad0.ts
#EXT-X-KEY:METHOD=AES-128,URI="https://tsbfask.com:65/20260608/g4jGnAUr/2000kb/hls/key.key",IV=0x00000000000000000000000000000001
#EXTINF:4.0,
https://tsbfask.com:65/20260608/g4jGnAUr/2000kb/hls/index0.ts
#EXT-X-ENDLIST
`,
  });

  assert.equal(result.keptSegments, 1);
  assert.equal(result.removedSegments, 1);
  assert.match(result.playlist, /https:\/\/tsbfask\.com:65\/20260608\/g4jGnAUr\/2000kb\/hls\/key\.key/);
  assert.match(result.playlist, /https:\/\/tsbfask\.com:65\/20260608\/g4jGnAUr\/2000kb\/hls\/index0\.ts/);
  assert.doesNotMatch(result.playlist, /I6vsA78Y/);
});

test("cleanHlsPlaylist rewrites AvGood encoded relative key and segments", () => {
  const result = cleanHlsPlaylist({
    sourceUrl: "https://avgood.com/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fd7100b5fc0e845fc/ts/index.m3u8",
    contentPathPrefix: "/remote_m3u8/data_2/video/m3u8/91%E8%A7%86%E9%A2%91%2Fd7%2Fd7100b5fc0e845fc/ts/",
    playlist: `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:17
#EXT-X-KEY:METHOD=AES-128,URI="key_1780888927.key",IV=0x00000000000000000000000000000000
#EXTINF:16.666667,
0000_1780888927.ts
#EXT-X-ENDLIST
`,
  });

  assert.equal(result.keptSegments, 1);
  assert.equal(result.removedSegments, 0);
  assert.match(result.playlist, /https:\/\/avgood\.com\/remote_m3u8\/data_2\/video\/m3u8\/91%E8%A7%86%E9%A2%91%2Fd7%2Fd7100b5fc0e845fc\/ts\/key_1780888927\.key/);
  assert.match(result.playlist, /https:\/\/avgood\.com\/remote_m3u8\/data_2\/video\/m3u8\/91%E8%A7%86%E9%A2%91%2Fd7%2Fd7100b5fc0e845fc\/ts\/0000_1780888927\.ts/);
  assert.doesNotMatch(result.playlist, /\/video\/m3u8\/key_1780888927\.key/);
});
