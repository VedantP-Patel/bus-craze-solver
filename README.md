# Bus Craze Traffic Jam - Autonomous AI Solver

An intelligent, non-invasive computer vision and heuristic raycasting solver for **Bus Craze - Traffic Jam Puzzle** (`net.happywit.bus.craze`). Built for reliable, high-level automation (Level 1 to 250+) via Android Debug Bridge (ADB).

---

## Architecture Overview

1. **Non-Invasive Vision & Touch Injection**:
   - Operates 100% through high-speed ADB frame capture (`exec-out screencap -p`) and human-paced input tap simulation.
   - Zero memory tampering, zero save-file editing, zero APK modification. Preserves Google Advertising ID (GAID) attribution and offerwall compliance.

2. **Computer Vision Engine (`vision.py`)**:
   - **Directional Raycasting**: Extracts vehicle roof arrows, applies PCA covariance, and determines exit trajectories along isometric grid axes.
   - **Corridor Collision Checking**: Projects a forward collision envelope (`corridor_width = 48px`) to distinguish unblocked vehicles from blocked ones before touching the screen.
   - **Color Classification**: Distinguishes full palette (Red, Orange, Yellow, Green, Cyan/LightBlue, DarkBlue, Purple, Pink) across vehicles and passenger queues.
   - **State Machine**: Automatically identifies `PLAYING`, `LEVEL_COMPLETE`, `LEVEL_FAILED`, `POPUP_CONTINUE`, and interstitial ads.

3. **Strategic Heuristic Solver (`solver.py`)**:
   - Prioritizes vehicles matching the front passenger queue.
   - Considers blocker dependency graphs to clear paths for trapped passenger matches.
   - **Deadlock Guard**: Strictly prohibits non-matching vehicle taps when $\le 1$ parking slot remains free.

4. **Autonomous Runner (`bot.py`)**:
   - Handles level transitions, ad dismissals, retry logic, and session persistence in `progress.json`.

---

## Getting Started

### Prerequisites
- Python 3.9+
- Android phone with **USB Debugging** enabled (connected via USB)
- ADB added to system PATH

### Installation
```powershell
git clone https://github.com/<username>/bus-craze-solver.git
cd bus-craze-solver
pip install -r requirements.txt
```

### Configuration
Verify your connected device serial in `config.py`:
```python
DEVICE_SERIAL = "35fbb9da"  # Replace with your adb device serial
```

### Running the Solver
```powershell
python bot.py --target 250
```

To stop at any time, press `Ctrl + C`. Progress is saved automatically to `progress.json`.
