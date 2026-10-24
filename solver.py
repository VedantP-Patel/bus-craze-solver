"""
Solver logic for Bus Craze.
Calculates priority moves based on passenger queue, vehicle colors,
and parking slot availability. Includes cooldown tracking for blocked vehicles.
"""

import time
import math
import config
from vision import COLOR_UNKNOWN

class BusJamSolver:
    def __init__(self, adb_bridge, vision_engine):
        self.adb = adb_bridge
        self.vision = vision_engine
        self.consecutive_stuck_cycles = 0
        self.tapped_history = {} # (x, y) -> last_tapped_time

    def step(self, img) -> bool:
        """
        Executes one solver decision step.
        Returns True if a move was executed, False if waiting or stuck.
        """
        vehicles = self.vision.detect_vehicles(img)
        if not vehicles:
            return False

        free_slots = self.vision.count_available_slots(img)
        queue_colors = self.vision.get_queue_front_colors(img)

        # If zero slots are free, wait for passengers to board and vehicle to depart
        if free_slots == 0:
            time.sleep(0.4)
            return False

        now = time.time()
        # Clean up history older than 6 seconds
        self.tapped_history = {pos: t for pos, t in self.tapped_history.items() if now - t < 6.0}

        candidates = self._rank_candidates(vehicles, queue_colors, free_slots, now)
        if not candidates:
            self.consecutive_stuck_cycles += 1
            if self.consecutive_stuck_cycles >= 5:
                print("[Solver] Board seems stuck. Attempting Shuffle...")
                self.adb.tap(*config.BTN_SHUFFLE)
                self.consecutive_stuck_cycles = 0
                self.tapped_history.clear()
                time.sleep(1.0)
            return False

        best = candidates[0]
        pos_key = (best["x"], best["y"])
        print(f"[Solver] Tapping vehicle at ({best['x']}, {best['y']}) [Color: {best['color']}], Free slots: {free_slots}")
        
        self.adb.tap(best["x"], best["y"])
        self.tapped_history[pos_key] = now
        self.consecutive_stuck_cycles = 0

        # Animation timing: allow vehicle to enter slot and passengers to board
        if queue_colors and best["color"] == queue_colors[0]:
            time.sleep(1.2)
        else:
            time.sleep(0.7)


        return True

    def _rank_candidates(self, vehicles: list, queue_colors: list, free_slots: int, now: float) -> list:
        """
        Ranks candidate vehicles based on raycasting collision detection,
        passenger queue matching, blocker dependencies, and deadlock safety.
        """
        scored = []
        board_center_x = 540
        board_center_y = 1350

        front_color = queue_colors[0] if queue_colors else None
        second_color = queue_colors[1] if len(queue_colors) > 1 else None

        for veh in vehicles:
            score = 0
            v_color = veh.get("color", COLOR_UNKNOWN)
            vx, vy = veh["x"], veh["y"]
            is_blocked = veh.get("is_blocked", False)

            # 1. Heavily penalize physically blocked vehicles
            if is_blocked:
                score -= 10000

            # 2. Cooldown check: if tapped within last 4 seconds and still present, penalize
            was_recently_tapped = False
            for (hx, hy), t in self.tapped_history.items():
                if math.hypot(vx - hx, vy - hy) < 35 and (now - t) < 4.0:
                    was_recently_tapped = True
                    break

            if was_recently_tapped:
                score -= 4000

            # Base score for free vehicles
            if not is_blocked:
                score += 500

                # Priority 1: Direct match for front of passenger queue
                if front_color and v_color == front_color:
                    score += 2500

                # Priority 2: Direct match for 2nd passenger in queue (if >= 2 slots)
                elif second_color and v_color == second_color and free_slots >= 2:
                    score += 1200

                # Priority 3: Direct match for 3rd passenger in queue (if >= 3 slots)
                elif len(queue_colors) > 2 and v_color == queue_colors[2] and free_slots >= 3:
                    score += 600

                # DEADLOCK GUARD: If only 1 slot is free, NEVER tap non-matching vehicle
                elif free_slots <= 1:
                    continue

                # General exploration when >= 2 slots are free
                else:
                    score += 100

                # Strategic Unblocking Bonus:
                # If moving this vehicle clears the path for a front-color vehicle!
                unblocks = veh.get("unblocks", [])
                if free_slots >= 2 and unblocks:
                    for blocked_veh in unblocks:
                        b_col = blocked_veh.get("color", COLOR_UNKNOWN)
                        if front_color and b_col == front_color:
                            score += 1000
                        elif second_color and b_col == second_color:
                            score += 400
                    score += len(unblocks) * 150

                # Distance from center heuristic (outer vehicles are easier to clear)
                dist_from_center = math.hypot(vx - board_center_x, vy - board_center_y)
                score += dist_from_center * 0.25

                # Small vehicles clear quicker
                if veh.get("area", 0) < 700:
                    score += 50

            scored.append((score, veh))

        # Filter out candidates with non-positive scores (blocked / in cooldown)
        positive_scored = [item for item in scored if item[0] > 0]
        if positive_scored:
            positive_scored.sort(key=lambda item: item[0], reverse=True)
            return [item[1] for item in positive_scored]

        return []

