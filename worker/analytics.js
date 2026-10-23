// YouTube numbers in Studio (owner request 2026-10-24).
//
// The engine collects YouTube Analytics every morning and posts it to
// /api/engine/analytics. Since the Studio redesign that endpoint only answered
// "accepted" and kept nothing, so the dashboard had no numbers. This module stores
// what arrives (per video per day, plus channel totals per day) and serves the
// dashboard's report.

export const ANALYTICS_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS yt_channel_daily (
    day TEXT PRIMARY KEY,
    views INTEGER NOT NULL DEFAULT 0,
    engaged_views INTEGER NOT NULL DEFAULT 0,
    minutes INTEGER NOT NULL DEFAULT 0,
    avg_view_seconds INTEGER NOT NULL DEFAULT 0,
    avg_view_pct REAL NOT NULL DEFAULT 0,
    subs_gained INTEGER NOT NULL DEFAULT 0,
    subs_lost INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS yt_video_daily (
    video_id TEXT NOT NULL,
    day TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    format TEXT NOT NULL DEFAULT '',
    is_golide INTEGER NOT NULL DEFAULT 0,
    published_at TEXT NOT NULL DEFAULT '',
    views INTEGER NOT NULL DEFAULT 0,
    engaged_views INTEGER NOT NULL DEFAULT 0,
    minutes INTEGER NOT NULL DEFAULT 0,
    avg_view_seconds INTEGER NOT NULL DEFAULT 0,
    avg_view_pct REAL NOT NULL DEFAULT 0,
    likes INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    shares INTEGER NOT NULL DEFAULT 0,
    subs_gained INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (video_id, day)
  )`,
  `CREATE INDEX IF NOT EXISTS idx_yt_video_daily_day ON yt_video_daily(day)`,
];

const DAY = /^\d{4}-\d{2}-\d{2}$/;
const int = (v) => Math.max(0, Math.round(Number(v) || 0));
const num = (v) => Math.max(0, Number(v) || 0);
const text = (v, n) => String(v ?? "").slice(0, n);

/** Store one sync payload: {channelId, daily:[...], videos:[...]}. Upserts by day. */
export async function storeAnalytics(db, payload, now = new Date().toISOString()) {
  const daily = Array.isArray(payload?.daily) ? payload.daily : [];
  const videos = Array.isArray(payload?.videos) ? payload.videos : [];
  const statements = [];
  for (const d of daily) {
    if (!DAY.test(String(d?.date || ""))) continue;
    statements.push(db.prepare(
      `INSERT INTO yt_channel_daily (day,views,engaged_views,minutes,avg_view_seconds,avg_view_pct,subs_gained,subs_lost,updated_at)
       VALUES (?,?,?,?,?,?,?,?,?)
       ON CONFLICT(day) DO UPDATE SET views=excluded.views, engaged_views=excluded.engaged_views,
         minutes=excluded.minutes, avg_view_seconds=excluded.avg_view_seconds, avg_view_pct=excluded.avg_view_pct,
         subs_gained=excluded.subs_gained, subs_lost=excluded.subs_lost, updated_at=excluded.updated_at`
    ).bind(d.date, int(d.views), int(d.engagedViews), int(d.estimatedMinutesWatched), int(d.averageViewDurationSeconds),
      num(d.averageViewPercentage), int(d.subscribersGained), int(d.subscribersLost), now));
  }
  for (const v of videos) {
    const day = String(v?.snapshotDate || "");
    const id = text(v?.videoId, 32).replace(/[^A-Za-z0-9_-]/g, "");
    if (!id || !DAY.test(day)) continue;
    statements.push(db.prepare(
      `INSERT INTO yt_video_daily (video_id,day,title,format,is_golide,published_at,views,engaged_views,minutes,
         avg_view_seconds,avg_view_pct,likes,comments,shares,subs_gained,updated_at)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
       ON CONFLICT(video_id,day) DO UPDATE SET title=excluded.title, format=excluded.format, is_golide=excluded.is_golide,
         published_at=excluded.published_at, views=excluded.views, engaged_views=excluded.engaged_views,
         minutes=excluded.minutes, avg_view_seconds=excluded.avg_view_seconds, avg_view_pct=excluded.avg_view_pct,
         likes=excluded.likes, comments=excluded.comments, shares=excluded.shares, subs_gained=excluded.subs_gained,
         updated_at=excluded.updated_at`
    ).bind(id, day, text(v.title, 200), v.format === "short" ? "short" : "long", v.isGolide ? 1 : 0,
      text(v.publishedAt, 40), int(v.views), int(v.engagedViews), int(v.estimatedMinutesWatched),
      int(v.averageViewDurationSeconds), num(v.averageViewPercentage), int(v.likes), int(v.comments),
      int(v.shares), int(v.subscribersGained), now));
  }
  for (let i = 0; i < statements.length; i += 100) await db.batch(statements.slice(i, i + 100));
  return { status: "stored", days: daily.length, video_days: videos.length };
}

function shiftDay(day, days) {
  const d = new Date(day + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

async function totals(db, from, to) {
  const row = await db.prepare(
    `SELECT COALESCE(SUM(views),0) views, COALESCE(SUM(minutes),0) minutes,
            COALESCE(SUM(subs_gained),0) gained, COALESCE(SUM(subs_lost),0) lost
       FROM yt_channel_daily WHERE day BETWEEN ? AND ?`
  ).bind(from, to).first();
  const eng = await db.prepare(
    `SELECT COALESCE(SUM(likes),0) likes, COALESCE(SUM(comments),0) comments, COALESCE(SUM(shares),0) shares
       FROM yt_video_daily WHERE day BETWEEN ? AND ?`
  ).bind(from, to).first();
  return {
    views: row.views, watch_hours: Math.round(row.minutes / 6) / 10,
    subscribers_net: row.gained - row.lost, likes: eng.likes, comments: eng.comments, shares: eng.shares,
  };
}

/** The dashboard report for the last `days` days of data (YouTube reports 2-3 days late). */
export async function analyticsReport(db, days = 28) {
  const span = [7, 28, 90].includes(Number(days)) ? Number(days) : 28;
  const latest = await db.prepare(`SELECT MAX(day) day, MAX(updated_at) at FROM yt_channel_daily`).first();
  if (!latest?.day) return { status: "empty", days: span };
  const to = latest.day;
  const from = shiftDay(to, -(span - 1));
  const before = [shiftDay(from, -span), shiftDay(from, -1)];
  const daily = await db.prepare(
    `SELECT day, views, minutes FROM yt_channel_daily WHERE day BETWEEN ? AND ? ORDER BY day`
  ).bind(from, to).all();
  const videos = await db.prepare(
    `SELECT video_id, MAX(title) title, MAX(format) format, MAX(is_golide) is_golide, MAX(published_at) published_at,
            SUM(views) views, SUM(minutes) minutes, SUM(likes) likes, SUM(comments) comments, SUM(shares) shares,
            SUM(subs_gained) subs,
            CASE WHEN SUM(views)>0 THEN SUM(avg_view_pct*views)/SUM(views) ELSE 0 END avg_pct
       FROM yt_video_daily WHERE day BETWEEN ? AND ?
       GROUP BY video_id HAVING SUM(views)>0 ORDER BY views DESC LIMIT 40`
  ).bind(from, to).all();
  return {
    status: "ok", days: span, from, to, updated_at: latest.at,
    totals: await totals(db, from, to),
    previous: await totals(db, before[0], before[1]),
    daily: daily.results || [],
    videos: (videos.results || []).map((v) => ({ ...v, avg_pct: Math.round(v.avg_pct * 10) / 10 })),
  };
}
