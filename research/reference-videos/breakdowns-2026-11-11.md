# Reference video breakdowns (vidIQ "watch", 2026-11-11)

Scene-by-scene breakdowns from vidIQ's video watcher (110 credits), kept for future reference.
Full transcripts are in this folder as `<video id>.txt`.

---

## 1. AI Terry: "Reverse engineer anything" (v_XdN5-ya9A), our niche's editing standard

**Rhythm:** the picture changes or animates every 1.5–3.5 s. Dark UI (near-black, faint grid), neon lime `#A3E635` and yellow `#FACC15` accents, rounded glass cards, white text. The presenter alternates full frame and picture-in-picture during screen captures.

**Scenes:**
- **0:00–0:01:** big animated "1982" with a sound hit.
- **0:02–0:17:** archive frames (IBM, Compaq) slide in, tracked callouts ("Reverse Engineered"), arrows, an exploded hardware diagram (Display, System Unit, Keyboard), a grid zooming into a laptop screen.
- **0:18–0:35:** a 3D dark cube with the Adobe logo, an animated price badge ($720/year), a magnifier, locks turning into glowing app icons ("All Seven, Rebuilt").
- **0:36–1:45:** a split card ("Their Office / Your Computer"), balance scales, hex/binary readouts, step cards (Read → Explain → Rebuild), a timeline (1980s Compaq → 1990s Linux → 2000s Open Source → Claude).
- **1:46–2:32:** mockup cards of what will be built, an installer progress bar, prompt cards with typing, then a disclaimer card (frosted glass, green highlights).
- **2:33–5:16:** a real GitHub repo in a dark floating browser frame with smooth scrolling and tags; node diagram (Your AI + Toolkit (213 tools) → AI Detective); real Claude Code sessions with zooms on the prompt and green check callouts; an app grid with a magnifier revealing machine code.
- **5:17–8:27:** decompiler visual (code → binary → shredded pages → readable book); NSA seal and Ghidra logo; a real terminal session with SHA-256 checks; an infographic of 4 components; a live command demo.
- **8:28–11:54:** a real screen capture of the app being built; comparison tables; UI mockup choices; a tech-stack card (Electron, TipTap, ExcelJS, Docx, Chart.js); a real desktop demo.
- **11:55–14:29:** layout choice, building the installer, Start-menu launch, checklists.
- **14:30–16:12:** a legal "road lanes" graphic, a recap of the numbers (13 apps, 213 tools, 1 suite), a 3D phone showing the WhatsApp community invite, the end screen.

**Why it looks edited, not AI-made:**
1. Real, unblurred screen captures as proof.
2. Consistent easing, soft drop shadows, glass blur layers, framing tied to what is said.
3. A sound on every card entrance, switch and pop.
4. One strict palette for 16 minutes.

**Tools a human uses for this:** Resolve or Premiere, After Effects or Cavalry, Figma, Screen Studio, Blender (3D cube, phone), Fairlight.

---

## 2. Claude editor skill (BiItnkevYoM), editing with Claude and Remotion

**Setup:**
- A Claude Project ("Claude Editor") with code execution on.
- A brand kit (logo, fonts, colours) and 2–3 reference edits as context.
- Instructions such as "pacing punchy, music under voice, never put shapes or text over a face".
- A `SKILL.md` ("edit-skill") built from references: fonts, colours, motion rules, caption format, intro style, b-roll logic. The instructions say: "Always use the edit-skill before any edit".
- An Epidemic Sound connector for music and SFX ("duck music under voice").
- Node.js 18+ installed.

**Per video:**
1. Drop the footage, voice, script and assets. Prompt: "Transcribe first. Show me the plan, then still frames of every graphic. Don't start motion until I approve the stills. Build a Remotion project with npm run studio / draft (480p) / final (1080p); every asset local; send edit.zip."
2. Approve the plan (a table of timestamps, lines, cuts, b-roll and graphic type).
3. Approve the stills.
4. Unzip, then `npm install`.
5. `npm run studio` (live preview).
6. `npm run draft` (480p).
7. All timestamped notes go in one message; Claude returns a patched `src.zip`. Then "teach this change to the edit-skill as a standing rule".
8. `npm run final` (1080p).

**Look:**
- Isometric 3D rooms, orbiting brand icons, kinetic counters, workflow node diagrams.
- Kinetic captions in the brand font (e.g. Fira Sans Condensed 700) with an accent colour (lime `#B8EF43` on black), placed clear of faces.
- 2% push-ins on key lines, cuts on speech pauses, split screens.
- Music ducked 15–18 dB under the voice; risers, pops, whooshes and dings synced to text entrances.

---

## 3. Code-only animation (-x6ZjVTK8aI), every frame is code

