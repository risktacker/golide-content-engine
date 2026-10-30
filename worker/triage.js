// Inbox triage (owner direction 2026-10-31): "as growth is coming I expect a lot of garbage
// in the inbox, so knowing what is garbage and opportunity can be hard."
//
// Every inbound thread gets one label with a one-line reason:
//   opportunity  someone offers to PAY us or work with us on something specific
//   message      a real person writing to us (a viewer, a customer, a friend)
//   pitch        someone selling us a service or asking for a cut (growth agencies, "results-based")
//   spam         automated mail, notifications, junk
// The cheap text model decides (OPENAI_API_KEY); without it, or if it fails, the rules below do.

const LABELS = ["opportunity", "message", "pitch", "spam"];
const MODEL = "gpt-5.6-luna";

const PITCH = [
  /results?[- ]based/i, /no upfront/i, /you don'?t pay/i, /is this (you|your channel)/i, /quick (one|question)\b/i,
  /\b(grow|scale|monetiz\w*|boost)\b.{0,40}\b(channel|audience|revenue|subscribers)\b/i, /\$\s?\d[\d,]*k?\+?\s*(in revenue|per month|a month|\/mo)/i,
  /\b(book|schedule|hop on) a (quick )?(call|chat)\b/i, /loom\.com\/share/i, /\b(seo|lead gen\w*|done[- ]for[- ]you)\b/i,
  /partnerships? (advisor|manager|executive)/i, /\bwe (help|work with) (creators|channels|brands)\b/i,
];
const OPPORTUNITY = [
  /\b(sponsor\w*|paid (partnership|collaboration|placement|segment)|rate card|your rates?|budget of|we('| a)re willing to pay|fee)\b/i,
  /\b(licen[cs]e|interview|feature you|speak at|guest on)\b/i,
];
const SPAM_SENDERS = /^(no-?reply|noreply|do-?not-?reply|notifications?|mailer-daemon|bounce)/i;
const ODD_DOMAINS = /\.(info|xyz|online|site|top|click|live|space|buzz|shop)$/i;

export function ruleLabel({ from = "", subject = "", body = "" }) {
  const text = `${subject}\n${body}`;
  const domain = from.split("@")[1] || "";
  if (SPAM_SENDERS.test(from)) return { label: "spam", reason: "Automated sender." };
  const pitch = PITCH.filter((r) => r.test(text)).length + (ODD_DOMAINS.test(domain) ? 1 : 0);
  const offer = OPPORTUNITY.filter((r) => r.test(text)).length;
  if (pitch >= 2 && pitch > offer) {
    return { label: "pitch", reason: "Reads like a mass sales pitch" + (ODD_DOMAINS.test(domain) ? ` from a throwaway domain (.${domain.split(".").pop()}).` : ".") };
  }
  if (offer >= 1) return { label: "opportunity", reason: "Mentions paying for or featuring your work. Check it's real." };
  return { label: "message", reason: "A person writing to you." };
}

const PROMPT = `You sort the inbox of a small tech-explainer YouTube channel (GOLIDE). Read the email and choose ONE label:
- "opportunity": a real company or person offers to PAY the channel or work with it on something specific (a sponsored segment, a review, licensing a clip, an interview, a joint video). They name what they want and who they are.
- "message": a real person writing to the channel (a viewer question, feedback, a customer, a personal note).
- "pitch": someone selling the channel a service or asking for a share of revenue: growth agencies, "results-based"/"no upfront cost" offers, editors, SEO, "is this your channel?" openers, mass-personalised videos, praise that names nothing specific.
- "spam": automated mail, notifications, newsletters, junk.
The test that sorts most cases: are they offering to pay us, or asking us to pay them (money or a cut)? Mass-sent signs: a template opener, big money promises, a throwaway sending domain, nothing specific about our videos.
Return JSON {"label": "...", "reason": "..."}; the reason is one plain sentence for the owner, naming the sign that decided it.`;

export async function aiLabel(env, message) {
  if (!env.OPENAI_API_KEY) return null;
  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: { authorization: `Bearer ${env.OPENAI_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({
      model: MODEL,
      instructions: PROMPT,
      input: `FROM: ${message.from}\nSUBJECT: ${message.subject}\n\n${String(message.body).slice(0, 6000)}`,
      max_output_tokens: 1200,
      reasoning: { effort: "low" },
      text: { format: { type: "json_schema", name: "triage", strict: true, schema: {
        type: "object", additionalProperties: false, required: ["label", "reason"],
        properties: { label: { type: "string", enum: LABELS }, reason: { type: "string" } } } } },
    }),
  });
  if (!response.ok) throw new Error(`triage model HTTP ${response.status}`);
  const data = await response.json();
  const text = data.output_text || (data.output || []).flatMap((o) => o.content || []).map((c) => c.text || "").join("");
  const parsed = JSON.parse(text);
  return LABELS.includes(parsed.label) ? { label: parsed.label, reason: String(parsed.reason || "").slice(0, 300) } : null;
}

export async function classify(env, message) {
  try {
    const ai = await aiLabel(env, message);
    if (ai) return ai;
  } catch (e) {
    console.log(JSON.stringify({ triage: "model_failed", error: String(e).slice(0, 200) }));
  }
  return ruleLabel(message);
}

/** Label one thread from its inbound messages and store it. */
export async function labelThread(env, threadId) {
  const thread = await env.DB.prepare(`SELECT participant_ref, subject FROM inbox_threads WHERE id=?`).bind(threadId).first();
  if (!thread) return null;
  const rows = (await env.DB.prepare(`SELECT body FROM inbox_messages WHERE thread_id=? AND direction='inbound' ORDER BY created_at ASC`)
    .bind(threadId).all()).results || [];
  if (!rows.length) return null;
  const body = rows.map((r) => r.body).join("\n\n---\n\n");
  const result = await classify(env, { from: thread.participant_ref, subject: thread.subject, body });
  await env.DB.prepare(`UPDATE inbox_threads SET label=?, label_reason=? WHERE id=?`).bind(result.label, result.reason, threadId).run();
  return result;
}

/** Threads that arrived before triage existed get labelled a few at a time. */
export async function labelMissing(env, limit = 5) {
  const rows = (await env.DB.prepare(`SELECT id FROM inbox_threads WHERE status='open' AND COALESCE(label,'')='' ORDER BY last_message_at DESC LIMIT ?`)
    .bind(limit).all()).results || [];
  for (const row of rows) {
    try { await labelThread(env, row.id); } catch (e) { console.log(JSON.stringify({ triage: "failed", error: String(e).slice(0, 200) })); }
  }
}
