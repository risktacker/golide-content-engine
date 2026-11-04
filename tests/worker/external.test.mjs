import test from "node:test";
import assert from "node:assert/strict";
import { buildExternalSpec } from "../../worker/external.js";

const base = { script: "one two three four five six seven eight nine ten.", voice_ref: "r2://temp/a.m4a" };

test("an external video is a Short the engine builds and publishes at once", () => {
  const now = new Date("2026-11-03T22:00:00Z");
  const spec = buildExternalSpec(base, now);
  assert.equal(spec.id, "golide-external-2026-11-04-0000");
  assert.equal(spec.purpose, "external-video");
  assert.equal(spec.production_authorized, true);
  assert.ok(["scheduled", "independent"].includes(spec.budget_class));  // the only classes the engine accepts
  assert.equal(spec.release.scheduled_at, "2026-11-03T22:00:00Z");
  assert.equal(spec.external.title, "");
});

test("the optional pieces are carried, bad links refused", () => {
  const spec = buildExternalSpec({ ...base, title: "Mine", link: "https://x.com/a", reference_link: "https://x.com/b", reference_ref: "r2://temp/p.jpg" });
  assert.equal(spec.title, "Mine");
  assert.equal(spec.external.reference_ref, "r2://temp/p.jpg");
  assert.throws(() => buildExternalSpec({ ...base, link: "x.com" }), /https/);
  assert.throws(() => buildExternalSpec({ ...base, script: "too short" }), /script/);
  assert.throws(() => buildExternalSpec({ ...base, voice_ref: "" }), /recording/);
});

import { normalizePlatforms } from "../../worker/index.js";
test("platform choice: missing means everywhere, nothing ticked means none", () => {
  assert.equal(normalizePlatforms(undefined), null);
  assert.deepEqual(normalizePlatforms([]), ["none"]);
  assert.deepEqual(normalizePlatforms(["LinkedIn", "youtube", "tiktok"]), ["youtube", "linkedin"]);
});
