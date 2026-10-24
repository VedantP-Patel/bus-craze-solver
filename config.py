"""
Configuration settings for Bus Craze Auto-Solver
Target Device: Redmi 13 5G (1080x2460)
Game: net.happywit.bus.craze
"""

DEVICE_SERIAL = "35fbb9da"
PACKAGE_NAME = "net.happywit.bus.craze"
TARGET_LEVEL = 250

SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2460

# Region of Interest (ROI) Boundaries
JAM_ROI = (980, 1700, 100, 980)
QUEUE_Y = 505
QUEUE_X_MIN = 320
QUEUE_X_MAX = 850

# Parking Slots
SLOT_Y = 720
SLOT_X_COORDS = [215, 325, 435, 545]
MAX_SLOTS = 4

# Buttons
BTN_PAUSE = (984, 165)
BTN_RESTART = (850, 169)
BTN_MAIN_PLAY = (540, 2008)
BTN_SHUFFLE = (231, 2225)
BTN_CONTINUE_CLOSE = (852, 660)
BTN_RETRY = (540, 1788)
BTN_NEXT_LEVEL = (540, 1788)

# Detection thresholds
WHITE_ARROW_MIN_GRAY = 240
ARROW_MIN_AREA = 80
ARROW_MAX_AREA = 1200
