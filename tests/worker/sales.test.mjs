import test from "node:test";
import assert from "node:assert/strict";
import { buildSaleSpec } from "../../worker/sales.js";

const base = { title: "My Book", script: "one two three four five six seven eight nine ten.", voice_ref: "r2://temp/a.m4a",
  link: "https://www.amazon.com/dp/X", cover_ref: "r2://temp/c.jpg" };

test("a sales spec is a Short the engine can build at once", () => {
  const now = new Date("2026-11-03T22:00:00Z");
  const spec = buildSaleSpec(base, now);
  assert.equal(spec.id, "golide-sale-2026-11-04-0000");
  assert.equal(spec.format, "short");
  assert.equal(spec.purpose, "sales-video");
  assert.equal(spec.production_authorized, true);
  assert.equal(spec.release.approved, true);
  assert.equal(spec.release.channel_id, "UCqaXVBSBz7iQsRHOupKt-3w");
  assert.equal(spec.release.scheduled_at, "2026-11-03T22:45:00Z");
  assert.equal(spec.sale.cover_ref, "r2://temp/c.jpg");
});

test("a later publish time is kept, an earlier one waits for the build", () => {
  const now = new Date("2026-11-03T22:00:00Z");
  assert.equal(buildSaleSpec({ ...base, publish_at: "2026-11-05T08:00:00Z" }, now).release.scheduled_at, "2026-11-05T08:00:00Z");
  assert.equal(buildSaleSpec({ ...base, publish_at: "2026-11-03T22:05:00Z" }, now).release.scheduled_at, "2026-11-03T22:45:00Z");
});

test("missing pieces are refused in plain words", () => {
  assert.throws(() => buildSaleSpec({ ...base, title: "" }), /title/);
  assert.throws(() => buildSaleSpec({ ...base, script: "too short" }), /script/);
  assert.throws(() => buildSaleSpec({ ...base, voice_ref: "" }), /recording/);
  assert.throws(() => buildSaleSpec({ ...base, link: "amazon.com" }), /https/);
});
