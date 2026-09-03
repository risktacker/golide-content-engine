from pathlib import Path


path = Path("src/golide_engine/orchestration/production.py")
source = path.read_text(encoding="utf-8")

voice_start = source.index(
    '        voice_cfg = self.providers.config["voice"]\n'
    '        narration = work / "narration-full-script-v2.mp3"'
)
voice_end_marker = '        self.runner.run(production_id, "voice-full-script-v2", voice_stage)\n'
voice_end = source.index(voice_end_marker, voice_start) + len(voice_end_marker)
voice_block = '''        voice_cfg = self.providers.config["voice"]
        narration_payload = work / "narration-tts.txt"
        narration = work / "narration-full-script-v2.mp3"
        timed_words_path = work / "timed-words-full-script-v2.json"
        voice = self.providers.voice(live=True)

        def voice_stage():
            self._require_absent(narration, "voice")
            self._require_absent(timed_words_path, "voice")
            spoken_text = script.strip()
            # This local guard runs before balance checks, voice lookups or paid TTS.
            voice.validate_spoken_narration(spoken_text)
            if narration_payload.exists():
                existing_payload = narration_payload.read_text(encoding="utf-8").strip()
                if existing_payload != spoken_text:
                    raise RuntimeError("narration TTS payload differs from checkpointed spoken script")
            else:
                narration_payload.write_text(spoken_text + "\\n", encoding="utf-8")
            characters = len(spoken_text)
            self.costs.require_monthly_character_capacity(
                "elevenlabs", characters, int(voice_cfg["monthly_character_limit"])
            )
            self._reserve(
                spec, voice_cfg["model"], Usage(characters=characters), provider="elevenlabs",
                stage="voice-full-script-v2",
            )
            voice.validate_voice()
            output = voice.synthesize(spoken_text, narration)
            details = output.details or {}
            words = details.get("words")
            if not words:
                raise RuntimeError("ElevenLabs narration returned no timing alignment")
            timed_words_path.write_text(
                json.dumps(words, indent=2) + "\\n", encoding="utf-8"
            )
            self.costs.record(
                production_id, "voice", "elevenlabs", voice_cfg["model"],
                Usage(characters=characters), output.request_id,
            )

        self.runner.run(production_id, "voice-full-script-v2", voice_stage)
'''
source = source[:voice_start] + voice_block + source[voice_end:]

