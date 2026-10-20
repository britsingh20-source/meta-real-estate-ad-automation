# Olive Tree Ads Manager — direct Meta integration

Account: **464678014577329**. Business portfolio: **876378461847162**.
Target: **10 reported enquiries/day at INR 500 average media spend/day**.
Targets are not guarantees. Hosting, AI and messaging costs are separate.

## Implemented in this release
- Responsive private dashboard with empty states (no fabricated performance).
- Direct Graph/Marketing API client, bearer tokens, bounded retries through the durable lead inbox, complete pagination or fail-closed response.
- Ten-minute Cloudflare scheduled sync; seven-day ad metrics and account-wide daily spend.
- Signed Page lead webhook, deduplicated inbox, account verification before contact storage, retry backoff and manual recent-form reconciliation.
- Lead stages: new, contacted, qualified, site_visit, quotation, won, lost, invalid.
- Competitor observation register with HTTPS sources and dates; competitor leads and spend unknown.
- Workers AI briefing grounded in aggregate data, with one daily scheduled briefing after connection. No lead contact details sent to AI.
- Existing Page post + existing ad set draft workflow; creation PAUSED, explicit activation, combined active daily-budget check.
- Observe mode by default. Optional budget guard pauses only app-managed ads at reported INR 500 account spend.
- Audit trail, D1 leases for sync/writes, fail-closed auth and live-write gate.

## Not yet implemented / not live
Direct Meta credentials and permissions are **not connected by deployment**.
End-to-end publishing, signed test leads and real reporting must be validated with authorised assets.
Automated competitor collection, new campaign/ad-set creation, generated video production, automatic creative experiments, CAPI outcome feedback, external notifications and external CRM integration are future work. The built-in lead desk is implemented.
No automatic budget increase or next-day resumption. Budget guard cannot guarantee a hard daily cash ceiling due to delivery/reporting delay and unmanaged campaigns.

## Deploy
1. Install Node 22+ and run `npm install`.
2. `npx wrangler d1 execute olivetree-ads-manager --remote --file schema.sql`.
3. Set secrets with `npx wrangler secret put NAME`, using the interactive prompt:
   - `ADMIN_TOKEN`: at least 32 random bytes, used only by the private dashboard.
   - `META_ACCESS_TOKEN`: authorised account read/write token.
   - `META_PAGE_ACCESS_TOKEN`: authorised Page lead token.
   - `META_APP_SECRET`: signature verification.
   - `META_VERIFY_TOKEN`: webhook verification.
4. Configure `META_PAGE_ID` and a currently supported `META_API_VERSION` in Cloudflare variables; verify version in Meta Developer Dashboard (no guessed default).
5. Keep `ENABLE_WRITES=false` until account currency/timezone, scopes, assets and lead retrieval pass live testing.
6. `npm test`, `npm run check`, `npx wrangler deploy`.
7. Configure Page `leadgen` subscription at `https://olivetree-ads-manager.britsingh20.workers.dev/webhooks/meta`.
8. Sign in with the dashboard key, sync, test a lead, reconcile, then enable bounded write operations as appropriate.

Do not commit credentials, leads or private reports to GitHub. The source repository is public; runtime contacts remain in the dedicated D1 database.

## Meta setup
Use a business-linked Meta developer app with access to the correct portfolio and account. Validate `ads_read`, `ads_management`, `leads_retrieval` and relevant Page scopes/access according to the actual app's access level, products and current Meta requirements. Access review or business verification may apply. Use Meta's official developer interface for credential provisioning; never paste tokens into chat.

## Operations
- Cron: `*/10 * * * *`; Meta account must report INR and Asia/Kolkata.
- Webhook: durable inbox first, contacts retrieved after ad-account verification.
- Failed inbox jobs stop after eight attempts and remain inspectable in D1; repeated webhook events do not duplicate them.
- Uncertain remote creation is marked `needs_reconciliation` and must never be blindly retried.
- Dashboard key exists only in tab memory. HTTPS and same-origin checks protect authenticated writes.
- Record actual customer outcomes; raw lead volume alone is not sufficient evidence of profitability.

## Validation
Pure rule checks and JavaScript syntax checks passed in the build session.
Node test suites cover target maths, India date boundaries, invalid metrics, messaging vs leads, budget guard, draft IDs, pagination, bearer auth and wrong-account rejection.
Live Meta integration remains unverified until credentials are configured.
