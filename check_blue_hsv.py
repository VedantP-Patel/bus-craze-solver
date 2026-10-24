import cv2
import numpy as np
import config
from vision import VisionEngine

img = cv2.imread('blue_check.png')
v = VisionEngine()
vehs = v.detect_vehicles(img)

print("Vehicles detected:")
for veh in vehs:
    c = veh['color']
    if 'BLUE' in c or 'CYAN' in c:
        # Sample average HSV
        cx, cy = veh['x'], veh['y']
        roi = img[cy-10:cy+10, cx-10:cx+10]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mean_h = np.median(hsv[:,:,0])
        mean_s = np.median(hsv[:,:,1])
        mean_v = np.median(hsv[:,:,2])
        print(f"  Pos: ({cx}, {cy}), Classified: {c}, HSV: (H={mean_h:.1f}, S={mean_s:.1f}, V={mean_v:.1f})")

# Also check passenger queue pixels
print("\nChecking passenger queue pixels across x=320 to 850:")
for x in range(config.QUEUE_X_MIN, config.QUEUE_X_MAX, 38):
    bgr = img[config.QUEUE_Y, x]
    pixel = np.uint8([[bgr]])
    hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
    classified = v._classify_bgr(bgr)
    print(f"  x={x}: BGR={list(bgr)}, HSV=(H={hsv[0]}, S={hsv[1]}, V={hsv[2]}), Classified={classified}")
