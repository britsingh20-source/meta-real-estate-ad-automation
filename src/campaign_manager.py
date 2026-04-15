"""
Campaign Manager
Creates and manages Meta Campaigns, Ad Sets, Ad Creatives, and Ads
for Real Estate lead generation with a ₹200/day total budget cap.
"""

import json
import logging
import os
import glob
from pathlib import Path
from datetime import datetime
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adimage import AdImage

from .meta_client import MetaClient
from .location_targeting import get_all_targeting_specs

logger = logging.getLogger(__name__)

AD_CONFIG_PATH = Path(__file__).parent.parent / "config" / "ad_config.json"
BUDGET_RULES_PATH = Path(__file__).parent.parent / "config" / "budget_rules.json"
ASSETS_DIR = Path(__file__).parent.parent / "assets"

TOTAL_DAILY_BUDGET_INR = 200      # ₹200/day hard cap across all ad sets

SUPPORTED_IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def load_ad_config() -> dict:
    with open(AD_CONFIG_PATH, "r") as f:
        return json.load(f)


def load_budget_rules() -> dict:
    with open(BUDGET_RULES_PATH, "r") as f:
        return json.load(f)


class CampaignManager:
    def __init__(self, client: MetaClient):
        self.client = client
        self.account = client.get_account()
        self.ad_config = load_ad_config()
        self.budget_rules = load_budget_rules()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Campaign
    # ─────────────────────────────────────────────────────────────────────────

    def create_campaign(self) -> str:
        """Creates an OUTCOME_LEADS campaign and returns its ID."""
        name = f"{self.ad_config['campaign_name_prefix']} | {datetime.now().strftime('%Y-%m-%d')}"

        campaign = self.client.retry(lambda: self.account.create_campaign(
            params={
                Campaign.Field.name: name,
                Campaign.Field.objective: "OUTCOME_LEADS",   # Updated: replaces deprecated LEAD_GENERATION
                Campaign.Field.status: Campaign.Status.active,
                Campaign.Field.special_ad_categories: [],
                "is_adset_budget_sharing_enabled": False,    # Required: using per-adset budgets, not CBO
            }
        ))
        campaign_id = campaign["id"]
        logger.info("Created Campaign: %s (ID: %s)", name, campaign_id)
        return campaign_id

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Ad Sets — one per location group, budget split equally
    # ─────────────────────────────────────────────────────────────────────────

    def create_adsets(self, campaign_id: str, lead_form_id: str) -> list:
        """
        Creates one Ad Set per location group.
        Splits ₹200/day equally across all ad sets (minimum ₹20/adset enforced).
        """
        specs = get_all_targeting_specs()
        n = len(specs)

        # Budget allocation: equal split, floor at ₹20 per adset
        per_adset_budget = max(20, TOTAL_DAILY_BUDGET_INR // n)
        logger.info(
            "Splitting ₹%d across %d ad sets → ₹%d each",
            TOTAL_DAILY_BUDGET_INR, n, per_adset_budget
        )

        created_ids = []
        for spec in specs:
            adset_id = self._create_single_adset(
                campaign_id=campaign_id,
                spec=spec,
                budget_inr=per_adset_budget,
                lead_form_id=lead_form_id
            )
            created_ids.append(adset_id)

        return created_ids

    def _create_single_adset(
        self, campaign_id: str, spec: dict,
        budget_inr: int, lead_form_id: str
    ) -> str:
        name = f"AdSet | {spec['name']} | {datetime.now().strftime('%Y-%m-%d')}"

        promoted_object = {
            "page_id": self.client.page_id,
            "lead_gen_form_id": lead_form_id
        }

        bid_strategy = self.budget_rules.get("bid_strategy", "LOWEST_COST_WITHOUT_CAP")

        params = {
            AdSet.Field.name: name,
            AdSet.Field.campaign_id: campaign_id,
            AdSet.Field.daily_budget: budget_inr * 100,     # Meta uses paise
            AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
            AdSet.Field.optimization_goal: AdSet.OptimizationGoal.lead_generation,
            AdSet.Field.bid_strategy: bid_strategy,
            AdSet.Field.targeting: spec["targeting"],
            AdSet.Field.promoted_object: promoted_object,
            AdSet.Field.status: AdSet.Status.active,
            AdSet.Field.start_time: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+0000"),
        }

        # Optional: cost cap to control CPL
        max_cpl = self.budget_rules.get("max_cpl_inr")
        if max_cpl and bid_strategy == "COST_CAP":
            params[AdSet.Field.bid_amount] = max_cpl * 100

        adset = self.client.retry(lambda: self.account.create_ad_set(params=params))
        logger.info("Created AdSet: %s (ID: %s)", name, adset["id"])
        return adset["id"]

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Ad Creative
    # ─────────────────────────────────────────────────────────────────────────

    def _find_assets_image(self) -> str | None:
        """
        Scans the assets/ folder for image files (.jpg, .jpeg, .png).
        Returns the path to the most recently modified image, or None if empty.
        """
        if not ASSETS_DIR.exists():
            logger.info("assets/ folder does not exist — skipping.")
            return None

        images = [
            p for p in ASSETS_DIR.iterdir()
            if p.suffix.lower() in SUPPORTED_IMAGE_EXTS and p.is_file()
        ]

        if not images:
            logger.info("No images found in assets/ folder.")
            return None

        # Pick the most recently modified image
        latest = max(images, key=lambda p: p.stat().st_mtime)
        logger.info("Using image from assets/: %s", latest.name)
        return str(latest)

    def create_creative(self, lead_form_id: str) -> str:
        """
        Builds a single-image lead-gen creative.

        Image priority:
          1. image_hash  — Meta hash of already-uploaded image (fastest)
          2. image_url   — Hosted URL (no upload needed)
          3. assets/     — Auto-scan assets/ folder for .jpg/.jpeg/.png
          4. image_path  — Explicit local path in ad_config.json
        """
        cfg = self.ad_config
        page_id = self.client.page_id

        link_data = {
            "message": cfg["ad_body"],
            "link": cfg.get("destination_url", f"https://www.facebook.com/{page_id}"),
            "name": cfg["headline"],
            "description": cfg.get("description", ""),
            "call_to_action": {
                "type": cfg.get("cta_type", "LEARN_MORE"),
                "value": {"lead_gen_form_id": lead_form_id}
            },
        }

        image_hash = cfg.get("image_hash", "").strip()

        if not image_hash:
            if cfg.get("image_url", "").strip():
                # Priority 2: hosted URL — no upload needed
                link_data["picture"] = cfg["image_url"].strip()
                logger.info("Using image_url for creative: %s", cfg["image_url"])

            else:
                # Priority 3: auto-scan assets/ folder
                asset_path = self._find_assets_image()

                if asset_path:
                    image_hash = self._upload_image(asset_path)
                    logger.info("Uploaded assets image, hash: %s", image_hash)

                elif cfg.get("image_path", "").strip():
                    # Priority 4: explicit image_path in config
                    img_path = cfg["image_path"].strip()
                    if os.path.exists(img_path):
                        image_hash = self._upload_image(img_path)
                        logger.info("Uploaded image_path image, hash: %s", image_hash)
                    else:
                        logger.warning(
                            "image_path '%s' not found. Add an image to assets/ or set "
                            "image_url in ad_config.json. Proceeding without image — "
                            "Meta may reject the creative.", img_path
                        )

        if image_hash:
            link_data["image_hash"] = image_hash

        story = {
            "page_id": page_id,
            "link_data": link_data
        }

        creative = self.client.retry(lambda: self.account.create_ad_creative(params={
            AdCreative.Field.name: f"Creative | {cfg['campaign_name_prefix']}",
            AdCreative.Field.object_story_spec: story,
        }))
        logger.info("Created AdCreative ID: %s", creative["id"])
        return creative["id"]

    def _upload_image(self, image_path: str) -> str:
        img = self.client.retry(lambda: self.account.create_ad_image(
            params={AdImage.Field.filename: image_path}
        ))
        return img[AdImage.Field.hash]

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Ads — attach creative to each ad set
    # ─────────────────────────────────────────────────────────────────────────

    def create_ads(self, adset_ids: list, creative_id: str) -> list:
        ad_ids = []
        for adset_id in adset_ids:
            ad = self.client.retry(lambda: self.account.create_ad(params={
                Ad.Field.name: f"Ad | {datetime.now().strftime('%Y-%m-%d')} | {adset_id}",
                Ad.Field.adset_id: adset_id,
                Ad.Field.creative: {"creative_id": creative_id},
                Ad.Field.status: Ad.Status.active,
            }))
            logger.info("Created Ad ID: %s for AdSet %s", ad["id"], adset_id)
            ad_ids.append(ad["id"])
        return ad_ids

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Full Launch (orchestrator)
    # ─────────────────────────────────────────────────────────────────────────

    def launch(self, lead_form_id: str) -> dict:
        """Full launch: Campaign → AdSets → Creative → Ads."""
        logger.info("=== LAUNCHING META AD CAMPAIGN ===")
        campaign_id = self.create_campaign()
        creative_id = self.create_creative(lead_form_id)
        adset_ids = self.create_adsets(campaign_id, lead_form_id)
        ad_ids = self.create_ads(adset_ids, creative_id)

        result = {
            "campaign_id": campaign_id,
            "adset_ids": adset_ids,
            "creative_id": creative_id,
            "ad_ids": ad_ids,
            "total_daily_budget_inr": TOTAL_DAILY_BUDGET_INR,
        }
        logger.info("Launch complete: %s", result)
        return result
