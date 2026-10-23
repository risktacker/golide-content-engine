// node --test tests/worker/contact.test.mjs
// 2026-10-24: the golidee.com contact panel posts here; messages land in the Studio Inbox.
import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { checkContact, handleContact } from "../../worker/contact.js";

function d1(sqlite) {
  return { prepare(sql) { const st = sqlite.prepare(sql); let b = [];
    const api = { bind(...a) { b = a; return api; }, async all() { return { results: st.all(...b) }; },
      async first() { return st.get(...b) ?? null; }, async run() { st.run(...b); return {}; } };
    return api; } };
}
function env() {
  const sqlite = new DatabaseSync(":memory:");
  sqlite.exec(`CREATE TABLE inbox_threads (id TEXT PRIMARY KEY, platform TEXT, external_thread_id TEXT, account_id TEXT,
    participant_ref TEXT, subject TEXT, status TEXT, last_message_at TEXT, created_at TEXT, updated_at TEXT, unread INTEGER);
    CREATE TABLE inbox_messages (id TEXT, thread_id TEXT, external_message_id TEXT, direction TEXT, body TEXT, created_at TEXT);`);
  return { sqlite, DB: d1(sqlite) };
}
const good = { name: "Ada", email: "Ada@Example.com", topic: "Working with GOLIDE",
  message: "I need a dashboard for my shop.", website: "", elapsed_ms: 9000 };
const post = (body, origin = "https://golidee.com", ip = "1.1.1.1") => new Request("https://studio.golidee.com/api/public/contact", {
  method: "POST", headers: { origin, "content-type": "application/json", "cf-connecting-ip": ip }, body: JSON.stringify(body) });

test("a real message lands in the Inbox as unread", async () => {
  const e = env();
  const res = await handleContact(post(good), e);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("access-control-allow-origin"), "https://golidee.com");
  const thread = e.sqlite.prepare("SELECT * FROM inbox_threads").get();
  assert.equal(thread.external_thread_id, "ada@example.com");
  assert.equal(thread.unread, 1);
  assert.match(e.sqlite.prepare("SELECT body FROM inbox_messages").get().body, /dashboard for my shop/);
});

test("bots get a quiet success and store nothing", async () => {
  const e = env();
  for (const bad of [{ ...good, website: "spam.biz" }, { ...good, elapsed_ms: 200 }]) {
    assert.equal((await handleContact(post(bad), e)).status, 200);
  }
  assert.equal(e.sqlite.prepare("SELECT COUNT(*) n FROM inbox_messages").get().n, 0);
});

test("other sites, bad input and floods are refused", async () => {
  const e = env();
  assert.equal((await handleContact(post(good, "https://evil.example"), e)).status, 403);
  assert.equal((await handleContact(post({ ...good, email: "nope" }), e)).status, 400);
  assert.equal(checkContact({ ...good, message: "hi" }).ok, false);
  for (let i = 0; i < 5; i++) assert.equal((await handleContact(post(good, undefined, "9.9.9.9"), e)).status, 200);
  assert.equal((await handleContact(post(good, undefined, "9.9.9.9"), e)).status, 429);
});

test("the browser preflight is answered", async () => {
  const res = await handleContact(new Request("https://studio.golidee.com/api/public/contact",
    { method: "OPTIONS", headers: { origin: "https://www.golidee.com" } }), env());
  assert.equal(res.status, 204);
  assert.equal(res.headers.get("access-control-allow-origin"), "https://www.golidee.com");
});
