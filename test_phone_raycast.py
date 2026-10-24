import cv2
import numpy as np
import math
import config
from vision import VisionEngine

def test_phone():
    img = cv2.imread('phone_screen.png')
    v = VisionEngine()
    vehicles = v.detect_vehicles(img)

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

    veh_with_dir = []
    for veh in vehicles:
        vx, vy = veh['x'], veh['y']
        best_dist, best_lbl = 999, None
        for (cx, cy), lbl in label_map.items():
            d = math.hypot(vx - cx, vy - cy)
            if d < best_dist:
                best_dist, best_lbl = d, lbl
        if best_lbl is not None:
            mask = (labels == best_lbl).astype(np.uint8)
            pts = np.argwhere(mask > 0)
            pts_xy = np.column_stack((pts[:, 1], pts[:, 0]))
            mean, eigenvectors = cv2.PCACompute(pts_xy.astype(np.float32), mean=None)
            v1, v2 = eigenvectors[0], eigenvectors[1]
            projections = np.dot(pts_xy - mean, v1)
            pos_proj = pts_xy[projections > 5]
            neg_proj = pts_xy[projections < -5]
            width_pos = np.std(np.dot(pos_proj - mean, v2)) if len(pos_proj) > 5 else 999
            width_neg = np.std(np.dot(neg_proj - mean, v2)) if len(neg_proj) > 5 else 999
            tip_dir = v1 if width_pos < width_neg else -v1
            dx = 1.0 if tip_dir[0] > 0 else -1.0
            dy = 0.58 if tip_dir[1] > 0 else -0.58
            norm = math.hypot(dx, dy)
            veh['dx'] = dx / norm
            veh['dy'] = dy / norm
            veh_with_dir.append(veh)

    corridor_width = 48.0
    for i, veh_i in enumerate(veh_with_dir):
        xi, yi = veh_i['x'], veh_i['y']
        dxi, dyi = veh_i['dx'], veh_i['dy']
        is_blocked = False
        blocker = None
        min_dist = 9999
        for j, veh_j in enumerate(veh_with_dir):
            if i == j:
                continue
            rx = veh_j['x'] - xi
            ry = veh_j['y'] - yi
            forward_dist = rx * dxi + ry * dyi
            if forward_dist > 25.0:
                lateral_dist = abs(-dyi * rx + dxi * ry)
                if lateral_dist < corridor_width:
                    is_blocked = True
                    if forward_dist < min_dist:
                        min_dist = forward_dist
                        blocker = veh_j
        veh_i['is_blocked'] = is_blocked
        veh_i['blocker'] = blocker

    free = [v for v in veh_with_dir if not v['is_blocked']]
    print(f"Total detected vehicles: {len(veh_with_dir)}")
    print(f"FREE vehicles count: {len(free)}")
    for f in free:
        print(f"  FREE: ({f['x']}, {f['y']}) Color: {f['color']}, Area: {f['area']}")

    blocked = [v for v in veh_with_dir if v['is_blocked']]
    print(f"BLOCKED vehicles count: {len(blocked)}")
    for b in blocked[:5]:
        blk = b['blocker']
        print(f"  BLOCKED: ({b['x']}, {b['y']}) [{b['color']}] -> blocked by ({blk['x']}, {blk['y']}) [{blk['color']}]")

if __name__ == '__main__':
    test_phone()
