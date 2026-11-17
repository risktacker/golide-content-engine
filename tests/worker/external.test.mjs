import test from "node:test";
import assert from "node:assert/strict";
import { buildExternalSpec, cleanLooks } from "../../worker/external.js";

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

test("2026-11-17: his own video can be a long video and in Inkee", () => {
  const spec = buildExternalSpec({ ...base, format: "long", video_style: "illustration" });
  assert.equal(spec.format, "long");
  assert.equal(spec.video_style, "illustration");
  assert.ok(spec.concept.scores.click_promise);
  const plain = buildExternalSpec({ ...base, format: "nonsense", video_style: "nope" });
  assert.equal(plain.format, "short");
  assert.equal(plain.video_style, "goli");
});

test("Stickman (2026-11-17) is the third style, for Shorts and long videos", () => {
  assert.equal(buildExternalSpec({ ...base, format: "long", video_style: "stickman" }).video_style, "stickman");
  assert.equal(buildExternalSpec({ ...base, format: "short", video_style: "stickman" }).video_style, "stickman");
});

test("Stickman + Goli is for long videos; a Short asked for it is Stickman alone", () => {
  assert.equal(buildExternalSpec({ ...base, format: "short", video_style: "stickman_goli" }).video_style, "stickman");
  assert.equal(buildExternalSpec({ ...base, format: "long", video_style: "stickman_goli" }).video_style, "stickman_goli");
});


test("a Goli video carries its style switches; paid counts are whole numbers 0-20; others are dropped", () => {
  assert.deepEqual(cleanLooks({ free: ["layers", "bogus", "layers"], paid: { xray: 2.4, white: 0, blueprint: 99, nope: 3 } }),
    { free: ["layers"], paid: { xray: 2, blueprint: 20 } });
  assert.equal(cleanLooks(null), null);
  assert.deepEqual(cleanLooks({}).free, ["puppets", "layers", "circuit", "glass"]);
  const spec = buildExternalSpec({ ...base, video_style: "goli", looks: { free: [], paid: { xray: 1 } } });
  assert.deepEqual(spec.looks, { free: [], paid: { xray: 1 } });
  assert.equal(buildExternalSpec({ ...base, video_style: "stickman", looks: { paid: { xray: 1 } } }).looks, undefined);
});
