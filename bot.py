"""
Main Autonomous Bot for Bus Craze.
Executes the game loop from current level up to Level 250 for AttaPoll reward task.
"""

import time
import argparse
import json
import os
import config
from adb_bridge import ADBBridge
from vision import VisionEngine
from solver import BusJamSolver

PROGRESS_FILE = "d:/Cheat/progress.json"

class BusCrazeBot:
    def __init__(self, target_level=config.TARGET_LEVEL):
        self.target_level = target_level
        self.adb = ADBBridge()
        self.vision = VisionEngine()
        self.solver = BusJamSolver(self.adb, self.vision)
        self.current_level = self._load_progress()
        self.start_time = time.time()
        self.levels_cleared = 0
        self.ad_consecutive_count = 0

    def _load_progress(self) -> int:
        if os.path.exists(PROGRESS_FILE):
            try:
                data = json.load(open(PROGRESS_FILE))
                lvl = data.get("current_level", 4)
                print(f"[Bot] Loaded saved progress: Level {lvl}")
                return lvl
            except Exception:
                pass
        return 4

    def _save_progress(self):
        data = {
            "current_level": self.current_level,
            "target_level": self.target_level,
            "levels_cleared": self.levels_cleared,
            "last_updated": time.ctime(),
            "elapsed_seconds": int(time.time() - self.start_time)
        }
        with open(PROGRESS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def run(self):
        print("=" * 60)
        print(f" BUS CRAZE AUTO-SOLVER (Goal: Level {self.target_level})")
        print(f" Starting from Level: {self.current_level}")
        print("=" * 60)

        while self.current_level < self.target_level:
            try:
                self.step()
                time.sleep(0.15)
            except KeyboardInterrupt:
                print("\n[Bot] Paused by user. Saving progress...")
                self._save_progress()
                break
            except Exception as e:
                print(f"[Bot Warning] Loop error: {e}")
                time.sleep(1.0)

        if self.current_level >= self.target_level:
            print("\n" + "=" * 60)
            print(f" SUCCESS! TARGET LEVEL {self.target_level} REACHED!")
            print(" Open AttaPoll now to claim your reward!")
            print("=" * 60)
            self._save_progress()

    def step(self):
        img = self.adb.capture_screen()
        state = self.vision.classify_screen_state(img)

        if state == "PLAYING":
            self.ad_consecutive_count = 0
            self.solver.step(img)

        elif state == "POPUP_CONTINUE":
            print("[Bot] Detected 'Continue?' popup. Closing to restart...")
            self.adb.tap(*config.BTN_CONTINUE_CLOSE)
            time.sleep(0.8)

        elif state == "LEVEL_FAILED":
            print(f"[Bot] Level {self.current_level} failed. Tapping Retry...")
            self.adb.tap(*config.BTN_RETRY)
            time.sleep(1.5)

        elif state == "LEVEL_COMPLETE":
            self.current_level += 1
            self.levels_cleared += 1
            pct = (self.current_level / self.target_level) * 100
            elapsed_min = (time.time() - self.start_time) / 60
            print("*" * 55)
            print(f"[VICTORY] Completed Level! Now on Level {self.current_level} / {self.target_level} ({pct:.1f}%)")
            print(f"[Stats] Levels cleared this session: {self.levels_cleared} | Time: {elapsed_min:.1f} min")
            print("*" * 55)
            self._save_progress()

            # Tap Next / Claim button
            self.adb.tap(*config.BTN_NEXT_LEVEL)
            time.sleep(2.0)

        elif state == "MAIN_MENU":
            print(f"[Bot] Main Menu / Map detected. Tapping Play at {config.BTN_MAIN_PLAY}...")
            self.adb.tap(*config.BTN_MAIN_PLAY)
            time.sleep(2.5)

        elif state == "AD":
            self.ad_consecutive_count += 1
            print(f"[Bot] Handling Ad / Overlay (detection #{self.ad_consecutive_count})...")
            # Try Back key first
            self.adb.press_back()
            time.sleep(1.0)
            if self.ad_consecutive_count in (3, 4):
                # Try clicking top corners for Close X
                self.adb.tap(990, 80)
                time.sleep(0.5)
                self.adb.tap(70, 80)
                time.sleep(0.5)
                self.adb.ensure_game_foreground()
            elif self.ad_consecutive_count >= 6:
                # Ad watchdog: unskippable or trapped ad, force-restart app to clear
                print("[Bot Watchdog] Trapped in ad/overlay. Restarting game cleanly...")
                self.adb.restart_game()
                self.ad_consecutive_count = 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bus Craze Level 250 Auto-Solver")
    parser.add_argument("--target", type=int, default=config.TARGET_LEVEL, help="Target level (default 250)")
    args = parser.parse_args()

    bot = BusCrazeBot(target_level=args.target)
    bot.run()
