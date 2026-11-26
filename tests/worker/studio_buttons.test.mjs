// 2026-11-25 (owner: "these buttons have to correspond with the backend; they are not there for decoration"):
// every Studio control on a video is pressed here against a real SQLite database and its effect on the video
// (the spec the engine reads) is checked. The engine side is checked in tests/test_studio_buttons.py.
import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { handleApi } from "../../worker/index.js";

function d1() {
  const db = new DatabaseSync(":memory:");
  const clean = (a) => a.map((v) => (v === undefined ? null : typeof v === "boolean" ? (v ? 1 : 0) : v));
  const stmt = (sql, args = []) => ({
    bind: (...a) => stmt(sql, a),
    first: async (col) => { const r = db.prepare(sql).get(...clean(args)); return r === undefined ? null : col ? r[col] : r; },
    all: async () => ({ results: db.prepare(sql).all(...clean(args)) }),
    run: async () => { const r = db.prepare(sql).run(...clean(args)); return { meta: { changes: Number(r.changes) } }; },
  });
  return {
    prepare: (sql) => stmt(sql),
    batch: async (list) => Promise.all(list.map((s) => s.run())),
    exec: async (sql) => db.exec(sql),
    raw: db,
  };
}

// the Worker builds its tables once per process, so the tests share one database and clear it between them
const SHARED = d1();
async function studio(connected = ["youtube", "instagram", "linkedin"]) {
  const DB = SHARED;
  const env = { DB };
  await handleApi(new Request("https://studio.golidee.com/api/health"), env, new URL("https://studio.golidee.com/api/health"));
  DB.raw.exec("DELETE FROM production_jobs; DELETE FROM engine_connections;");
  const now = new Date().toISOString();
  for (const p of connected) {
    DB.raw.prepare(`INSERT OR REPLACE INTO engine_connections (platform,connected,account_label,external_account_id,synced_at)
      VALUES (?,1,'','',?)`).run(p, now);
  }
  return env;
}

function job(env, id, status, spec = {}) {
  const now = new Date().toISOString();
  env.DB.raw.prepare(`INSERT INTO production_jobs (job_id,format,spec_json,status,stage,created_at,updated_at)
    VALUES (?,'short',?,?,'x',?,?)`).run(id, JSON.stringify({ id, ...spec }), status, now, now);
}

async function press(env, path, body) {
  const url = new URL("https://studio.golidee.com" + path);
  const res = await handleApi(new Request(url, { method: "POST", body: JSON.stringify(body ?? {}),
    headers: { "content-type": "application/json" } }), env, url);
  return { status: res.status, body: await res.json() };
}

const spec = (env, id) => JSON.parse(env.DB.raw.prepare("SELECT spec_json FROM production_jobs WHERE job_id=?").get(id).spec_json);
const row = (env, id) => env.DB.raw.prepare("SELECT * FROM production_jobs WHERE job_id=?").get(id);

test("Use AI voice saves the video type, the styles and the platforms he ticked", async () => {
  const env = await studio();
  job(env, "j1", "waiting_owner_voice");
  const r = await press(env, "/api/production-jobs/j1/ai-voice", { style: "goli", platforms: ["youtube", "instagram"],
    looks: { free: ["layers", "puppets"], paid: {} } });
  assert.equal(r.body.status, "queued");
  const s = spec(env, "j1");
  assert.equal(s.voice_choice, "ai");
  assert.equal(s.video_style, "goli");
  assert.deepEqual(s.platforms, ["youtube", "instagram"]);
  assert.ok(s.looks && Array.isArray(s.looks.free) && s.looks.free.includes("layers") && s.looks.free.includes("puppets"));
  assert.ok(!s.looks.free.includes("circuit"), "a style he switched off stays off");
});

