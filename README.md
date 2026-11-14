# Athena_LifePoweredbyTech

This repository contains the team project for the Life Powered by Tech hackathon. The main frontend app is the Expo + React Native project in `livebetter/`.

## Project structure

- `livebetter/` — active mobile frontend app used for demo mode and live integration work
- `backend/` — the one FastAPI backend: login, water, electricity, food, Big Brain, security (see `backend/README.md`)
- `research/big_brain/` — Manvi's Big Brain notebooks (originals; the backend uses the ported functions)
- `LiveBetter_Frontend_Starter/` — starter project and installation guidance
- `kentish/` — separate Expo experiment/prototype folder
- `README.md` — repo-level overview for the team

## Frontend app overview

The app is a mobile-first household management dashboard designed for:

- utility bill tracking for water and electricity
- pantry and grocery management
- household onboarding
- recipe suggestions based on available pantry ingredients
- AI coach guidance and utility scenarios
- local demo persistence using AsyncStorage

The frontend intentionally works in demo mode without a backend so the team can validate UX, flows, and logic before the real services are connected.

## Main codebase explanation

### `livebetter/app/`
This folder contains Expo Router screen files. Each file is a route/page.

- `app/index.tsx` — root route; redirects to the correct first screen
- `app/welcome.tsx` — welcome screen with login/register choices
- `app/login.tsx` — log-in screen (placeholder UI, not real auth)
- `app/register.tsx` — sign-up screen placeholder
- `app/onboarding.tsx` — multi-step household setup form
- `app/(tabs)/...` — main tabbed app screens:
  - home
  - utilities
  - water
  - electricity
  - bill
  - pantry
  - receipt
  - recipe/[id]
  - activity
  - coach
  - settings
  - pantry-updated

### `livebetter/src/`
This folder contains the shared app logic and types.

- `src/context.tsx` — global application state and app actions (`useApp`)
- `src/api.ts` — live backend integration layer and environment vars
- `src/mock.ts` — demo-data generators, local persistence, mock forecasts, mock insights
- `src/types.ts` — all shared data models (`Household`, `Bill`, `PantryItem`, `Recipe`, etc.)
- `src/ui.tsx` — shared page shell, cards, buttons, fields, navigation bar
- `src/theme.ts` — colors, spacing, typography, helper formatting
- `src/components/utility-detail.tsx` — detail page for water/electricity

### Config and project files

- `app.json` — Expo app metadata, Android package id, camera permissions
- `eas.json` — EAS build config
- `package.json` — app scripts and dependencies
- `.env.local` — environment variables for mock/live backend switching
- `tsconfig.json` — TypeScript config

## Installation and startup

### Prerequisites

- Node.js LTS
- npm
- Git
- Expo Go on Android (or emulator)

### Install

From the repo root:

```bash
cd Athena_LifePoweredbyTech/livebetter
npm install
```

Create `.env.local` in `livebetter/`:

```env
EXPO_PUBLIC_USE_MOCKS=true
EXPO_PUBLIC_API_URL=https://your-fastapi-host.example
```

Notes:
- Keep `EXPO_PUBLIC_USE_MOCKS=true` for demo mode.
- Switch to `false` only when the backend is live and reachable.
- Never use `localhost` on a physical phone; use a real public HTTPS URL instead.

### Run the app

```bash
cd Athena_LifePoweredbyTech/livebetter
npx expo start
```

Common run options:

```bash
npx expo start --web
npm run android
npm run ios
npx expo start --clear
```

## App page flow and URL map

The app uses Expo Router. The active route URLs are:

