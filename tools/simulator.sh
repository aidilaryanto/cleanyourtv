#!/usr/bin/env bash
# Build the launcher and run it in an Android TV emulator with a browser dashboard.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [ -z "$SDK" ]; then
  for candidate in "$HOME/Library/Android/sdk" "$HOME/Android/Sdk"; do
    if [ -d "$candidate" ]; then SDK=$candidate; break; fi
  done
fi
if [ -z "$SDK" ]; then
  echo "ERROR: Android SDK not found. Set ANDROID_HOME to its location." >&2
  exit 1
fi

EMULATOR="$SDK/emulator/emulator"
AVDMANAGER="$SDK/cmdline-tools/latest/bin/avdmanager"
IMAGE="system-images;android-34;android-tv;arm64-v8a"
AVD_NAME="CleanYourTV_TV_API_34"
ADB="$(command -v adb || true)"

if [ ! -x "$EMULATOR" ] || [ ! -x "$AVDMANAGER" ]; then
  echo "ERROR: Android Emulator and cmdline-tools are required in $SDK." >&2
  exit 1
fi
if [ -z "$ADB" ]; then
  ADB="$SDK/platform-tools/adb"
fi
if [ ! -x "$ADB" ]; then
  echo "ERROR: adb was not found. Install Android SDK Platform-Tools." >&2
  exit 1
fi
if [ -z "${JAVA_HOME:-}" ]; then
  if [ -x /usr/libexec/java_home ]; then
    JAVA_HOME="$(/usr/libexec/java_home -v 17 2>/dev/null || true)"
  fi
  for candidate in /opt/homebrew/opt/openjdk@17 /usr/local/opt/openjdk@17; do
    if [ -z "${JAVA_HOME:-}" ] && [ -x "$candidate/bin/java" ]; then JAVA_HOME=$candidate; fi
  done
fi
if [ -n "${JAVA_HOME:-}" ]; then export JAVA_HOME; export PATH="$JAVA_HOME/bin:$PATH"; fi

if [ ! -d "$SDK/system-images/android-34/android-tv/arm64-v8a" ]; then
  echo "ERROR: the Android TV API 34 system image is missing." >&2
  echo "Install it with: \"$SDK/cmdline-tools/latest/bin/sdkmanager\" \"$IMAGE\"" >&2
  exit 1
fi

if ! "$EMULATOR" -list-avds | grep -Fxq "$AVD_NAME"; then
  printf 'no\n' | "$AVDMANAGER" create avd --name "$AVD_NAME" --package "$IMAGE" --device tv_1080p
fi

find_running_avd() {
  while IFS= read -r serial; do
    [ -n "$serial" ] || continue
    name=$("$ADB" -s "$serial" emu avd name 2>/dev/null | sed -n '1p' | tr -d '\r')
    if [ "$name" = "$AVD_NAME" ]; then printf '%s\n' "$serial"; return 0; fi
  done < <("$ADB" devices | awk '$1 ~ /^emulator-[0-9]+$/ && $2 == "device" {print $1}')
}

SERIAL="$(find_running_avd || true)"
EMULATOR_PID=""
REMOTE_PID=""
cleanup() {
  if [ -n "$REMOTE_PID" ] && kill -0 "$REMOTE_PID" 2>/dev/null; then
    kill "$REMOTE_PID"
    wait "$REMOTE_PID" 2>/dev/null || true
  fi
  if [ -n "$EMULATOR_PID" ] && kill -0 "$EMULATOR_PID" 2>/dev/null; then
    kill "$EMULATOR_PID"
    wait "$EMULATOR_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [ -z "$SERIAL" ]; then
  PORT=5554
  while "$ADB" -s "emulator-$PORT" get-state >/dev/null 2>&1; do PORT=$((PORT + 2)); done
  SERIAL="emulator-$PORT"
  "$EMULATOR" -avd "$AVD_NAME" -no-window -no-audio -no-snapshot-load -no-boot-anim -port "$PORT" &
  EMULATOR_PID=$!
fi

echo "Waiting for Android TV emulator ($SERIAL) to finish booting..."
BOOTED=""
for _ in $(seq 1 180); do
  STATE=$("$ADB" -s "$SERIAL" get-state 2>/dev/null || true)
  if [ "$STATE" = device ]; then
    BOOTED=$("$ADB" -s "$SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')
    if [ "$BOOTED" = 1 ]; then break; fi
  fi
  if [ -n "$EMULATOR_PID" ] && ! kill -0 "$EMULATOR_PID" 2>/dev/null; then
    echo "ERROR: Android Emulator exited before it finished booting." >&2
    exit 1
  fi
  sleep 1
done
if [ "$BOOTED" != 1 ]; then
  echo "ERROR: Android TV emulator did not finish booting within 180 seconds." >&2
  exit 1
fi

ANDROID_HOME="$SDK" SIMULATOR_ADB_SERIAL="$SERIAL" SIMULATOR_AVD_NAME="$AVD_NAME" STOCK_LAUNCHER="" \
  "$ROOT/launcher/build-and-install.sh"
python3 "$ROOT/tools/simulator-remote.py" --adb "$ADB" --serial "$SERIAL" &
REMOTE_PID=$!
echo "The browser dashboard combines the emulator screen, TV status, and virtual remote."
echo "Stop the simulator with Ctrl+C in this terminal."
wait "$REMOTE_PID"
