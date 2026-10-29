"""The simulator uses the launcher's guarded Home handover through local ADB."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
AVD_NAME = "CleanYourTV_TV_API_34"
STOCK_HOME = "com.google.android.tvlauncher/.MainActivity"
NEW_HOME = "com.gathin.tvhome/.MainActivity"

FAKE_ADB = r'''
import json
import os
import sys

state_path = os.environ["FAKE_ADB_STATE"]
with open(state_path) as source:
    state = json.load(source)
args = sys.argv[1:]
command = args[2:]
if command == ["get-state"]:
    print("device")
elif command == ["emu", "avd", "name"]:
    print(state["avd"])
elif command[:1] == ["install"]:
    print("Success")
elif command[:1] == ["shell"]:
    shell = command[1]
    state["commands"].append(shell)
    if "getprop ro.build.version.sdk" in shell:
        print("34")
    elif "pm list packages -d" in shell and state["stock_disabled"]:
        print("package:" + state["stock"])
    elif "pm list packages -d" in shell:
        pass
    elif "resolve-activity" in shell and "set-home-activity" not in shell:
        print(state["home"])
    elif "query-activities" in shell:
        print(state["home"])
        print("com.google.android.tvlauncher/.MainActivity")
    elif "am start" in shell:
        print("Starting: Intent { cmp=com.gathin.tvhome/.MainActivity }")
        print("Status: ok")
    elif "pm disable-user" in shell:
        if state["disable_fails"]:
            print("Error: disable refused")
            sys.exit(1)
        else:
            state["stock_disabled"] = True
            print("Package " + state["stock"] + " new state: disabled-user")
    elif "pm enable" in shell:
        state["stock_disabled"] = False
    elif "set-home-activity" in shell:
        state["home"] = "com.gathin.tvhome/.MainActivity"
    with open(state_path, "w") as target:
        json.dump(state, target)
else:
    sys.exit(1)
'''


class SimulatorHandoverTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.launcher = self.base / "launcher"
        self.launcher.mkdir()
        shutil.copy2(ROOT / "launcher" / "build-and-install.sh", self.launcher)
        gradle = self.launcher / "gradlew"
        gradle.write_text(
            '#!/bin/sh\n'
            'mkdir -p app/build/outputs/apk/release\n'
            'printf apk > app/build/outputs/apk/release/app-release.apk\n'
        )
        gradle.chmod(0o755)
        (self.base / "tools").mkdir()
        self.sdk = self.base / "sdk"
        adb = self.sdk / "platform-tools" / "adb"
        adb.parent.mkdir(parents=True)
        fake = self.base / "fake_adb.py"
        fake.write_text(FAKE_ADB)
        adb.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n')
        adb.chmod(0o755)
        self.state_path = self.base / "adb-state.json"
        self.java = self.base / "java"
        self.java.mkdir()

    def run_installer(self, avd=AVD_NAME, disable_fails=False):
        self.state_path.write_text(json.dumps({
            "avd": avd,
            "home": STOCK_HOME,
            "stock": "com.google.android.tvlauncher",
            "stock_disabled": False,
            "disable_fails": disable_fails,
            "commands": [],
        }))
        environment = os.environ.copy()
        environment.pop("TV_HOST", None)
        environment["ANDROID_HOME"] = str(self.sdk)
        environment["SIMULATOR_ADB_SERIAL"] = "emulator-5554"
        environment["SIMULATOR_AVD_NAME"] = AVD_NAME
        environment["FAKE_ADB_STATE"] = str(self.state_path)
        environment["JAVA_HOME"] = str(self.java)
        result = subprocess.run(
            ["bash", str(self.launcher / "build-and-install.sh")],
            cwd=self.launcher,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        state = json.loads(self.state_path.read_text())
        return result, state

    @unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "requires a POSIX shell")
    def test_build_and_install_disables_stock_home_after_launcher_starts(self):
        result, state = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(state["stock_disabled"])
        self.assertEqual(state["home"], NEW_HOME)
        start = next(i for i, command in enumerate(state["commands"]) if "am start" in command)
        disable = next(i for i, command in enumerate(state["commands"]) if "pm disable-user" in command)
        self.assertLess(start, disable)
        self.assertIn("Home now resolves to", result.stdout)

    @unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "requires a POSIX shell")
    def test_adb_install_mode_refuses_other_avds_before_building(self):
        result, state = self.run_installer(avd="Some_Other_AVD")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to change Home", result.stderr)
        self.assertFalse(state["commands"])
        self.assertFalse((self.launcher / "app/build/outputs/apk/release/app-release.apk").exists())

    @unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "requires a POSIX shell")
    def test_stock_disable_failure_stops_handover(self):
        result, state = self.run_installer(disable_fails=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not disable stock Home", result.stderr)
        self.assertFalse(state["stock_disabled"])
        self.assertFalse(any("set-home-activity" in command for command in state["commands"]))


if __name__ == "__main__":
    unittest.main()
