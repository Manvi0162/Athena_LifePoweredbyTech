#!/usr/bin/env bash
# Run inside the extracted LiveBetter_Frontend_Starter directory.
# Requires Node.js LTS, npm, network, and Git Bash (Windows) or a bash shell.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$(dirname "$HERE")/livebetter}"
if [[ -e "$TARGET" ]]; then
  echo "Target already exists: $TARGET"
  echo "Choose a new target, e.g. bash install-from-starter.sh ../livebetter-new"
  exit 1
fi
PARENT="$(dirname "$TARGET")"
PROJECT="$(basename "$TARGET")"
mkdir -p "$PARENT"
cd "$PARENT"
npx create-expo-app@latest "$PROJECT"
cd "$PROJECT"
# Clear starter routes; Expo Router must only find our app directory.
rm -rf app src
cp -R "$HERE/app" ./app
cp -R "$HERE/src" ./src
cp "$HERE/app.json" ./app.json
cp "$HERE/eas.json" ./eas.json
cp "$HERE/.env.example" ./.env.local
cat "$HERE/.gitignore.append" >> .gitignore
npx expo install expo-image-picker @react-native-async-storage/async-storage
printf '\nSUCCESS: Source installed to %s\n' "$TARGET"
printf 'Next commands:\n  cd "%s"\n  npx expo start --clear\n' "$TARGET"
