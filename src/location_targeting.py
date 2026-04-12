"""
Location Targeting Engine
Builds precise Meta Ads targeting specs from locations.json
Supports: city-level, radius (km), pin-code, and custom coordinate targeting.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "locations.json"


def load_locations() -> Dict:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def build_geo_locations(location_config: Dict) -> Dict[str, Any]:
    """
    Converts a location config entry into a Meta geo_locations targeting object.

    Supports three targeting modes:
      1. city   – target a Meta city by key (most precise for India)
      2. radius – lat/lng + radius_km for hyper-local targeting
      3. pincode – one or more pin codes
    """
    mode = location_config.get("mode", "city")
    geo = {}

    if mode == "city":
        # Meta city keys: look up via Graph API /search?type=adgeolocation&q=<city>
        geo["cities"] = [
            {
                "key": loc["meta_city_key"],
                "radius": loc.get("radius_km", 17),          # default 17 km buffer
                "distance_unit": "kilometer"
            }
            for loc in location_config["targets"]
        ]

    elif mode == "radius":
        geo["custom_locations"] = [
            {
                "latitude": loc["lat"],
                "longitude": loc["lng"],
                "radius": loc.get("radius_km", 10),
                "distance_unit": "kilometer",
                "address_string": loc.get("label", "")
            }
            for loc in location_config["targets"]
        ]

    elif mode == "pincode":
        geo["zips"] = [
            {"key": str(pin)}
            for loc in location_config["targets"]
            for pin in loc["pincodes"]
        ]

    geo["location_types"] = location_config.get("location_types", ["home", "recent"])
    return geo


def build_targeting_spec(location_config: Dict, audience_config: Dict) -> Dict[str, Any]:
    """
    Assembles the full Meta targeting spec for a Real Estate ad set.
    Combines geo, demographics, interests and behaviors.
    """
    geo_locations = build_geo_locations(location_config)

    targeting = {
        "geo_locations": geo_locations,
        "age_min": audience_config.get("age_min", 25),
        "age_max": audience_config.get("age_max", 55),
        "genders": audience_config.get("genders", [0]),     # 0=all, 1=male, 2=female
        "publisher_platforms": audience_config.get(
            "publisher_platforms", ["facebook", "instagram"]
        ),
        "facebook_positions": audience_config.get(
            "facebook_positions", ["feed", "marketplace"]
        ),
        "instagram_positions": audience_config.get(
            "instagram_positions", ["stream", "story", "reels"]
        ),
        "device_platforms": ["mobile", "desktop"],
    }

    # Real-estate interest targeting
    interests = audience_config.get("interests", [])
    behaviors = audience_config.get("behaviors", [])

    flex_spec = []
    if interests:
        flex_spec.append({"interests": interests})
    if behaviors:
        flex_spec.append({"behaviors": behaviors})
    if flex_spec:
        targeting["flexible_spec"] = flex_spec

    # Exclude renters / non-buyers if configured
    exclusions = audience_config.get("exclusions", [])
    if exclusions:
        targeting["exclusions"] = {"interests": exclusions}

    logger.info(
        "Built targeting spec | mode=%s | age=%d–%d | platforms=%s",
        location_config.get("mode"),
        targeting["age_min"],
        targeting["age_max"],
        targeting["publisher_platforms"]
    )
    return targeting


def get_all_targeting_specs() -> List[Dict]:
    """
    Returns one targeting spec per location group defined in locations.json.
    Each spec becomes one Ad Set in the campaign.
    """
    config = load_locations()
    audience = config.get("audience_defaults", {})
    specs = []

    for group in config["location_groups"]:
        spec = build_targeting_spec(group, {**audience, **group.get("audience_override", {})})
        specs.append({
            "name": group["name"],
            "targeting": spec,
            "daily_budget_inr": group.get("daily_budget_inr", 200)
        })

    logger.info("Generated %d targeting specs from locations.json", len(specs))
    return specs
