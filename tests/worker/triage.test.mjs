// node --test tests/worker/triage.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { classify, ruleLabel } from "../../worker/triage.js";

const COMMEUNE = {
  from: "tabitha.caldermark@commeunethrivehub.info", subject: "Re: G$LIDE - Is This You?",
  body: "Quick one - is @esiah.1 your YouTube channel? We've crafted a system that's helped creators generate an additional 20,000+ (USD) in revenue from YouTube in a month... We work exclusively on a results-based compensation model. https://www.loom.com/share/16356c2ca9314d70932949fcbef75ae9",
};

test("the 2026-10-30 growth-agency email is a pitch", () => {
  assert.equal(ruleLabel(COMMEUNE).label, "pitch");
});

test("a paid sponsorship is an opportunity, a viewer is a message, no-reply is spam", () => {
  assert.equal(ruleLabel({ from: "anna@acme.com", subject: "Sponsored segment", body: "We'd like a sponsored segment in your next video; our budget is 300 dollars." }).label, "opportunity");
  assert.equal(ruleLabel({ from: "john@gmail.com", subject: "robots", body: "Loved the Microduck video, how do they train them?" }).label, "message");
  assert.equal(ruleLabel({ from: "noreply@service.com", subject: "Your receipt", body: "Thanks" }).label, "spam");
});

test("without a model key the rules decide", async () => {
  assert.equal((await classify({}, COMMEUNE)).label, "pitch");
});
