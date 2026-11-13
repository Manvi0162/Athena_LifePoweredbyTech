# LiveBetter — Complete Expo Frontend Starter

**Mobile client for the MDX 13–14 November 2026 "Powered to Live Better" hackathon.**

See **INSTALL.md** for exact setup, commands, testing, API integration, troubleshooting and APK generation.

## What works immediately in Demo mode
- Local household onboarding, preferences, budget target.
- Home dashboard, quick navigation, recent activity, reset.
- Manual water and electricity bill entry, historical next-cycle use/cost estimates, confidence labels, period and method transparency.
- Camera/gallery previews for bills and grocery receipts (no pretend OCR).
- Manual editable receipt review, explicit fictional sample input, purchase confirmation updating pantry and grocery expense.
- Manual inventory add/edit/unavailable and optional expiry field.
- Example recipe ranking by ingredient coverage, missing items, confirm cooking, idempotent local stock deductions.
- Explainability panel with evidence/assumptions and a what-if usage change that does not invent monetary savings.
- Persistent demo state after app restarts (AsyncStorage).
- API adapter with explicit Live mode, loading/errors, and planned endpoint contracts.
- Android EAS Build configuration for standalone APK.

## What's NOT implemented by this frontend package alone
- Server-side OCR/LLM/vision processing.
- Official CWA/CEB tariff-aware cost engine.
- Genuine third-party recipe dataset integration. All built-in demo recipes are fictional examples.
- Production login/session authentication or household row-level security.
- Deployment, trained forecast models, or accurate savings projections.
- Hardware data, meter-reading inputs, barcode reading.

The package is designed to allow **Member 1** to finish UI work without blocking on Members 2–5, without making false claims about completed integrations. Refer to the supplied `LiveBetter_Hackathon_Team_Blueprint.pdf`, especially pp. 5–12 and 15–17, for task allocation and honest-data rules.

## User data and AI disclosure
The offline app uses fictional demo records. It should not store sensitive bills or credentials in the public repository. AsyncStorage is unencrypted and suitable only for non-sensitive demo state, not real access tokens. The frontend starter was AI-assisted using ChatGPT; record AI tool usage and actual human contributions in the team README/decision log. Verify copyright/licensing obligations before using the authentic UniTools recipe dataset in production.
