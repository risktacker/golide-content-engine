// Website contact panel (owner request 2026-10-24).
//
// "Email hello@golidee.com" links did nothing on computers without a mail app.
// golidee.com now opens a side panel; its form posts here. The message lands in
// the Studio Inbox (reply from there) and the owner gets a copy whose Reply goes
// straight to the visitor. No login for visitors; spam is held back by a hidden
// field, a minimum fill time and a per-address hourly limit.

import { MAIL_FROM, emailHtml, recordInbound } from "./mail.js";

export const CONTACT_ORIGINS = new Set([
  "https://golidee.com", "https://www.golidee.com", "https://marketplace.golidee.com",
]);
export const CONTACT_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS contact_rate (ip TEXT NOT NULL, at TEXT NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS idx_contact_rate ON contact_rate(ip, at)`,
];
const PER_HOUR = 5;
const MIN_FILL_MS = 2500;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function cors(origin) {
  const allow = CONTACT_ORIGINS.has(origin) ? origin : "https://golidee.com";
  return { "access-control-allow-origin": allow, "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "content-type", "access-control-max-age": "86400", vary: "origin" };
}

function reply(origin, status, body) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", ...cors(origin) } });
}

const clean = (v, n) => String(v ?? "").replace(/\r/g, "").trim().slice(0, n);

/** Validate a submission; returns {ok, fields} or {ok:false, error, silent}. */
export function checkContact(body) {
  const fields = {
    name: clean(body?.name, 100), email: clean(body?.email, 200).toLowerCase(),
    topic: clean(body?.topic, 120) || "Hello GOLIDE", message: clean(body?.message, 4000),
  };
  if (clean(body?.website, 200)) return { ok: false, silent: true, error: "spam" };        // hidden field filled
  if (Number(body?.elapsed_ms || 0) < MIN_FILL_MS) return { ok: false, silent: true, error: "too fast" };
  if (!fields.name) return { ok: false, error: "Please add your name." };
  if (!EMAIL.test(fields.email)) return { ok: false, error: "Please add a valid email so we can reply." };
  if (fields.message.length < 10) return { ok: false, error: "Please write a little more about what you need." };
  return { ok: true, fields };
}

async function overLimit(db, ip, now) {
  const since = new Date(now - 3600_000).toISOString();
  const row = await db.prepare(`SELECT COUNT(*) n FROM contact_rate WHERE ip=? AND at>?`).bind(ip, since).first();
  return Number(row?.n || 0) >= PER_HOUR;
}

async function notifyOwner(env, f) {
  if (!env.RESEND_API_KEY || !env.OWNER_EMAIL) return;
  const subject = `Website: ${f.topic} (from ${f.name})`.slice(0, 180);
  const body = `${f.name} <${f.email}> wrote through golidee.com:\n\n${f.message}\n\nReply to this email to answer them, or answer from the Studio Inbox.`;
  await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({ from: MAIL_FROM, to: [env.OWNER_EMAIL], reply_to: f.email, subject,
      html: emailHtml({ subject, body }), text: body }),
  }).catch((e) => console.log(JSON.stringify({ contact_notify: "failed", error: String(e) })));
}

export async function handleContact(request, env, now = Date.now()) {
  const origin = request.headers.get("origin") || "";
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
  if (request.method !== "POST") return reply(origin, 405, { error: "use POST" });
  if (!CONTACT_ORIGINS.has(origin)) return reply(origin, 403, { error: "unknown site" });
  let body;
  try { body = await request.json(); } catch { return reply(origin, 400, { error: "bad request" }); }
  const result = checkContact(body);
  if (!result.ok) return result.silent ? reply(origin, 200, { status: "sent" }) : reply(origin, 400, { error: result.error });
  for (const sql of CONTACT_SCHEMA) await env.DB.prepare(sql).run();
  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  if (await overLimit(env.DB, ip, now)) return reply(origin, 429, { error: "Too many messages. Please try again later." });
  await env.DB.prepare(`INSERT INTO contact_rate (ip, at) VALUES (?, ?)`).bind(ip, new Date(now).toISOString()).run();
  const f = result.fields;
  await recordInbound(env.DB, f.email, `Website: ${f.topic}`, `${f.name} wrote through golidee.com:\n\n${f.message}`);
  await notifyOwner(env, f);
  return reply(origin, 200, { status: "sent" });
}
