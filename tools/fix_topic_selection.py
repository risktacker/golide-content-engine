from pathlib import Path

path = Path("src/golide_engine/orchestration/production.py")
source = path.read_text(encoding="utf-8")

old = '''        demand_path = work / "platform-demand.json"
        if self.youtube is not None:
            gate = YouTubeDemandGate(self.youtube, self.database)
            try:
                candidate, demand = gate.select(spec)
            except TopicDemandRejected:
                candidate_path = work / "trend-candidates.json"

                def trend_candidate_stage():
                    self._require_absent(candidate_path, "trend-candidates")
                    seeds = gate.trending_seeds()
                    if not seeds:
                        raise TopicDemandRejected(
                            "the YouTube trend feed returned no usable Science & Technology seeds"
                        )
                    seed_packet = json.dumps(
                        [{"title": item["title"], "market": item["market"]} for item in seeds[:60]],
                        separators=(",", ":"),
                    )
'''
new = '''        demand_path = work / "platform-demand.json"
        if self.youtube is not None:
            gate = YouTubeDemandGate(self.youtube, self.database)
            # Scheduled automation specs are deliberately generic. They must always
            # discover and compare fresh niche topics rather than allowing the generic
            # seed query (or an old trial topic) to become the production topic.
            requires_fresh_topic = (
                spec.get("purpose") == "channel-automation"
                and not spec.get("topic_candidates")
            )
            try:
                if requires_fresh_topic:
                    raise TopicDemandRejected("scheduled automation requires fresh topic discovery")
                candidate, demand = gate.select(spec)
            except TopicDemandRejected:
                candidate_path = work / "trend-candidates.json"

                def trend_candidate_stage():
                    self._require_absent(candidate_path, "trend-candidates")
                    seeds = gate.trending_seeds()
                    if not seeds:
                        raise TopicDemandRejected(
                            "the YouTube trend feed returned no usable Science & Technology seeds"
                        )
                    recent_titles = [
                        row["title"] for row in self.database.rows(
                            "SELECT title FROM productions WHERE production_id<>? ORDER BY updated_at DESC LIMIT 25",
                            (production_id,),
                        )
                        if row.get("title")
                    ]
                    seed_packet = json.dumps(
                        [{
                            "title": item["title"],
                            "markets": item.get("markets", []),
                            "views_per_day": item.get("views_per_day", 0),
                        } for item in seeds[:60]],
                        separators=(",", ":"),
                    )
'''
if old not in source:
    raise SystemExit("topic-selection marker changed; refusing patch")
source = source.replace(old, new, 1)

old_prompt = '''                        "Create 3 to 5 original G$LIDE science, technology, unusual-true-event or impossible-but-real explainer candidates from current YouTube platform signals. Do not copy video titles or premises. Each candidate must have a concise search query and one direct authoritative primary or institutional source URL found through web search. Reject gossip, celebrity news, politics, unsupported claims and topics that cannot support a premium visual explanation.",
                        f"CURRENT BRIEF\\n{spec['brief']}\\n\\nPLATFORM TREND SEEDS\\n{seed_packet}",
'''
new_prompt = '''                        "Create 3 to 5 original G$LIDE science, technology, unusual-true-event or impossible-but-real explainer candidates from current YouTube platform signals. Compare the candidates for current demand, visual explanation potential, evidence strength, broad curiosity and novelty. Do not copy video titles or premises. Do not reuse or lightly reword any recently produced/trial topic supplied in RECENT G$LIDE TOPICS. Each candidate must have a concise search query and one direct authoritative primary or institutional source URL found through web search. Reject gossip, celebrity news, politics, unsupported claims and topics that cannot support a premium visual explanation.",
                        f"CURRENT BRIEF\\n{spec['brief']}\\n\\nRECENT G$LIDE TOPICS\\n{json.dumps(recent_titles)}\\n\\nPLATFORM TREND SEEDS\\n{seed_packet}",
'''
if old_prompt not in source:
    raise SystemExit("trend prompt marker changed; refusing patch")
source = source.replace(old_prompt, new_prompt, 1)

path.write_text(source, encoding="utf-8")
print("fresh topic selection patch applied")
