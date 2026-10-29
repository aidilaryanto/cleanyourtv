#!/usr/bin/env python3
"""Serve a local simulator dashboard with a virtual remote and Android status."""

import argparse
import json
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


KEYS = {
    "up": "19",
    "down": "20",
    "left": "21",
    "right": "22",
    "ok": "23",
    "back": "4",
    "home": "3",
    "menu": "82",
    "volume-up": "24",
    "volume-down": "25",
    "mute": "164",
}

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CleanYourTV Simulator</title>
  <style>
    :root {
      color-scheme: dark;
      font: 15px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0c1018;
      color: #eef2fa;
      --panel: #151c28;
      --line: #2b3545;
      --muted: #9aa8ba;
      --accent: #73adff;
    }
    * { box-sizing: border-box; }
    body { min-width: 320px; min-height: 100vh; margin: 0; }
    header {
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
      padding: 18px clamp(16px, 3vw, 36px); border-bottom: 1px solid var(--line);
      background: #101620;
    }
    h1 { margin: 0; font-size: 19px; letter-spacing: .01em; }
    .connection { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
    .dot { width: 9px; height: 9px; border-radius: 50%; background: #f0ad4e; }
    .dot.online { background: #43d18b; box-shadow: 0 0 12px #43d18b66; }
    .layout {
      display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 18px;
      width: min(1500px, 100%); margin: 0 auto; padding: 20px clamp(14px, 2.4vw, 30px);
    }
    .screen-panel, .card { border: 1px solid var(--line); border-radius: 16px; background: var(--panel); }
    .screen-panel { display: flex; min-height: 360px; flex-direction: column; overflow: hidden; }
    .panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px;
      padding: 12px 16px; border-bottom: 1px solid var(--line); color: var(--muted); font-size: 13px; }
    #screen-state { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .screen-wrap { display: grid; flex: 1; min-height: 300px; place-items: center; padding: 10px;
      background: radial-gradient(ellipse at center, #202938 0, #111720 75%); }
    #screen { display: block; width: 100%; height: 100%; max-height: calc(100vh - 130px);
      object-fit: contain; image-rendering: auto; }
    #screen.empty { display: none; }
    #screen-empty { color: var(--muted); text-align: center; }
    aside { display: flex; flex-direction: column; gap: 14px; }
    .card { padding: 15px; }
    h2 { margin: 0 0 12px; font-size: 14px; font-weight: 650; }
    .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .stat { min-width: 0; padding: 10px; border: 1px solid #252f3e; border-radius: 11px; background: #111720; }
    .label { display: block; margin-bottom: 4px; color: var(--muted); font-size: 11px; text-transform: uppercase;
      letter-spacing: .07em; }
    .value { display: block; overflow: hidden; font-size: 13px; font-weight: 600; text-overflow: ellipsis; }
    .wide { grid-column: 1 / -1; }
    .remote { display: grid; grid-template: repeat(3, 54px) / repeat(3, 1fr); gap: 7px;
      width: min(100%, 220px); margin: 0 auto 12px; }
    button { border: 1px solid #3c485b; border-radius: 13px; background: #222c3b; color: #f6f8fc;
      font: inherit; font-size: 16px; font-weight: 650; cursor: pointer; touch-action: manipulation;
      user-select: none; transition: background .12s, transform .08s; }
    button:hover { background: #303d51; }
    button:active { transform: scale(.96); background: #3b4e69; }
    button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    .ok { border-radius: 50%; background: #31415a; font-size: 13px; }
    .empty { visibility: hidden; }
    .extras { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; }
    .extras button { min-height: 42px; font-size: 12px; }
    #remote-state { min-height: 1.4em; margin: 10px 0 0; color: var(--muted); text-align: center; font-size: 12px; }
    footer { padding: 0 16px 18px; color: #718096; text-align: center; font-size: 11px; }
    @media (max-width: 820px) {
      .layout { grid-template-columns: minmax(0, 1fr); }
      aside { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); align-items: start; }
      .screen-panel { min-height: 45vh; }
      .screen-wrap { min-height: 38vh; }
      #screen { max-height: 65vh; }
    }
  </style>
</head>
<body>
  <header>
    <h1>CleanYourTV Simulator</h1>
    <div class="connection"><span id="connection-dot" class="dot"></span><span id="connection">Connecting...</span></div>
  </header>
  <main class="layout">
    <section class="screen-panel" aria-label="Android TV screen">
      <div class="panel-heading"><span>LIVE SCREEN</span><span id="screen-state">Waiting for emulator</span></div>
      <div class="screen-wrap">
        <img id="screen" alt="Live Android TV simulator screen">
        <div id="screen-empty">Waiting for the emulator screen...</div>
      </div>
    </section>
    <aside>
      <section class="card">
        <h2>TV status</h2>
        <div class="stats">
          <div class="stat"><span class="label">Android</span><span id="android" class="value">—</span></div>
          <div class="stat"><span class="label">Resolution</span><span id="resolution" class="value">—</span></div>
          <div class="stat"><span class="label">Battery</span><span id="battery" class="value">—</span></div>
          <div class="stat"><span class="label">Power</span><span id="power" class="value">—</span></div>
          <div class="stat"><span class="label">Wi-Fi</span><span id="wifi" class="value">—</span></div>
          <div class="stat"><span class="label">Uptime</span><span id="uptime" class="value">—</span></div>
          <div class="stat wide"><span class="label">Active app</span><span id="foreground" class="value">—</span></div>
        </div>
      </section>
      <section class="card">
        <h2>Virtual remote</h2>
        <div class="remote" aria-label="Directional pad">
          <button class="empty" tabindex="-1" aria-hidden="true"></button>
          <button data-key="up" aria-label="Up">▲</button>
          <button class="empty" tabindex="-1" aria-hidden="true"></button>
          <button data-key="left" aria-label="Left">◀</button>
          <button class="ok" data-key="ok" aria-label="OK">OK</button>
          <button data-key="right" aria-label="Right">▶</button>
          <button class="empty" tabindex="-1" aria-hidden="true"></button>
          <button data-key="down" aria-label="Down">▼</button>
          <button class="empty" tabindex="-1" aria-hidden="true"></button>
        </div>
        <div class="extras">
          <button data-key="back">Back</button><button data-key="home">Home</button><button data-key="menu">Menu</button>
          <button data-key="volume-down">Vol −</button><button data-key="mute">Mute</button>
          <button data-key="volume-up">Vol +</button>
        </div>
        <p id="remote-state" role="status">Ready</p>
      </section>
    </aside>
  </main>
  <footer>Local dashboard · no SSID or network address is displayed</footer>
  <script>
    const $ = (id) => document.getElementById(id);
    const image = $("screen");
    let screenBusy = false;
    let statusBusy = false;

    async function refreshScreen() {
      if (screenBusy) return;
      screenBusy = true;
      try {
        const response = await fetch("/api/screen.png?t=" + Date.now(), { cache: "no-store" });
        if (!response.ok) throw new Error("Emulator screen is unavailable");
        const blob = await response.blob();
        const next = URL.createObjectURL(blob);
        const previous = image.dataset.url;
        image.onload = () => { if (previous) URL.revokeObjectURL(previous); };
        image.src = next;
        image.dataset.url = next;
        image.classList.remove("empty");
        $("screen-empty").hidden = true;
        $("screen-state").textContent = "Updating every second";
      } catch (error) {
        $("screen-state").textContent = "Waiting for emulator";
        $("screen-empty").hidden = false;
        image.classList.add("empty");
      } finally {
        screenBusy = false;
      }
    }

    async function refreshStatus() {
      if (statusBusy) return;
      statusBusy = true;
      try {
        const response = await fetch("/api/status?t=" + Date.now(), { cache: "no-store" });
        if (!response.ok) throw new Error("Status unavailable");
        const data = await response.json();
        $("connection").textContent = data.connection;
        $("connection-dot").classList.toggle("online", data.connection === "Connected");
        $("android").textContent = data.android;
        $("resolution").textContent = data.resolution;
        $("battery").textContent = data.battery;
        $("power").textContent = data.power;
        $("wifi").textContent = data.wifi;
        $("uptime").textContent = data.uptime;
        $("foreground").textContent = data.foreground;
      } catch (error) {
        $("connection").textContent = "Unavailable";
        $("connection-dot").classList.remove("online");
      } finally {
        statusBusy = false;
      }
    }

    document.querySelectorAll("[data-key]").forEach((button) => {
      button.addEventListener("click", async () => {
        const label = button.getAttribute("aria-label") || button.textContent.trim();
        $("remote-state").textContent = "Sending " + label + "...";
        try {
          const response = await fetch("/api/key", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key: button.dataset.key })
          });
          const result = await response.json();
          if (!response.ok) throw new Error(result.error || "Remote command failed");
          $("remote-state").textContent = "Sent " + label;
        } catch (error) {
          $("remote-state").textContent = error.message;
        }
      });
    });

    refreshScreen();
    refreshStatus();
    setInterval(refreshScreen, 1000);
    setInterval(refreshStatus, 2500);
  </script>
</body>
</html>
"""

STATUS_FIELDS = (
    "ro.product.manufacturer",
    "ro.product.model",
    "ro.build.version.release",
    "ro.build.version.sdk",
)


def parse_properties(output):
    properties = {}
    for line in output.splitlines():
        match = re.match(r"\[([^]]+)\]: \[(.*)]$", line.strip())
        if match:
            properties[match.group(1)] = match.group(2)
    return properties


def format_uptime(output):
    try:
        seconds = int(float(output.split()[0]))
    except (IndexError, ValueError):
        return "Unavailable"
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def parse_resolution(output):
    match = re.search(r"(\d+)x(\d+)", output)
    if not match:
        return "Unavailable"
    return f"{match.group(1)} × {match.group(2)}"


def parse_battery(output):
    values = {}
    for line in output.splitlines():
        match = re.match(r"\s*(level|status):\s*(\d+)", line)
        if match:
            values[match.group(1)] = int(match.group(2))
    level = values.get("level")
    status = values.get("status")
    battery = f"{level}%" if level is not None else "Unavailable"
    power = {2: "Charging", 3: "Discharging", 4: "Not charging", 5: "Full"}.get(status, "Unknown")
    return battery, power


def parse_wifi(output):
    if re.search(r"Wi-Fi is disabled|Wi-Fi disabled|mWifiEnabled\s*=\s*false", output, re.I):
        return "Disabled"
    if re.search(r"mNetworkInfo.*?state:\s*CONNECTED|NetworkInfo.*?state:\s*CONNECTED", output, re.I):
        return "Connected"
    if re.search(r"Wi-Fi is enabled|Wi-Fi enabled|mWifiEnabled\s*=\s*true", output, re.I):
        return "Enabled"
    return "Unknown"


def parse_foreground(output):
    patterns = (
        r"(?:mResumedActivity|topResumedActivity)=.*?\s([A-Za-z0-9._]+)/([A-Za-z0-9._$]+)",
        r"mFocusedApp=.*?\s([A-Za-z0-9._]+)/([A-Za-z0-9._$]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)
    return "Unavailable"


class Simulator:
    def __init__(self, adb, serial):
        self.adb = adb
        self.serial = serial
        self._status = {
            "connection": "Connecting",
            "android": "Unavailable",
            "resolution": "Unavailable",
            "battery": "Unavailable",
            "power": "Unknown",
            "wifi": "Unknown",
            "uptime": "Unavailable",
            "foreground": "Unavailable",
        }
        self._status_lock = threading.Lock()

    def command(self, *args, timeout=5, check=True):
        return subprocess.run(
            [self.adb, "-s", self.serial, *args],
            check=check,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def read(self, *args):
        try:
            result = self.command(*args)
        except (OSError, subprocess.SubprocessError):
            return ""
        return result.stdout.strip()

    def collect_status(self):
        state = self.read("get-state")
        status = dict(self._status)
        if state != "device":
            status["connection"] = "Offline"
            return status

        status["connection"] = "Connected"
        properties = parse_properties(self.read("shell", "getprop"))
        manufacturer = properties.get(STATUS_FIELDS[0], "")
        model = properties.get(STATUS_FIELDS[1], "")
        release = properties.get(STATUS_FIELDS[2], "")
        sdk = properties.get(STATUS_FIELDS[3], "")
        device_name = " ".join(value for value in (manufacturer, model) if value) or "Android TV"
        android_name = f"Android {release}" if release else "Android"
        if sdk:
            android_name += f" (API {sdk})"
        status["android"] = f"{device_name} · {android_name}"
        status["resolution"] = parse_resolution(self.read("shell", "wm", "size"))
        status["battery"], status["power"] = parse_battery(self.read("shell", "dumpsys", "battery"))
        status["wifi"] = parse_wifi(self.read("shell", "dumpsys", "wifi"))
        status["uptime"] = format_uptime(self.read("shell", "cat", "/proc/uptime"))
        status["foreground"] = parse_foreground(self.read("shell", "dumpsys", "activity", "activities"))
        return status

    def status(self):
        status = self.collect_status()
        with self._status_lock:
            self._status = status
            return dict(self._status)

    def cached_status(self):
        with self._status_lock:
            return dict(self._status)

    def send_key(self, key):
        keycode = KEYS.get(key) if isinstance(key, str) else None
        if keycode is None:
            raise ValueError("Unknown remote button")
        self.command("shell", "input", "keyevent", keycode)

    def capture_screen(self):
        result = subprocess.run(
            [self.adb, "-s", self.serial, "exec-out", "screencap", "-p"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        if not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("The emulator did not return a valid screen image")
        return result.stdout


def make_handler(simulator):
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                self.respond(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
                return
            if self.path.startswith("/api/status"):
                self.respond_json(200, simulator.cached_status())
                return
            if self.path.startswith("/api/screen.png"):
                try:
                    image = simulator.capture_screen()
                except (OSError, RuntimeError, subprocess.SubprocessError) as failure:
                    print(f"ERROR: could not capture emulator screen: {failure}", file=sys.stderr, flush=True)
                    self.respond_json(502, {"error": "Emulator screen is unavailable"})
                    return
                self.respond(200, image, "image/png")
                return
            self.send_error(404)

        def do_POST(self):
            if self.path != "/api/key":
                self.send_error(404)
                return
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Origin") != origin:
                self.send_error(403, "Requests must come from the dashboard")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 128:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(length))
                key = payload.get("key") if isinstance(payload, dict) else None
                if not isinstance(key, str) or key not in KEYS:
                    raise ValueError("Unknown remote button")
            except (ValueError, json.JSONDecodeError) as failure:
                self.respond_json(400, {"error": str(failure)})
                return
            try:
                simulator.send_key(key)
            except (OSError, subprocess.SubprocessError) as failure:
                print(f"ERROR: could not send remote key: {failure}", file=sys.stderr, flush=True)
                self.respond_json(502, {"error": "Could not send key to the simulator"})
                return
            self.respond_json(200, {"ok": True})

        def respond_json(self, status, value):
            self.respond(status, json.dumps(value).encode("utf-8"), "application/json; charset=utf-8")

        def respond(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    return DashboardHandler


def refresh_status(simulator):
    while True:
        try:
            simulator.status()
        except (OSError, subprocess.SubprocessError) as failure:
            print(f"ERROR: could not read emulator status: {failure}", file=sys.stderr, flush=True)
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True, help="Path to the Android Debug Bridge executable")
    parser.add_argument("--serial", required=True, help="Android emulator serial")
    args = parser.parse_args()

    simulator = Simulator(args.adb, args.serial)
    threading.Thread(target=refresh_status, args=(simulator,), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(simulator))
    server.daemon_threads = True
    host, port = server.server_address
    url = f"http://{host}:{port}/"
    print(f"Simulator dashboard: {url}", flush=True)
    if not webbrowser.open(url, new=1):
        print("Open the simulator dashboard URL above in a browser.", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
