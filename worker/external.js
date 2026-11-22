// External videos (owner direction 2026-11-03): any day, any time, outside the schedule.
//
// The owner uploads his own recording and pastes the script he read (so the words can be
// cross-checked against the audio). Optional: a link for the description and captions, and a
// reference (a picture of the real thing, or a link to it). The engine builds the video from
// these instead of its own script, then publishes it as soon as it is built.

export const CHANNEL_ID = "UCqaXVBSBz7iQsRHOupKt-3w";

const LONG_SCORES = {
  click_promise: 9, thumbnail_title_fit: 9, narrative_engine: 9, visual_depth: 9, evidence_strength: 8,
  retention_design: 9, broad_relevance: 8, novelty: 8, revenue_fit: 7,
};

const SHORT_SCORES = {
  scroll_stop: 9, visual_payoff: 9, curiosity_gap: 9, retention_design: 9, broad_relevance: 8,
  evidence_strength: 8, novelty: 8, replay_or_loop: 8, revenue_fit: 6,
};

// 2026-11-17 (owner): the styles a Goli video may use. Free ones (no model call) listed by key; paid ones (a model
// writes the scene) with how many, 0 to 20. Anything else is dropped. Null when nothing usable was sent.
const FREE_LOOKS = ["puppets", "white", "layers", "circuit", "glass", "xray", "blueprint"];
const PAID_LOOKS = [];   // 2026-11-18: every style is a free kit now
export function cleanLooks(value) {
  if (!value || typeof value !== "object") return null;
  const free = Array.isArray(value.free) ? [...new Set(value.free.map(String).filter((k) => FREE_LOOKS.includes(k)))] : [...FREE_LOOKS];
  const paid = {};
  for (const [key, n] of Object.entries(value.paid && typeof value.paid === "object" ? value.paid : {})) {
    const count = Math.max(0, Math.min(20, Math.round(Number(n) || 0)));
    if (PAID_LOOKS.includes(key) && count) paid[key] = count;
  }
  return { free, paid };
}

function text(value, max = 20000) {
  return String(value ?? "").trim().slice(0, max);
}

function lusakaStamp(date) {
  const iso = new Date(date.getTime() + 2 * 3600 * 1000).toISOString(); // Africa/Lusaka, UTC+2
  return iso.slice(0, 10) + "-" + iso.slice(11, 13) + iso.slice(14, 16);
}

export function buildExternalSpec(payload, now = new Date()) {
  const title = text(payload.title, 100);
  const script = text(payload.script);
  const voice = text(payload.voice_ref);
  const link = text(payload.link, 600);
  const referenceRef = text(payload.reference_ref);
  const referenceLink = text(payload.reference_link, 600);
  if (script.split(/\s+/).filter(Boolean).length < 8) throw new Error("Paste the script you recorded.");
  if (!voice.startsWith("r2://")) throw new Error("Upload your recording first.");
  for (const value of [link, referenceLink]) {
    if (value && !/^https?:\/\/\S+$/.test(value)) throw new Error("Links must start with https://");
  }
  if (referenceRef && !referenceRef.startsWith("r2://")) throw new Error("The reference picture did not finish uploading.");
  // 2026-11-17 (owner): a Short or a long video, in Goli or Inkee (the illustration engine)
  const format = payload.format === "long" ? "long" : "short";
  // Stickman (owner 2026-11-17): the third style, for Shorts (3D Shorts engine, 2026-11-22) and long videos (ReachMora)
  // "stickman_goli": Goli beside the Stickman scene as the explainer (owner's channel), chosen per video
  let style = ["goli", "illustration", "stickman", "stickman_goli"].includes(payload.video_style) ? payload.video_style : "goli";
  // Stickman is on Shorts again (owner 2026-11-18, after the fast-cut Elon test); Stickman + Goli stays long only
  if (style === "stickman_goli" && format !== "long") style = "stickman";
  const id = "golide-external-" + lusakaStamp(now);
  const looks = style === "goli" ? cleanLooks(payload.looks) : null;
  return {
    id,
    ...(looks ? { looks } : {}),
    studio_managed: true,
    format,
    video_style: style,
    purpose: "external-video",
    title: title || "External video · " + lusakaStamp(now).slice(0, 10),
    brief: "A video built from the owner's own script and recording.",
    external: { title, script, link, reference_ref: referenceRef, reference_link: referenceLink },
    owner_voice_media_ref: voice,
    owner_voice_required: true,
    budget_class: "scheduled",   // the engine accepts scheduled or independent only; this uses the normal short allocation
    generate_at: now.toISOString(),
    max_cost_usd: 6.0,
    production_authorized: true,
    output_destination: "render-and-upload",
    concept: { family: "owner-video", promise: "The owner's own script, illustrated", scores: format === "long" ? LONG_SCORES : SHORT_SCORES },
    platform_demand: { verdict: "pass", reason: "owner-started external video" },
    generation_parameters: {
      brand_preset: "golide-editorial", voice: "owner-recording-only", pacing: "fast", visual_density: 4,
      motion_intensity: 4, annotation_density: 3, avatar_frequency: 2, sound_design: 3, image_change_bias: 4,
      editorial_manifest: "beat-motion-audio-v1", schedule_rule: "studio-external-video",
    },
    music: { mood: "curious-tension" },
    avatar_reference_images: [],
    // Published as soon as it is built: a time already passed means "now" to the uploader.
    release: { approved: true, channel_id: CHANNEL_ID, scheduled_at: now.toISOString().replace(/\.\d{3}Z$/, "Z") },
  };
}
