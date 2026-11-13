# Athena_LifePoweredbyTech

This repository contains the team project for the Life Powered by Tech hackathon. The main frontend app is the Expo + React Native project in `livebetter/`.

## Project structure

- `livebetter/` — active mobile frontend app used for demo mode and live integration work
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
| `/login` | `app/login.tsx` | login placeholder screen |
| `/register` | `app/register.tsx` | registration placeholder screen |
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

/login or /register
   -> user enters details (placeholder UI for now)
   -> /onboarding

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
- The app explicitly does not claim real tariff calculations, OCR reading, or live backend authentication unless those services are connected.
- Do not store real personal information in demo data or commit secrets into `.env.local`.

For app-specific setup and command details, see the README inside `livebetter/`.

