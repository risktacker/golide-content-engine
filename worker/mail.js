// GOLIDE email: hello@golidee.com in Studio's Inbox.
//
// Receive: Cloudflare Email Routing hands each message for hello@ to the
// Worker's email() handler. It is stored as a conversation (one per sender)
// and a copy is forwarded to the owner's mailbox when EMAIL_FORWARD_TO is set.
// Send: Studio posts to /api/inbox/send; the message goes out through Resend
// as "GOLIDE <hello@golidee.com>" in the GOLIDE email design.

export const MAIL_FROM = "GOLIDE <hello@golidee.com>";
export const MAIL_ADDRESS = "hello@golidee.com";

const now = () => new Date().toISOString();
const clean = (v) => String(v ?? "").trim();

// ---------------------------------------------------------------- design ---

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Table-based with bgcolor attributes: mail apps that drop <div> backgrounds
// keep table colours, so light text never lands on a white page.
export function emailHtml({ subject, body, eyebrow = "GOLIDE" }) {
  const paragraphs = clean(body).split(/\n{2,}/).map((p) =>
    `<p style="margin:0 0 16px;font-size:16px;line-height:1.6;color:#ecedef">${esc(p).replace(/\n/g, "<br>")}</p>`).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark"><title>${esc(subject)}</title></head>
<body style="margin:0;padding:0;background:#0b0c10" bgcolor="#0b0c10">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#0b0c10" style="background:#0b0c10">
<tr><td align="center" style="padding:28px 14px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#121419" style="max-width:560px;background:#121419;border:1px solid #23262e;border-radius:14px">
<tr><td style="padding:28px 28px 8px;font-family:Arial,Helvetica,sans-serif">
<p style="margin:0 0 18px;font-size:12px;letter-spacing:3px;color:#e9c46a">${esc(eyebrow)}</p>
${paragraphs}
</td></tr>
<tr><td style="padding:8px 28px 26px;font-family:Arial,Helvetica,sans-serif;border-top:1px solid #23262e">
<p style="margin:16px 0 0;font-size:13px;line-height:1.5;color:#9a9ea8">GOLIDE &middot; <a href="https://golidee.com" style="color:#e9c46a;text-decoration:none">golidee.com</a><br>Reply to this email to reach us.</p>
</td></tr></table>
</td></tr></table></body></html>`;
}

// ----------------------------------------------------------------- send ----

export async function sendMail(env, { to, subject, body }) {
  if (!env.RESEND_API_KEY) throw new Error("email sending is not set up yet (RESEND_API_KEY missing)");
  const address = clean(to).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) throw new Error("enter a valid email address");
  if (!clean(subject)) throw new Error("subject is required");
  if (!clean(body)) throw new Error("message is empty");
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({
      from: MAIL_FROM, to: [address], reply_to: MAIL_ADDRESS, subject: clean(subject),
      html: emailHtml({ subject, body }), text: clean(body) + "\n\nGOLIDE · golidee.com",
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`email was not sent: ${data.message || response.status}`);
  return { id: clean(data.id), to: address };
}

// -------------------------------------------------------------- storage ----

async function threadFor(db, address, subject) {
  const existing = await db.prepare(`SELECT id FROM inbox_threads WHERE platform='email' AND external_thread_id=?`).bind(address).first();
  const stamp = now();
  if (existing) {
    await db.prepare(`UPDATE inbox_threads SET status='open', subject=?, last_message_at=?, updated_at=? WHERE id=?`)
      .bind(subject, stamp, stamp, existing.id).run();
    return existing.id;
  }
  const id = crypto.randomUUID();
  await db.prepare(`INSERT INTO inbox_threads (id,platform,external_thread_id,account_id,participant_ref,subject,status,last_message_at,created_at,updated_at)
    VALUES (?, 'email', ?, ?, ?, ?, 'open', ?, ?, ?)`).bind(id, address, MAIL_ADDRESS, address, subject, stamp, stamp, stamp).run();
  return id;
}

async function addMessage(db, threadId, direction, body, externalId) {
  await db.prepare(`INSERT INTO inbox_messages (id,thread_id,external_message_id,direction,body,created_at) VALUES (?,?,?,?,?,?)`)
    .bind(crypto.randomUUID(), threadId, externalId || crypto.randomUUID(), direction, body.slice(0, 20000), now()).run();
}

export async function sendAndRecord(env, payload) {
  const sent = await sendMail(env, payload);
  const threadId = await threadFor(env.DB, sent.to, clean(payload.subject));
  await addMessage(env.DB, threadId, "outbound", clean(payload.body), sent.id);
  return { status: "sent", thread_id: threadId, ...sent };
}

export async function closeThread(db, id) {
  await db.prepare(`UPDATE inbox_threads SET status='closed', updated_at=? WHERE id=?`).bind(now(), id).run();
}

// -------------------------------------------------------------- receive ----

function decodeQP(text) {
  const bytes = [];
  const soft = text.replace(/=\r?\n/g, "");
  for (let i = 0; i < soft.length; i++) {
    if (soft[i] === "=" && /^[0-9A-F]{2}$/i.test(soft.slice(i + 1, i + 3))) { bytes.push(parseInt(soft.slice(i + 1, i + 3), 16)); i += 2; }
    else bytes.push(soft.charCodeAt(i) & 0xff);
  }
  return new TextDecoder().decode(new Uint8Array(bytes));
}

function decodeB64(text) {
  try {
    const bin = atob(text.replace(/\s+/g, ""));
    return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)));
  } catch { return ""; }
}

function splitPart(raw) {
  const at = raw.search(/\r?\n\r?\n/);
  const head = at < 0 ? raw : raw.slice(0, at);
  const body = at < 0 ? "" : raw.slice(at).replace(/^\r?\n\r?\n/, "");
  const headers = {};
  for (const line of head.replace(/\r?\n[ \t]+/g, " ").split(/\r?\n/)) {
    const i = line.indexOf(":");
    if (i > 0) headers[line.slice(0, i).trim().toLowerCase()] = line.slice(i + 1).trim();
  }
  return { headers, body };
}

function partText(part) {
  const type = (part.headers["content-type"] || "text/plain").toLowerCase();
  const encoding = (part.headers["content-transfer-encoding"] || "").toLowerCase();
  if (type.startsWith("multipart/")) {
    const boundary = /boundary="?([^";]+)"?/i.exec(part.headers["content-type"] || "")?.[1];
    if (!boundary) return "";
    const pieces = part.body.split("--" + boundary).slice(1).filter((p) => !p.startsWith("--")).map(splitPart);
    const plain = pieces.find((p) => (p.headers["content-type"] || "text/plain").toLowerCase().startsWith("text/plain"));
    const chosen = plain || pieces.find((p) => (p.headers["content-type"] || "").toLowerCase().startsWith("multipart/"))
      || pieces.find((p) => (p.headers["content-type"] || "").toLowerCase().startsWith("text/html"));
    return chosen ? partText(chosen) : "";
  }
  let text = part.body;
  if (encoding === "quoted-printable") text = decodeQP(text);
  else if (encoding === "base64") text = decodeB64(text);
  if (type.startsWith("text/html")) {
    text = text.replace(/<style[\s\S]*?<\/style>/gi, "").replace(/<br\s*\/?>/gi, "\n").replace(/<\/p>/gi, "\n\n")
      .replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
  }
  return text;
}

// Keep the new words only: drop the quoted earlier conversation.
export function newText(text) {
  const lines = String(text).replace(/\r/g, "").split("\n");
  const out = [];
  for (const line of lines) {
    if (/^On .+wrote:\s*$/.test(line) || /^-{2,}\s*Original Message/i.test(line) || /^From: .+/.test(line) && out.length) break;
    if (line.startsWith(">")) continue;
    out.push(line);
  }
  return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

export function parseEmail(raw) {
  const top = splitPart(raw);
  return { subject: top.headers.subject || "(no subject)", messageId: top.headers["message-id"] || "", text: newText(partText(top)) };
}

export async function receiveMail(message, env) {
  const raw = await new Response(message.raw).text();
  const parsed = parseEmail(raw);
  const from = clean(/<([^>]+)>/.exec(message.from)?.[1] || message.from).toLowerCase();
  const threadId = await threadFor(env.DB, from, decodeHeader(parsed.subject));
  await addMessage(env.DB, threadId, "inbound", parsed.text || "(no text)", parsed.messageId);
  if (env.EMAIL_FORWARD_TO) {
    try { await message.forward(env.EMAIL_FORWARD_TO); } catch (e) { console.log(JSON.stringify({ forward: "failed", error: String(e) })); }
  }
}

// Encoded subjects: =?UTF-8?B?...?= / =?UTF-8?Q?...?=
function decodeHeader(value) {
  return String(value).replace(/=\?([^?]+)\?([BQ])\?([^?]*)\?=/gi, (_, cs, kind, text) =>
    kind.toUpperCase() === "B" ? decodeB64(text) : decodeQP(text.replace(/_/g, " ")));
}

// The record-needed script, re-sent on demand from Studio (same look as the engine's).
export function scriptEmailHtml({ title, label, window, script, link }) {
  const rows = String(script).split("\n").map((row) => row.trim()).filter(Boolean).map((row) =>
    /^\[.+\]$/.test(row)
      ? `<p style="margin:18px 0 6px;font-size:12px;letter-spacing:2px;color:#e9c46a">${esc(row.slice(1, -1))}</p>`
      : `<p style="margin:0 0 10px;font-size:17px;line-height:1.5;color:#ecedef">${esc(row)}</p>`).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark"></head>
<body style="margin:0;padding:0;background:#0b0c10" bgcolor="#0b0c10">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#0b0c10" style="background:#0b0c10"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#121419" style="max-width:600px;background:#121419;border:1px solid #23262e;border-radius:14px"><tr><td style="padding:26px;font-family:Arial,Helvetica,sans-serif">
<p style="margin:0 0 8px;font-size:12px;letter-spacing:2px;color:#e9c46a">${esc(label.toUpperCase())} &middot; RECORD ${esc(window)}</p>
<h2 style="margin:0 0 16px;font-weight:600;color:#ecedef">${esc(title)}</h2>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tr><td width="3" bgcolor="#e9c46a" style="background:#e9c46a"></td><td style="padding:4px 0 4px 16px">${rows}</td></tr></table>
<p style="margin:24px 0 0"><a href="${esc(link)}" style="display:inline-block;background:#e9c46a;color:#0b0c10;padding:12px 22px;border-radius:999px;font-weight:700;text-decoration:none">Upload recording</a></p>
</td></tr></table></td></tr></table></body></html>`;
}

export async function emailScript(env, job) {
  if (!env.RESEND_API_KEY) throw new Error("email sending is not set up yet (RESEND_API_KEY missing)");
  if (!env.OWNER_EMAIL) throw new Error("OWNER_EMAIL is not set");
  if (!clean(job.script)) throw new Error("this job has no script yet");
  const long = job.format === "long";
  const label = long ? "Long video" : "Short";
  const window = long ? "3:30 to 5:00" : "0:30 to 1:30";
  const link = `https://studio.golidee.com/#job-${job.job_id}`;
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({
      from: MAIL_FROM, to: [env.OWNER_EMAIL], subject: `Record today: [${label}] ${clean(job.title)}`.slice(0, 180),
      html: scriptEmailHtml({ title: clean(job.title), label, window, script: job.script, link }),
      text: `${label} script. Record it in your own voice, ${window}.\n\n${job.script}\n\nUpload your recording: ${link}`,
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`email was not sent: ${data.message || response.status}`);
  return { status: "sent", to: env.OWNER_EMAIL };
}
