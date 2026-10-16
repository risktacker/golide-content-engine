// node --test tests/worker/health.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { collectHealth, renderHealth, lusakaDay } from "../../worker/health.js";

function d1(sqlite) {   // the tiny slice of the D1 API that health.js uses
  return { prepare(sql) { const st = sqlite.prepare(sql); let b = [];
    const api = { bind(...a) { b = a; return api; }, async all() { return { results: st.all(...b) }; }, async first() { return st.get(...b) ?? null; } };
    return api; } };
}

function seed() {
  const db = new DatabaseSync(":memory:");
  db.exec(`CREATE TABLE content_posts(id TEXT, title TEXT, status TEXT, scheduled_at TEXT, created_at TEXT, updated_at TEXT, content_class TEXT);
  CREATE TABLE social_variants(post_id TEXT, platform TEXT, status TEXT, last_error TEXT);
  CREATE TABLE production_jobs(job_id TEXT, format TEXT, title TEXT, status TEXT, stage TEXT, error TEXT, scheduled_at TEXT, release_url TEXT, archived_at TEXT, updated_at TEXT);
  CREATE TABLE automation_control(id INTEGER, enabled INTEGER);
  CREATE TABLE cron_runs(workflow TEXT, ok INTEGER, detail TEXT, at TEXT);
  CREATE TABLE social_oauth_tokens(platform TEXT, expires_at TEXT, refresh_token_enc TEXT);
  CREATE TABLE x_oauth_tokens(id INTEGER, expires_at TEXT);
  INSERT INTO automation_control VALUES(1,1);
  INSERT INTO x_oauth_tokens VALUES(1,'2026-10-08T17:31:53Z');
  INSERT INTO social_oauth_tokens VALUES('linkedin','2026-12-03T17:04:45Z',''),('instagram','2026-12-03T17:38:33Z',''),('facebook','2026-12-03T17:19:20Z','x'),('youtube','2026-10-08T12:27:38Z','x');`);
  return db;
}
const post = (db, id, title, variants) => {
  db.prepare(`INSERT INTO content_posts VALUES(?,?,?,?,?,?,?)`).run(id, title, "published", "2026-10-07T06:30:00Z", "2026-10-07T06:31:00Z", "2026-10-07T06:32:00Z", "post");
  for (const [p, s, e] of variants) db.prepare(`INSERT INTO social_variants VALUES(?,?,?,?)`).run(id, p, s, e ?? null);
};
const ALL_OK = [["facebook", "published"], ["instagram", "published"], ["linkedin", "published"], ["x", "published"]];

test("Lusaka day boundaries", () => {
  const d = lusakaDay(new Date("2026-10-07T22:30:00Z"));
  assert.equal(d.date, "2026-10-08");
  assert.equal(d.start.toISOString(), "2026-10-07T22:00:00.000Z");
});

test("a clean day says all good", async () => {
  const db = seed();
  post(db, "golide-post-2026-10-07-post-a", "From Apps to Outcomes", ALL_OK);
  post(db, "golide-post-2026-10-07-post-b", "AI Glasses and Everyday Trust", ALL_OK);
  db.prepare(`INSERT INTO production_jobs VALUES(?,?,?,?,?,?,?,?,?,?)`).run("golide-short-2026-10-07", "short", "Meta's New AI Shops for You.", "scheduled", "youtube-scheduled", null, "2026-10-07T11:00:00Z", null, null, "2026-10-07T12:10:39Z");
  post(db, "golide-short-2026-10-07-reels", "Meta", [["facebook", "published"], ["instagram", "published"], ["linkedin", "published"], ["youtube", "published"]]);
  const r = await collectHealth(d1(db), new Date("2026-10-07T18:00:00Z"));
  assert.deepEqual(r.issues, []);
  assert.equal(renderHealth(r).subject, "GOLIDE daily: all good");
  assert.equal(r.sections.length, 3);
});

test("missing post, failure, fallback, waiting voice and failed dispatch are all reported", async () => {
  const db = seed();
  post(db, "golide-post-2026-10-07-post-b", "AI Glasses", [["facebook", "published"], ["instagram", "published", "the carousel went out as one image"], ["linkedin", "failed", "token expired"], ["x", "published"]]);
  db.prepare(`INSERT INTO production_jobs VALUES(?,?,?,?,?,?,?,?,?,?)`).run("golide-short-2026-10-07", "short", "Meta shops", "waiting_owner_voice", "owner-voice", null, null, null, null, "2026-10-07T07:05:00Z");
  db.prepare(`INSERT INTO cron_runs VALUES(?,?,?,?)`).run("content-distribution-scheduler.yml", 0, "401 Bad credentials", "2026-10-07T06:30:01Z");
  const r = await collectHealth(d1(db), new Date("2026-10-07T18:00:00Z"));
  const all = r.issues.join("\n");
  assert.match(all, /08:30 post was never created/);
  assert.match(all, /Instagram: published, but the carousel/);
  assert.match(all, /LinkedIn: failed\. token expired/);
  assert.match(all, /Record today's short/);
  assert.match(all, /content-distribution-scheduler\.yml run could not be started/);
  assert.equal(r.issues.length, 5);
  assert.match(renderHealth(r).subject, /5 things need you/);
});

test("expiring login without refresh and automation off", async () => {
  const db = seed();
  db.exec(`UPDATE automation_control SET enabled=0; UPDATE social_oauth_tokens SET expires_at='2026-10-10T00:00:00Z' WHERE platform='linkedin'`);
  const r = await collectHealth(d1(db), new Date("2026-10-08T18:00:00Z"));
  assert.match(r.issues.join("\n"), /switched OFF/);
  assert.match(r.issues.join("\n"), /LinkedIn login expires in 1 day/);
  assert.doesNotMatch(r.issues.join("\n"), /never created/);   // automation off: no false alarms
});

test("a long video's socials minutes after release are 'going out', not a problem", async () => {
  const db = seed();
  db.prepare(`INSERT INTO production_jobs VALUES(?,?,?,?,?,?,?,?,?,?)`).run("golide-long-2026-10-07", "long", "Tablets", "scheduled", "youtube-scheduled", null, "2026-10-07T17:30:00Z", null, null, "2026-10-07T13:00:00Z");
  db.prepare(`INSERT INTO content_posts VALUES(?,?,?,?,?,?,?)`).run("golide-long-2026-10-07-social", "Tablets", "scheduled", "2026-10-07T17:30:00Z", "", "", "long");
  for (const p of ["facebook", "instagram", "linkedin"]) db.prepare(`INSERT INTO social_variants VALUES(?,?,?,?)`).run("golide-long-2026-10-07-social", p, "pending", null);
  const r = await collectHealth(d1(db), new Date("2026-10-07T18:00:00Z"));
  assert.ok(!r.issues.some((i) => i.startsWith("Long video,")));
});
