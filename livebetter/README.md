# LiveBetter frontend

This is the Expo frontend for the Athena LifePoweredbyTech project. It is a mobile-first React Native app built for the hackathon demo and allows local testing without a backend.

## What this app does

- local household onboarding and demo state
- utility bill tracking for water and electricity
- pantry and receipt workflows
- recipe suggestions and cook actions
- activity log and AI coach recommendations
- mock/demo mode for offline local testing

## Prerequisites

- Node.js LTS (18+ recommended; 20 LTS preferred)
- npm
- Git
- Expo Go on an Android device, or Android Studio / iOS simulator

## Install

From the repo root:

```bash
cd Athena_LifePoweredbyTech/livebetter
npm install
```

Create a local environment file:

```bash
copy NUL .env.local
```

Add the following contents:

```env
EXPO_PUBLIC_USE_MOCKS=true
EXPO_PUBLIC_API_URL=https://your-fastapi-host.example
```

For an offline demo, keep `EXPO_PUBLIC_USE_MOCKS=true`.

If a real backend is ready later, switch to:

```env
EXPO_PUBLIC_USE_MOCKS=false
EXPO_PUBLIC_API_URL=https://your-fastapi-host.example
```

## Run the app

Start the Expo dev server:

```bash
npx expo start
```

Then:

- scan the QR code with Expo Go on your Android phone
- or run the app in a browser with `npx expo start --web`
- or run Android Studio / iOS simulator with `npm run android` / `npm run ios`

If the device cannot reach the dev machine, use:

```bash
npx expo start --tunnel
```

## Quick test flow

1. Launch the app.
2. Complete the onboarding screen.
3. Open Utilities and add a sample water bill and electricity bill.
4. Open Pantry and add a sample receipt.
5. Confirm inventory updates.
6. Use a recipe and mark it as cooked.
7. Open the Activity and AI Coach sections to confirm data flows.

## Backend integration

The app checks `EXPO_PUBLIC_API_URL` and `EXPO_PUBLIC_USE_MOCKS` in `src/api.ts`.

- Demo mode: `EXPO_PUBLIC_USE_MOCKS=true`
- Live mode: `EXPO_PUBLIC_USE_MOCKS=false` with a real HTTPS host

Do not use `localhost` on a physical phone. Use the deployed API URL instead.

## Troubleshooting

- Clear Metro cache: `npx expo start --clear`
- Install missing Expo-compatible packages: `npx expo install`
- Check TypeScript: `npx tsc --noEmit`
- If the app cannot connect to API: verify the server is reachable and using HTTPS

## Development notes

This is a hackathon frontend intended to work in mock mode until backend services are available. The goal is to let the team develop and test the UI without blocking on backend dependencies.
