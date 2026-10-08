// Temporary media cleanup (R2 bucket, prefix temp/).
//
// Rule: nothing in temp/ lives longer than 72 hours. Published posts already
// delete their media straight away; this sweep catches everything else
// (failed or partial posts, owner recordings, rebuild previews, abandoned
// uploads). The only files kept past 72 hours are those of a post that is
// still waiting to go out (draft, scheduled or publishing).

export const MEDIA_KEEP_HOURS = 72;

function refsIn(row) {
  const refs = [];
  if (row.media_ref) refs.push(String(row.media_ref));
  try {
    for (const part of JSON.parse(row.parts_json || "[]")) {
      const s = String(part), i = s.indexOf("r2://");
      if (i >= 0) refs.push(s.slice(i));
    }
  } catch {}
  return refs;
}

export async function sweepMedia(env, now = new Date()) {
  if (!env.MEDIA) return { status: "skipped", reason: "no R2 binding" };
  const cutoff = now.getTime() - MEDIA_KEEP_HOURS * 3600e3;
  const { results: pending = [] } = await env.DB.prepare(`SELECT v.media_ref, v.parts_json FROM social_variants v
    JOIN content_posts p ON p.id=v.post_id WHERE p.status IN ('draft','scheduled','publishing')`).all();
  const keep = new Set(pending.flatMap(refsIn));

  const doomed = [];
  let files = 0, bytes = 0, freed = 0, cursor;
  do {
    const page = await env.MEDIA.list({ prefix: "temp/", cursor, limit: 1000 });
    for (const obj of page.objects) {
      const old = obj.uploaded.getTime() < cutoff && !keep.has("r2://" + obj.key);
      if (old) { doomed.push(obj.key); freed += obj.size; }
      else { files += 1; bytes += obj.size; }
    }
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);

  for (let i = 0; i < doomed.length; i += 1000) await env.MEDIA.delete(doomed.slice(i, i + 1000));
  const stamp = now.toISOString();
  for (const key of doomed) {
    await env.DB.prepare(`UPDATE temporary_media SET status='deleted', deleted_at=? WHERE object_key=?`).bind(stamp, "r2://" + key).run();
  }
  // Upload slots that never received a file, and old bookkeeping rows.
  const cutoffIso = new Date(cutoff).toISOString();
  const { results: stale = [] } = await env.DB.prepare(`SELECT object_key FROM temporary_media WHERE status='active' AND created_at<?`).bind(cutoffIso).all();
  for (const row of stale) {
    if (keep.has(row.object_key)) continue;
    await env.DB.prepare(`UPDATE temporary_media SET status='deleted', deleted_at=? WHERE object_key=?`).bind(stamp, row.object_key).run();
  }
  await env.DB.prepare(`DELETE FROM temporary_media WHERE status='deleted' AND deleted_at<?`)
    .bind(new Date(now.getTime() - 30 * 86400e3).toISOString()).run();

  const result = { status: "ok", deleted: doomed.length, freed_bytes: freed, files, bytes, kept_for_pending_posts: keep.size };
  console.log(JSON.stringify({ media_sweep: result }));
  return result;
}

export function sizeLabel(bytes) {
  if (bytes >= 1024 ** 3) return (bytes / 1024 ** 3).toFixed(2) + " GB";
  if (bytes >= 1024 ** 2) return (bytes / 1024 ** 2).toFixed(1) + " MB";
  return Math.round(bytes / 1024) + " KB";
}
