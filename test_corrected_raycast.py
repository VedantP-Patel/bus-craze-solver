import cv2
import numpy as np
import math
import config
from vision import VisionEngine

def test_corrected():
    img = cv2.imread('check_playing.png')
    v = VisionEngine()
    vehicles = v.detect_vehicles(img)

    ymin, ymax, xmin, xmax = config.JAM_ROI
    roi = img[ymin:ymax, xmin:xmax]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, config.WHITE_ARROW_MIN_GRAY, 255, cv2.THRESH_BINARY)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh)

    label_map = { (int(centroids[i][0]) + xmin, int(centroids[i][1]) + ymin): i for i in range(1, num_labels) }

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
            
            # WIDER END IS THE ARROWHEAD
            tip_dir = v1 if width_pos > width_neg else -v1
            dx = 1.0 if tip_dir[0] > 0 else -1.0
            dy = 0.58 if tip_dir[1] > 0 else -0.58
            norm = math.hypot(dx, dy)
            veh['dx'] = dx / norm
            veh['dy'] = dy / norm

    corridor_width = 48.0
    for i, vi in enumerate(vehicles):
        is_blocked = False
        blocker = None
        min_dist = 9999
        for j, vj in enumerate(vehicles):
            if i == j:
                continue
            rx, ry = vj['x'] - vi['x'], vj['y'] - vi['y']
            fd = rx * vi['dx'] + ry * vi['dy']
            if fd > 25.0:
                ld = abs(-vi['dy'] * rx + vi['dx'] * ry)
                if ld < corridor_width:
                    is_blocked = True
                    if fd < min_dist:
                        min_dist = fd
                        blocker = vj
        vi['is_blocked'] = is_blocked
        vi['blocker'] = blocker

    free = [v for v in vehicles if not v['is_blocked']]
    print(f"Total vehicles: {len(vehicles)}")
    print(f"TRUE FREE VEHICLES ({len(free)}):")
    for f in free:
        print(f"  ({f['x']}, {f['y']}) Color: {f['color']}, dx={f['dx']:.2f}, dy={f['dy']:.2f}")

    annotated = img.copy()
    for vi in vehicles:
        x, y = vi['x'], vi['y']
        color = (0, 255, 0) if not vi['is_blocked'] else (0, 0, 255)
        cv2.circle(annotated, (x, y), 22, color, 3)
        dx, dy = int(vi['dx'] * 60), int(vi['dy'] * 60)
        cv2.arrowedLine(annotated, (x, y), (x + dx, y + dy), color, 3, tipLength=0.3)
        cv2.putText(annotated, vi['color'][:3], (x - 20, y - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imwrite('real_free_annotated.png', annotated)
    print('Saved real_free_annotated.png')

if __name__ == '__main__':
    test_corrected()
