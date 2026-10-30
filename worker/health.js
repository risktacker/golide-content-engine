// Daily health email (20:00 Lusaka).
//
// One email a day that says, platform by platform, what went out today and
// what needs the owner. Built inside the Worker from D1, so it still arrives
// when GitHub Actions never started (a failed dispatch is itself reported).

import { sizeLabel } from "./storage.js";
import { brandShell, MAIL_FROM, INK, MUTED, GOLD_TEXT } from "./mail.js";

const LUSAKA_OFFSET_H = 2;
const PLATFORMS = ["instagram", "facebook", "linkedin", "x", "youtube"];
const NAMES = { instagram: "Instagram", facebook: "Facebook", linkedin: "LinkedIn", x: "X", youtube: "YouTube" };
const SHORT_DAYS = [0, 1, 3, 5];   // Sun, Mon, Wed, Fri (Lusaka)
const LONG_DAYS = [2, 4, 6];       // Tue, Thu, Sat
const GREEN = "#2e7d4f", RED = "#b4413b", AMBER = "#b07a12";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const iso = (d) => d.toISOString();
const short = (s, n = 160) => { const t = String(s ?? "").replace(/\s+/g, " ").trim(); return t.length > n ? t.slice(0, n - 1) + "…" : t; };

export function lusakaDay(now) {
  const local = new Date(now.getTime() + LUSAKA_OFFSET_H * 3600e3);
  const date = local.toISOString().slice(0, 10);
  const start = new Date(Date.parse(date + "T00:00:00Z") - LUSAKA_OFFSET_H * 3600e3);
  return { date, weekday: local.getUTCDay(), start, end: new Date(start.getTime() + 86400e3) };
}

async function all(db, sql, ...binds) {
  const { results = [] } = await db.prepare(sql).bind(...binds).all();
  return results;
}

async function first(db, sql, ...binds) {
  return (await db.prepare(sql).bind(...binds).first()) || null;
}

function variantLine(v) {
  const name = NAMES[v.platform] || v.platform;
  if (v.status === "published" && v.last_error) return { mark: "warn", text: `${name}: published, but ${short(v.last_error)}` };
  if (v.status === "published") return { mark: "ok", text: `${name}: published` };
  if (v.status === "failed") return { mark: "bad", text: `${name}: failed. ${short(v.last_error || "no reason given")}` };
  return { mark: "wait", text: `${name}: not out yet (${v.status})` };
}

