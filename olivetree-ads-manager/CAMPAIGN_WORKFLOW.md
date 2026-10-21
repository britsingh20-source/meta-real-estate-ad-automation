# Home interior campaign workflow
## Scope
Adds a daily campaign proposal and dashboard review notification to the existing Olive Tree Ads Manager. Fixed account and existing write gates remain in place.
Target: 10 reported enquiries/day, INR 500 proposed media budget/day, INR 50 target CPL. No guarantee. Hosting, research provider and messaging costs are separate.

This release is source code, not an installed ChatGPT plugin or a verified live integration. It does not create a complete Meta campaign, upload media, activate ads, or send external campaign-ready alerts. Approval means "approved for setup", not publication. Existing Page-post ad creation remains a separate workflow.

## Implemented
- Existing ten-minute Worker trigger invokes daily preparation independently of Meta reporting credentials.
- Three original English ad-copy options for home interiors in Coimbatore, creative briefs and a higher-intent lead form specification.
- One shared INR 500/day campaign budget, not INR 500 per creative.
- Competitor evidence sample counts (storage/layout, kitchen, project proof); English keyword counts are descriptive, not a ranking of performance.
- Daily proposal deduplication, D1 lease for preparation and review, version-specific approvals.
- Dashboard notification and complete review panel.
- Explicit not_connected / no_matches / failed research states. Missing evidence produces a clearly labelled baseline proposal. It never claims competitor research succeeded.
- Input text is treated as untrusted data and cannot add offers or alter budgets.
- No customer contact details go to a research provider.
- Uses existing state and locks tables; no schema migration.

## Evidence-source setup still required
No commercial data service was purchased, enabled or connected. Birch account connection alone is not evidence that a competitor-ad API/feed is available.
Meta's public Ad Library website and Ad Library API have different coverage/access. Do not assume a connected Marketing API token can export Indian commercial competitor ads.
Verify a provider's coverage, access, terms and cost before using it.

Set COMPETITOR_FEED_URL in the Worker's environment to an administrator-controlled HTTPS JSON endpoint with no query parameters or embedded credentials. Optional bearer credential: COMPETITOR_FEED_TOKEN secret. No redirects. Maximum 300 KB, 50 observations, all-or-nothing validation.
This is a normalized feed adapter, not a built-in web search or scraper. A provider-specific collector must supply this format:

```json
{
  "complete": true,
  "ads": [{
    "name": "Example advertiser",
    "url": "https://www.facebook.com/ads/library/?id=1234567890",
    "text": "Verbatim visible ad text supplied by the evidence provider",
    "country": "IN",
    "market": "Coimbatore",
    "active": true,
    "observedAt": "2026-10-21T00:00:00Z"
  }]
}
```

The sample is a test fixture, not a real ad. Each observation must be at most seven days old, not future-dated, with a unique specific Ad Library URL. The provider must substantiate market relevance and observation time; this adapter validates shape/freshness and does not independently authenticate an ad's existence or actual targeting.
An empty complete feed means no matching results, not that no competitors are advertising.
Daily collection errors are disclosed; a user can retry the same day with Research & prepare proposal. New proposals require a new review. Dashboard keeps the latest proposal.

## Authenticated API
- GET /api/campaign-workflow: source configuration flag, latest proposal, last attempt and dashboard notification.
- POST /api/campaign-prepare: regenerate a proposal; does not publish.
- POST /api/campaign-approve with {"id":"current-proposal-id"}: records review approval only; stale IDs rejected.
These use existing dashboard bearer authentication and POST origin checks.

## Rollout
1. Run npm test and npm run check in olivetree-ads-manager.
2. Deploy through the project's existing Cloudflare process, preserving all secrets/bindings. Keep ENABLE_WRITES=false unless separately validated.
3. Confirm /health and authenticated dashboard. Generate a proposal; confirm source status is honest and review is version-specific.
4. Connect and verify an evidence feed. Test one actual active Coimbatore interior ad and validate its source manually.
5. Select owned media and configure campaign/lead form in Meta. Review active account budgets, existing spend, and spending controls.
6. Review the final ad and explicitly publish it through the existing authorised flow. Budget/reporting delays mean the current watchdog cannot promise a hard cash ceiling.

External notifications, automatic optimization, complete new Meta campaign/ad-set/form creation, installable ChatGPT MCP packaging and live end-to-end verification remain future work.
