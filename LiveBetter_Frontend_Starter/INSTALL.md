# LiveBetter Mobile Frontend — Step-by-step install

## Important
This starter was written for the 13–14 November 2026 hackathon. It includes an on-device demo that runs **without other members' backend**. The offline demo is NOT proof of real OCR, genuine recipe dataset usage, verified CWA/CEB tariff calculations, multi-user authentication, or a deployed API. Switch to real services with the owners' agreed contracts before claiming them in judging. AI-assisted code must be disclosed in the README per the hackathon rules.

## 0. Install prerequisites
- **Node.js LTS** https://nodejs.org (npm bundled)
- **VS Code** https://code.visualstudio.com
- **Git** https://git-scm.com/downloads (Windows: Git Bash)
- **Expo Go** on an Android phone. Connect your phone and development computer to the same Wi-Fi.
- An **Expo account** at https://expo.dev for standalone APK creation.
- **Optional:** Android Studio if you prefer an emulator. Not needed with a real Android phone.

Confirm in Git Bash or terminal:
```bash
node -v
npm -v
git --version
```

## 1. Fast automated install — Git Bash / Linux / macOS
Unzip the provided starter package. Open Git Bash **inside the extracted `LiveBetter_Frontend_Starter` directory**:
```bash
bash install-from-starter.sh
cd ../livebetter
npx expo start --clear
```
The installer will create an Expo project in a new sibling folder called `livebetter`, replace scaffold route files with the provided app, install the two additional dependencies, and create `.env.local`. It needs an internet connection. If the installer asks you to select an SDK, choose the Expo Go-compatible default (during the November 2026 transition this is SDK 57).

## 1b. Manual equivalent (if automatic script fails)
From the folder **containing** `LiveBetter_Frontend_Starter`:
```bash
npx create-expo-app@latest livebetter
cd livebetter
rm -rf app src
cp -R ../LiveBetter_Frontend_Starter/app ./app
cp -R ../LiveBetter_Frontend_Starter/src ./src
cp ../LiveBetter_Frontend_Starter/app.json ./app.json
cp ../LiveBetter_Frontend_Starter/eas.json ./eas.json
cp ../LiveBetter_Frontend_Starter/.env.example ./.env.local
cat ../LiveBetter_Frontend_Starter/.gitignore.append >> .gitignore
npx expo install expo-image-picker @react-native-async-storage/async-storage
npx expo start --clear
```
These are **bash/Git Bash** commands; `rm` and `cp` are not PowerShell syntax. If Windows is using PowerShell, open Git Bash from the extracted directory instead.

## 2. Start on Android
- Run `npx expo start` in the `livebetter` directory.
- Scan the QR code using Expo Go.
- If LAN cannot connect: `npx expo start --tunnel`.
- You should see **Welcome to LiveBetter**. Complete onboarding with fictional demo details.
- Confirm that the four tabs display at the bottom.

## 3. Test the frontend **before the backend exists**
- Open Utilities → Add bill. Enter water bill: 2026-10-01 to 2026-10-31, 13 m³, Rs 350. Save.
- Add electricity bill for the same range: 180 kWh, Rs 2100. Save.
- Review historical next-cycle baselines and caveats; DO NOT present values as official CEB/CWA tariff results.
- Open Pantry → Receipt → Load fictional sample receipt → Confirm purchase. Observe inventory increases and purchase amount in the dashboard.
- Find Vegetable Fried Rice → confirm cooking. Observe quantities decrease, but expenses do not increase.
- Mark a pantry item unavailable. Observe recipe coverage/missing ingredients change.
- Open AI Coach. See assumptions, source count and recommendations.
- Open Activity log. Confirm events survive closing/reopening the app.

## 4. Integrate backend when ready
In `.env.local`:
```dotenv
EXPO_PUBLIC_USE_MOCKS=false
EXPO_PUBLIC_API_URL=https://YOUR-FASTAPI-HOST.example
```
Restart the Expo server using `npx expo start --clear`. Never use `localhost` as a physical phone's API host; that would refer to the phone itself. Use a reachable HTTPS host.

