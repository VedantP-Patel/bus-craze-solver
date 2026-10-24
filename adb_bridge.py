"""
ADB Bridge for fast screen capture and touch input injection.
Optimized for low-latency Android automation.
"""

import subprocess
import time
import cv2
import numpy as np
import config

class ADBBridge:
    def __init__(self, serial=config.DEVICE_SERIAL):
        self.serial = serial
        self.cmd_prefix = ["adb"]
        if self.serial:
            self.cmd_prefix.extend(["-s", self.serial])
        self._ensure_connection()

    def _ensure_connection(self):
        """Verifies ADB can communicate with the phone."""
        try:
            out = subprocess.check_output(self.cmd_prefix + ["devices"]).decode()
            if self.serial and self.serial not in out:
                # If specific serial not listed, check if any device is attached
                lines = [l for l in out.strip().split("\n") if "device" in l and not l.startswith("List")]
                if lines:
                    found_serial = lines[0].split()[0]
                    print(f"[ADB] Updating device serial to: {found_serial}")
                    self.serial = found_serial
                    self.cmd_prefix = ["adb", "-s", self.serial]
                else:
                    raise RuntimeError("No connected device detected via ADB!")
            print(f"[ADB] Connected to device: {self.serial}")
        except Exception as e:
            print(f"[ADB Error] Failed to connect: {e}")
            raise

    def capture_screen(self, retries=3) -> np.ndarray:
        """Captures screen directly into memory as an OpenCV BGR image."""
        for attempt in range(retries):
            try:
                cmd = self.cmd_prefix + ["exec-out", "screencap", "-p"]
                raw_bytes = subprocess.check_output(cmd)
                img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
                if img is not None and img.shape[0] > 100:
                    return img
            except Exception as e:
                time.sleep(0.3)
        # Fallback to shell screencap
        try:
            subprocess.run(self.cmd_prefix + ["shell", "screencap", "-p", "/sdcard/_bot_sc.png"], check=True)
            subprocess.run(self.cmd_prefix + ["pull", "/sdcard/_bot_sc.png", "_bot_sc.png"], check=True)
            img = cv2.imread("_bot_sc.png")
            if img is not None:
                return img
        except Exception as e:
            print(f"[ADB Error] Screencap fallback failed: {e}")
        raise RuntimeError("Failed to capture screen image via ADB.")

    def tap(self, x: int, y: int, delay: float = 0.05):
        """Injects a screen tap at (x, y)."""
        cmd = self.cmd_prefix + ["shell", "input", "tap", str(int(x)), str(int(y))]
        subprocess.run(cmd, check=False)
        if delay > 0:
            time.sleep(delay)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Simulates a swipe gesture."""
        cmd = self.cmd_prefix + ["shell", "input", "swipe", str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(duration_ms)]
        subprocess.run(cmd, check=False)

    def press_back(self, delay: float = 0.5):
        """Sends Android Back button keyevent (KEY_BACK = 4)."""
        cmd = self.cmd_prefix + ["shell", "input", "keyevent", "4"]
        subprocess.run(cmd, check=False)
        if delay > 0:
            time.sleep(delay)

    def ensure_game_foreground(self):
        """Verifies Bus Craze is the foreground app, launching it if necessary."""
        try:
            out = subprocess.check_output(self.cmd_prefix + ["shell", "dumpsys", "window"]).decode(errors="ignore")
            if config.PACKAGE_NAME not in out:
                print(f"[ADB] Relaunching {config.PACKAGE_NAME}...")
                subprocess.run(self.cmd_prefix + ["shell", "monkey", "-p", config.PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"], check=False)
                time.sleep(3.0)
        except Exception as e:
            print(f"[ADB Warning] Could not check foreground app: {e}")

    def restart_game(self):
        """Force-stops and relaunches Bus Craze cleanly."""
        print(f"[ADB] Force-stopping and relaunching {config.PACKAGE_NAME}...")
        subprocess.run(self.cmd_prefix + ["shell", "am", "force-stop", config.PACKAGE_NAME], check=False)
        time.sleep(1.0)
        subprocess.run(self.cmd_prefix + ["shell", "monkey", "-p", config.PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"], check=False)
        time.sleep(4.0)

