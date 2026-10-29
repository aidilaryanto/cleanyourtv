#!/usr/bin/env bash
# Apply or reset a theme on the CleanYourTV Android TV emulator.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [ -z "$SDK" ]; then
  for candidate in "$HOME/Library/Android/sdk" "$HOME/Android/Sdk"; do
    if [ -d "$candidate" ]; then SDK=$candidate; break; fi
  done
fi
ADB="$(command -v adb || true)"
if [ -z "$ADB" ]; then ADB="$SDK/platform-tools/adb"; fi
if [ -z "$SDK" ] || [ ! -x "$ADB" ]; then
  echo "ERROR: Android SDK Platform-Tools are required. Set ANDROID_HOME if needed." >&2
  exit 1
fi

AVD_NAME="CleanYourTV_TV_API_34"
SERIAL="${ANDROID_SERIAL:-}"
if [ -z "$SERIAL" ]; then
  while IFS= read -r candidate; do
    [ -n "$candidate" ] || continue
    name=$("$ADB" -s "$candidate" emu avd name 2>/dev/null | sed -n '1p' | tr -d '\r')
    if [ "$name" = "$AVD_NAME" ]; then SERIAL=$candidate; break; fi
  done < <("$ADB" devices | awk '$1 ~ /^emulator-[0-9]+$/ && $2 == "device" {print $1}')
fi
if [[ ! "$SERIAL" =~ ^emulator-[0-9]+$ ]]; then
  echo "ERROR: no Android emulator is selected. Start it with tools/simulator.sh first." >&2
  exit 1
fi
AVD="$("$ADB" -s "$SERIAL" emu avd name 2>/dev/null | sed -n '1p' | tr -d '\r')"
if [ "$AVD" != "$AVD_NAME" ]; then
  echo "ERROR: refusing to change theme on '$SERIAL' (expected $AVD_NAME, found '${AVD:-unknown}')." >&2
  exit 1
fi
if [ -z "$("${ADB}" -s "$SERIAL" shell pm path com.gathin.tvhome | tr -d '\r')" ]; then
  echo "ERROR: the launcher is not installed on $AVD_NAME. Start it with tools/simulator.sh first." >&2
  exit 1
fi

if [ "$#" -ne 1 ]; then
  echo "Usage: tools/simulator-theme.sh <theme-folder> | --reset" >&2
  exit 2
fi

PACKAGE=com.gathin.tvhome
URI="content://$PACKAGE.theme"
TMP=/data/local/tmp/cyt-theme
REVISION="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
REVISION_FILE="$(mktemp)"
printf '%s' "$REVISION" > "$REVISION_FILE"
trap 'rm -f "$REVISION_FILE"' EXIT
ADB_DEVICE=("$ADB" -s "$SERIAL")

put() {
  local source=$1 name=$2
  local output=""
  if ! output=$("${ADB_DEVICE[@]}" shell content write --uri "$URI/$name" < "$source" 2>&1) \
      || [[ "$output" == *"Error while accessing provider:"* || "$output" == *"Exception"* || "$output" == *"Permission Denial"* ]]; then
    echo "ERROR: could not write $name through the launcher theme provider." >&2
    [ -z "$output" ] || printf '%s\n' "$output" >&2
    return 1
  fi
}

delete() {
  local output=""
  if ! output=$("${ADB_DEVICE[@]}" shell content delete --uri "$URI/$1" 2>&1) \
      || [[ "$output" == *"Error while accessing provider:"* || "$output" == *"Exception"* || "$output" == *"Permission Denial"* ]]; then
    echo "ERROR: could not delete $1 through the launcher theme provider." >&2
    [ -z "$output" ] || printf '%s\n' "$output" >&2
    return 1
  fi
}

clear_wallpapers() {
  delete wallpapers
}

restart_launcher() {
  "${ADB_DEVICE[@]}" shell am force-stop "$PACKAGE"
  local output=""
  output=$("${ADB_DEVICE[@]}" shell am start -n "$PACKAGE/.MainActivity" 2>&1)
  if [[ "$output" == *"Error type"* || "$output" == *"Exception"* ]]; then
    echo "ERROR: the launcher could not be restarted on the Android TV simulator." >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}

if [ "$1" = --reset ]; then
  delete config.json
  delete wallpaper.jpg
  delete wallpapers/captions.txt
  clear_wallpapers
  put "$REVISION_FILE" theme_revision
  restart_launcher
  echo "Theme reset on the Android TV simulator."
  exit 0
fi

THEME="$1"
if [ ! -f "$THEME/config.json" ]; then
  echo "ERROR: no config.json in $THEME" >&2
  exit 1
fi
python3 -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8-sig"))' "$THEME/config.json" \
  || { echo "ERROR: $THEME/config.json is not valid JSON." >&2; exit 1; }

if [ -d "$THEME/wallpapers" ]; then
  while IFS= read -r -d '' image; do
    name=${image##*/}
    case "$name" in
      *.[jJ][pP][gG]|*.[jJ][pP][eE][gG]|*.[pP][nN][gG]|*.[wW][eE][bB][pP])
        if [[ ! "$name" =~ ^[A-Za-z0-9_.-]+$ || "$name" == *..* ]]; then
          echo "ERROR: unsupported wallpaper filename: $name" >&2
          exit 1
        fi
        ;;
    esac
  done < <(find "$THEME/wallpapers" -maxdepth 1 -type f -print0)
fi

put "$THEME/config.json" config.json
if [ -f "$THEME/wallpaper.jpg" ]; then
  put "$THEME/wallpaper.jpg" wallpaper.jpg
else
  delete wallpaper.jpg
fi
delete wallpapers/captions.txt
clear_wallpapers
if [ -d "$THEME/wallpapers" ]; then
  for image in "$THEME"/wallpapers/*; do
    [ -f "$image" ] || continue
    name=${image##*/}
    case "$name" in
      *.[jJ][pP][gG]|*.[jJ][pP][eE][gG]|*.[pP][nN][gG]|*.[wW][eE][bB][pP])
        put "$image" "wallpapers/$name"
        ;;
    esac
  done
fi
if [ -f "$THEME/wallpapers/captions.txt" ]; then
  put "$THEME/wallpapers/captions.txt" wallpapers/captions.txt
fi
put "$REVISION_FILE" theme_revision
restart_launcher
echo "Theme $(basename "$THEME") applied on the Android TV simulator."