| URL | File | Purpose |
|---|---|---|
| `/` | `app/index.tsx` | root redirect page |
| `/welcome` | `app/welcome.tsx` | first entry screen |
| `/login` | `app/login.tsx` | email + password; then the Microsoft Authenticator code if switched on |
| `/register` | `app/register.tsx` | create an account (backend `POST /auth/signup`) |
| `/(tabs)/bill?kind=water\|electricity` | `app/(tabs)/bill.tsx` | one form per utility; bill photo fills it in (`/bills/parse`) |
| `/(tabs)/habits?kind=` | `app/(tabs)/habits.tsx` | water habits (W1–W5) or appliances and habits (E1–E5) only |
| `/(tabs)/stock`, `/(tabs)/ingredients` | | groceries and stock; ingredient table |
| `/(tabs)/cook-now` | | scan an ingredient → what it is → recipes that use it → AI recipe if none → save → cook |
| `/(tabs)/activity`, `/(tabs)/activity-detail?category=` | | Activity tab: sections; timeline with dates and PDF export |
| `/security` | `app/security.tsx` | security pattern + optional Microsoft Authenticator (after registration and from Settings) |
| `/onboarding` | `app/onboarding.tsx` | household setup flow |
| `/(tabs)/home` | `app/(tabs)/home.tsx` | main dashboard |
| `/(tabs)/utilities` | `app/(tabs)/utilities.tsx` | utility overview |
| `/(tabs)/water` | `app/(tabs)/water.tsx` | water detail page |
| `/(tabs)/electricity` | `app/(tabs)/electricity.tsx` | electricity detail page |
| `/(tabs)/bill` | `app/(tabs)/bill.tsx` | add utility bill |
| `/(tabs)/pantry` | `app/(tabs)/pantry.tsx` | pantry and recipe finder |
| `/(tabs)/receipt` | `app/(tabs)/receipt.tsx` | add grocery receipt |
| `/(tabs)/recipe/[id]` | `app/(tabs)/recipe/[id].tsx` | recipe details and cook flow |
| `/(tabs)/pantry-updated` | `app/(tabs)/pantry-updated.tsx` | confirmation after cooking |
| `/(tabs)/coach` | `app/(tabs)/coach.tsx` | AI coach chat |
| `/(tabs)/activity` | `app/(tabs)/activity.tsx` | household log |
| `/(tabs)/settings` | `app/(tabs)/settings.tsx` | settings and household info |

### Page flow

```text
/ -> index.tsx
   -> if household exists: /(tabs)/home
   -> otherwise: /welcome

/welcome
   -> /login or /register

/register -> /security?setup=1 (set pattern; "Do you want Microsoft Authenticator?" yes / not now) -> /onboarding
/login -> (code from Microsoft Authenticator, if on) -> /(tabs)/home, or /onboarding if no household yet

/onboarding
   -> save household setup
   -> /(tabs)/home

/(tabs)/home
   -> utilities, pantry, coach, activity, settings
   -> add bill: /(tabs)/bill
   -> scan receipt: /(tabs)/receipt
   -> view pantry recipe: /(tabs)/recipe/[id]
   -> cook -> /(tabs)/pantry-updated

/(tabs)/utilities
   -> /(tabs)/water or /(tabs)/electricity
   -> /(tabs)/bill?kind=water|electricity

/(tabs)/pantry
   -> /(tabs)/receipt
   -> /(tabs)/recipe/[id]
   -> /(tabs)/activity

/(tabs)/coach
   -> suggestions and scenario-based advice
```

## App behavior summary

### Demo mode
The app uses `DEMO_MODE = process.env.EXPO_PUBLIC_USE_MOCKS !== 'false'` in `src/api.ts`.

- When `EXPO_PUBLIC_USE_MOCKS=true`, the app runs against mock data and local AsyncStorage.
- When `EXPO_PUBLIC_USE_MOCKS=false`, it tries to call the backend using `EXPO_PUBLIC_API_URL`.

### Data flow

- `src/context.tsx` holds the app-wide state and exposes actions like `onboard`, `addBill`, `confirmReceipt`, `recipes`, `cook`, and `scenario`.
- `src/mock.ts` simulates household, pantry, receipt, forecast, and recipe data for demo mode.
- `src/api.ts` defines the live routes that the frontend expects from the backend.
- `src/types.ts` keeps the contract consistent across the app.

### UI shell
`src/ui.tsx` provides the shared screen layout and tab navigation. Most pages use the generic `Page` component with common cards, buttons, and form fields.

## App structure after the 14 Nov redesign
Tabs: **Home · Utilities · Pantry · Coach · Activity**. Every element has a backend route behind it; features without
one were removed (language switch, manual pantry edit, expiry dates, "try one change").
- **Home:** Add a bill / Scan a receipt, utility baseline, Groceries (one card), Needs attention (security, missing
  bills, AI recommendations that matter now).
