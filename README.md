# Ardubotr4: BLE Robot Controller (Arduino UNO R4 WiFi + Python GUI)

Ardubotr4 is a small end‑to‑end project to drive a two‑wheel robot from your PC over Bluetooth Low Energy (BLE).
It consists of:
- Arduino firmware for UNO R4 WiFi that exposes a BLE service and drives the motors, an ultrasonic distance sensor, a scanning servo, and the built‑in LED matrix.
- A Python desktop controller (Tkinter + Bleak) with five buttons that sends plain‑text commands to the robot over BLE.

The setup is designed to be simple: the robot advertises as "ardubotr4" and accepts text commands like "forward", "back", "left", "right", and "switch". The LED matrix shows arrows or a circle as feedback, and the robot won’t drive forward if an obstacle is too close.


## Repository layout
- `sketch/ardubotr4.ino` – Arduino UNO R4 WiFi firmware (BLE peripheral)
- `sketch/Readme.md` – Notes about the Arduino sketch
- `main.py` – Python Tkinter BLE controller (BLE central)
- `pyproject.toml` – Python project config (Poetry), depends on `bleak`


## Requirements

PC side (controller):
- Windows 10/11 (tested). Linux/macOS may work but BLE backends differ.
- Python 3.12+ (per `pyproject.toml`).
- A BLE‑capable Bluetooth adapter.

Robot side (firmware and hardware):
- Arduino UNO R4 WiFi board.
- AFMotor_R4 Motor Shield with 2 DC motors (channels 1 and 2).
- Ultrasonic distance sensor HC‑SR04 (TRIG: A0, ECHO: A1).
- Servo on pin 10 (to scan left/right).
- Optional encoders on A2 (right) and A3 (left).


## Install and run the Python controller

You can use Poetry (recommended in this repo) or a plain virtual environment.

Using Poetry:

```cmd
poetry install
poetry run python main.py
```

Using a plain virtual environment (alternative):

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install bleak
python main.py
```

What the controller does:
- Scans for a BLE peripheral named `ardubotr4` and connects.
- Tries to use the characteristic `19B10001-E8F2-537E-4F6C-D104768A1214` (falls back to any writable characteristic if needed).
- Shows a simple 5‑button pad: Forward, Back, Left, Right, Switch.
- Sends plain UTF‑8 text commands without newline.

Default command mapping (edit in `main.py` if you need different text):
- Forward → `forward`
- Back → `back`
- Left → `left`
- Right → `right`
- Switch (toggle enable/stop) → `switch`

Notes:
- If your firmware expects different strings or a different characteristic UUID, update `COMMANDS`, `COMMAND_CHAR_UUID`, and `ROBOT_SERVICE_UUID` in `main.py`.
- Some devices require a write with response. This app uses `REQUIRE_RESPONSE_ON_WRITE = True`; set it to `False` if your device needs write‑without‑response.


## Quick start checklist
1. Power the Arduino robot. It should start advertising as `ardubotr4`.
2. On Windows, ensure Bluetooth is ON and the device is not paired in the OS (pairing is not required for BLE GATT).
3. Start the controller (`python main.py` or `poetry run python main.py`).
4. Wait for “Connected to ardubotr4” in the status line. If needed, click “Reconnect”.
5. Press buttons to drive the robot. The LED matrix should show arrows; the Serial Monitor will show logs.


## Troubleshooting
- Device not found:
  - Make sure the board is powered and advertising as `ardubotr4`.
  - Keep the board close to the PC; BLE range can be short.
  - Close other apps that may hold the BLE connection and avoid pairing the device in Windows Bluetooth settings.
- Connected but robot does not react:
  - Open Arduino Serial Monitor (115200) to see received commands.
  - Confirm the characteristic UUID matches your firmware.
  - Ensure the text commands match what the firmware expects (edit `COMMANDS` in `main.py` if needed).
  - Try toggling `REQUIRE_RESPONSE_ON_WRITE` between `True` and `False`.
- Backend/platform issues:
  - Windows BLE support requires a compatible Bluetooth adapter and drivers.
  - Linux/macOS are not covered here; consult Bleak docs for platform specifics.


## Install the Arduino sketch (UNO R4 WiFi)

Required Arduino libraries (install via Library Manager):
- ArduinoBLE
- Arduino_LED_Matrix
- AFMotor_R4
- NewPing
- Servo

Steps:
1. Open Arduino IDE 2.x.
2. Install the libraries above (Tools → Manage Libraries…).
3. Open `sketch/ardubotr4.ino`.
4. Select the board: Arduino UNO R4 WiFi.
5. Select the correct COM port.
6. Upload the sketch.
7. Open Serial Monitor at 115200 baud to observe logs.

BLE service and characteristic (defined in the sketch):
- Service UUID: `19B10000-E8F2-537E-4F6C-D104768A1214`
- Characteristic UUID: `19B10001-E8F2-537E-4F6C-D104768A1214`

Commands accepted by the firmware (plain text):
- `forward` (also supports `up`)
- `back` / `backward` (also supports `down`)
- `left` 
- `right`
- `switch` / `stop` (toggles enable/stop)

Safety and behavior:
- The robot will not drive forward if an obstacle is closer than 22 cm (ultrasonic check).
- The LED matrix shows arrows for motion and a circle when toggled by `switch`.
- A small servo scans left/right to help with obstacle awareness.

Wiring reference:
- HC‑SR04: TRIG → A0, ECHO → A1
- Servo signal → D10
- Encoders (optional): right → A2, left → A3
- DC motors on AFMotor_R4 shield: channels 1 and 2


## License
This project is released into the public domain via The Unlicense. See the `LICENSE` file for details.
