# LiveBetter (Team Athena)

**IET MDX "Life Powered by Tech" hackathon, 13–14 November 2026 · Theme 3: Powered to Live Better**

LiveBetter is a mobile app for a Mauritian household. It predicts the next water and electricity bills before they
arrive, explains how each estimate was calculated, keeps the kitchen pantry up to date from grocery receipts, suggests what
to cook with what is already there, and shows what one change in habits does to both bills. It works in English,
French and Kreol Morisien.

| | |
|---|---|
| **Team** | Sanjana (water), Alexandra (electricity, database), Shruti (food, receipts, recipes), Manvi (AI recommendation engine), Kentish (app UI, deployment) |
| **App** | Expo / React Native (`livebetter/`) · Android APK via EAS, or Expo Go |
| **Backend** | One Python FastAPI service (`backend/`) on Render, Supabase (PostgreSQL + Auth) |
| **Tests** | 123 automated backend tests (`pytest`), plus browser end-to-end checks with Playwright |

Submission links (filled in by the team): APK / Expo link: `TO FILL` · Backup demo video: `TO FILL` · Pitch slides: `TO FILL`

---

## Contents
1. [Problem and user](#1-problem-and-user)
2. [What the app does](#2-what-the-app-does)
3. [Real data: what powers each feature](#3-real-data-what-powers-each-feature)
4. [How the predictions work](#4-how-the-predictions-work)
5. [Surprise card: Misuse](#5-surprise-card-misuse)
6. [Architecture and tech stack](#6-architecture-and-tech-stack)
7. [AI tools: how we used AI (honest disclosure)](#7-ai-tools-how-we-used-ai-honest-disclosure)
8. [Decision log](#8-decision-log)
9. [How to run it](#9-how-to-run-it)
10. [Repository structure](#10-repository-structure)
11. [Limitations we know about](#11-limitations-we-know-about)
12. [Deployment, APK build and contingency plans](#12-deployment-apk-build-and-contingency-plans)

---

## 1. Problem and user

**Our user:** a parent in a Mauritian family of four, paying CWA (water) and CEB (electricity) bills, doing the weekly
shop, and trying to stay within a monthly budget.

**Their problems:**
- **Bills are a surprise.** CWA and CEB charge in rising blocks: a few extra m³ or kWh fall into a more expensive
  block, and the family only finds out when the bill arrives.
- **Food is bought and forgotten.** There is no simple link between what is in the kitchen and what to cook.
- **Advice is generic.** "Save water" never says what a shorter shower is worth on *this* family's bill.

**Mauritian context:** the average Mauritian uses **198.9 litres of water per person per day** and the average
household **201.5 kWh of electricity per month** (Statistics Mauritius, *Energy and Water Statistics 2025*). Both
figures, the official CWA and CEB tariffs and Mauritian temperatures are used inside the app, not just on a slide.

## 2. What the app does

| Tab | What the user can do |
|---|---|
| **Home** | Predicted next water and electricity bills ("Your baseline"), "With your plan" after applying a change, groceries spent this month, **Needs attention** (security alerts, missing bills, the top 3 AI recommendations) |
| **Utilities** | Water and Electricity pages: next bill estimate with a low–high range, **Why this estimate** (explainable AI), **Accuracy so far** (MAPE), past bills, habit questions. Add a bill by **photo** (AI fills the form, the user checks and confirms) |
| **Pantry** | Stock and ingredients, **scan a receipt** (AI reads it, food and non-food separated, user confirms, no duplicate receipts), **scan an ingredient** with the camera, recipes from our database checked against the pantry with real quantities, an **AI recipe** from what the family has (allergies and diet respected), **I cooked it** lowers the stock, My recipes |
| **Coach** | A what-if conversation: "I want to shower more every day" → "How many minutes?" → effect on the water AND electricity bills and the budget → **Apply to my plan** → Home shows the predicted bills with the plan; ✕ removes it |
| **Activity** | Everything that happened, by category (AI, water, electricity, groceries, security), with a date filter and **PDF export** |
| **Settings** | Language (English / Français / Kreol Morisien), household details, security (pattern, Microsoft Authenticator), reset and 24-hour restore |

## 3. Real data: what powers each feature

All sources are listed with links in `backend/water/data/SOURCES.md` and `backend/electricity/data/SOURCES.md`.

| Dataset | Source | Feature it powers |
|---|---|---|
| CWA domestic tariff (rising blocks, minimum charge, meter rent, postal) | CWA tariff (Proag 2014, Tableau 3; unchanged since 2012), checked on a real CWA bill | Every water bill in rupees, the bill check, every water saving |
| CEB domestic tariff 2026 (12 blocks) + minimum charge by tariff code 110 / 120 / 140 | ceb.mu via Expat Mauritius (Jul 2026), checked on a real CEB bill (145 kWh → Rs 998) | Every electricity bill in rupees, every electricity saving |
| 198.9 L per person per day; 201.5 kWh per household per month | Statistics Mauritius, *Energy and Water Statistics 2025*, Tables 1 and 11 | "You vs Mauritius" benchmarks |
| Mauritian monthly temperature 2016–2025, coast and central plateau | ERA5 reanalysis (Open-Meteo archive) | Season adjustment of the water forecast |
| +2.6% water per °C (homes without AC) | Salvo (2018), *Nature Communications*: panel study of 121,480 Singapore households | Season adjustment of the water forecast |
| 4,219 days of smart-meter readings from 17 households | Zenodo 7506076 (CC BY 4.0), processed in `backend/water/data_prep/` | Weekend factor (×1.12) and the day-to-day spread used for the forecast range |
| Reservoir levels, rainfall by region, CWA production 2024–2025 | Statistics Mauritius ESI 2025, Tables 13–15 | "Dry month / reservoirs" context message on the water page |
| Shower 7.9 L/min, flush 9.8 L, washing machine 111 L/load, dripping tap 31 L/day | REU 2016 (Water Research Foundation), US EPA WaterSense | What-if and savings calculations |
| Appliance power (AC 1.2 kW, water heater 3 kW, …) | Typical ratings (assumptions, marked as such; the user can enter the label value) | Electricity savings in the Coach |
| Recipe database | Supabase tables `lb_recipes` / `lb_recipe_ingredients` | Recipes matched against the pantry |
| Demo household data | Fictional, clearly labelled (`database` branch seeds, `sample_water.json`, `demo_electricity.json`) | Demo only; no real personal data |

## 4. How the predictions work

The predictions are **statistics and rules on purpose, not machine learning**: one household has only 2 to 12 bills,
far too few to train a model, and every rupee must be explainable. (The organisers' brief says the same: "a simple
rule that works beats a model that doesn't".)

**Water forecast** (`backend/water/forecast.py`): a multiplicative seasonal baseline.
1. **Baseline:** the household's average m³ per day over its last 3 confirmed bills × days in the next bill period.
2. **Season and weekends:** each day × weekend factor (1.12) × temperature factor (1 + 2.6% × (month temperature −
   yearly average)), using the Mauritian temperatures.
3. **Visible adjustments, each on its own line:** the user's own "I expect +10% next month" (habit question W5),
   savings from actions completed since the last bill, and a self-correction if past forecasts were 3% or more off
   (median of real ÷ predicted).
4. **Cost:** the CWA rising-block tariff, never an average price per m³.
5. **Range:** with 3+ bills, from the household's own bill-to-bill spread; with 1–2 bills, a Monte Carlo simulation of
   the month (400 runs, days drawn from the real smart-meter distribution, 10th–90th percentile, wider with 1 bill).
6. **Accuracy:** walk-forward backtesting (each past bill predicted from the bills before it) gives **MAPE** (mean
   absolute percentage error), shown as "Accuracy so far ±X%". Each new bill is also compared with the forecast saved
   for that period.

**Electricity forecast** (`backend/electricity/forecast.py`): the household's average kWh per day from its bills and
meter readings × 30 days, range from its lowest and highest measured rates, CEB 2026 tariff, MAPE. It does not yet have
a season (air-conditioning) adjustment.

**Habit questions** (W1–W5, E1–E5): the bills already contain normal habits, so the answers do not change the forecast
(no double counting). They unlock personal savings; only "expected change next month" moves the forecast, as its own
line. "Not sure" stays unknown.

**AI recommendation engine** (`backend/big_brain/`, from Manvi's notebooks in `research/big_brain/`): collects the
recommendations calculated by the water, electricity and food modules, checks the data (receipt totals, possible
duplicate receipts), scores each action with **priority = 0.40 × impact + 0.35 × urgency + 0.25 × confidence**, adds a
bonus for the household's main goal, compares savings per 30 days, and shows the top 3 on Home.

**Coach** (`backend/big_brain/whatif.py`): rules turn the sentence into a concrete change (minutes, hours, guests…), ask
for anything missing, then the water and electricity engines recalculate both bills with the official tariffs. Hot
water links the two: litres × 0.5 hot × 4.186 kJ/L/°C × 25 °C ÷ 3,600 ÷ 0.9 efficiency = kWh. Applied plans are added
to the predicted bills on Home.

**Where AI is used inside the app, and how it is fenced in:** Gemini reads bill and receipt photos (the user always
confirms), recognises food in a photo, writes AI recipes from the real pantry, classifies unclear Coach sentences into
a fixed list of changes, and words explanations in English, French or Kreol. It never calculates a number: every
number in AI text is checked against our calculation, and if one does not match, the AI text is replaced by a template.
There is no RAG and no fine-tuned model.

## 5. Surprise card: Misuse

**Misuse we identified:** someone who picks up the owner's unlocked, signed-in phone (a child playing, a housemate,
a controlling partner) taps *Reset account*, deletes bills, changes the household details or switches security
off. The household loses its records and evidence (bills are proof of what was paid), and the recommendations become
wrong.

**Safeguards (checked by the backend, not just hidden in the app):**

| Safeguard | How |
|---|---|
| Security pattern for protected actions | Reset account, restore after a reset, delete a bill, change household details, switch security off. Drawing it gives a one-time permission for that one action, valid 5 minutes (`X-Step-Up` header) |
| Lockout | 5 wrong patterns, passwords or codes → locked 5 minutes |
| The owner sees attempts | Red alert on Home (refreshed when Home comes back into view) and in Settings → Security; every attempt in Activity |
| Undo | A reset hides the records; they can be restored for 24 hours (pattern needed) |
| Microsoft Authenticator (optional) | Offered after registration and in Settings → Security; login then needs password + 6-digit code; 8 one-time recovery codes; switching it off needs pattern AND code. Secret stored encrypted (Fernet) |
| Pattern cannot be changed by the misuser | Setting or changing it needs the account password (or an authenticator / recovery code) |

Built with public libraries only (`pyotp`, `segno`, `cryptography`). Tests: `backend/tests/test_security.py`.

## 6. Architecture and tech stack

```text
Android app (Expo / React Native, TypeScript, expo-router, EN / FR / Kreol)
        │  HTTPS, Supabase access token
        ▼
FastAPI backend on Render (Python) ── one login and household for every module
   ├─ water/         Sanjana: CWA tariff, forecast, what-if, habits
   ├─ electricity/   Alexandra: CEB tariff, forecast, appliances
   ├─ receipts/, pantry/, recipes/, food_recognition/   Shruti: receipts, pantry, recipes, cooking
   ├─ big_brain/     Manvi: recommendation ranking, coach, explanations
   ├─ core/          login, security (pattern, authenticator, lockouts, undo)
   └─ integration/   the app's routes
        │                                   │
        ▼                                   ▼
Supabase (cloud PostgreSQL + Auth,        Gemini API (Google), Groq / OpenRouter as fallback
row-level security: each household        for food photos: read photos, word explanations,
sees only its own rows)                   numbers checked, never calculated
```

**How the cloud is used:** the FastAPI backend runs on **Render** (free plan; it sleeps when idle, so the app waits up
to 60 s for the first answer). **Supabase** hosts the database and authentication, with row-level security. The
**Gemini** API key and all other secrets live only in the backend's environment variables, never in the app or in
git. The app is built as an **APK with EAS** (Expo's cloud build service).

**Cost and reach:** today everything runs on free tiers plus pay-per-use Gemini; the cost that grows with users is AI
photo reading. The app reaches families as an Android app in their own language; a utility, a bank or an NGO could
offer it to households.

**Stack:** Expo SDK 58, React Native, TypeScript, expo-router · Python, FastAPI, Pydantic, httpx · Supabase (PostgreSQL,
Auth, RLS) · pyotp, segno, cryptography · pandas / numpy (data preparation) · pytest, Playwright · GitHub, Render, EAS.

## 7. AI tools: how we used AI (honest disclosure)

The rules allow AI tools and ask us to say what we used them for. We used them a lot, and we want to be clear about it.

**AI tools used to build LiveBetter:**

| Tool | What we used it for |
|---|---|
| **Claude (Anthropic)** | The largest share of the code. Claude wrote most of the integration: merging the four modules into one backend, the shared login and household, the security layer for the surprise card, the conversational Coach, the explainable-forecast and bill-photo endpoints, the app redesign screens, the French / Kreol translations, the fixes for Android and Render, most of the tests, and drafts of this README, the pitch deck and the demo script. The commits authored as **"Athena integration"** were produced with Claude. It also explained the code to the team so that each of us can answer questions about it. |
| **ChatGPT (OpenAI)** | Brainstorming the idea and features, research questions, help with code and debugging, and wording. |
| **Codex (OpenAI)** | Writing and fixing parts of the code. |
| **GitHub Copilot** | Code completion in the editor. |
| **Figma (AI features)** | UI mockups and screen layouts for the app design. |

**What the team did:** chose the problem, the user and the surprise-card response; found, checked and cleaned the
Mauritian datasets and tariffs (and checked them against our own real CWA and CEB bills); built the first version of
each module (water, electricity, food, the Big Brain notebooks, the UI prototype, the Supabase database); decided the
design rules (statistics instead of ML, the AI never calculates, no expiry dates, no UI without a backend); reviewed and
tested what the AI tools produced on our own phones; deployed to Render, Supabase and EAS; and prepared the pitch. Where
AI-written code did not match what we wanted, we asked for changes or fixed it ourselves.

**AI used inside the app (at runtime):** Gemini (Google) reads bill and receipt photos, recognises food, writes AI
recipe drafts, classifies unclear Coach sentences and words explanations in three languages. Groq and OpenRouter are
fallback providers for food photos. All of them run on the backend with our keys; their output is checked (user
confirmation for photos, number check for text). The Kreol translations were machine-assisted and should be reviewed
by a native speaker.

## 8. Decision log

Times are Mauritius time (UTC+4), from our commit history.

| When | Decision | Why |
|---|---|---|
| Fri 12:46 | Theme 3, one user: a Mauritian family of four managing water, electricity and food on a budget | A specific person with a real monthly pain, rather than "everyone in Mauritius" |
| Fri 14:52 | Use the official CWA and CEB tariffs, checked against our own real bills, instead of a flat price per unit | Rising blocks are the real cause of bill surprises; a flat price would give wrong numbers |
| Fri 18:14 | Statistics and rules, not machine learning, with honest statuses ("preliminary" / "better supported") | One household has too few bills to train a model; every rupee must be explainable |
| Fri 20:51 | One FastAPI backend with each teammate's module and one shared login and household | Five separate services could not share data or be deployed in 24 hours |
| Fri 23:01 | Surprise card "Misuse": pattern for 5 sensitive actions, lockout, owner alert, 24-hour undo, optional Microsoft Authenticator | The real risk is someone else using the owner's unlocked phone; a login password alone does not stop that |
| Sat 01:27 | AI never calculates: Gemini only reads photos and words text, and any AI sentence with a number we did not calculate is replaced | Trust: a wrong number on a family's bill is worse than a plain sentence |
| Sat 01:35 | Redesign: remove every screen element without a backend behind it, remove expiry dates, bill photo fills the form | A smaller app that works end to end beats more features that don't |
| Sat 03:18 | Whole app in English, French and Kreol Morisien | Mauritian households read all three; numbers never change with the language |
| Sat 04:35 | Deploy on Render + Supabase, APK with EAS, with contingency plans (local backend, Expo Go, offline demo, video) | The app must work on a real phone during judging |
| Sat 05:21 | Coach becomes a conversation that asks follow-up questions, and applied plans change the predicted bills | Users do not write complete what-if questions; a plan should visibly change the forecast |
| Sat 06:17 | Accuracy shown as MAPE for both water and electricity (fixed the electricity average to absolute errors) | A percentage everyone understands, comparable between m³ and kWh and between homes |

## 9. How to run it

### Backend (local)
```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env        # local mode works with an empty .env (accounts and data in local files)
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```
- **Local mode** (no Supabase keys): demo login `demo@livebetter.mu` / `demo1234`.
- **Supabase mode:** set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in `backend/.env` and run the SQL files in
  `backend/sql/` once (01 → 04). The backend uses only the publishable key; the secret key is not used by any code
  and must never be put in the app or in git.
- **AI features:** set `GEMINI_API_KEY`. Without it, forecasts, tariffs, the Coach numbers and recipe matching still
  work; photo reading and AI wording are switched off with a clear message.
- **Render:** also set `LIVEBETTER_SECRET` (long random text, never change it after go-live), optionally
  `MFA_ENCRYPTION_KEY`.
- Full step-by-step guide: `backend/README.md`.

### App
```bash
cd livebetter
npm install
# livebetter/.env.local (never committed):
#   EXPO_PUBLIC_USE_MOCKS=false
#   EXPO_PUBLIC_API_URL=https://YOUR-BACKEND.onrender.com   (or http://<laptop IP>:8000)
npx expo start --tunnel
```
Scan the QR code with Expo Go. `EXPO_PUBLIC_USE_MOCKS=true` runs an offline demo with fictional data (the security
features and the AI need the backend).

### Tests
```bash
cd backend
python -m pytest -q
```

### Demo path (about 7 minutes)
Home baseline → Utilities → Water: *Why this estimate*, *Accuracy so far* → add a water bill from a photo → water
habits → Electricity → Pantry: scan a receipt, scan an ingredient, recipes, *I cooked it* → Home: *Needs attention* →
Coach: "I want to shower more every day" → 10 min → heater → *Apply to my plan* → Home: "With your plan" → Activity,
PDF, language switch → Settings: wrong pattern → Home alert → log in with the authenticator code.

## 10. Repository structure

| Folder | Contents |
|---|---|
| `livebetter/` | The mobile app (Expo / React Native). `app/` = screens (expo-router), `src/` = API client, state, translations, shared UI |
| `backend/` | The FastAPI backend: `water/`, `electricity/`, `receipts/`, `pantry/`, `recipes/`, `food_recognition/`, `big_brain/`, `core/`, `integration/`, `sql/`, `tests/` |
| `research/big_brain/` | Manvi's original notebooks for the recommendation engine (the backend uses the ported functions) |
| `LiveBetter_Frontend_Starter/` | The starter project and installation notes from the first hours |
| `kentish/` | Kentish's first UI prototype |
| `database` branch | Supabase schema extensions, the atomic RPC for the recommendation engine, fictional demo seeds |

Screens: `/welcome`, `/login`, `/register`, `/security`, `/onboarding`, and the tabs `/home`, `/utilities` (→ `/water`,
`/electricity`, `/bill`, `/habits`), `/pantry` (→ `/stock`, `/ingredients`, `/receipt`, `/cook-now`, `/my-recipes`,
`/recipe/[id]`), `/coach`, `/activity` (→ `/activity-detail`), `/settings`.

## 11. Limitations we know about

- Electricity has no season (air-conditioning) adjustment yet; we did not find a sourced Mauritian number for it.
- Appliance power values and the shower, flush and washing-machine defaults are typical (mostly North-American)
  figures; the user can replace them.
- Accuracy (MAPE) is only meaningful after a few bills; with 2–3 bills it is an early indication.
- The Kreol translation needs review by a native speaker.
- Photo reading depends on the Gemini API and on photo quality; the user always checks the values.
- Render's free plan sleeps; the first request can take about 50 seconds.

---

## 12. Deployment, APK build and contingency plans

*Written by Kentish.*

### LiveBetter — Backend Deployment & APK Build Guide

#### 1. Backend Deployment (Render)

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

#### 2. Connect the Frontend to Render

In the Expo frontend's `.env.local` file:

```dotenv
EXPO_PUBLIC_USE_MOCKS=false
EXPO_PUBLIC_API_URL=https://YOUR-BACKEND.onrender.com
```

Replace the URL with the actual deployed backend address.

#### 3. Run the Frontend (Development)

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

#### 4. Build the Android APK

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

#### 5. Architecture

**Android APK (React Native + Expo)** → **Render (FastAPI Backend)** → **Supabase PostgreSQL + AI/Forecasting Services**

The APK contains the mobile frontend. The backend runs separately on Render and communicates through HTTPS.

**Important:** Backend code changes require a Render redeployment but usually do not require rebuilding the APK. Frontend code changes require a new APK build for the updated installable application. Changes to the backend URL embedded in the APK also require rebuilding it.


### LiveBetter — Backend Contingency Plan (Render Failure)

**Objective:** Ensure LiveBetter remains demonstrable if Render crashes, becomes unavailable, or experiences network issues during the hackathon.

#### Plan A — Restore Render (Primary)

1. Open [Render Dashboard](https://dashboard.render.com/) and inspect the service logs.
2. Check for missing dependencies, incorrect environment variables, or application errors.
3. Select **Manual Deploy → Deploy latest commit** to redeploy.
4. Verify `https://YOUR-BACKEND.onrender.com/docs` is accessible.

If Render is experiencing a platform-wide outage, immediately switch to Plan B.

#### Plan B — Run FastAPI Locally (Secondary)

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

#### Plan C — Offline Demo Mode (Last Resort)

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

### LiveBetter — APK Failure Contingency Plan

**Objective:** Demonstrate the full LiveBetter application if the Android APK fails to install, crashes, or cannot be built.

#### Plan A — Run with Expo Go (Recommended Fallback)

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

#### Plan B — Run in Laptop Browser (Secondary Fallback)

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

#### Plan C — Offline Demonstration (Last Resort)

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