- **Utilities → Water / Electricity:** next billing cycle → *Why this estimate* (explainable AI: factors, bill
  calculation, what would make it more accurate) → past bills (✕ to delete, pattern needed) → habits (edit opens only
  that module's questions).
- **Pantry:** *Groceries and stock* (scan receipt, ingredient table) and *Cook with something now* (scan → description
  → recipes from the database that use it → AI recipe, labelled AI-generated, can be saved → cook → stock goes down).
- **Activity:** AI recommendations, Water, Electricity, Groceries and pantry, Security; each opens a timeline with
  date filter and PDF export (Kentish's export).

## 14 Nov (night) additions
- **Languages:** English, Français, Kreol Morisien. Chosen on the Welcome / Register screen and in Settings; all screens,
  forms and the activity PDF report use it (`livebetter/src/i18n.ts`, `src/translations.ts`). Calculated numbers never
  change. With `GEMINI_API_KEY`, the AI texts (forecast explanation, coach suggestion) are also written in that
  language, with the same number check. Kreol uses the standard spelling: please have a native speaker review it.
- **AI Coach (What if…?):** no preset questions. Shower changes count water AND water-heater electricity (if the water
  heater is electric); guests count water and electricity. Every answer has a rule-based suggestion; **Apply to my
  plan** (or typing "apply it") records the change (`household_actions`, Activity → AI recommendations) and saves it as
  a goal in the water / electricity module when possible. `POST /household/coach/apply`, `GET /household/plans`.
- **Recipes:** scanning an ingredient shows database recipes AND an AI-generated recipe; **Use this recipe · I cooked
  it** saves it and lowers the pantry stock; **My recipes** lists saved recipes and all database recipes.

## Phone / cloud checklist (Render + Supabase + APK)
- **Render environment variables:** `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `GEMINI_API_KEY`, `LIVEBETTER_SECRET`
  (long random text, never change it after go-live), optionally `MFA_ENCRYPTION_KEY`. Without `MFA_ENCRYPTION_KEY` the
  authenticator key is derived from `LIVEBETTER_SECRET`, so authenticators keep working after every redeploy.
- **Supabase SQL:** `backend/sql/03_module_state.sql` and `04_user_security.sql` must be run once.
- **Email confirmation:** with Supabase "Confirm email" on, Register shows "check your email"; the user confirms, logs
  in, and is taken to the security setup first. For the demo you can switch it off in Supabase → Authentication →
  Providers → Email.
- **Photos on Android** (receipt, bill, food scan) are uploaded with React Native's XMLHttpRequest; Expo's fetch rejected
  them ("Unsupported FormDataPart implementation").
- **Sessions:** Supabase tokens expire after about an hour; the app refreshes them automatically.
- **Render free plan sleeps:** open `https://YOUR-BACKEND.onrender.com/docs` a minute before the demo; the app waits up
  to 60 s for the first answer.

## Surprise card: Misuse

**Misuse we identified:** someone who picks up the owner's unlocked, signed-in phone (a child playing, a housemate,
a controlling partner) taps *Reset account*, deletes bills, changes the household details or switches security
off. The household loses its records and evidence (bills are proof of what was paid), and Big Brain gives
wrong advice.

**Safeguards (checked by the backend, not just hidden in the app):**

| Safeguard | How |
|---|---|
| Security pattern for protected actions | reset account, restore after a reset, delete/replace a bill, change household details, switch security off. Drawing it gives a one-time permission for that one action, valid 5 minutes (`X-Step-Up` header) |
| Lockout | 5 wrong patterns, passwords or codes → locked 5 minutes |
| The owner sees attempts | red alert on Home and in Settings → Security; every attempt in Activity ("BLOCKED: someone tried to reset the account without the pattern") |
| Undo | a reset hides the records and can be restored for 24 hours (pattern needed) |
| Microsoft Authenticator (optional) | offered after registration and in Settings → Security; login then needs password + 6-digit code; 8 one-time recovery codes; switching it off needs pattern AND code |
| Pattern can't be changed by the misuser | setting/changing it needs the account password (or an authenticator/recovery code) |

**Demo (2 minutes):** Settings → *Reset account* → draw a wrong pattern twice ("3 attempts left") → Cancel →
Home shows the red security alert → Activity shows the blocked attempts → owner draws the right pattern →
reset → *Restore my records* → everything is back. Then sign out and log in with the authenticator code.
Automated: `backend/tests/test_security.py` (6 tests).

## Quick team usage checklist

1. open the app in `/livebetter`
2. run `npm install`
3. set `.env.local`
4. run `npx expo start`
5. scan QR code in Expo Go
6. complete onboarding
7. add a sample water/electricity bill
8. add a recipe/receipt flow to test pantry updates
9. check AI Coach for usage insights

## Notes for the team

- This frontend is designed to be functional in demo mode before any backend contract is finalized.
- In live mode (`EXPO_PUBLIC_USE_MOCKS=false`) login, registration, security and every module run on the backend.
  Demo (mock) mode still works offline, but the security features need the backend.
- Do not store real personal information in demo data or commit secrets into `.env.local`.

For app-specific setup and command details, see the README inside `livebetter/`.

