"""
main.py — Entry point for Meta Real Estate Ad Automation
Usage:
  python main.py --action launch
  python main.py --action pull_leads
  python main.py --action optimize
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from src.meta_client import MetaClient
from src.campaign_manager import CampaignManager
from src.lead_puller import LeadPuller
from src.budget_optimizer import BudgetOptimizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


def save_report(name: str, data: dict):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"{name}_{ts}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("Report saved: %s", path)


def action_launch(client: MetaClient):
    """Create a full campaign with ad sets, creative, and ads."""
    lead_form_id = (
        os.environ.get("LEAD_FORM_ID_OVERRIDE")
        or os.environ.get("META_LEAD_FORM_ID")
    )
    if not lead_form_id:
        logger.error("META_LEAD_FORM_ID not set. Cannot launch without a lead form.")
        sys.exit(1)

    manager = CampaignManager(client)
    result = manager.launch(lead_form_id=lead_form_id)
    save_report("launch", result)

    logger.info("=== LAUNCH SUMMARY ===")
    logger.info("Campaign ID  : %s", result["campaign_id"])
    logger.info("Ad Sets      : %s", result["adset_ids"])
    logger.info("Ads          : %s", result["ad_ids"])
    logger.info("Daily Budget : ₹%d", result["total_daily_budget_inr"])


def action_pull_leads(client: MetaClient):
    """Fetch new leads from all Meta lead gen forms."""
    puller = LeadPuller(client)
    total = puller.pull_all_forms()
    summary = puller.summarize_today()
    save_report("leads_summary", {"total_new": total, "by_form": summary})

    logger.info("=== LEADS SUMMARY ===")
    logger.info("New leads pulled: %d", total)
    for form, count in summary.items():
        logger.info("  %s: %d leads", form, count)


def action_optimize(client: MetaClient):
    """Run budget optimizer for the active campaign."""
    campaign_id = (
        os.environ.get("CAMPAIGN_ID_OVERRIDE")
        or os.environ.get("META_CAMPAIGN_ID")
    )
    if not campaign_id:
        # Try to find the latest active campaign automatically
        campaigns = client.list_campaigns()
        active = [c for c in campaigns if c.get("status") == "ACTIVE"]
        if not active:
            logger.error("No active campaigns found and META_CAMPAIGN_ID not set.")
            sys.exit(1)
        campaign_id = active[0]["id"]
        logger.info("Auto-selected campaign: %s", campaign_id)

    optimizer = BudgetOptimizer(client)
    report = optimizer.run(campaign_id)
    save_report("optimizer", report)

    logger.info("=== OPTIMIZER SUMMARY ===")
    logger.info("Total spend today : ₹%.2f", report["total_spend_inr"])
    logger.info("Total leads today : %d", report["total_leads"])
    logger.info("Paused ad sets    : %s", report["paused"] or "none")
    logger.info("Scaled ad sets    : %s", report["scaled"] or "none")


def main():
    parser = argparse.ArgumentParser(description="Meta Real Estate Ad Automation")
    parser.add_argument(
        "--action",
        choices=["launch", "pull_leads", "optimize"],
        required=True,
        help="Action to perform"
    )
    args = parser.parse_args()

    client = MetaClient()

    dispatch = {
        "launch": action_launch,
        "pull_leads": action_pull_leads,
        "optimize": action_optimize,
    }
    dispatch[args.action](client)


if __name__ == "__main__":
    main()
