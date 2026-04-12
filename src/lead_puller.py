"""
Lead Puller
Fetches new leads from Meta Lead Ads forms and saves them to CSV.
Supports cursor-based pagination so duplicate leads are never saved.
"""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from .meta_client import MetaClient

logger = logging.getLogger(__name__)

LEADS_DIR = Path(__file__).parent.parent / "leads"
CURSOR_FILE = LEADS_DIR / ".cursor.json"      # tracks pagination cursor per form
LEADS_DIR.mkdir(exist_ok=True)


def load_cursors() -> dict:
    if CURSOR_FILE.exists():
        with open(CURSOR_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cursors(cursors: dict):
    with open(CURSOR_FILE, "w") as f:
        json.dump(cursors, f, indent=2)


def flatten_lead(lead: dict) -> dict:
    """Converts Meta field_data list → flat dict for CSV."""
    row = {
        "lead_id": lead.get("id"),
        "created_time": lead.get("created_time"),
    }
    for field in lead.get("field_data", []):
        key = field.get("name", "").strip().lower().replace(" ", "_")
        values = field.get("values", [])
        row[key] = values[0] if values else ""
    return row


class LeadPuller:
    def __init__(self, client: MetaClient):
        self.client = client
        self.page_id = client.page_id

    def pull_all_forms(self) -> int:
        """Pull leads from all active lead gen forms on the page."""
        forms = self.client.get_lead_forms(self.page_id)
        cursors = load_cursors()
        total_new = 0

        for form in forms:
            form_id = form["id"]
            form_name = form.get("name", form_id)
            after = cursors.get(form_id)

            new_count, new_cursor = self._pull_form(form_id, form_name, after)
            total_new += new_count

            if new_cursor:
                cursors[form_id] = new_cursor

        save_cursors(cursors)
        logger.info("Total new leads pulled: %d", total_new)
        return total_new

    def _pull_form(self, form_id: str, form_name: str, after_cursor: str = None):
        """Paginate through a form's leads and append to CSV."""
        today = datetime.now().strftime("%Y-%m-%d")
        csv_path = LEADS_DIR / f"leads_{form_name.replace(' ', '_')}_{today}.csv"

        all_leads = []
        last_cursor = after_cursor

        while True:
            page = self.client.get_leads(form_id, after_cursor=last_cursor)
            data = page.get("data", [])
            if not data:
                break

            all_leads.extend(data)

            paging = page.get("paging", {})
            cursors_obj = paging.get("cursors", {})
            last_cursor = cursors_obj.get("after")

            # Stop if no more pages
            if not paging.get("next"):
                break

        if not all_leads:
            logger.info("No new leads for form %s", form_name)
            return 0, last_cursor

        rows = [flatten_lead(l) for l in all_leads]
        fieldnames = list({k for r in rows for k in r.keys()})

        write_header = not csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerows(rows)

        logger.info(
            "Saved %d leads from form '%s' → %s",
            len(rows), form_name, csv_path
        )
        return len(rows), last_cursor

    def get_today_csv_paths(self) -> list:
        today = datetime.now().strftime("%Y-%m-%d")
        return list(LEADS_DIR.glob(f"*{today}*.csv"))

    def summarize_today(self) -> dict:
        """Returns a quick summary of today's leads across all CSVs."""
        summary = {}
        for csv_path in self.get_today_csv_paths():
            with open(csv_path, "r", encoding="utf-8") as f:
                count = sum(1 for _ in csv.DictReader(f))
            summary[csv_path.stem] = count
        return summary
