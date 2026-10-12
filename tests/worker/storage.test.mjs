import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { sweepMedia } from "../../worker/storage.js";

const d1 = (s) => ({ prepare(sql){ const st=s.prepare(sql); let b=[]; const a={bind(...x){b=x;return a;},async all(){return{results:st.all(...b)}},async first(){return st.get(...b)??null},async run(){st.run(...b);return{}}}; return a; } });
function bucket(objs){ const store=new Map(objs.map(o=>[o.key,o])); return { store,
  async list({prefix}){ return { objects:[...store.values()].filter(o=>o.key.startsWith(prefix)), truncated:false }; },
  async delete(keys){ for(const k of [].concat(keys)) store.delete(k); } }; }

test("sweeps files older than 72h except a pending post's, and only under temp/", async () => {
  const now = new Date("2026-10-08T18:00:00Z"), h = (n) => new Date(now.getTime() - n * 3600e3);
  const db = new DatabaseSync(":memory:");
  db.exec(`CREATE TABLE content_posts(id,status);CREATE TABLE social_variants(post_id,media_ref,parts_json);
  CREATE TABLE temporary_media(object_key,status,deleted_at,created_at);
  CREATE TABLE production_jobs(owner_voice_media_ref,status);
  INSERT INTO production_jobs VALUES('r2://temp/a/voice-waiting.wav','failed'),('r2://temp/a/voice.m4a','scheduled');
  INSERT INTO content_posts VALUES('future','scheduled'),('done','published');
  INSERT INTO social_variants VALUES('future','r2://temp/a/keep.mp4','["cover:r2://temp/a/keepcover.jpg"]'),('done','r2://temp/a/old.png','[]');
  INSERT INTO temporary_media VALUES('r2://temp/a/old.png','active',NULL,'2026-10-04T00:00:00Z'),('r2://temp/a/never-uploaded','active',NULL,'2026-10-01T00:00:00Z'),('r2://temp/a/gone','deleted','2026-09-01T00:00:00Z','2026-09-01T00:00:00Z');`);
  const MEDIA = bucket([
    { key: "temp/a/old.png", size: 5e6, uploaded: h(100) },
    { key: "temp/a/voice.m4a", size: 2e6, uploaded: h(80) },
    { key: "temp/a/voice-waiting.wav", size: 3e6, uploaded: h(90) },
    { key: "temp/a/fresh.png", size: 1e6, uploaded: h(10) },
    { key: "temp/a/keep.mp4", size: 9e6, uploaded: h(200) },
    { key: "temp/a/keepcover.jpg", size: 1e5, uploaded: h(200) },
    { key: "brand/logo.png", size: 1e4, uploaded: h(5000) },
  ]);
  const r = await sweepMedia({ MEDIA, DB: d1(db) }, now);
  assert.equal(r.deleted, 2);
  assert.equal(r.freed_bytes, 7e6);
  assert.deepEqual([...MEDIA.store.keys()].sort(), ["brand/logo.png", "temp/a/fresh.png", "temp/a/keep.mp4", "temp/a/keepcover.jpg", "temp/a/voice-waiting.wav"]);
  const rows = Object.fromEntries(db.prepare(`SELECT object_key,status FROM temporary_media`).all().map(r => [r.object_key, r.status]));
  assert.equal(rows["r2://temp/a/old.png"], "deleted");
  assert.equal(rows["r2://temp/a/never-uploaded"], "deleted");
  assert.equal(rows["r2://temp/a/gone"], undefined);   // bookkeeping older than 30 days pruned
});
