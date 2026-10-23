// node --test tests/worker/analytics.test.mjs
// 2026-10-24: Studio stores the morning YouTube sync (it used to drop it) and shows it.
import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { ANALYTICS_SCHEMA, analyticsReport, storeAnalytics } from "../../worker/analytics.js";

function d1(sqlite) {
  const prepare = (sql) => { const st = sqlite.prepare(sql); let b = [];
    const api = { bind(...a) { b = a; return api; }, async all() { return { results: st.all(...b) }; },
      async first() { return st.get(...b) ?? null; }, async run() { st.run(...b); return {}; }, _run() { st.run(...b); } };
    return api; };
  return { prepare, async batch(list) { for (const s of list) s._run(); return []; } };
}

function fresh() {
  const sqlite = new DatabaseSync(":memory:");
  for (const sql of ANALYTICS_SCHEMA) sqlite.exec(sql);
  return d1(sqlite);
}

const payload = (days) => ({
  channelId: "UC",
  daily: days.map((d, i) => ({ date: d, views: 100 + i, engagedViews: 50, estimatedMinutesWatched: 120,
    averageViewDurationSeconds: 70, averageViewPercentage: 55, subscribersGained: 3, subscribersLost: 1 })),
  videos: days.flatMap((d) => [
    { videoId: "gkEM7Li8pYw", title: "Tesla Roadster Flying Demo Explained", format: "long", isGolide: true,
      snapshotDate: d, views: 80, estimatedMinutesWatched: 100, averageViewPercentage: 40, likes: 2, comments: 1, shares: 0, subscribersGained: 2 },
    { videoId: "c1exHjolJSE", title: "DEFE DEFE (Lyric Video)", format: "long", isGolide: false,
      snapshotDate: d, views: 20, averageViewPercentage: 60, likes: 1, comments: 0 },
  ]),
});

const days = Array.from({ length: 60 }, (_, i) => new Date(Date.UTC(2026, 7, 22 + i)).toISOString().slice(0, 10));

test("a sync is stored and a second sync updates instead of duplicating", async () => {
  const db = fresh();
  await storeAnalytics(db, payload(days));
  await storeAnalytics(db, payload(days));
  const row = await db.prepare("SELECT COUNT(*) n FROM yt_video_daily").first();
  assert.equal(row.n, 120);
});

test("the report sums the period, ranks videos and compares with the period before", async () => {
  const db = fresh();
  await storeAnalytics(db, payload(days));
  const r = await analyticsReport(db, "28");
  assert.equal(r.status, "ok");
  assert.equal(r.days, 28);
  assert.equal(r.daily.length, 28);
  assert.equal(r.videos[0].video_id, "gkEM7Li8pYw");
  assert.equal(r.videos[0].views, 80 * 28);
  assert.equal(r.totals.subscribers_net, 2 * 28);
  assert.ok(r.previous.views > 0);
  assert.equal(r.totals.watch_hours, Math.round((120 * 28) / 6) / 10);
});

test("bad rows are skipped and an empty store says so", async () => {
  const db = fresh();
  assert.equal((await analyticsReport(db, 28)).status, "empty");
  await storeAnalytics(db, { daily: [{ date: "not-a-day" }], videos: [{ videoId: "x", snapshotDate: "2026-13" }] });
  assert.equal((await db.prepare("SELECT COUNT(*) n FROM yt_video_daily").first()).n, 0);
  assert.equal((await analyticsReport(db, 999)).days, 28);
});
