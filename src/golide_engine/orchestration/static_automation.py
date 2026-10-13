from __future__ import annotations

import json
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from golide_engine.engine.content_rules import static_post_instructions
from golide_engine.engine.social_copy import clean_url, fit_x, strip_citations
from golide_engine.engine.products import ProductRegistry
from golide_engine.engine.social_image import SocialImageProfile
from golide_engine.providers.registry import ProviderRegistry
from golide_engine.storage.r2 import r2_store_from_environment
from golide_engine.studio_bridge import StudioBridge


_SLIDE: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "heading": {"type": "string"},
        "emphasis": {"type": "string"},
        "text": {"type": "string"},
    },
    "required": ["heading", "emphasis", "text"],
}

# Story slides have no title (owner direction 2026-10-07): the sentence is the slide.
_STORY: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "text": {"type": "string"},
        "emphasis": {"type": "string"},
    },
    "required": ["text", "emphasis"],
}

STATIC_DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "weekly_theme": {"type": "string"},
        "content_lane": {
            "type": "string",
            "enum": [
                "awareness", "authority", "proof", "story",
                "conversion", "education", "flexible",
            ],
        },
        "value_units": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {"type": "string"},
        },
        "platform_copy": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "instagram": {"type": "string"},
                "facebook": {"type": "string"},
                "linkedin": {"type": "string"},
                "x": {"type": "string"},
            },
            "required": ["instagram", "facebook", "linkedin", "x"],
        },
        "carousel": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "points": {"type": "array", "minItems": 5, "maxItems": 5, "items": _STORY},
                "callout": _STORY,
            },
            "required": ["points", "callout"],
        },
        "product_slide": _STORY,
        "x_replies": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": {"type": "string"},
        },
        "source_url": {"type": "string"},
        "image_hook": {"type": "string"},
        "image_hook_emphasis": {"type": "string"},
        "image_concept": {"type": "string"},
        "glow_color": {"type": "string", "enum": ["gold", "cyan", "white"]},
        "use_product": {"type": "boolean"},
        "product_bridge_position": {
            "type": "integer",
            "enum": [0, 2, 3],
        },
    },
    "required": [
        "title", "weekly_theme", "content_lane", "value_units",
        "platform_copy", "carousel", "product_slide", "x_replies", "source_url",
        "image_hook", "image_hook_emphasis",
        "image_concept", "glow_color",
        "use_product", "product_bridge_position",
    ],
}


