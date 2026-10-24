"""
Vision module for Bus Craze.
Handles screen state classification, vehicle arrow detection,
vehicle color classification, and passenger queue recognition.
"""

import cv2
import numpy as np
import config

COLOR_PURPLE = "PURPLE"
COLOR_YELLOW = "YELLOW"
COLOR_GREEN  = "GREEN"
COLOR_RED    = "RED"
COLOR_CYAN   = "CYAN"
COLOR_ORANGE = "ORANGE"
COLOR_PINK   = "PINK"
COLOR_BLUE   = "BLUE"
COLOR_UNKNOWN = "UNKNOWN"

class VisionEngine:
    def __init__(self):
        pass

    def classify_screen_state(self, img: np.ndarray) -> str:
        """
        Determines the current game screen:
        - 'POPUP_CONTINUE'
        - 'PLAYING'
        - 'LEVEL_COMPLETE'
        - 'LEVEL_FAILED'
        - 'MAIN_MENU'
        - 'AD'
        """
        # 1. Check for "Continue?" / "Out of Space" popup ('X' button at 852, 660)
        roi_cont = img[630:690, 820:880]
        if roi_cont.size > 0:
            white_pixels = np.sum(np.all(roi_cont > 220, axis=2))
            banner_blue = np.mean(img[630:690, 400:600, 0])
            if white_pixels > 80 and banner_blue > 130:
                return "POPUP_CONTINUE"

        # 2. Check for PLAYING state (Pause button at top-right: x in [930, 1040], y in [120, 210])
        pause_roi = img[120:210, 930:1040]
        if pause_roi.size > 0:
            hsv = cv2.cvtColor(pause_roi, cv2.COLOR_BGR2HSV)
            blue_mask = cv2.inRange(hsv, (95, 160, 160), (125, 255, 255))
            if np.sum(blue_mask > 0) > 300:
                return "PLAYING"

        # 3. Check for Victory / Level Complete (Gold/Green Next Button + Victory Banner)
        win_roi = img[1700:1850, 400:680]
        if win_roi.size > 0:
            is_gold_btn = np.mean(win_roi[:, :, 1]) > 140 and np.mean(win_roi[:, :, 2]) > 150 and np.mean(win_roi[:, :, 0]) < 90
            win_ribbon = img[260:350, 300:700]
            if is_gold_btn and np.mean(win_ribbon[:, :, 1]) > 140:
                return "LEVEL_COMPLETE"

        # 4. Check for Main Menu / Map Screen (Big green Play button at 540, 2008)
        menu_roi = img[1950:2070, 450:630]
        if menu_roi.size > 0:
            hsv_menu = cv2.cvtColor(menu_roi, cv2.COLOR_BGR2HSV)
            green_mask = cv2.inRange(hsv_menu, (35, 120, 120), (85, 255, 255))
            if np.sum(green_mask > 0) > 800:
                return "MAIN_MENU"

        # 5. Check for "Level Failed!" screen (Blue Retry button around 540, 1788 on dark overlay)
        retry_roi = img[1740:1830, 450:630]
        if retry_roi.size > 0:
            b_mean = np.mean(retry_roi[:, :, 0])
            r_mean = np.mean(retry_roi[:, :, 2])
            top_dimmed = np.mean(img[100:300, 100:900]) < 80
            if b_mean > 160 and (b_mean - r_mean) > 40 and top_dimmed:
                return "LEVEL_FAILED"

        # 6. Ad overlay or unknown screen
        return "AD"

    def detect_vehicles(self, img: np.ndarray) -> list:
        """
        Finds all vehicles on the jam board by locating white roof arrows.
        Returns a list of dicts:
        [{'x': int, 'y': int, 'color': str, 'area': int}, ...]
        """
        ymin, ymax, xmin, xmax = config.JAM_ROI
        roi = img[ymin:ymax, xmin:xmax]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        _, thresh = cv2.threshold(gray, config.WHITE_ARROW_MIN_GRAY, 255, cv2.THRESH_BINARY)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh)

        vehicles = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if config.ARROW_MIN_AREA <= area <= config.ARROW_MAX_AREA:
                cx = int(centroids[i][0]) + xmin
                cy = int(centroids[i][1]) + ymin
                color = self._extract_vehicle_color(img, cx, cy)

                vehicles.append({
                    "x": cx,
                    "y": cy,
                    "area": int(area),
                    "color": color
                })

        vehicles = self._compute_raycasts(img, vehicles)
        return vehicles

    def _compute_raycasts(self, img: np.ndarray, vehicles: list) -> list:
        """
        Calculates directional vectors for each vehicle arrow using PCA and width ratio.
        Performs forward raycasting collision detection (corridor width = 48.0)
        to identify which vehicles are completely free to exit vs blocked.
        """
        if not vehicles:
            return []

        import math
        ymin, ymax, xmin, xmax = config.JAM_ROI
        roi = img[ymin:ymax, xmin:xmax]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, config.WHITE_ARROW_MIN_GRAY, 255, cv2.THRESH_BINARY)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh)

        label_map = {}
        for i in range(1, num_labels):
            cx = int(centroids[i][0]) + xmin
            cy = int(centroids[i][1]) + ymin
            label_map[(cx, cy)] = i

        # Calculate directional vector for each vehicle
        for veh in vehicles:
            vx, vy = veh['x'], veh['y']
            best_dist, best_lbl = 999, None
            for (cx, cy), lbl in label_map.items():
                d = math.hypot(vx - cx, vy - cy)
                if d < best_dist:
                    best_dist = d
                    best_lbl = lbl

            if best_lbl is not None:
                mask = (labels == best_lbl).astype(np.uint8)
                pts = np.argwhere(mask > 0)
                if len(pts) >= 10:
                    pts_xy = np.column_stack((pts[:, 1], pts[:, 0]))
                    mean, eigenvectors = cv2.PCACompute(pts_xy.astype(np.float32), mean=None)
                    v1, v2 = eigenvectors[0], eigenvectors[1]
                    projections = np.dot(pts_xy - mean, v1)
                    pos_proj = pts_xy[projections > 5]
                    neg_proj = pts_xy[projections < -5]
                    width_pos = np.std(np.dot(pos_proj - mean, v2)) if len(pos_proj) > 5 else 999
                    width_neg = np.std(np.dot(neg_proj - mean, v2)) if len(neg_proj) > 5 else 999
                    # The arrowhead is significantly wider than the shaft/tail
                    tip_dir = v1 if width_pos > width_neg else -v1

                    dx = 1.0 if tip_dir[0] > 0 else -1.0
                    dy = 0.58 if tip_dir[1] > 0 else -0.58

                    norm = math.hypot(dx, dy)
                    veh['dx'] = dx / norm
                    veh['dy'] = dy / norm
                else:
                    veh['dx'], veh['dy'] = 0.0, 0.0
            else:
                veh['dx'], veh['dy'] = 0.0, 0.0

            veh['is_blocked'] = False
            veh['blocker'] = None
            veh['unblocks'] = []

        # Raycasting collision check
        corridor_width = 48.0
        for i, vi in enumerate(vehicles):
            if vi['dx'] == 0.0 and vi['dy'] == 0.0:
                vi['is_blocked'] = True
                continue

            xi, yi = vi['x'], vi['y']
            dxi, dyi = vi['dx'], vi['dy']
            is_blocked = False
            blocker = None
            min_block_dist = 9999.0

            for j, vj in enumerate(vehicles):
                if i == j:
                    continue
                rx = vj['x'] - xi
                ry = vj['y'] - yi
                forward_dist = rx * dxi + ry * dyi
                if forward_dist > 25.0:
                    lateral_dist = abs(-dyi * rx + dxi * ry)
                    if lateral_dist < corridor_width:
                        is_blocked = True
                        if forward_dist < min_block_dist:
                            min_block_dist = forward_dist
                            blocker = vj

            vi['is_blocked'] = is_blocked
            vi['blocker'] = blocker
            if blocker is not None:
                blocker['unblocks'].append(vi)

        return vehicles

    def _extract_vehicle_color(self, img: np.ndarray, cx: int, cy: int) -> str:
        """Samples body roof color directly surrounding the arrow, excluding ground."""
        h, w, _ = img.shape
        samples = []
        for dy in range(-16, 17, 4):
            for dx in range(-16, 17, 4):
                px = cx + dx
                py = cy + dy
                if 0 <= px < w and 0 <= py < h:
                    bgr = img[py, px]
                    if np.mean(bgr) > 235:
                        continue
                    pixel = np.uint8([[bgr]])
                    hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
                    # Car roof paint has high saturation (> 85), background ground is lower
                    if hsv[1] > 85:
                        samples.append((bgr, hsv))

        if not samples:
            return COLOR_UNKNOWN

        hues = [s[1][0] for s in samples]
        median_h = np.median(hues)
        if 35 <= median_h <= 85:
            return COLOR_GREEN
        elif 15 <= median_h < 35:
            return COLOR_YELLOW
        elif 85 < median_h <= 98:
            return COLOR_CYAN
        elif 98 < median_h <= 125:
            return COLOR_BLUE
        elif 125 < median_h <= 155:
            return COLOR_PURPLE
        elif 155 < median_h < 172:
            return COLOR_PINK
        elif median_h >= 172 or median_h < 12:
            avg_bgr = np.mean([s[0] for s in samples], axis=0)
            if avg_bgr[2] > 200 and avg_bgr[1] > 120 and avg_bgr[0] < 50:
                return COLOR_ORANGE
            return COLOR_RED

        return COLOR_UNKNOWN


    def get_queue_front_colors(self, img: np.ndarray) -> list:
        """
        Extracts passenger colors waiting in queue.
        Front of the queue is on the LEFT (x ~ 320), moving towards the right.
        """
        colors_found = []
        for x in range(config.QUEUE_X_MIN, config.QUEUE_X_MAX, 38):
            bgr = img[config.QUEUE_Y, x]
            if np.mean(bgr) < 220:
                c = self._classify_bgr(bgr)
                if c != COLOR_UNKNOWN:
                    if not colors_found or colors_found[-1] != c:
                        colors_found.append(c)

        return colors_found[:4]

    def _classify_bgr(self, bgr) -> str:
        pixel = np.uint8([[bgr]])
        hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
        h_val, s_val, _ = hsv[0], hsv[1], hsv[2]

        if s_val < 40:
            return COLOR_UNKNOWN
        if 35 <= h_val <= 85:
            return COLOR_GREEN
        elif 18 <= h_val < 35:
            return COLOR_YELLOW
        elif 85 < h_val <= 98:
            return COLOR_CYAN
        elif 98 < h_val <= 125:
            return COLOR_BLUE
        elif 125 < h_val <= 155:
            return COLOR_PURPLE
        elif 155 < h_val <= 172:
            return COLOR_PINK
        elif h_val < 15 or h_val >= 172:
            if bgr[2] > 200 and bgr[1] > 120 and bgr[0] < 50:
                return COLOR_ORANGE
            return COLOR_RED
        return COLOR_UNKNOWN


    def count_available_slots(self, img: np.ndarray) -> int:
        """
        Checks the 4 default parking slots.
        Empty slot ground color is beige/gray: BGR ~ [200, 175, 155].
        """
        empty_count = 0
        for sx in config.SLOT_X_COORDS:
            bgr = img[config.SLOT_Y, sx]
            pixel = np.uint8([[bgr]])
            hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
            sat = hsv[1]
            if sat < 65 and bgr[0] > 140 and bgr[2] > 120:
                empty_count += 1

        return empty_count
