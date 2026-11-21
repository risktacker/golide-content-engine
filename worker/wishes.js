// Stickman library wishes (owner 2026-11-21): what the storyboard writer asked for that the ReachMora library
// cannot draw yet (a place, an icon, a moving picture, a role, a company logo). The engine posts them after each
// Stickman storyboard; Studio lists them by how often videos needed them, so each new batch is drawn from real need.

export const WISHES_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS stickman_wishes (
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    times INTEGER NOT NULL DEFAULT 0,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    last_title TEXT NOT NULL DEFAULT '',
    done INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (kind, name)
  )`,
];

const KINDS = new Set(["place", "icon", "move", "camera", "role", "logo", "act"]);

export async function storeWishes(db, body) {
  const items = Array.isArray(body?.items) ? body.items.slice(0, 200) : [];
  const title = String(body?.title || "").slice(0, 300);
  const now = new Date().toISOString();
  let stored = 0;
  for (const item of items) {
    const kind = String(item?.kind || "").toLowerCase();
    const name = String(item?.name || "").trim().toLowerCase().slice(0, 80);
    if (!KINDS.has(kind) || !name) continue;
    await db.prepare(`INSERT INTO stickman_wishes (kind,name,times,first_seen,last_seen,last_title,done)
      VALUES (?,?,1,?,?,?,0)
      ON CONFLICT(kind,name) DO UPDATE SET times=times+1,last_seen=excluded.last_seen,last_title=excluded.last_title,done=0`)
      .bind(kind, name, now, now, title).run();
    stored++;
  }
  return { status: "ok", stored };
}

export async function listWishes(db) {
  const { results } = await db.prepare(`SELECT kind,name,times,first_seen,last_seen,last_title,done FROM stickman_wishes
    ORDER BY done ASC, times DESC, last_seen DESC LIMIT 200`).all();
  return { wishes: results || [] };
}

export async function markWishDone(db, body) {
  const kind = String(body?.kind || "").toLowerCase(), name = String(body?.name || "").toLowerCase();
  await db.prepare(`UPDATE stickman_wishes SET done=? WHERE kind=? AND name=?`).bind(body?.done === false ? 0 : 1, kind, name).run();
  return { status: "ok" };
}
