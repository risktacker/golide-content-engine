// Free transcript reader (owner 2026-11-22): the Studio's own Worker reads YouTube's captions for a video, the
// way free transcript sites do, so the engine can model a video without a paid service. Three routes, first win:
// the watch page's transcript panel, then the caption tracks from the Android and web players.

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36";

export function videoId(input) {
  const s = String(input || "").trim();
  if (/^[A-Za-z0-9_-]{11}$/.test(s)) return s;
  const m = s.match(/(?:v=|youtu\.be\/|shorts\/|embed\/|live\/)([A-Za-z0-9_-]{11})/);
  return m ? m[1] : "";
}

const clean = (t) => String(t || "").replace(/&amp;/g, "&").replace(/&#39;/g, "'").replace(/&quot;/g, '"')
  .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\[(music|applause|laughter)\]/gi, " ").replace(/\s+/g, " ").trim();

async function watchPage(id) {
  const r = await fetch(`https://www.youtube.com/watch?v=${id}&hl=en&bpctr=9999999999&has_verified=1`, {
    headers: { "user-agent": UA, "accept-language": "en-US,en;q=0.9", cookie: "CONSENT=YES+1; SOCS=CAI" },
  });
  return r.ok ? await r.text() : "";
}

function between(html, re) { const m = html.match(re); return m ? m[1] : ""; }

async function fromPanel(id, html) {
  const params = between(html, /"getTranscriptEndpoint":\{"params":"([^"]+)"/);
  if (!params) return "";
  const version = between(html, /"INNERTUBE_CONTEXT_CLIENT_VERSION":"([^"]+)"/) || "2.20251120.00.00";
  const key = between(html, /"INNERTUBE_API_KEY":"([^"]+)"/);
  const r = await fetch(`https://www.youtube.com/youtubei/v1/get_transcript${key ? `?key=${key}` : ""}`, {
    method: "POST",
    headers: { "content-type": "application/json", "user-agent": UA, origin: "https://www.youtube.com" },
    body: JSON.stringify({ context: { client: { clientName: "WEB", clientVersion: version, hl: "en" } }, params }),
  });
  if (!r.ok) return "";
  const out = [];
  (function walk(n) {
    if (!n || typeof n !== "object") return;
    if (n.transcriptSegmentRenderer) {
      out.push((n.transcriptSegmentRenderer.snippet?.runs || []).map((x) => x.text).join(""));
      return;
    }
    for (const v of Object.values(n)) walk(v);
  })(await r.json());
  return clean(out.join(" "));
}

async function fromTrack(url) {
  if (!url) return "";
  const r = await fetch(url.replace(/&fmt=[^&]*/, "") + "&fmt=json3", { headers: { "user-agent": UA } });
  if (!r.ok) return "";
  const body = await r.text();
  if (!body) return "";
  try {
    const data = JSON.parse(body);
    return clean((data.events || []).flatMap((e) => (e.segs || []).map((s) => s.utf8)).join(" "));
  } catch {
    return clean(body.replace(/<[^>]+>/g, " "));
  }
}

function pickTrack(tracks) {
  const list = (tracks || []).filter((t) => t?.baseUrl);
  return (list.find((t) => /^en/.test(t.languageCode) && t.kind !== "asr") || list.find((t) => /^en/.test(t.languageCode))
    || list[0] || {}).baseUrl || "";
}

async function fromAndroid(id) {
  const r = await fetch("https://www.youtube.com/youtubei/v1/player", {
    method: "POST",
    headers: { "content-type": "application/json", "user-agent": "com.google.android.youtube/20.10.38 (Linux; U; Android 14) gzip" },
    body: JSON.stringify({ videoId: id, context: { client: { clientName: "ANDROID", clientVersion: "20.10.38", androidSdkVersion: 34, hl: "en" } } }),
  });
  if (!r.ok) return "";
  const data = await r.json();
  return fromTrack(pickTrack(data?.captions?.playerCaptionsTracklistRenderer?.captionTracks));
}

async function fromWebTracks(html) {
  const raw = between(html, /"captionTracks":(\[.*?\])(?:,"audioTracks"|,"translationLanguages")/);
  if (!raw) return "";
  try { return fromTrack(pickTrack(JSON.parse(raw))); } catch { return ""; }
}

export async function transcript(input) {
  const id = videoId(input);
  if (!id) return { ok: false, error: "not a YouTube link", tried: [] };
  const tried = [];
  let html = "";
  const routes = [
    ["panel", async () => { html = html || await watchPage(id); return fromPanel(id, html); }],
    ["android", () => fromAndroid(id)],
    ["web-tracks", async () => { html = html || await watchPage(id); return fromWebTracks(html); }],
  ];
  for (const [name, run] of routes) {
    try {
      const text = await run();
      tried.push({ route: name, words: text ? text.split(" ").length : 0 });
      if (text && text.split(" ").length > 30) return { ok: true, video_id: id, route: name, words: text.split(" ").length, text, tried };
    } catch (e) {
      tried.push({ route: name, error: String(e?.message || e).slice(0, 160) });
    }
  }
  return { ok: false, video_id: id, error: "no transcript from any route", tried };
}
