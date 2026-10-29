# Android TV launcher simulator

Run the launcher in an Android TV virtual device and use its local web dashboard:

```bash
tools/simulator.sh
```

The script builds the release APK, creates the `CleanYourTV_TV_API_34` AVD if it does not exist,
starts it headlessly, then uses `launcher/build-and-install.sh` to build and install the launcher,
confirm it starts, disable a recognized stock Home app, and set it as Home. It then opens one local
browser dashboard. The dashboard shows the emulator screen, Android version, display resolution,
battery and power state, Wi-Fi state, uptime, and foreground app. Its virtual remote has D-pad, OK,
Back, Home, Menu, volume, and mute buttons. The screen refreshes about once a second and status
refreshes every two seconds. Stop the dashboard and an emulator started by the script with Ctrl+C
in the simulator terminal; the AVD and its app data remain available for the next run.

## Apply a theme

Keep the simulator running in one terminal. In a second terminal, apply a theme from this repo:

```bash
tools/simulator-theme.sh themes/aurora
```

The script uploads `config.json`, an optional `wallpaper.jpg`, and an optional `wallpapers/`
collection, then restarts the launcher in place. Reset to the built-in launcher configuration with:

```bash
tools/simulator-theme.sh --reset
```

Theme changes persist in the AVD between simulator runs. The helper only accepts the
`CleanYourTV_TV_API_34` emulator; it refuses to send theme files to a TV or another device.

On this Android TV emulator image, the system's Home key may still open Google's stock launcher.
The script starts the custom launcher directly so it can be tested; if Home takes you away from it,
rerun `tools/simulator.sh` to launch it again.

## Requirements

- JDK 17
- Android SDK Emulator, Platform-Tools, and the `android-34;android-tv;arm64-v8a` system image
- Python 3 (standard library only) and a browser

The script uses `ANDROID_HOME` or `ANDROID_SDK_ROOT` when set; otherwise it checks the standard
Android SDK locations on macOS and Linux. If the TV system image is missing, install it with:

```bash
sdkmanager "system-images;android-34;android-tv;arm64-v8a"
```

The dashboard binds only to `127.0.0.1`; it is not exposed to the network. Wi-Fi SSID and IP
addresses are not displayed. This is an emulator, not a substitute for checking the launcher on a
real TV. Hardware-specific settings, remote keys, HDMI inputs, Wi-Fi behavior, and performance can
differ.