**Pipeline:**
1. **Setup:** Claude Code (Opus) in a folder; it checks and installs Node, FFmpeg and Python; folders `videos/finished`, `videos/engines`, `videos/skills`.
2. **Script:** `script.md` with camera notes under each sentence (e.g. "the depot at dawn, trams in a row, a tag over you: age 15"). "Plan the shots" gives a numbered shot list.
3. **Voice:** TTS (ElevenLabs, Fish Audio, Cartesia, Google, Microsoft), then `whisper vo.wav --word_timestamps True`, so every cut and title lands on a word; pauses can be added.
4. **Style skill (`skills/my-style/SKILL.md`), numbers instead of adjectives:**
   - High ¾ isometric camera, 24° lens, 2%/s push-in, handheld shake only in disaster scenes.
   - Tilt-shift miniature look, warm key light, soft shadows, 0.05 grain.
   - No subtitles: pixel HUD boxes and name tags over characters and objects.
   - Python-synthesised SFX or imported wav.
   - Mood-board images as references.
5. **Review (VideoHub):** a live browser preview of the canvas scenes (no 45-minute renders). Click a problem, add a note, "Send to Claude". Claude fixes `scenes/*.js` and writes the bug into SKILL.md as a rule ("labels never cover each other", "people walk around props, never through").
6. **Render:** headless Chrome captures the canvas frames, FFmpeg assembles them with `vo.wav` and `mix.wav`. Chunks render in parallel; `edit.json` reorders or trims without re-rendering.
7. **Packaging:** titles, description and chapters from the script; thumbnail prompts from frames (Google Flow).

---

## 4. AI Telly-style F-15EX (4XlC6tqh92U), photoreal 3D machine explainer

**Scenes:**
- **0:00–0:05:** fast 3D cutaways (Vulcan cannon, ammo drum, missiles); frosted-glass or X-ray skin over brushed steel, chrome and bronze internals; volumetric flare; orbital and macro moves.
- **0:06–0:15:** a jet in a dark hangar; glowing structure lines reveal spars and ribs; 3D tracked HUD labels with leader lines.
- **0:16–0:39:** cockpit inside and out over a real-looking coast; the pilot and WSO; a targeting-pod laser; impact; a thermal HUD view.
- **0:40–1:23:** history (F-4, MiG-21); gloved hands placing a J-35 on a map table; carriers, radar domes, datalink lines.
- **1:24–1:49:** X-ray gun firing, radar cross-section, lock-on, afterburners, 6 fuel tanks highlighted in yellow and cyan.
- **1:50–1:54:** Blender viewport behind the scenes.
- **1:55–3:24:** fuselage sections with tracked labels; red force vectors bending the spars in a 9 G turn; wind-tunnel particles; an exploded honeycomb panel.
- **3:25 onward:** cockpit and MFDs, jamming sphere, LANTIRN pods with thermal picture-in-picture, missile release, a full Vulcan mechanism, the F110 engine in 4 labelled stages (blue cold air to red combustion), fly-by-wire pulses to glowing control surfaces, history and payload outro.

**System:**
- **Palette:** slate grey, navy, sky blue, steel; accents neon cyan, green, safety orange.
- **Type:** uppercase geometric sans with a mono HUD font.
- **Devices:** X-ray cutaways, 3D-tracked labels, datalink beams and rings.
- **Cuts:** 18–24 a minute.
- **Premium because:** physically accurate rigs (ammo belts, compressor blades), volumetric light and PBR wear, and every part glows the instant it is named.
- **Tools:** Blender (Cycles, geometry nodes), Unreal for terrain, After Effects for HUD.

---

## 5. "You're Elon Musk" Short (znWzWYHoLOg), toon 3D world

**Scenes (2:51):**
- An office with a holographic globe and a capsule-body character with a 2D face.
- A $1T money pyramid.
- An AI go-kart race (company logos on carts, Elon falling behind).
- Elon as puppet master of Tesla, xAI, X and SpaceX.
- The Colossus data centre with a 122-day timer.
- A queue at the Nvidia/TSMC booth.
- A "FEED ME DATA!" tube.
- The Twitter sink walk.
- Tweets sucked into a fibre tube.
- A Cybertruck with lidar cones.
- Optimus holding an egg.
- Earth bottlenecks, then the Moon.
- Starship landing; a Starlink mesh around Earth.
- A Dyson sphere.
- A Neuralink Pong checklist.
- An X flag on Mars.

**System:**
- Low-poly cel-shaded 3D world with 2D expressive faces on capsule bodies, in a "tycoon game" look.
- Metaphors made literal.
- Holographic boards, checklists and progress bars.
- Word-highlight bold captions.
- A cut every 1.5–2.5 s, continuous push-ins and orbits, transitions through screens and windows.
- **Tools:** Blender, Unreal or Unity toon shaders, Illustrator face sprites, After Effects, CapCut.

---

## Not captured
vidIQ returns written scene-by-scene breakdowns, not image frames. No still screenshots exist from these videos. Frames can only be grabbed where the video file can be downloaded, and YouTube downloads are blocked from this workspace.