test("Uploading his recording saves the same choices", async () => {
  const env = await studio();
  job(env, "j2", "waiting_owner_voice");
  const r = await press(env, "/api/production-jobs/j2/voice", { media_ref: "r2://temp/2026/11/25/abc-voice.m4a",
    style: "stickman_goli", platforms: ["youtube"] });
  assert.equal(r.status, 200);
  const s = spec(env, "j2");
  assert.equal(s.video_style, "stickman_goli");
  assert.deepEqual(s.platforms, ["youtube"]);
  assert.equal(s.owner_voice_media_ref, "r2://temp/2026/11/25/abc-voice.m4a");
  assert.equal(row(env, "j2").status, "queued");
});

test("A platform he did not tick, or one that is disconnected, never gets the video", async () => {
  const env = await studio(["youtube", "instagram"]);
  job(env, "j3", "waiting_owner_voice");
  await press(env, "/api/production-jobs/j3/ai-voice", { style: "goli", platforms: ["youtube", "linkedin"] });
  assert.deepEqual(spec(env, "j3").platforms, ["youtube"]);
});

test("The video type buttons change the style until the video is being built, then say so", async () => {
  const env = await studio();
  job(env, "j4", "queued");
  assert.equal((await press(env, "/api/production-jobs/j4/style", { style: "stickman" })).body.style, "stickman");
  assert.equal(spec(env, "j4").video_style, "stickman");
  env.DB.raw.prepare("UPDATE production_jobs SET status='running' WHERE job_id='j4'").run();
  assert.equal((await press(env, "/api/production-jobs/j4/style", { style: "goli" })).status, 409);
});

test("Paste a link (with its transcript), Find a topic, Skip and Remove do what they say", async () => {
  const env = await studio();
  job(env, "j5", "waiting_owner_link");
  const words = Array.from({ length: 50 }, (_, i) => "word" + i).join(" ");
  await press(env, "/api/production-jobs/j5/replace-script", { link: "https://www.youtube.com/watch?v=znWzWYHoLOg", transcript: words });
  assert.equal(spec(env, "j5").replace_model.url, "https://www.youtube.com/watch?v=znWzWYHoLOg");
  assert.ok(spec(env, "j5").replace_model.transcript.startsWith("word0"));
  assert.equal(row(env, "j5").status, "queued");
  job(env, "j6", "waiting_owner_link");
  await press(env, "/api/production-jobs/j6/find-topic");
  assert.equal(spec(env, "j6").research_now, true);
  job(env, "j7", "waiting_owner_voice");
  await press(env, "/api/production-jobs/j7/skip");
  assert.equal(row(env, "j7").status, "skipped");
  job(env, "j8", "scheduled");
  await press(env, "/api/production-jobs/j8/archive");
  assert.ok(row(env, "j8").archived_at);
});

test("The engine's Made with report is kept on the video and shown in the list", async () => {
  const env = await studio();
  job(env, "j9", "running");
  const url = new URL("https://studio.golidee.com/api/production-jobs");
  const { updateProductionStatusForTest } = await import("../../worker/index.js");
  await updateProductionStatusForTest(env.DB, "j9", { status: "scheduled", stage: "youtube-scheduled",
    madeWith: { style: "goli", platforms: ["youtube"], blocks: { pages: 3 }, kit: "ember", doctor_fixed: { empty: 1 } } });
  const res = await handleApi(new Request(url), env, url);
  const jobs = (await res.json()).jobs;
  const mw = JSON.parse(jobs.find((j) => j.job_id === "j9").made_with);
  assert.equal(mw.kit, "ember");
  assert.deepEqual(mw.platforms, ["youtube"]);
});

test("The living studio tick reaches the video's spec, and stays off when not ticked", async () => {
  // owner 2026-11-26: a TRIAL tick next to the styles
  const env = await studio();
  job(env, "jL1", "waiting_owner_voice"); job(env, "jL2", "waiting_owner_voice");
  await press(env, "/api/production-jobs/jL1/ai-voice", { style: "goli", platforms: ["youtube"], looks: { free: ["layers"], paid: {}, live: true } });
  await press(env, "/api/production-jobs/jL2/ai-voice", { style: "goli", platforms: ["youtube"], looks: { free: ["layers"], paid: {} } });
  assert.equal(spec(env, "jL1").looks.live, true);
  assert.equal(spec(env, "jL2").looks.live, undefined);
});