// Gather everything for the report. Pure data, no formatting.
export async function collectHealth(db, now = new Date(), storage = null) {
  const day = lusakaDay(now);
  const issues = [];
  const sections = [];
  const automation = await first(db, `SELECT enabled FROM automation_control WHERE id=1`);
  const enabled = Number(automation?.enabled || 0) === 1;
  if (!enabled) issues.push("Automation is switched OFF in Studio, so nothing is posting on its own.");

  // 1. Static posts: 08:30 (post-a) and 17:30 (post-b).
  for (const [slot, label, hour] of [["a", "08:30 post", 8.5], ["b", "17:30 post", 17.5]]) {
    const id = `golide-post-${day.date}-post-${slot}`;
    const post = await first(db, `SELECT id,title,status FROM content_posts WHERE id=?`, id);
    const due = now.getTime() >= day.start.getTime() + (hour + 0.75) * 3600e3;
    if (!post) {
      if (enabled && due) {
        issues.push(`The ${label} was never created.`);
        sections.push({ title: label, subtitle: "Never created", lines: [{ mark: "bad", text: "No post was made for this slot. Check the content scheduler run." }] });
      }
      continue;
    }
    const variants = await all(db, `SELECT platform,status,last_error FROM social_variants WHERE post_id=? ORDER BY platform`, id);
    const lines = variants.map(variantLine);
    for (const l of lines) if (l.mark !== "ok") issues.push(`${label}, ${l.text}`);
    sections.push({ title: label, subtitle: post.title, lines });
  }

  // 2. Videos made today and their social copies.
  const kind = SHORT_DAYS.includes(day.weekday) ? "short" : LONG_DAYS.includes(day.weekday) ? "long" : "";
  const jobs = await all(db, `SELECT job_id,format,title,status,stage,error,scheduled_at,release_url,updated_at FROM production_jobs
    WHERE archived_at IS NULL AND (job_id LIKE ? OR (scheduled_at>=? AND scheduled_at<?) OR (updated_at>=? AND updated_at<?)) ORDER BY job_id`,
    `%-${day.date}`, iso(day.start), iso(day.end), iso(day.start), iso(day.end));
  if (kind && enabled && !jobs.some((j) => j.format === kind)) {
    issues.push(`Today's ${kind === "long" ? "long video" : "short"} was never started.`);
    sections.push({ title: kind === "long" ? "Long video" : "Short", subtitle: "Never started", lines: [{ mark: "bad", text: "No production job exists for today. Check the production scheduler run." }] });
  }
  for (const job of jobs) {
    const label = job.format === "long" ? "Long video" : "Short";
    const lines = [];
    if (job.status === "waiting_owner_voice") { lines.push({ mark: "wait", text: "Script is ready. Waiting for your recording." }); issues.push(`Record today's ${label.toLowerCase()}: ${job.title || job.job_id}.`); }
    else if (job.status === "failed") { lines.push({ mark: "bad", text: `Failed at ${job.stage}. ${short(job.error || "")}` }); issues.push(`${label} failed at ${job.stage}.`); }
    else if (["scheduled", "completed", "published"].includes(job.status)) {
      lines.push({ mark: "ok", text: `YouTube: ${job.status === "scheduled" ? "uploaded and scheduled" : "published"}` });
      if (job.error) { lines.push({ mark: "warn", text: short(job.error) }); issues.push(`${label}: ${short(job.error)}`); }
    }
    else lines.push({ mark: "wait", text: `In progress (${job.status}, ${job.stage})` });
    const social = await all(db, `SELECT v.platform,v.status,v.last_error,p.scheduled_at FROM content_posts p JOIN social_variants v ON v.post_id=p.id
      WHERE p.id LIKE ? AND v.platform<>'youtube' ORDER BY v.platform`, `${job.job_id}%`);
    for (const v of social) {
      const l = variantLine(v);
      // 2026-10-16: the 19:30 long video reaches Facebook, Instagram and LinkedIn in the
      // 20:00 run, minutes after this email. Not out yet within 90 minutes of release
      // is "on its way", not a problem.
      const fresh = v.status !== "published" && v.status !== "failed" && v.scheduled_at
        && now.getTime() - Date.parse(v.scheduled_at) < 90 * 60e3;
      if (fresh) { lines.push({ mark: "wait", text: `${NAMES[v.platform] || v.platform}: going out in the next run` }); continue; }
      lines.push(l);
      if (l.mark !== "ok") issues.push(`${label}, ${l.text}`);
    }
    sections.push({ title: label, subtitle: job.title || job.job_id, lines });
  }

  // 3. Older recordings still owed (any day).
  const owed = await all(db, `SELECT job_id,format,title FROM production_jobs WHERE archived_at IS NULL AND status='waiting_owner_voice' AND job_id NOT LIKE ?`, `%-${day.date}`);
  for (const job of owed) issues.push(`Still waiting for your recording: ${job.title || job.job_id}.`);

  // 3b. Inbox (2026-10-31): only real opportunities and real people need you; pitches and spam don't.
  const mail = await all(db, `SELECT participant_ref,subject,label FROM inbox_threads
    WHERE status='open' AND unread=1 AND label IN ('opportunity','message')`).catch(() => []);
  for (const m of mail) {
    issues.push(m.label === "opportunity"
      ? `Opportunity in the inbox: ${m.subject || m.participant_ref}.`
      : `Unanswered message from ${m.participant_ref}.`);
  }

  // 4. Anything from the last 3 days still failed, partial or stuck.
  const stuck = await all(db, `SELECT id,title,status FROM content_posts
    WHERE COALESCE(scheduled_at,created_at)>=? AND COALESCE(scheduled_at,created_at)<?
      AND (status IN ('failed','partial') OR (status='publishing' AND updated_at<strftime('%Y-%m-%dT%H:%M:%fZ','now','-45 minutes')))`,
    iso(new Date(day.start.getTime() - 3 * 86400e3)), iso(day.start));
  for (const p of stuck) issues.push(`Earlier post still ${p.status}: ${p.title || p.id}.`);

  // 5. Scheduler dispatches that GitHub refused in the last 24 hours.
  const dispatches = await all(db, `SELECT workflow,detail,at FROM cron_runs WHERE ok=0 AND at>=?`, iso(new Date(now.getTime() - 86400e3)))
    .catch(() => []);
  for (const d of dispatches) issues.push(`The ${d.workflow} run could not be started (${short(d.detail, 80)}).`);

  // 6. Logins that expire without a refresh token.
  const tokens = await all(db, `SELECT platform,expires_at,refresh_token_enc FROM social_oauth_tokens`);
  const x = await first(db, `SELECT expires_at FROM x_oauth_tokens WHERE id=1`);
  const connected = new Set(tokens.map((t) => t.platform).concat(x ? ["x"] : []));
  for (const p of PLATFORMS) if (!connected.has(p)) issues.push(`${NAMES[p]} is not connected.`);
  for (const t of tokens) {
    if (t.refresh_token_enc || !t.expires_at) continue;
    const days = Math.floor((Date.parse(t.expires_at) - now.getTime()) / 86400e3);
    if (days < 0) issues.push(`${NAMES[t.platform] || t.platform} login has expired. Reconnect it in Studio.`);
    else if (days <= 7) issues.push(`${NAMES[t.platform] || t.platform} login expires in ${days} day${days === 1 ? "" : "s"}. Reconnect it in Studio.`);
  }

  if (storage && storage.status === "ok") {
    sections.push({ title: "Storage", subtitle: `${storage.files} temporary file${storage.files === 1 ? "" : "s"}, ${sizeLabel(storage.bytes)}`, lines: [
      { mark: "ok", text: storage.deleted ? `Cleaned ${storage.deleted} file${storage.deleted === 1 ? "" : "s"} older than 72 hours (${sizeLabel(storage.freed_bytes)} freed)` : "Nothing older than 72 hours" },
    ] });
    if (storage.bytes > 5 * 1024 ** 3) issues.push(`Temporary storage is at ${sizeLabel(storage.bytes)}, over half the free 10 GB.`);
  }
  return { date: day.date, enabled, issues, sections };
}

