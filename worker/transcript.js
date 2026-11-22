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
  const html = r.ok ? await r.text() : "";
  note(`watch ${r.status} ${html.length} panel:${/getTranscriptEndpoint/.test(html)} tracks:${/captionTracks/.test(html)} playability:${between(html, /"playabilityStatus":\{"status":"([A-Z_]+)"/)}`);
  return html;
}

function between(html, re) { const m = html.match(re); return m ? m[1] : ""; }

async function fromPanel(id, html) {
  const params = between(html, /"getTranscriptEndpoint":\{"params":"([^"]+)"/);
  if (!params) return "";
  const version = between(html, /"INNERTUBE_CONTEXT_CLIENT_VERSION":"([^"]+)"/) || "2.20251120.00.00";
  const key = between(html, /"INNERTUBE_API_KEY":"([^"]+)"/);
  const r = await fetch(`https://www.youtube.com/youtubei/v1/get_transcript${key ? `?key=${key}` : ""}`, {
    method: "POST",
    headers: { "content-type": "application/json", "user-agent": UA, origin: "https://www.youtube.com",
      "x-goog-visitor-id": between(html, /"VISITOR_DATA":"([^"]+)"/), "x-youtube-client-name": "1", "x-youtube-client-version": version },
    body: JSON.stringify({ context: { client: { clientName: "WEB", clientVersion: version, hl: "en",
      visitorData: between(html, /"VISITOR_DATA":"([^"]+)"/) || undefined } }, params }),
  });
  note(`get_transcript ${r.status}`);
  if (!r.ok) { note((await r.text()).slice(0, 120)); return ""; }
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
  const body = r.ok ? await r.text() : "";
  note(`track ${r.status} ${body.length} ${/[?&]kind=asr/.test(url) ? "asr" : ""} pot:${/[?&]pot=/.test(url)} exp:${between(url, /[?&]exp=([^&]+)/)}`);
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

const CLIENTS = {
  ios: [{ clientName: "IOS", clientVersion: "20.10.4", deviceMake: "Apple", deviceModel: "iPhone16,2", osName: "iPhone", osVersion: "18.3.2.22D82" },
    "com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)"],
  tv_embed: [{ clientName: "TVHTML5_SIMPLY_EMBEDDED_PLAYER", clientVersion: "2.0" }, UA],
  web_embed: [{ clientName: "WEB_EMBEDDED_PLAYER", clientVersion: "1.20251120.01.00" }, UA],
  mweb: [{ clientName: "MWEB", clientVersion: "2.20251120.01.00" }, "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"],
  tv: [{ clientName: "TVHTML5", clientVersion: "7.20251120.10.00" }, "Mozilla/5.0 (ChromiumStylePlatform) Cobalt/Version"],
};

async function fromClient(id, name) {
  const [client, agent] = CLIENTS[name];
  const body = { videoId: id, context: { client: { ...client, hl: "en" } }, contentCheckOk: true, racyCheckOk: true };
  if (/EMBED/.test(client.clientName)) body.context.thirdParty = { embedUrl: `https://www.youtube.com/embed/${id}` };
  const r = await fetch("https://www.youtube.com/youtubei/v1/player?prettyPrint=false", {
    method: "POST", headers: { "content-type": "application/json", "user-agent": agent, origin: "https://www.youtube.com" },
    body: JSON.stringify(body),
  });
  const data = r.ok ? await r.json() : {};
  const tr = data?.captions?.playerCaptionsTracklistRenderer?.captionTracks || [];
  note(`${name} ${r.status} ${data?.playabilityStatus?.status} tracks:${tr.length}`);
  return fromTrack(pickTrack(tr));
}

async function fromAndroid(id) {
  const r = await fetch("https://www.youtube.com/youtubei/v1/player", {
    method: "POST",
    headers: { "content-type": "application/json", "user-agent": "com.google.android.youtube/20.10.38 (Linux; U; Android 14) gzip" },
    body: JSON.stringify({ videoId: id, context: { client: { clientName: "ANDROID", clientVersion: "20.10.38", androidSdkVersion: 34, hl: "en" } } }),
  });
  const data = r.ok ? await r.json() : {};
  const tr = data?.captions?.playerCaptionsTracklistRenderer?.captionTracks || [];
  note(`android ${r.status} ${data?.playabilityStatus?.status} tracks:${tr.length} ${tr.map((t) => t.languageCode + (t.kind || "")).join(",")}`);
  return fromTrack(pickTrack(data?.captions?.playerCaptionsTracklistRenderer?.captionTracks));
}

async function fromWebTracks(html) {
  const raw = between(html, /"captionTracks":(\[.*?\])(?:,"audioTracks"|,"translationLanguages")/);
  if (!raw) return "";
  try { return fromTrack(pickTrack(JSON.parse(raw))); } catch { return ""; }
}

const NOTE = [];
const note = (x) => { if (NOTE.length < 20) NOTE.push(String(x).slice(0, 140)); };

export async function transcript(input) {
  NOTE.length = 0;
  const id = videoId(input);
  if (!id) return { ok: false, error: "not a YouTube link", tried: [] };
  const tried = [];
  let html = "";
  const routes = [
    ["panel", async () => { html = html || await watchPage(id); return fromPanel(id, html); }],
    ["android", () => fromAndroid(id)],
    ["web-tracks", async () => { html = html || await watchPage(id); return fromWebTracks(html); }],
    ...Object.keys(CLIENTS).map((name) => [name, () => fromClient(id, name)]),
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
  return { ok: false, video_id: id, error: "no transcript from any route", tried, notes: [...NOTE] };
}
