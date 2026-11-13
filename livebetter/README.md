# LiveBetter frontend

This is the Expo + React Native frontend for the Athena LifePoweredbyTech hackathon app. It is designed to work in demo mode first, so the team can validate screens, flows, and UX without waiting for the backend team.

## What the app does

- household onboarding and profile setup
- utility tracking for water and electricity
- pantry inventory management
- grocery receipt confirmation and stock updates
- recipe suggestions based on available ingredients
- AI coach answers and utility scenario insights
- local persistence with AsyncStorage for demo state

## Entire codebase overview

### `app/`
This folder contains Expo Router screens. Each file is a route/page in the app.

- `app/index.tsx` — root redirect for first-time entry
- `app/welcome.tsx` — welcome / entry page
- `app/login.tsx` — placeholder login screen
- `app/register.tsx` — placeholder register screen
- `app/onboarding.tsx` — multi-step household assessment
- `app/(tabs)/home.tsx` — main dashboard
- `app/(tabs)/utilities.tsx` — utility overview
- `app/(tabs)/water.tsx` — water detail page
- `app/(tabs)/electricity.tsx` — electricity detail page
- `app/(tabs)/bill.tsx` — add a utility bill
- `app/(tabs)/pantry.tsx` — pantry inventory + recipe discovery
- `app/(tabs)/receipt.tsx` — add and review grocery receipt items
- `app/(tabs)/recipe/[id].tsx` — recipe detail and cook confirmation
- `app/(tabs)/pantry-updated.tsx` — success screen after a cook action
- `app/(tabs)/coach.tsx` — AI coach chat assistant
- `app/(tabs)/activity.tsx` — household activity log and date-range PDF export
- `app/(tabs)/settings.tsx` — settings page

### `src/`
This folder contains shared logic used across screens.

- `src/context.tsx` — app-wide state and actions such as onboarding, adding bills, confirming receipts, and cooking recipes
- `src/api.ts` — live backend integration and environment variable handling
- `src/mock.ts` — local mock/state logic for demo mode; includes sample data, forecast logic, recipe matching, and AsyncStorage save/load
- `src/types.ts` — shared models for households, utilities, recipes, activity, pantry, and scenarios
- `src/ui.tsx` — shared screen shell, cards, buttons, inputs, and the bottom navigation
- `src/theme.ts` — color palette and common styling helpers
- `src/components/utility-detail.tsx` — reusable component for utility screens

### Other important files

- `app.json` — Expo app metadata and native permissions
- `eas.json` — EAS build configuration
- `package.json` — scripts and dependencies
- `.env.local` — environment settings for demo/live mode
- `tsconfig.json` — TypeScript setup
- `assets/` — app images and static resources

## Page flow and route structure

The app uses Expo Router. The main routes are:

| URL | File | Purpose |
|---|---|---|
| `/` | `app/index.tsx` | redirects to welcome |
| `/welcome` | `app/welcome.tsx` | welcome screen |
| `/login` | `app/login.tsx` | login UI placeholder |
| `/register` | `app/register.tsx` | registration UI placeholder |
| `/onboarding` | `app/onboarding.tsx` | setup household details |
| `/(tabs)/home` | `app/(tabs)/home.tsx` | dashboard |
| `/(tabs)/utilities` | `app/(tabs)/utilities.tsx` | utility overview |
| `/(tabs)/water` | `app/(tabs)/water.tsx` | water detail |
| `/(tabs)/electricity` | `app/(tabs)/electricity.tsx` | electricity detail |
| `/(tabs)/bill` | `app/(tabs)/bill.tsx` | add utility bill |
| `/(tabs)/pantry` | `app/(tabs)/pantry.tsx` | pantry and recipe finder |
| `/(tabs)/receipt` | `app/(tabs)/receipt.tsx` | scanning and confirming a grocery receipt |
| `/(tabs)/recipe/[id]` | `app/(tabs)/recipe/[id].tsx` | recipe detail page |
| `/(tabs)/pantry-updated` | `app/(tabs)/pantry-updated.tsx` | successful cook result |
| `/(tabs)/coach` | `app/(tabs)/coach.tsx` | AI coach page |
| `/(tabs)/activity` | `app/(tabs)/activity.tsx` | household log |
| `/(tabs)/settings` | `app/(tabs)/settings.tsx` | settings |

