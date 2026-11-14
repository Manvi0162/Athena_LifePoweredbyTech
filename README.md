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


## LiveBetter — Backend Deployment & APK Build Guide

### 1. Backend Deployment (Render)

The LiveBetter backend uses **Python FastAPI**, hosted on **Render**, with **Supabase PostgreSQL** for database storage.

**Deployment steps:**
1. Push the backend code to the GitHub repository.
2. Open [Render Dashboard](https://dashboard.render.com/) and create a new **Web Service** connected to the GitHub repository.
3. Select the Python runtime and configure:
   - **Root Directory:** Backend folder (if applicable).
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Ensure `requirements.txt` includes `fastapi`, `uvicorn[standard]`, and other required dependencies.
5. Configure the necessary database credentials and API secrets in Render's environment variables.
6. Deploy and verify the backend at `https://YOUR-BACKEND.onrender.com/docs`.

**Updating the backend:**

```bash
git add .
git commit -m "Update backend"
git push origin Sanjana
```

If Auto-Deploy is enabled, Render automatically deploys changes pushed to the configured branch. Otherwise, use **Manual Deploy → Deploy latest commit**.

Use **Clear build cache & deploy** only when troubleshooting build or dependency caching problems.

### 2. Connect the Frontend to Render

In the Expo frontend's `.env.local` file:

```dotenv
EXPO_PUBLIC_USE_MOCKS=false
EXPO_PUBLIC_API_URL=https://YOUR-BACKEND.onrender.com
```

Replace the URL with the actual deployed backend address.

### 3. Run the Frontend (Development)

Open a terminal in the `livebetter` frontend folder:

```bash
npm install
npx expo start --clear
```

Scan the QR code using Expo Go on Android.

If there are network connection issues:

```bash
npx expo start --tunnel
```

### 4. Build the Android APK

**One-time setup:**

```bash
npm install -g eas-cli
eas login
eas build:configure
```

Ensure `eas.json` contains:

```json
{
  "build": {
    "preview": {
      "distribution": "internal",
      "environment": "preview",
      "android": {
        "buildType": "apk"
      }
    }
  }
}
```

**Configure production-connected API settings for the preview build:**

```bash
eas env:create --environment preview --name EXPO_PUBLIC_USE_MOCKS --value false --visibility plaintext
eas env:create --environment preview --name EXPO_PUBLIC_API_URL --value https://YOUR-BACKEND.onrender.com --visibility plaintext
```

If variables already exist, update them instead of creating duplicates.

**Build the APK:**

```bash
eas build --platform android --profile preview
```

After successful compilation, Expo provides a download link for the installable APK.

### 5. Architecture

**Android APK (React Native + Expo)** → **Render (FastAPI Backend)** → **Supabase PostgreSQL + AI/Forecasting Services**

The APK contains the mobile frontend. The backend runs separately on Render and communicates through HTTPS.

**Important:** Backend code changes require a Render redeployment but usually do not require rebuilding the APK. Frontend code changes require a new APK build for the updated installable application. Changes to the backend URL embedded in the APK also require rebuilding it.


## LiveBetter — Backend Contingency Plan (Render Failure)

**Objective:** Ensure LiveBetter remains demonstrable if Render crashes, becomes unavailable, or experiences network issues during the hackathon.

### Plan A — Restore Render (Primary)

1. Open [Render Dashboard](https://dashboard.render.com/) and inspect the service logs.
2. Check for missing dependencies, incorrect environment variables, or application errors.
3. Select **Manual Deploy → Deploy latest commit** to redeploy.
4. Verify `https://YOUR-BACKEND.onrender.com/docs` is accessible.

If Render is experiencing a platform-wide outage, immediately switch to Plan B.

### Plan B — Run FastAPI Locally (Secondary)

Run the backend on a team laptop connected to the same Wi-Fi as the Android device.

**1. Start the backend:**

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

**2. Find the laptop's local IPv4 address:**

Windows:

```bash
ipconfig
```

Look for the Wi-Fi adapter's IPv4 address, for example `192.168.1.10`.

**3. Update frontend `.env.local`:**

```dotenv
EXPO_PUBLIC_USE_MOCKS=false
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000
```

**4. Restart Expo:**

```bash
npx expo start --tunnel
```

Test the API using `http://192.168.1.10:8000/docs` from the phone.

**Important:** This local-IP approach is for development using Expo Go. An already-built APK retains its embedded API URL. Switching it to a local HTTP backend may require changing Android network-security settings and rebuilding the APK. The laptop and phone must share the same accessible network, and the laptop firewall must permit port 8000.

### Plan C — Offline Demo Mode (Last Resort)

If both cloud and local backend connections fail, use the frontend's existing mock-data functionality.

**1. Change `.env.local`:**

```dotenv
EXPO_PUBLIC_USE_MOCKS=true
```

**2. Restart Expo:**

```bash
npx expo start --tunnel
```

Demonstrate onboarding, sample utility estimates, pantry inventory, recipe interactions and AI Coach screens using explicitly labeled fictional data stored locally.

For a standalone offline APK, build a separate preview configuration with `EXPO_PUBLIC_USE_MOCKS=true` set in EAS.

**Limitation:** Demo mode does not prove actual backend integration, verified tariff calculations, real OCR or dataset-powered AI. Do not present it as equivalent to the live system.

**Failover priority:** Render → Local FastAPI → Offline Demo APK → Backup video.

## LiveBetter — APK Failure Contingency Plan

**Objective:** Demonstrate the full LiveBetter application if the Android APK fails to install, crashes, or cannot be built.

### Plan A — Run with Expo Go (Recommended Fallback)

Use Expo Go to run the React Native application directly on an Android phone without installing the standalone APK.

**1. Install Expo Go**

Download [Expo Go](https://expo.dev/go) on the Android phone. Ensure its SDK version is compatible with the project's Expo SDK.

**2. Open the frontend project**

In Git Bash or VS Code terminal:

```bash
cd livebetter
npm install
npx expo start --clear
```

**3. Connect the Android phone**

- Connect the laptop and phone to the same Wi-Fi network.
- Open Expo Go and scan the QR code displayed in the terminal.
- The LiveBetter application should load directly.

**4. If the network connection fails**

Stop Expo using `Ctrl + C`, then run:

```bash
npx expo start --tunnel
```

Scan the new QR code.

**Important:** The laptop must remain powered on, with the Expo development server running throughout the demonstration. The deployed FastAPI backend must also remain accessible.

### Plan B — Run in Laptop Browser (Secondary Fallback)

Expo supports running React Native applications in a web browser, provided the required web dependencies and components are compatible.

**1. Install web dependencies**

Inside the frontend directory:

```bash
cd livebetter
npx expo install react-dom react-native-web @expo/metro-runtime
```

**2. Verify backend configuration**

In `.env.local`:

```dotenv
EXPO_PUBLIC_USE_MOCKS=false
EXPO_PUBLIC_API_URL=https://YOUR-BACKEND.onrender.com
```

**3. Launch the web application**

```bash
npx expo start --web --clear
```

Open the local address displayed in the terminal, typically:

`http://localhost:8081`

**4. Demonstrate LiveBetter**

Use the browser to demonstrate onboarding, dashboard, utility estimates, pantry management, recipe recommendations, and AI Coach.

**Limitations:** Browser support must be tested in advance. Camera/image-picker behavior may differ from Android, and the FastAPI backend must allow the browser's origin through its CORS configuration.

### Plan C — Offline Demonstration (Last Resort)

If both the APK and backend integration fail, switch to the frontend's local demo mode.

Update `.env.local`:

```dotenv
EXPO_PUBLIC_USE_MOCKS=true
```

Restart Expo using either:

```bash
# Android through Expo Go
npx expo start --tunnel
```

Or:

```bash
# Laptop browser
npx expo start --web --clear
```

Demonstrate the predefined fictional household, manual bill entry, pantry operations, recipe interactions, and local AI Coach interface.

Clearly disclose that the demonstration uses simulated data rather than live backend services.

**Fallback priority:** Standalone APK → Expo Go → Laptop browser → Offline Demo → Backup video.

**Important:** Expo Go and the laptop browser are development-server alternatives, not standalone APK replacements. Both require the laptop and Expo server to remain running. They should be verified before the judging session, not configured for the first time during the demonstration.