class StaticAutomation:
    """Generate the two locked daily static posts with near-zero operator input."""

    ESTIMATED_POST_USD = 0.049

    def __init__(
        self,
        root: str | Path = ".",
        *,
        bridge: StudioBridge | None = None,
    ):
        self.root = Path(root).resolve()
        self.bridge = bridge or StudioBridge(
            os.getenv("GOLIDE_STUDIO_BASE_URL", "https://studio.golidee.com")
        )
        self.providers = ProviderRegistry(self.root / "config/providers.json")
        self.image_profile = SocialImageProfile(
            self.root / "config/social-image-profile.json"
        )
        self.media_store = r2_store_from_environment()
        if self.media_store is None:
            raise RuntimeError("R2 temporary storage is required for static automation")
        self.calendar = json.loads(
            (self.root / "config/content-calendar.json").read_text(encoding="utf-8")
        )
        self.budget = json.loads(
            (self.root / "config/budget-policy.json").read_text(encoding="utf-8")
        )

    def _live_registry(self) -> ProductRegistry:
        url = os.getenv(
            "GOLIDE_PRODUCT_REGISTRY_URL",
            "https://marketplace.golidee.com/api/product-registry",
        ).strip()
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "GOLIDE-Static-Automation/1.0",
                },
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload.get("products"), list) and payload["products"]:
                return ProductRegistry.from_payload(payload)
        except Exception:
            pass
        return ProductRegistry(self.root / "config/product-registry.json")

    def due_slots(self, now: datetime | None = None) -> list[dict[str, Any]]:
        zone = ZoneInfo(self.calendar["timezone"])
        moment = (now or datetime.now(timezone.utc)).astimezone(zone)
        weekday = moment.strftime("%A").lower()
        due: list[dict[str, Any]] = []
        for rule in self.calendar["daily_posts"]:
            if weekday not in rule["days"]:
                continue
            hour, minute = (int(part) for part in rule["time"].split(":", 1))
            scheduled = moment.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            if moment < scheduled:
                continue
            due.append({
                "slot": rule["slot"],
                "scheduled_at": scheduled,
                "platforms": tuple(rule["platforms"]),
            })
        return due

    @staticmethod
    def _product_packet(product) -> dict[str, Any]:
        if product is None:
            return {}
        return {
            "id": product.id,
            "name": product.name,
            "target_audience": product.target_audience,
            "problem_solved": product.problem_solved,
            "marketplace_url": product.marketplace_url,
            "keywords": list(product.keywords),
            "creator_niches": list(product.creator_niches),
            "target_geographies": list(product.target_geographies),
            "lifecycle_status": product.lifecycle_status,
            "priority": product.priority,
        }

    def _draft(
        self,
        *,
        content_id: str,
        slot: str,
        product,
    ) -> dict[str, Any]:
        product_packet = self._product_packet(product)
        live_signal = slot == "post-a"
        instructions = static_post_instructions(slot, has_product=product is not None)
        try:
            recent = self.bridge.recent_posts(21)
        except Exception:  # history helps; it must never stop a post
            recent = []
        body = (
            f"DATE_UTC={datetime.now(timezone.utc).date().isoformat()}\n"
            f"SLOT={slot}\n"
            f"CONTENT_ID={content_id}\n"
            f"CANDIDATE_PRODUCT={json.dumps(product_packet, ensure_ascii=False)}\n"
            f"RECENT_POSTS={json.dumps(recent, ensure_ascii=False)}"
        )
        text = self.providers.text(live=True)
        output = text.generate_json(
            instructions,
            body,
            STATIC_DRAFT_SCHEMA,
            web_search=live_signal,
            max_output_tokens=4500,
        )
        draft = dict(output.value)
        # 2026-10-13: a worn or repeated hook gets one rewrite with the reason.
        from ..engine.content_rules import hook_problems
        recent_hooks = [str(item.get("hook") or item.get("title") or "") for item in recent]
        problems = hook_problems(str(draft.get("image_hook", "")), recent_hooks)
        if problems:
            print(json.dumps({"status": "hook_rewrite", "hook": draft.get("image_hook"), "problems": problems}))
            try:
                output = text.generate_json(
                    instructions,
                    body + "\n\nYOUR PREVIOUS DRAFT\n" + json.dumps(draft, ensure_ascii=False)
                    + "\n\nREWRITE IT with a fresh hook. Fix: " + "; ".join(problems)
                    + ". Keep the story, facts and slides unless they repeat the same formula.",
                    STATIC_DRAFT_SCHEMA,
                    web_search=False,
                    max_output_tokens=4500,
                )
                draft = dict(output.value)
            except Exception as exc:  # the first draft still goes out
                print(json.dumps({"status": "hook_rewrite_failed", "error": str(exc)[:300]}))
        draft["_request_id"] = output.request_id
        return draft

    def _carousel(self, draft: dict[str, Any], product=None) -> list[str]:
        """Render and upload the text slides; a failure leaves a single image.

        Order (owner direction 2026-10-07): the 5 story slides, the marketplace
        slide second to last, then the follow call-out. With the image first,
        that is 8 images.
        """
        from golide_engine.engine.carousel import Slide, render_slide

        def slide(item, **kind):
            return Slide(heading=strip_citations(str(item.get("heading", ""))),
                         text=strip_citations(str(item.get("text", ""))),
                         emphasis=str(item.get("emphasis", "")), **kind)

        def filled(item) -> bool:
            return bool(str(item.get("text", "")).strip() or str(item.get("heading", "")).strip())

        carousel = draft.get("carousel") or {}
        points = [p for p in carousel.get("points", []) if filled(p)][:5]
        callout = carousel.get("callout") or carousel.get("takeaway") or {}
        if len(points) < 2 or not filled(callout):
            return []
        slides = [slide(p, marker=str(i + 1)) for i, p in enumerate(points)]
        product_item = draft.get("product_slide") or {}
        if product is not None and filled(product_item):
            slides.append(slide(product_item, product=True))
        slides.append(slide(callout, final=True))
        total = len(slides) + 1
        refs: list[dict[str, Any]] = []
        try:
            with tempfile.TemporaryDirectory(prefix="golide-carousel-") as tmp:
                for index, item in enumerate(slides):
                    path = render_slide(item, index + 2, total, Path(tmp) / f"slide-{index + 2}.jpg")
                    upload = self.media_store.upload_bytes(
                        filename=f"golide-auto-slide-{index + 2}.jpg",
                        media_kind="image",
                        data=path.read_bytes(),
                        content_type="image/jpeg",
                        retention_hours=48,
                    )
                    refs.append({"media_ref": upload.media_ref, "media_kind": "image",
                                 "expires_at": upload.expires_at.isoformat()})
        except Exception as exc:  # the post still goes out as one image
            print(json.dumps({"status": "carousel_skipped", "error": str(exc)}))
            return []
        self.bridge.register_media(refs)
        return [r["media_ref"] for r in refs]

    def _generate_image(
        self,
        draft: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        hook = str(draft["image_hook"]).replace("\u2014", ",").replace("\u2013", ",").strip()
        emphasis = str(draft.get("image_hook_emphasis", "")).strip()
        prompt = self.image_profile.build_prompt(
            concept=str(draft["image_concept"]),
            glow_color=str(draft.get("glow_color", "gold")),
        )
        provider = self.providers.images("hero", live=True)

        with tempfile.TemporaryDirectory(prefix="golide-static-auto-") as tmp:
            root = Path(tmp)
            master = root / "master.png"
            meta = root / "meta-4x5.jpg"
            square = root / "square-1x1.jpg"
            provider.create_image(prompt, master, "1024x1536")
            self.image_profile.adapt(master, meta, square, hook=hook, emphasis=emphasis)

            meta_upload = self.media_store.upload_bytes(
                filename="golide-auto-meta-4x5.jpg",
                media_kind="image",
                data=meta.read_bytes(),
                content_type="image/jpeg",
                retention_hours=48,
            )
            square_upload = self.media_store.upload_bytes(
                filename="golide-auto-square-1x1.jpg",
                media_kind="image",
                data=square.read_bytes(),
                content_type="image/jpeg",
                retention_hours=48,
            )

        self.bridge.register_media([
            {
                "media_ref": meta_upload.media_ref,
                "media_kind": "image",
                "expires_at": meta_upload.expires_at.isoformat(),
            },
            {
                "media_ref": square_upload.media_ref,
                "media_kind": "image",
                "expires_at": square_upload.expires_at.isoformat(),
            },
        ])
        return (
            {
                "media_ref": meta_upload.media_ref,
                "expires_at": meta_upload.expires_at.isoformat(),
            },
            {
                "media_ref": square_upload.media_ref,
                "expires_at": square_upload.expires_at.isoformat(),
            },
        )

    def run_due(self, now: datetime | None = None) -> list[dict[str, Any]]:
        zone = ZoneInfo(self.calendar["timezone"])
        moment = (now or datetime.now(timezone.utc)).astimezone(zone)
        registry = self._live_registry()
        active_products = registry.eligible()
        monthly_cap = float(
            os.getenv(
                "GOLIDE_STATIC_OPENAI_MONTHLY_CAP_USD",
                self.budget["openai"].get("static_post_cap_usd", 3),
            )
        )
        month = moment.strftime("%Y-%m")
        current_count = self.bridge.static_month_count(month)
        results: list[dict[str, Any]] = []
        failures: list[str] = []

        for slot in self.due_slots(now):
            content_id = (
                f"golide-post-{moment.date().isoformat()}-{slot['slot']}"
            )
            if self.bridge.content_exists(content_id):
                results.append({"id": content_id, "status": "already_exists"})
                continue

            if (current_count + 1) * self.ESTIMATED_POST_USD > monthly_cap + 1e-9:
                results.append({
                    "id": content_id,
                    "status": "paused_funds",
                    "reason": (
                        f"static OpenAI guard is ${monthly_cap:.2f}; "
                        f"estimated next monthly total would exceed it"
                    ),
                })
                break

            try:
                # Locked split: post-a is a pure trend post (no product), post-b is
                # always about one GOLIDE Marketplace product.
                # Every carousel carries one marketplace slide when a product is live
                # (owner direction 2026-10-07: second to last, before the call-out).
                product = registry.choose_auto(seed=content_id) if active_products else None
                draft = self._draft(
                    content_id=content_id,
                    slot=slot["slot"],
                    product=product,
                )
                # Both daily posts are trend posts; the product only appears as one
                # Instagram slide in the evening carousel (owner direction 2026-10-07).
                use_product = False
                bridge_position = 0

                meta, square = self._generate_image(draft)
                units = [strip_citations(str(item)) for item in draft["value_units"] if str(item).strip()]
                copies = {
                    key: strip_citations(str(value))
                    for key, value in draft["platform_copy"].items()
                }
                link = clean_url(str(draft.get("source_url", "")))
                for platform in ("facebook", "linkedin"):
                    copies[platform] = _drop_urls(copies[platform])
                    if link:
                        copies[platform] = copies[platform].rstrip() + "\n\nSource: " + link
                for platform in ("instagram", "x"):
                    copies[platform] = _drop_urls(copies[platform])
                copies["x"] = fit_x(copies["x"])
                replies = [fit_x(_drop_urls(strip_citations(str(r)))) for r in draft.get("x_replies", []) if str(r).strip()][:2]
                slides = self._carousel(draft, product)
                if slides:
                    points = min(5, len([p for p in (draft.get("carousel") or {}).get("points", [])
                                         if str(p.get("text", "") or p.get("heading", "")).strip()]))
                    for platform in ("instagram", "facebook", "linkedin"):
                        copies[platform] = match_counts(copies[platform], points)
                    if product is not None and "bio" not in copies["instagram"].lower():
                        copies["instagram"] = copies["instagram"].rstrip() + "\n\nLink in bio."
                    url = clean_url(str(getattr(product, "marketplace_url", "") or "")) if product is not None else ""
                    if url:
                        # The marketplace slide also goes to Facebook and LinkedIn, where links
                        # work in the post itself (2026-10-08 audit).
                        for platform in ("facebook", "linkedin"):
                            copies[platform] = copies[platform].rstrip() + "\n\nFrom the GOLIDE Marketplace: " + url

                scheduled_utc = slot["scheduled_at"].astimezone(timezone.utc).isoformat()
                payload = {
                    "id": content_id,
                    "content_class": "post",
                    "content_lane": draft["content_lane"],
                    "weekly_theme": draft["weekly_theme"],
                    "title": draft["title"],
                    "master_text": "\n\n".join(units),
                    "value_units": units,
                    "product_bridge_position": bridge_position or None,
                    "product_mode": "auto_product" if use_product else "brand",
                    "product_id": "",
                    "resolved_product_id": product.id if use_product else "",
                    "selection_seed": content_id,
                    "registry_products": registry.snapshot()["products"],
                    "media_approved": True,
                    "qa_approved": False,
                    "release_approved": True,
                    "scheduled_at": scheduled_utc,
                    "variants": [
                        {
                            "platform": platform,
                            "title": "",
                            "body": copies[platform],
                            # The same 8 images go to Instagram, Facebook and LinkedIn
                            # (owner direction 2026-10-07); X stays one image (cost).
                            "media_ref": (
                                meta["media_ref"]
                                if platform in {"instagram", "facebook"} or (slides and platform == "linkedin")
                                else square["media_ref"]
                            ),
                            "parts": (
                                [f"slide:{ref}" for ref in slides] if platform in {"instagram", "facebook", "linkedin"}
                                else replies if platform == "x" else []
                            ),
                        }
                        for platform in ("instagram", "facebook", "linkedin", "x")
                    ],
                }
                created = self.bridge.create_content(payload)
                current_count += 1
                results.append({
                    "id": content_id,
                    "status": created.get("status", "scheduled"),
                    "title": draft["title"],
                    "slot": slot["slot"],
                    "product": product.name if use_product else None,
                    "estimated_usd": self.ESTIMATED_POST_USD,
                })
            except Exception as exc:
                # One slot failing must never stop the other (2026-10-08 audit).
                failures.append(f"{content_id}: {str(exc)[:300]}")
                results.append({"id": content_id, "status": "failed", "error": str(exc)[:300]})

        if failures:
            print(json.dumps({"status": "static_slots_failed", "results": results}))
            raise RuntimeError("static post failed: " + " | ".join(failures))
        return results


def _drop_urls(text: str) -> str:
    import re

    cleaned = re.sub(r"\s*https?://\S+", "", text)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


_NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_COUNT_NOUNS = r"(steps?|levels?|ways?|signs?|things?|lessons?|mistakes?|rules?|tips?|ideas?|points?|reasons?|moves?|questions?|habits?|stages?)"


def hook_count(hook: str) -> int | None:
    """The number of items a hook promises ("3 levels", "Three signs"), if any."""
    import re

    match = re.search(r"\b(\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")\b\s+(?:\w+\s+)?" + _COUNT_NOUNS, hook, re.I)
    if not match:
        return None
    value = match.group(1).lower()
    return int(value) if value.isdigit() else _NUMBER_WORDS[value]


def match_counts(caption: str, points: int) -> str:
    """Make every "N steps/levels/..." in a caption agree with the slides."""
    import re

    words = {v: k for k, v in _NUMBER_WORDS.items()}

    def fix(match):
        value = match.group(1)
        new = str(points) if value.isdigit() else words.get(points, str(points))
        if value[:1].isupper():
            new = new.capitalize()
        return new + match.group(2)

    return re.sub(r"\b(\d{1,2}|" + "|".join(_NUMBER_WORDS) + r"|" + "|".join(w.capitalize() for w in _NUMBER_WORDS) + r")(\s+(?:\w+\s+)?" + _COUNT_NOUNS + r")",
                  fix, caption)