### Route flow

```text
/ -> index.tsx
   -> /welcome

/welcome
   -> /login or /register

/register
   -> account details form (authentication integration pending)

/onboarding
   -> save household details
   -> /(tabs)/home

/(tabs)/home
   -> open utilities, pantry, coach, activity, settings
   -> add bill: /(tabs)/bill
   -> add receipt: /(tabs)/receipt
   -> recipe detail: /(tabs)/recipe/[id]
   -> after cook: /(tabs)/pantry-updated

/(tabs)/utilities
   -> /(tabs)/water or /(tabs)/electricity
   -> /(tabs)/bill?kind=water|electricity

/(tabs)/pantry
   -> /(tabs)/receipt
   -> /(tabs)/recipe/[id]
   -> /(tabs)/activity

/(tabs)/activity
   -> filter history by inclusive start/end dates
   -> export matching entries as a PDF (browser print/save on web; share PDF on mobile)

/(tabs)/coach
   -> AI coach suggestions, scenarios, and utility guidance
```

## How the frontend is organized

### State management
`src/context.tsx` is the central state container. It exposes shared functions for:

- `onboard` — store household details
- `addBill` — save a water/electricity bill
- `addItem` — add or edit pantry items
- `confirmReceipt` — save confirmed grocery purchases
- `forecast` — return utility forecast data
- `insights` — return summary values
- `recipes` — return recipe suggestions
- `cook` — update pantry inventory after a recipe is cooked
- `scenario` — return an illustrative usage reduction scenario

### Demo behavior
The app is intentionally split between mock and live logic.

- `src/mock.ts` handles demo data, persistence, and example recipes.
- `src/api.ts` handles real backend calls when `EXPO_PUBLIC_USE_MOCKS=false`.
- `mock data` is stored using AsyncStorage under a demo key, so the app remains usable offline.

### UI framework
The UI is built with shared components from `src/ui.tsx` and styling from `src/theme.ts`.

Most pages follow the same shell:

- brand header
- optional back button
- content section
- bottom tab navigation for major app areas

## Install and run the frontend

### Prerequisites

- Node.js LTS (recommended 18+ or 20+)
- npm
- Git
- Expo Go on Android or an emulator

### Install dependencies

From the repo root:

```bash
cd Athena_LifePoweredbyTech/livebetter
npm install
```

Create `.env.local`:

```env
EXPO_PUBLIC_USE_MOCKS=true
EXPO_PUBLIC_API_URL=https://your-fastapi-host.example
```

### Start the app

```bash
npx expo start
```

Then do one of the following:

- scan the QR code in Expo Go on Android
- run `npx expo start --web`
- use Android Studio / simulator with `npm run android`
- use iOS simulator with `npm run ios`

For a clean restart:

```bash
npx expo start --clear
```

If a device cannot reach your laptop, use:

```bash
npx expo start --tunnel
```

## Live backend setup

When the backend is ready, set:

```env
EXPO_PUBLIC_USE_MOCKS=false
EXPO_PUBLIC_API_URL=https://your-production-or-staging-backend.example
```

Then restart Expo:

```bash
npx expo start --clear
```

Important:
- never use `localhost` as a phone API host
- use a reachable HTTPS endpoint instead
- do not store secrets or private tokens in `EXPO_PUBLIC_*` values

## Quick test flow

1. Launch the app.
2. Complete onboarding.
3. Open Utilities and add a sample water bill and electricity bill.
4. Open Pantry and add a sample receipt.
5. Confirm the inventory changes.
6. Open a recipe and cook it.
7. Open Activity and AI Coach to verify state updates.

## Troubleshooting

- Metro cache issues: `npx expo start --clear`
- Missing Expo packages: `npx expo install`
- Type-check issues: `npx tsc --noEmit`
- API connection issues: verify backend URL and device network access

## Notes for the team

This frontend is intentionally built to be fully functional in demo mode and to fail safely when a backend is not yet connected. That means the app can be tested, reviewed, and refined even before the backend team has finalized the contract.

The app does not claim real tariff calculations, OCR results, or authentication until those systems are integrated and verified.
