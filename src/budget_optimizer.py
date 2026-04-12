"""
Budget Optimizer
Monitors active ad sets every 4 hours via GitHub Actions.
Enforces ₹200/day total cap, pauses overspenders, scales top performers.

Rules (configured in budget_rules.json):
  - If CPL > max_cpl_inr     → pause ad set immediately
  - If CPL < target_cpl_inr  → scale budget up (up to scale_cap_inr)
  - If total spend > 200 INR → pause all remaining ad sets for the day
"""

import json
import logging
from pathlib import Path
from typing import List, Dict

from .meta_client import MetaClient

logger = logging.getLogger(__name__)

BUDGET_RULES_PATH = Path(__file__).parent.parent / "config" / "budget_rules.json"
TOTAL_DAILY_BUDGET_INR = 200


def load_rules() -> dict:
    with open(BUDGET_RULES_PATH, "r") as f:
        return json.load(f)


def extract_cpl(insights: list) -> float:
    """Extracts cost-per-lead from insights response."""
    if not insights:
        return 0.0
    row = insights[0]
    for action in row.get("cost_per_action_type", []):
        if action.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
            try:
                return float(action["value"])
            except (KeyError, ValueError):
                pass
    return 0.0


def extract_spend(insights: list) -> float:
    if not insights:
        return 0.0
    try:
        return float(insights[0].get("spend", 0))
    except (ValueError, TypeError):
        return 0.0


def extract_leads(insights: list) -> int:
    if not insights:
        return 0
    row = insights[0]
    for action in row.get("actions", []):
        if action.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
            try:
                return int(action["value"])
            except (KeyError, ValueError):
                pass
    return 0


class BudgetOptimizer:
    def __init__(self, client: MetaClient):
        self.client = client
        self.rules = load_rules()

    def run(self, campaign_id: str) -> dict:
        """
        Main optimizer loop for a campaign.
        Returns a dict summarising actions taken.
        """
        rules = self.rules
        max_cpl = rules.get("max_cpl_inr", 150)
        target_cpl = rules.get("target_cpl_inr", 80)
        scale_cap_inr = rules.get("scale_cap_inr", 80)       # max budget per adset
        scale_factor = rules.get("scale_factor", 1.3)        # 30% increase on winners

        adsets = self.client.list_adsets(campaign_id)
        report = {
            "campaign_id": campaign_id,
            "total_spend_inr": 0.0,
            "total_leads": 0,
            "paused": [],
            "scaled": [],
            "kept": [],
        }

        # ── Step 1: Tally total spend ─────────────────────────────────────────
        adset_data: List[Dict] = []
        for adset in adsets:
            adset_id = adset["id"]
            adset_name = adset.get("name", adset_id)
            status = adset.get("status", "ACTIVE")

            insights = self.client.get_adset_insights(adset_id, date_preset="today")
            spend = extract_spend(insights)
            cpl = extract_cpl(insights)
            leads = extract_leads(insights)
            current_budget = int(adset.get("daily_budget", 0)) // 100   # paise → INR

            report["total_spend_inr"] += spend
            report["total_leads"] += leads

            adset_data.append({
                "id": adset_id,
                "name": adset_name,
                "status": status,
                "spend": spend,
                "cpl": cpl,
                "leads": leads,
                "current_budget": current_budget,
            })

        # ── Step 2: Hard cap — if total spend ≥ ₹200, pause everything ────────
        if report["total_spend_inr"] >= TOTAL_DAILY_BUDGET_INR:
            logger.warning(
                "Total spend ₹%.2f has hit ₹%d cap — pausing all active adsets.",
                report["total_spend_inr"], TOTAL_DAILY_BUDGET_INR
            )
            for ad in adset_data:
                if ad["status"] == "ACTIVE":
                    self.client.pause_adset(ad["id"])
                    report["paused"].append(ad["name"])
            return report

        # ── Step 3: Per-adset rules ───────────────────────────────────────────
        remaining_budget = TOTAL_DAILY_BUDGET_INR - report["total_spend_inr"]

        for ad in adset_data:
            adset_id = ad["id"]
            cpl = ad["cpl"]
            spend = ad["spend"]
            current_budget = ad["current_budget"]

            if ad["status"] != "ACTIVE":
                continue

            # No leads yet — skip until data matures (allow ₹30 spend)
            if spend < 30 and cpl == 0.0:
                report["kept"].append(ad["name"])
                logger.info("AdSet '%s' — not enough data yet (spend ₹%.1f)", ad["name"], spend)
                continue

            # Pause if CPL is too high
            if cpl > max_cpl:
                self.client.pause_adset(adset_id)
                report["paused"].append(ad["name"])
                logger.info(
                    "PAUSED '%s' — CPL ₹%.1f > max ₹%d",
                    ad["name"], cpl, max_cpl
                )
                continue

            # Scale up if CPL is great and we have remaining budget headroom
            if cpl < target_cpl and remaining_budget > 20:
                new_budget = min(
                    int(current_budget * scale_factor),
                    scale_cap_inr
                )
                if new_budget > current_budget:
                    self.client.update_adset_budget(adset_id, new_budget)
                    report["scaled"].append(f"{ad['name']} ₹{current_budget}→₹{new_budget}")
                    logger.info(
                        "SCALED '%s' — CPL ₹%.1f < target ₹%d → budget ₹%d→₹%d",
                        ad["name"], cpl, target_cpl, current_budget, new_budget
                    )
                else:
                    report["kept"].append(ad["name"])
            else:
                report["kept"].append(ad["name"])
                logger.info(
                    "KEPT '%s' — CPL ₹%.1f, spend ₹%.1f",
                    ad["name"], cpl, spend
                )

        logger.info(
            "Optimizer complete | spend=₹%.2f | leads=%d | paused=%d | scaled=%d",
            report["total_spend_inr"],
            report["total_leads"],
            len(report["paused"]),
            len(report["scaled"]),
        )
        return report
