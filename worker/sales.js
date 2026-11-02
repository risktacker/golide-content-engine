// Sales videos started by hand in Studio (owner direction 2026-11-03).
//
// "A placeholder for sales videos, not the one scheduled by the engine, where I can paste the
// script that I've used for the audio, then you run it and you produce the video for me. And
// the video goes into all those platforms."
//
// Studio writes a production job the engine claims on its next run (started straight away):
// the engine skips topic, research and script writing, and builds from the owner's script
// and recording. The product picture is the owner's own (a book cover), never redrawn.

export const CHANNEL_ID = "UCqaXVBSBz7iQsRHOupKt-3w";
const BUILD_MINUTES = 45; // the build takes 20 to 30 minutes; publishing waits for it

const SHORT_SCORES = {
  scroll_stop: 9, visual_payoff: 9, curiosity_gap: 9, retention_design: 9, broad_relevance: 8,
  evidence_strength: 8, novelty: 8, replay_or_loop: 8, revenue_fit: 6,
};

function text(value, max = 20000) {
  return String(value ?? "").trim().slice(0, max);
}

function lusakaStamp(date) {
  const local = new Date(date.getTime() + 2 * 3600 * 1000); // Africa/Lusaka, UTC+2 all year
  const iso = local.toISOString();
  return iso.slice(0, 10) + "-" + iso.slice(11, 13) + iso.slice(14, 16);
}

export function buildSaleSpec(payload, now = new Date()) {
  const title = text(payload.title, 100);
  const script = text(payload.script);
  const voice = text(payload.voice_ref);
  const link = text(payload.link, 600);
  const cover = text(payload.cover_ref);
  const product = text(payload.product_name, 120) || title;
  if (!title) throw new Error("Give the video a title.");
  if (script.split(/\s+/).filter(Boolean).length < 8) throw new Error("Paste the full script you recorded (at least 8 words).");
  if (!voice.startsWith("r2://")) throw new Error("Upload your recording first.");
  if (link && !/^https:\/\/\S+$/.test(link)) throw new Error("The buy link must start with https://");
  if (cover && !cover.startsWith("r2://")) throw new Error("The cover image upload did not finish; try again.");
  const earliest = new Date(now.getTime() + BUILD_MINUTES * 60 * 1000);
  let publish = earliest;
  if (text(payload.publish_at)) {
    const chosen = new Date(text(payload.publish_at));
    if (Number.isNaN(chosen.getTime())) throw new Error("The publish time is not a valid date.");
    if (chosen > publish) publish = chosen;
  }
  const id = "golide-sale-" + lusakaStamp(now);
  return {
    id,
    studio_managed: true,
    format: "short",
    purpose: "sales-video",
    title,
    brief: `Sales Short for the owner's own product, ${product}, in his own recorded words.`,
    sale: { script, link, cover_ref: cover, product_name: product },
    owner_voice_media_ref: voice,
    owner_voice_required: true,
    budget_class: "manual",
    generate_at: now.toISOString(),
    max_cost_usd: 6.0,
    production_authorized: true,
    output_destination: "render-and-upload",
    concept: { family: "owner-product", promise: "The owner's product, shown for real", scores: SHORT_SCORES },
    platform_demand: { verdict: "pass", reason: "owner-started sales video" },
    generation_parameters: {
      brand_preset: "golide-editorial", voice: "owner-recording-only", pacing: "fast", visual_density: 4,
      motion_intensity: 4, annotation_density: 3, avatar_frequency: 2, sound_design: 3, image_change_bias: 4,
      editorial_manifest: "beat-motion-audio-v1", schedule_rule: "studio-sales-video",
    },
    music: { mood: "curious-tension" },
    avatar_reference_images: [],
    release: { approved: true, channel_id: CHANNEL_ID, scheduled_at: publish.toISOString().replace(/\.\d{3}Z$/, "Z") },
  };
}