**Backend contract currently PROPOSED, not verified:**
- `POST /households/onboarding` — JSON household fields
- `POST /bills` — bill fields + `household_id`
- `GET /utilities/forecast?household_id=...&category=water|electricity` — `Forecast` object
- `POST /receipts/parse` — multipart `file`, `household_id` → `{items, receipt_id}`
- `POST /receipts/confirm` — `{household_id, receipt_id, items}`
- `GET /pantry?household_id=...` — array or `{items:[...]}`
- `POST /pantry` / `PATCH /pantry` — PROPOSED additional CRUD paths; agree with M2/M4
- `POST /recipes/recommend` — `{household_id}` → array or `{recipes:[...]}`
- `POST /recipes/{id}/cook` — `{household_id, idempotency_key}`
- `GET /household/insights?household_id=...` — `Insight`
- `POST /household/scenarios` — `{household_id,category,reduction_percent}` → `Scenario`

**Authentication is intentionally not faked**: the frontend's onboarding is a local **demo-account entry**, NOT production login/signup. Member 2 needs to provide Supabase/Auth requirements; then wire a short-lived user JWT in `src/api.ts`, enforce server-side household isolation, and remove demo-only client assumptions. Do not commit private keys or tokens. A client-controlled `household_id` is not an authorization scheme. Demo profile persistence and activity entries in Live mode are not authoritative database reads.

For request/response shapes, see `src/types.ts`. Change types and adapters together with M2–M5; do not independently invent production contracts. Live mode returns API errors rather than silently switching to fictional data.

## 5. GitHub rules
Create a public repository at hackathon kickoff and commit the work actually produced during the event. Include the true development timeline, decision log and AI-tool usage disclosure. From within the `livebetter` directory:
```bash
git init
git add .
git commit -m "Build Expo LiveBetter mobile frontend demo"
# Then connect the actual public repository created by the team:
git remote add origin https://github.com/YOUR_ORG/YOUR_REPO.git
git branch -M main
git push -u origin main
```
DO NOT overwrite the team's existing history or blindly push to `main` if several teammates contribute. Prefer a feature branch and PR where required. Do not commit `.env.local`, bills with real personal details, APK credentials or API secrets. Verify `.gitignore` includes `.env*` except `.env.example`.

## 6. Android APK
```bash
npm install -g eas-cli
eas login
eas build:configure
eas build --platform android --profile preview
```
Accept EAS-managed Android signing if prompted. When ready, open the EAS build URL on Android and install the APK. This is a normal **standalone Android APK**, not Expo Go. The generated package may have a different filename from `LiveBetter.apk`.

Important: standalone APK still requires a deployed API if you build with `EXPO_PUBLIC_USE_MOCKS=false`. If building the offline demo, it works without a server but is insufficient for the hackathon's actual real-data/backend criteria. EAS environment configuration must contain the desired `EXPO_PUBLIC_` settings during the remote build; do not assume uncommitted `.env.local` is uploaded. For demo APK, configure the `preview` build environment to use `EXPO_PUBLIC_USE_MOCKS=true` or EAS environment variables; for live builds use the real HTTPS URL with `false`.

## 7. Troubleshooting
- **Blank/example screen:** remove both scaffold `app/` and `src/` before copying starter. Re-run `npx expo start --clear`.
- **Cannot resolve async-storage or image-picker:** `npx expo install @react-native-async-storage/async-storage expo-image-picker`.
- **QR not opening:** both devices same Wi-Fi; try `npx expo start --tunnel`.
- **Backend `Network request failed`:** use public HTTPS URL; do not use `localhost` on phone. Check FastAPI deployment, TLS, and permissions.
- **OCR doesn't happen in Demo mode:** intentional; manual entry is the fallback. OCR requires Member 4's endpoint.
- **Demo recipes do not satisfy real dataset rule:** intentional; use Member 4's verified UniTools dataset-backed endpoint.
- **Expo cloud build fails:** first ensure `npx expo start` works, then `npx expo-doctor`; inspect the specific EAS build logs.
- **Type-check:** run `npx tsc --noEmit` from the scaffolded Expo project after dependency install.

## 8. Judge-ready acceptance checks
- App works on physical Android and on the standalone preview APK.
- Onboarding saves and survives app restart (demo local, live persistent backend still requires read endpoint).
- Both historical bill forms and utility forecasts work.
- Receipt review allows all fields to be edited before authoritative save.
- A confirmed purchase increases grocery expense and pantry quantities exactly once.
- A confirmed cooking event changes stock but not grocery expense.
- Unavailable items change recipe coverage.
- AI Coach shows evidence, period, method, assumptions, and limitations.
- At least one **real recipe dataset** powers an actual live feature; sample data alone does not count.
- Verified CWA/CEB tariff rules replace historical-cost estimates before claiming official cost accuracy.
- Surprise-card adaptation, README, timed decision log, pitch, backup demo video, public Git history and required links are submitted by the organizer deadline.
