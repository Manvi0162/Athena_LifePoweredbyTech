# Athena_LifePoweredbyTech

This repository contains the frontend for the Life Powered by Tech hackathon project, built as an Expo + React Native app.

## Repository structure

- `livebetter/` — the active frontend app used for the demo and local testing
- `LiveBetter_Frontend_Starter/` — starter files and installation notes
- `kentish/` — an additional Expo project used for experimentation / alternate prototype work

## Frontend app to run

Use the app in `livebetter/`.

## Prerequisites

- Node.js LTS (18+ recommended; 20 LTS preferred)
- npm
- Git
- Expo Go installed on a physical Android device, or Android Studio / iOS simulator if you want emulators
- A device connected to the same Wi‑Fi network as your development machine when using Expo Go

## Install and run the frontend

From the repo root:

```bash
git clone <your-repo-url>
cd Athena_LifePoweredbyTech/livebetter
npm install
```

Create a local environment file:

```bash
copy NUL .env.local
```

Then add these values:

```env
EXPO_PUBLIC_USE_MOCKS=true
EXPO_PUBLIC_API_URL=https://your-fastapi-host.example
```

Notes:
- Keep `EXPO_PUBLIC_USE_MOCKS=true` for the offline demo experience.
- Change it to `false` only when a real backend is deployed and reachable.
- Do not put secrets or private keys in `EXPO_PUBLIC_*` values.

Start the app:

```bash
npx expo start
```

You can then:

- open the QR code in Expo Go on your phone
- run the web version with `npx expo start --web`
- launch Android with `npm run android`
- launch iOS with `npm run ios`

## Quick usage guide

1. Launch the app.
2. Complete onboarding with demo household details.
3. Explore the tabs: Home, Utilities, Pantry, Coach, and Activity.
4. Add a sample water and electricity bill to test the dashboard.
5. Add a sample receipt in Pantry to confirm the inventory flow.
6. Mark recipes as cooked to see stock changes.
7. Use the AI Coach to review suggestions and explainability details.

## Working with a real backend

When the backend is ready, set:

```env
EXPO_PUBLIC_USE_MOCKS=false
EXPO_PUBLIC_API_URL=https://your-production-or-staging-backend.example
```

Then restart Expo:

```bash
npx expo start --clear
```

Important: on a physical phone, never use `localhost` as the API host. Use a reachable HTTPS URL instead.

## Troubleshooting

- If Metro has cached stale state, run `npx expo start --clear`.
- If the app cannot connect to the API, verify the device and laptop are on the same network or use a public HTTPS endpoint.
- If packages fail to resolve, run:

```bash
npx expo install
```

- For type-checking, run:

```bash
npx tsc --noEmit
```

## Additional notes

This frontend is designed to work in demo mode without a real backend, which makes local testing and prototype validation easier. The app intentionally uses mock/demo data until the backend contract is fully integrated.

For more detailed setup and mock/backend instructions, see the app README in `livebetter/README.md`.
