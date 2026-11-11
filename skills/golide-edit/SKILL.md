---
name: golide-edit
description: GOLIDE's house editing rules for long tech-explainer videos. Use before planning or building any edit, template or scene in the GOLIDE edit engine; every owner correction is added here as a rule.
---

# GOLIDE house edit (v1, 2026-11-11)

Modelled on the channels we compete with (AI Terry, Nate Herk, Brendan Jowett, Matt Penny): real proof on
screen, motion design with intent, one look for the whole video. It must read as an edited video, never as
AI output. Numbers, not adjectives.

## Look
- Canvas 1920x1080 (long), 1080x1920 (Shorts). Safe area 96 px each side; captions band bottom 18 %.
- Background: near-black `#07080B` with a faint 48 px grid (white at 4 %) and one soft radial glow
  (`#1B2333`, 1200x700 px) that drifts 2 % across the video. Never flat black, never a new background per scene.
- Palette: white `#F4F1EA` text, GOLIDE gold `#E8C268` accent, highlighter yellow `#FACC15` at 35 % on real
  pages, data cyan `#38BDF8` for second series, alert red `#EF4444` for losses only. Brand colours only on logos.
- Type: Poppins 800/900 for titles and numbers, Inter 500/600 for labels. Titles max 6 words. Labels 28-40 px.
  Numbers always digits.
- Cards: radius 18 px, fill `#11141A` at 92 %, 1 px border white 8 %, shadow 0 40 px 120 px black 60 %,
  backdrop blur 18 px (glass). Real pages always sit inside a browser frame (44 px bar, three dots).
- One soft grain (3 %) and a 6 % vignette over everything: the finished-look layer.

## Motion (the After Effects craft, in numbers)
- Easing: entrances `back.out(1.4)` (overshoot and settle) 0.6-0.8 s; moves `power2.inOut`; exits `power3.in`
  0.35 s. Never linear except highlighter strokes and counters.
- Anticipation: a 4 % scale-down for 0.12 s before a big entrance. Follow-through: children stagger 0.06 s.
- Camera: every shot keeps moving: 2 %/s push-in by default; a targeted push (up to 1.9x) to the thing being
  said, landing 0.1 s before the word. Never a static frame longer than 1.2 s.
- Depth: at least two layers per shot moving at different speeds (parallax: foreground 1.0, card 0.6,
  background grid 0.2). Depth of field: background blurred 6 px when a card is in front.
- Motion blur on any move faster than 1200 px/s (directional blur 8-14 px for 2 frames).
- Reveals: mask wipes and track-matte reveals for titles and lists, not fades. Fades only for the background.
- Highlighting on real pages: yellow highlighter stroke drawn left-to-right in 0.35 s exactly on the words,
  then a 1.1x push to them. Circle-in (gold, 4 px, hand-drawn wobble) for a single number or button.
- Numbers: count up over 0.9 s with `power2.out`, then a 1.08x punch and an impact sound.
- Kinetic type: key words build word by word on the spoken word; the punch word scales 1.15x and turns gold.

## Rhythm and cutting
- A new visual or a new move every 1.5-3.5 s; a full scene change every 5-9 s.
- Cut on the spoken word (word timings), never mid-word. Sound leads the picture by 4 frames into a new scene
  (J-cut feel).
- Transitions by story beat: match cut (same shape or position carries over) for continuation; whip pan
  (0.25 s, motion blur) for "but", "meanwhile", a new chapter; mask wipe for a list item; hard cut on a punch.
  No dissolves between scenes.
- Speed ramp on whips: ease into 3x then out.

## Real proof first
- When a fact has a source, show the source: the captured page in a browser frame with the fact highlighted.
  Then the fact as a designed card (stat, quote, comparison, step).
- Logos are the real ones (3D glossy tiles), never look-alikes. Faces of real people are blurred.
- Every source shown is logged for the free guide and the community classroom.

## Scene types (templates)
browser_shot, stat_counter, quote_card, comparison, timeline, flow, steps, logo_tiles, object_3d,
kinetic_title, chapter_card, follow_cta. Each takes data plus the words that trigger its moves.

## Sound
- Voice at -16 LUFS. Music one track, steady, about 4-5 dB under the voice, faded in and out over 4 s.
- SFX on purpose: whoosh on whips and card entrances (-24 dB), click on highlighter and list items (-26 dB),
  impact on counters (-22 dB), riser 1.2 s into a chapter card. Never more than one SFX per 0.4 s.

## Standing owner rules
- Follow call-out only while it is said, then gone.
- No avatars of real people. No generative look-alikes of real products.
- Stills before motion; a trial before live; the daily engine keeps running until a new edit is approved.
