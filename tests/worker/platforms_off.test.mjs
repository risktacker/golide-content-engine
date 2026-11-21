// 2026-11-21 (owner): a platform he disconnected is "Off": never on a video's list, never posted to.
import test from "node:test";
import assert from "node:assert/strict";
import { onlyConnected } from "../../worker/index.js";

const db = (on) => ({
  prepare: () => ({ all: async () => ({ results: on.map((platform) => ({ platform })) }) }),
});

test("a disconnected platform is dropped from the chosen list", async () => {
  const got = await onlyConnected(db(["youtube", "instagram", "linkedin"]), ["youtube", "instagram", "facebook", "linkedin"]);
  assert.deepEqual(got, ["youtube", "instagram", "linkedin"]);
});

test("no choice means every connected platform, not every platform", async () => {
  assert.deepEqual(await onlyConnected(db(["youtube", "linkedin"]), null), ["youtube", "linkedin"]);
});

test("nothing connected that he picked means nowhere, and 'none' stays none", async () => {
  assert.deepEqual(await onlyConnected(db(["youtube"]), ["facebook"]), ["none"]);
  assert.deepEqual(await onlyConnected(db(["youtube"]), ["none"]), ["none"]);
});