const MARKS = {
  ok: ["&#10003;", GREEN], warn: ["!", AMBER], bad: ["&#10007;", RED], wait: ["&#8230;", MUTED],
};

export function renderHealth(report) {
  const n = report.issues.length;
  const pretty = new Date(report.date + "T12:00:00Z").toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });
  const subject = n ? `GOLIDE daily: ${n} thing${n === 1 ? "" : "s"} need${n === 1 ? "s" : ""} you` : "GOLIDE daily: all good";
  const headline = n ? `${n} thing${n === 1 ? "" : "s"} need${n === 1 ? "s" : ""} you` : "Everything went out. Nothing needs you.";

  const issueHtml = n ? `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 26px;background:#fbf3f2;border-radius:10px"><tr><td style="padding:16px 18px">
${report.issues.map((i) => `<p style="margin:0 0 8px;font-size:15px;line-height:1.5;color:${INK}"><span style="color:${RED};font-weight:700">&#8226;</span>&nbsp; ${esc(i)}</p>`).join("")}
</td></tr></table>` : "";

  const sectionHtml = report.sections.map((s) => `
<p style="margin:0 0 2px;color:${GOLD_TEXT};font-size:12px;letter-spacing:2px;font-weight:600">${esc(s.title.toUpperCase())}</p>
<p style="margin:0 0 10px;font-size:15px;line-height:1.4;color:${INK};font-weight:600">${esc(short(s.subtitle, 110))}</p>
${s.lines.map((l) => { const [sym, col] = MARKS[l.mark]; return `<p style="margin:0 0 6px;font-size:14px;line-height:1.5;color:${INK}"><span style="display:inline-block;width:18px;color:${col};font-weight:700">${sym}</span>${esc(l.text)}</p>`; }).join("")}
<div style="height:18px"></div>`).join("");

  const inner = `<p style="color:${GOLD_TEXT};letter-spacing:2px;font-size:12px;margin:0 0 8px;font-weight:600">DAILY HEALTH &middot; ${esc(pretty.toUpperCase())}</p>
<h2 style="margin:0 0 20px;font-weight:600;color:${INK};font-size:22px;line-height:1.3">${esc(headline)}</h2>
${issueHtml}${sectionHtml || `<p style="color:${MUTED};font-size:14px">Nothing was scheduled today.</p>`}
<p style="margin:8px 0 8px"><a href="https://studio.golidee.com/" style="display:inline-block;background:#0b0c10;color:#ffffff;padding:13px 24px;border-radius:999px;font-weight:600;text-decoration:none;font-size:15px">Open Studio</a></p>`;

  const text = [`${headline} (${pretty})`, ""]
    .concat(report.issues.map((i) => `- ${i}`), n ? [""] : [])
    .concat(report.sections.flatMap((s) => [`${s.title}: ${s.subtitle}`, ...s.lines.map((l) => `  ${({ ok: "OK", warn: "!!", bad: "XX", wait: ".." })[l.mark]} ${l.text}`), ""]))
    .concat(["https://studio.golidee.com/"]).join("\n");

  return { subject, html: brandShell({ subject, preheader: n ? report.issues[0] : "Everything went out today.", inner }), text };
}

export async function sendHealthEmail(env, now = new Date(), storage = null) {
  if (!env.RESEND_API_KEY || !env.OWNER_EMAIL) return { status: "skipped", reason: "email not set up" };
  const { subject, html, text } = renderHealth(await collectHealth(env.DB, now, storage));
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({ from: MAIL_FROM, to: [env.OWNER_EMAIL], subject, html, text }),
  });
  const ok = response.ok;
  console.log(JSON.stringify({ health_email: ok ? "sent" : "failed", status: response.status, subject }));
  return { status: ok ? "sent" : "failed", subject };
}