board_start = source.index(
    '        previous_storyboard_path = work / "storyboard-authoritative-v2.json"\n'
)
board_end_marker = '        self.runner.run(production_id, "storyboard-authoritative-v5", storyboard_stage)\n'
board_end = source.index(board_end_marker, board_start) + len(board_end_marker)
board_block = '''        previous_storyboard_path = work / "storyboard-authoritative-v2.json"
        asset_inventory: dict[str, dict[str, Any]] = {}
        previous_scenes: list[dict[str, Any]] = []
        if previous_storyboard_path.exists():
            previous_storyboard = json.loads(
                previous_storyboard_path.read_text(encoding="utf-8")
            )
            previous_scenes = previous_storyboard.get("scenes", [])
            for previous_scene in previous_scenes:
                asset_inventory.setdefault(
                    previous_scene["asset_key"],
                    {
                        "asset_key": previous_scene["asset_key"],
                        "visual_prompt": previous_scene.get("visual_prompt", ""),
                    },
                )
                for previous_layer in previous_scene.get("secondary_assets", []):
                    asset_inventory.setdefault(
                        previous_layer["asset_key"],
                        {
                            "asset_key": previous_layer["asset_key"],
                            "visual_prompt": previous_layer.get("visual_prompt", ""),
                        },
                    )

        storyboard_path = work / "storyboard-authoritative-v5.json"

        def storyboard_stage():
            self._require_absent(storyboard_path, "storyboard")
            primary_limit = 5 if spec["format"] == "short" else 12
            minimum_unique = 5 if spec["format"] == "short" else 12
            minimum_layered_ratio = 0.15 if spec["format"] == "short" else 0.25

            if previous_scenes:
                # Recovery uses already-paid media and never invents replacement assets.
                def editorial_tokens(value: str) -> set[str]:
                    return {
                        token for token in re.findall(r"[a-z0-9]+", value.lower())
                        if len(token) > 2
                    }

                template_tokens = []
                for template in previous_scenes:
                    searchable = " ".join([
                        str(template.get("spoken_excerpt", "")),
                        str(template.get("visual_caption", "")),
                        str(template.get("visual_prompt", "")),
                    ])
                    template_tokens.append(editorial_tokens(searchable))

                motion_types = [
                    "push-in", "pan-left", "reframe", "pull-out",
                    "pan-right", "layer-reveal",
                ]
                transitions = ["cut", "match-cut", "paper-wipe", "object-transition"]
                roles = ["CONTEXT", "CAUSE_EFFECT", "CONTRAST", "REVEAL"]
                planned_scenes = []
                for index, beat in enumerate(beats):
                    beat_tokens = editorial_tokens(beat["text"])
                    scores = [
                        len(beat_tokens & tokens) * 100
                        - ((template_index - index) % len(previous_scenes))
                        for template_index, tokens in enumerate(template_tokens)
                    ]
                    template = previous_scenes[max(range(len(scores)), key=scores.__getitem__)]
                    spoken_words = str(beat["text"]).split()
                    caption = " ".join(spoken_words[:6]).rstrip(".,;:!?")
                    number_match = re.search(r"\\b\\d+(?:\\.\\d+)?\\b", beat["text"])
                    annotation = {"kind": "none"}
                    if number_match:
                        annotation = {
                            "kind": "number",
                            "text": number_match.group(0),
                            "start_offset": 0.08,
                            "duration": min(1.1, max(0.1, float(beat["duration"]) - 0.1)),
                            "position": "center",
                            "color_token": "golide-gold",
                        }
                    planned_scenes.append({
                        "beat_id": beat["id"],
                        "asset_key": template["asset_key"],
                        "visual_role": template.get("visual_role", roles[index % len(roles)]),
                        "visual_caption": caption,
                        "visual_prompt": template.get("visual_prompt", ""),
                        "motion": {
                            "type": motion_types[index % len(motion_types)],
                            "intensity": "strong" if index % 5 == 0 else "medium",
                            "transition": transitions[index % len(transitions)],
                            "easing": "ease-in-out",
                            "emphasis": caption,
                            "audio_cue": "impact" if index % 9 == 0 else (
                                "soft-trace" if index % 3 == 0 else "none"
                            ),
                            "annotation": annotation,
                        },
                        "secondary_assets": template.get("secondary_assets", []),
                        "subject_bounds": template.get("subject_bounds", []),
                    })
            else:
                # New production: plan the full edit before the first image purchase.
                planning_input = json.dumps({
                    "format": spec["format"],
                    "brief": spec["brief"],
                    "narration": script,
                    "research": research,
                    "editorial_beats": beats,
                    "primary_asset_limit": primary_limit,
                    "minimum_unique_primary_assets": minimum_unique,
                    "minimum_layered_scene_ratio": minimum_layered_ratio,
                }, separators=(",", ":"))
                self._reserve(
                    spec, text_model,
                    Usage(
                        input_tokens=max(1, len(planning_input) // 4),
                        output_tokens=12000,
                    ),
                    stage="storyboard-authoritative-v5",
                )
                output = text.generate_json(
                    """Plan a premium G$LIDE science/technology explanation edit. Return exactly one scene for every supplied beat_id and never change narration timing. Build a deliberate Premiere-Pro/After-Effects-like visual language using the available motion grammar: multi-layer composition, 2.5D-feeling parallax through foreground/detail layers, camera push/pull/pan/reframe, diagram-like reveals, tracked labels or numbers, kinetic emphasis, object/match transitions, depth, restrained technical HUD/data overlays, and blue/gold paper-cut compositing. Do not use an effect merely because it exists; each motion, layer and SFX cue must explain what the narrator is saying.

Use the smallest paid image set that still looks genuinely varied. Respect the supplied primary asset limit. Meet or exceed the supplied minimum unique primary assets. No primary asset may dominate the episode or repeat for more than two consecutive beats. Reuse an asset only when the viewer is intentionally returning to the same concept, and change framing/layers to show progression. At least the supplied minimum layered-scene ratio must use secondary assets. Reuse secondary detail/HUD assets when sensible rather than generating needless images.

Sound cues must correspond to visible actions: soft-trace for diagram/data movement, tick for numbers/UI, paper/swipe for directional reveals, impact only for rare major reveals. Keep many beats without SFX so sound has hierarchy. Use hard cuts often; reserve paper-wipe, match-cut and object-transition for motivated transitions. Use annotations sparingly and keep them inside each beat. Visual prompts must describe the actual explanatory image to generate, not editing instructions or text-heavy title cards. Favor diagrams, cutaways, mechanisms, scale comparisons, maps/data or object relationships over generic decorative art. Never request readable paragraphs in generated images.""",
                    planning_input,
                    STORYBOARD_SCHEMA,
                    max_output_tokens=12000,
                )
                planned_scenes = output.value["scenes"]
                self._record_text(production_id, "storyboard-authoritative-v5", output)

            planned = {scene["beat_id"]: scene for scene in planned_scenes}
            expected = {beat["id"] for beat in beats}
            if len(planned) != len(planned_scenes) or set(planned) != expected:
                raise RuntimeError("storyboard must contain every editorial beat exactly once")

            primary_keys = {scene["asset_key"] for scene in planned_scenes}
            if len(primary_keys) > primary_limit:
                raise RuntimeError(
                    f"storyboard requested {len(primary_keys)} primary assets; limit is {primary_limit}"
                )
            if not previous_scenes and len(primary_keys) < minimum_unique:
                raise RuntimeError(
                    f"storyboard has only {len(primary_keys)} unique primary assets; minimum is {minimum_unique}"
                )
            layered_ratio = sum(bool(scene.get("secondary_assets")) for scene in planned_scenes) / len(planned_scenes)
            if not previous_scenes and layered_ratio < minimum_layered_ratio:
                raise RuntimeError(
                    f"storyboard layered-scene ratio {layered_ratio:.1%} is below {minimum_layered_ratio:.1%}"
                )

            requested_asset_keys = set(primary_keys)
            requested_asset_keys.update(
                layer["asset_key"]
                for scene in planned_scenes
                for layer in scene.get("secondary_assets", [])
            )
            if previous_scenes and not requested_asset_keys.issubset(asset_inventory):
                unknown = sorted(requested_asset_keys - set(asset_inventory))
                raise RuntimeError(f"corrective storyboard invented uncached assets: {unknown}")

            merged = []
            for beat in beats:
                scene = planned[beat["id"]]
                self._safe_id(scene["asset_key"])
                for layer in scene.get("secondary_assets", []):
                    self._safe_id(layer["asset_key"])
                merged.append({
                    "id": beat["id"],
                    "asset_key": scene["asset_key"],
                    "visual_role": scene["visual_role"],
                    "start": beat["start"],
                    "end": beat["end"],
                    "duration": beat["duration"],
                    "spoken_excerpt": beat["text"],
                    "visual_caption": scene["visual_caption"],
                    "visual_prompt": scene["visual_prompt"],
                    "motion": scene["motion"],
                    "secondary_assets": scene.get("secondary_assets", []),
                    "subject_bounds": scene.get("subject_bounds", []),
                })
            storyboard_path.write_text(
                json.dumps({
                    "timing_source": "elevenlabs-normalized-alignment",
                    "planning_mode": "cached-correction" if previous_scenes else "fresh-premium",
                    "scenes": merged,
                }, indent=2) + "\\n",
                encoding="utf-8",
            )

        self.runner.run(production_id, "storyboard-authoritative-v5", storyboard_stage)
'''
source = source[:board_start] + board_block + source[board_end:]

old_loop = (
    '        hero_keys = set(dict.fromkeys(hero_candidates[:hero_limit]))\n'
    '        for asset_key, scene in unique_assets.items():\n'
)
new_loop = '''        hero_keys = set(dict.fromkeys(hero_candidates[:hero_limit]))
        # Preflight the complete image batch before generating the first image.
        image_batch = []
        for asset_key in unique_assets:
            is_hero = asset_key in hero_keys and asset_key not in secondary_keys
            image_batch.append((
                hero_image_cost_model if is_hero else support_image_cost_model,
                Usage(images=1),
            ))
        self.budget.reserve_batch(
            spec, image_batch, provider="openai", stage="planned-visual-asset-batch"
        )
        for asset_key, scene in unique_assets.items():
'''
if old_loop not in source:
    raise SystemExit("asset-loop marker changed; refusing patch")
source = source.replace(old_loop, new_loop, 1)

old_mix = '"music_volume": 0.08, "duck_under_voice": True'
if old_mix not in source:
    raise SystemExit("music-volume marker changed; refusing patch")
source = source.replace(
    old_mix, '"music_volume": 0.03, "duck_under_voice": True', 1
)

path.write_text(source, encoding="utf-8")
print("production standard patch applied")
