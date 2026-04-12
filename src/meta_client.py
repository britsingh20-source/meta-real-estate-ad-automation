"""
Meta API Client — wraps facebook-business SDK with retry logic and logging.
"""

import os
import time
import logging
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.leadgenform import LeadgenForm
from facebook_business.exceptions import FacebookRequestError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class MetaClient:
    """Initializes and manages the Meta Ads API session."""

    def __init__(self):
        self.app_id = os.environ["META_APP_ID"]
        self.app_secret = os.environ["META_APP_SECRET"]
        self.access_token = os.environ["META_ACCESS_TOKEN"]
        self.ad_account_id = os.environ["META_AD_ACCOUNT_ID"]  # e.g. act_XXXXXXXXXX
        self.page_id = os.environ["META_PAGE_ID"]

        FacebookAdsApi.init(self.app_id, self.app_secret, self.access_token)
        self.account = AdAccount(self.ad_account_id)
        logger.info("Meta API initialised for account: %s", self.ad_account_id)

    def get_account(self) -> AdAccount:
        return self.account

    def retry(self, fn, retries=3, delay=5):
        """Retry wrapper for transient Meta API errors."""
        for attempt in range(1, retries + 1):
            try:
                return fn()
            except FacebookRequestError as e:
                logger.warning("Attempt %d/%d failed: %s", attempt, retries, e)
                if attempt == retries:
                    raise
                time.sleep(delay * attempt)

    # ── Campaign helpers ──────────────────────────────────────────────────────

    def list_campaigns(self):
        return self.retry(lambda: self.account.get_campaigns(
            fields=[Campaign.Field.id, Campaign.Field.name,
                    Campaign.Field.status, Campaign.Field.daily_budget]
        ))

    def get_campaign(self, campaign_id: str) -> Campaign:
        return Campaign(campaign_id).api_get(
            fields=[Campaign.Field.id, Campaign.Field.name,
                    Campaign.Field.status, Campaign.Field.daily_budget]
        )

    # ── Ad Set helpers ────────────────────────────────────────────────────────

    def list_adsets(self, campaign_id: str):
        c = Campaign(campaign_id)
        return self.retry(lambda: c.get_ad_sets(
            fields=[AdSet.Field.id, AdSet.Field.name, AdSet.Field.daily_budget,
                    AdSet.Field.status, AdSet.Field.targeting,
                    AdSet.Field.bid_amount]
        ))

    def pause_adset(self, adset_id: str):
        adset = AdSet(adset_id)
        self.retry(lambda: adset.api_update(params={AdSet.Field.status: AdSet.Status.paused}))
        logger.info("Paused AdSet %s", adset_id)

    def resume_adset(self, adset_id: str):
        adset = AdSet(adset_id)
        self.retry(lambda: adset.api_update(params={AdSet.Field.status: AdSet.Status.active}))
        logger.info("Resumed AdSet %s", adset_id)

    def update_adset_budget(self, adset_id: str, daily_budget_inr: int):
        """daily_budget_inr in full Rupees — stored as paise (×100)."""
        adset = AdSet(adset_id)
        self.retry(lambda: adset.api_update(params={
            AdSet.Field.daily_budget: daily_budget_inr * 100
        }))
        logger.info("Updated AdSet %s budget to ₹%d/day", adset_id, daily_budget_inr)

    # ── Insights helpers ──────────────────────────────────────────────────────

    def get_adset_insights(self, adset_id: str, date_preset="today"):
        adset = AdSet(adset_id)
        return self.retry(lambda: adset.get_insights(
            params={"date_preset": date_preset},
            fields=["spend", "impressions", "clicks", "actions",
                    "cost_per_action_type", "cpm", "ctr"]
        ))

    def get_campaign_insights(self, campaign_id: str, date_preset="today"):
        campaign = Campaign(campaign_id)
        return self.retry(lambda: campaign.get_insights(
            params={"date_preset": date_preset},
            fields=["spend", "impressions", "clicks", "actions",
                    "cost_per_action_type", "cpm", "ctr"]
        ))

    # ── Lead form helpers ─────────────────────────────────────────────────────

    def get_lead_forms(self, page_id: str = None):
        from facebook_business.adobjects.page import Page
        pid = page_id or self.page_id
        page = Page(pid)
        return self.retry(lambda: page.get_lead_gen_forms(
            fields=[LeadgenForm.Field.id, LeadgenForm.Field.name,
                    LeadgenForm.Field.status]
        ))

    def get_leads(self, form_id: str, after_cursor: str = None):
        form = LeadgenForm(form_id)
        params = {"limit": 100}
        if after_cursor:
            params["after"] = after_cursor
        return self.retry(lambda: form.get_leads(
            params=params,
            fields=["id", "created_time", "field_data"]
        ))
