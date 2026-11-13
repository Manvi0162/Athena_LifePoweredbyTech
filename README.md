# Athena_LifePoweredbyTech

This repository contains the team project for the Life Powered by Tech hackathon. The main frontend app is the Expo + React Native project in `livebetter/`.

## Project structure

- `livebetter/` — active mobile frontend app used for the current demo and live integration work
- `LiveBetter_Frontend_Starter/` — starter project and original installation notes
- `kentish/` — separate Expo prototype/demo app
- `README.md` — repo-level overview for the team

## Current frontend app overview

This project is now the LiveBetter household management app. The main screens and flow reflect the current app state:

- welcome / login / register screens
- onboarding household setup
- home dashboard
- utilities and utility detail pages for water and electricity
- bill entry flow
- pantry inventory and recipe recommendation flow
- receipt capture / item confirmation flow
- AI coach assistant
- activity log
- settings page
- pantry updated confirmation screen

The app intentionally starts in demo mode so the team can test the UX without depending on a live backend.

## Main codebase explanation

### `livebetter/app/`
This folder contains the Expo Router pages and screen tree used by the app.

- `app/index.tsx` — root redirect for first-time entry
- `app/welcome.tsx` — welcome page
- `app/login.tsx` — login UI placeholder
- `app/register.tsx` — registration UI placeholder
- `app/onboarding.tsx` — multi-step household assessment
- `app/(tabs)/home.tsx` — household dashboard
- `app/(tabs)/utilities.tsx` — utility overview
- `app/(tabs)/water.tsx` — water detail
- `app/(tabs)/electricity.tsx` — electricity detail
- `app/(tabs)/bill.tsx` — bill entry page
- `app/(tabs)/pantry.tsx` — pantry inventory and recipe finder
- `app/(tabs)/receipt.tsx` — add or review grocery receipt items
- `app/(tabs)/recipe/[id].tsx` — recipe detail and cook action
- `app/(tabs)/pantry-updated.tsx` — post-cook success screen
- `app/(tabs)/coach.tsx` — AI coach assistant screen
- `app/(tabs)/activity.tsx` — household history page
- `app/(tabs)/settings.tsx` — settings screen

### `livebetter/src/`
This folder contains the app logic shared across pages.

- `src/context.tsx` — app-wide state and action handlers (`useApp`)
- `src/api.ts` — live backend integration layer and `EXPO_PUBLIC_*` environment handling
- `src/mock.ts` — mock/demo data, persistence, recipe generation, and forecast logic
- `src/types.ts` — shared data contracts for households, bills, pantry, recipes, and activity
- `src/ui.tsx` — shared UI shell: page layouts, cards, buttons, fields, tabs
- `src/theme.ts` — styling constants and formatting helpers
- `src/components/utility-detail.tsx` — reusable detail component for utility screens

### Config and project files

- `app.json` — Expo app metadata, permissions, package name
- `eas.json` — EAS build config
- `package.json` — scripts and dependencies
- `.env.local` — demo/live environment values
- `tsconfig.json` — TypeScript setup

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

The current app route structure is:

| URL | Page | Purpose |
|---|---|---|
| `/` | `app/index.tsx` | root redirect |
| `/welcome` | `app/welcome.tsx` | first screen |
| `/login` | `app/login.tsx` | login placeholder |
| `/register` | `app/register.tsx` | register placeholder |
| `/onboarding` | `app/onboarding.tsx` | household assessment |
| `/(tabs)/home` | `app/(tabs)/home.tsx` | main dashboard |
| `/(tabs)/utilities` | `app/(tabs)/utilities.tsx` | utility overview |
| `/(tabs)/water` | `app/(tabs)/water.tsx` | water detail |
| `/(tabs)/electricity` | `app/(tabs)/electricity.tsx` | electricity detail |
| `/(tabs)/bill` | `app/(tabs)/bill.tsx` | add bill |
| `/(tabs)/pantry` | `app/(tabs)/pantry.tsx` | pantry and recipe finder |
| `/(tabs)/receipt` | `app/(tabs)/receipt.tsx` | review purchase receipt |
| `/(tabs)/recipe/[id]` | `app/(tabs)/recipe/[id].tsx` | recipe details |
| `/(tabs)/pantry-updated` | `app/(tabs)/pantry-updated.tsx` | cook confirmation |
| `/(tabs)/coach` | `app/(tabs)/coach.tsx` | AI coach |
| `/(tabs)/activity` | `app/(tabs)/activity.tsx` | household activity log |
| `/(tabs)/settings` | `app/(tabs)/settings.tsx` | settings |

### Page flow

```text
/ -> index.tsx
   -> if household is saved: /(tabs)/home
   -> else: /welcome

/welcome
   -> /login or /register
   -> /onboarding

/onboarding
   -> save household details
   -> /(tabs)/home

/(tabs)/home
   -> /(tabs)/utilities
   -> /(tabs)/pantry
   -> /(tabs)/coach
   -> /(tabs)/activity
   -> /(tabs)/settings
   -> /(tabs)/bill
   -> /(tabs)/receipt
   -> /(tabs)/recipe/[id]
   -> /(tabs)/pantry-updated

/(tabs)/utilities
   -> /(tabs)/water or /(tabs)/electricity
   -> /(tabs)/bill

/(tabs)/pantry
   -> /(tabs)/receipt
   -> /(tabs)/recipe/[id]
   -> /(tabs)/activity
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

