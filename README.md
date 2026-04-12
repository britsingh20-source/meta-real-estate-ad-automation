# Meta Real Estate Ad Automation
> Automated Meta (Facebook/Instagram) Lead Generation for Real Estate — ₹200/day budget, location-precise targeting, fully run on GitHub Actions.

---

## What This Does

| Workflow | Schedule | What it does |
|---|---|---|
| `launch_ads.yml` | Daily 7 AM IST | Creates campaign → ad sets → creative → ads |
| `pull_leads.yml` | Every 2 hours | Pulls new leads from Meta Lead Forms to CSV |
| `budget_optimizer.yml` | Every 4 hours | Pauses high-CPL adsets, scales low-CPL winners, enforces ₹200/day cap |

---

## Project Structure

```
meta-ad-automation/
├── .github/workflows/
│   ├── launch_ads.yml          # Daily campaign launch
│   ├── pull_leads.yml          # Lead puller (every 2h)
│   └── budget_optimizer.yml    # Budget watchdog (every 4h)
├── config/
│   ├── locations.json          # Location groups (city / radius / pincode)
│   ├── ad_config.json          # Ad copy, headline, image, CTA
│   └── budget_rules.json       # CPL targets, scaling rules
├── src/
│   ├── meta_client.py          # Meta API wrapper
│   ├── campaign_manager.py     # Campaign / AdSet / Ad creation
│   ├── location_targeting.py   # Geo targeting engine
│   ├── lead_puller.py          # Lead fetcher with pagination
│   └── budget_optimizer.py     # CPL monitor & auto-optimizer
├── leads/                      # Auto-created CSVs go here
├── reports/                    # JSON run reports
├── main.py                     # CLI entry point
├── requirements.txt
└── .env.example
```

---

## Quick Setup (5 Steps)

### Step 1 — Fork / Clone this repo
```bash
git clone https://github.com/YOUR_USERNAME/meta-ad-automation.git
cd meta-ad-automation
```

### Step 2 — Add GitHub Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret Name | Where to find it |
|---|---|
| `META_APP_ID` | Meta Developer Portal → Your App |
| `META_APP_SECRET` | Meta Developer Portal → Your App |
| `META_ACCESS_TOKEN` | Graph API Explorer → long-lived Page token |
| `META_AD_ACCOUNT_ID` | Meta Business Manager (format: `act_XXXXXXX`) |
| `META_PAGE_ID` | Your Facebook Page ID |
| `META_LEAD_FORM_ID` | Meta Ads Manager → Lead Centre → Form ID |

### Step 3 — Configure locations
Edit `config/locations.json`:
- **City mode**: Add your city's Meta city key (look up via Graph API `/search?type=adgeolocation&q=Coimbatore`)
- **Radius mode**: Set lat/lng of your project site + radius in km
- **Pincode mode**: Add target pin codes

### Step 4 — Configure your ad creative
Edit `config/ad_config.json`:
- Update `headline`, `ad_body`, `description`
- Set `image_hash` (if image already uploaded to Meta) or `image_path` (local file)
- Set your `cta_type`: `GET_QUOTE`, `LEARN_MORE`, `BOOK_NOW`

### Step 5 — Run manually to test
```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
python main.py --action launch
python main.py --action pull_leads
python main.py --action optimize
```

---

## Budget Logic (₹200/day)

```
Total daily budget = ₹200
├── Split equally across N location ad sets
├── Floor: minimum ₹20 per ad set
├── Cap: maximum ₹80 per ad set (even after scaling)
│
├── If CPL > ₹150 → PAUSE that ad set
├── If CPL < ₹80  → SCALE budget by 30% (up to ₹80 cap)
└── If total spend ≥ ₹200 → PAUSE ALL immediately
```

Tune these thresholds in `config/budget_rules.json`.

---

## How to Find Your Meta City Key

```bash
curl "https://graph.facebook.com/v19.0/search?type=adgeolocation&q=Coimbatore&access_token=YOUR_TOKEN"
```
Copy the `key` from the response and paste it into `locations.json`.

---

## Leads Output

Leads are saved as CSV files in the `leads/` folder:
```
leads/leads_My_Form_Name_2025-07-01.csv
```
Fields: `lead_id`, `created_time`, `full_name`, `phone_number`, `email`, `city`, etc. (depends on your form fields).

---

## License
MIT — free to use and modify for your business.
