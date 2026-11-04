// External videos (owner direction 2026-11-03): any day, any time, outside the schedule.
//
// The owner uploads his own recording and pastes the script he read (so the words can be
// cross-checked against the audio). Optional: a link for the description and captions, and a
// reference (a picture of the real thing, or a link to it). The engine builds the video from
// these instead of its own script, then publishes it as soon as it is built.

export const CHANNEL_ID = "UCqaXVBSBz7iQsRHOupKt-3w";

const SHORT_SCORES = {
  scroll_stop: 9, visual_payoff: 9, curiosity_gap: 9, retention_design: 9, broad_relevance: 8,
  evidence_strength: 8, novelty: 8, replay_or_loop: 8, revenue_fit: 6,
};

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
  const id = "golide-external-" + lusakaStamp(now);
  return {
    id,
    studio_managed: true,
    format: "short",
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
    concept: { family: "owner-video", promise: "The owner's own script, illustrated", scores: SHORT_SCORES },
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
