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
from golide_engine.engine.social_copy import fit_x, strip_citations
from golide_engine.engine.products import ProductRegistry
from golide_engine.engine.social_image import SocialImageProfile
from golide_engine.providers.registry import ProviderRegistry
from golide_engine.storage.r2 import r2_store_from_environment
from golide_engine.studio_bridge import StudioBridge


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
            "minItems": 3,
            "maxItems": 4,
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
        "platform_copy", "image_hook", "image_hook_emphasis",
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
        instructions = static_post_instructions(slot)
        body = (
            f"DATE_UTC={datetime.now(timezone.utc).date().isoformat()}\n"
            f"SLOT={slot}\n"
            f"CONTENT_ID={content_id}\n"
            f"CANDIDATE_PRODUCT={json.dumps(product_packet, ensure_ascii=False)}"
        )
        text = self.providers.text(live=True)
        output = text.generate_json(
            instructions,
            body,
            STATIC_DRAFT_SCHEMA,
            web_search=live_signal,
            max_output_tokens=2600,
        )
        draft = dict(output.value)
        draft["_request_id"] = output.request_id
        return draft

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

            # Locked split: post-a is a pure trend post (no product), post-b is
            # always about one GOLIDE Marketplace product.
            product = (
                registry.choose_auto(seed=content_id)
                if slot["slot"] == "post-b" and active_products
                else None
            )
            draft = self._draft(
                content_id=content_id,
                slot=slot["slot"],
                product=product,
            )
            use_product = product is not None
            bridge_position = (
                int(draft["product_bridge_position"])
                if use_product
                else 0
            )
            if use_product and bridge_position not in {2, 3}:
                bridge_position = 2

            meta, square = self._generate_image(draft)
            units = [strip_citations(str(item)) for item in draft["value_units"] if str(item).strip()]
            copies = {
                key: strip_citations(str(value))
                for key, value in draft["platform_copy"].items()
            }
            if use_product:
                url = product.marketplace_url
                for platform in copies:
                    if url and url not in copies[platform]:
                        copies[platform] = copies[platform].rstrip() + "\n\n" + url
            copies["x"] = fit_x(copies["x"])

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
                        "media_ref": (
                            meta["media_ref"]
                            if platform in {"instagram", "facebook"}
                            else square["media_ref"]
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

        return results
