# BLE Robot Controller for Arduino UNO R4 WiFi

A smart robot controlled over Bluetooth Low Energy with obstacle detection and LED matrix feedback.

## Features

- Bluetooth LE control – the robot advertises as `ardubotr4` and accepts simple text commands.
- Obstacle detection – ultrasonic sensor prevents collisions.
- LED matrix – shows arrows for the current action and a circle for toggle.
- Servo scanner – rotates the sensor to look left/right.
- Safety – `SWITCH` command toggles enable/stop.

## Hardware

- Arduino UNO R4 WiFi
- Motor Shield with 2 DC motors (AFMotor_R4)
- Ultrasonic sensor HC‑SR04 (TRIG: A0, ECHO: A1)
- Servo on pin 10 for sensor rotation
- Encoders (optional): A2 (right), A3 (left)

## BLE Commands

Send plain text to characteristic `19B10001-E8F2-537E-4F6C-D104768A1214`:

| Command | Action |
|---------|--------|
| `forward`, `up`, `вперед` | Drive forward (with obstacle check)
| `back`, `backward`, `down`, `назад` | Drive backward
| `left`, `влево` | Turn left
| `right`, `вправо` | Turn right
| `switch`, `stop`, `стоп` | Toggle enable/stop

## Safety

- Auto‑stop if obstacle distance < 22 cm.
- `switch` fully disables motor control until toggled again.
- Serial monitoring at 115200 baud logs commands and state.

## Installation (Arduino)

1. Install these libraries via Arduino IDE Library Manager:
   - `ArduinoBLE`
   - `Arduino_LED_Matrix`
   - `AFMotor_R4`
   - `NewPing`
   - `Servo`
2. Open `ardubotr4.ino` in Arduino IDE 2.x.
3. Select board: Arduino UNO R4 WiFi and the correct COM port.
4. Upload the sketch.
5. Optionally open Serial Monitor (115200) for debugging.

## Usage

1. Power the robot. It will advertise as `ardubotr4`.
2. Connect from the Python controller in this repo (`main.py`) or any BLE app.
3. Send one of the commands listed above to the characteristic.
4. Watch the LED matrix and Serial Monitor for feedback.
5. Use `switch` to toggle enable/stop at any time.

## LED Matrix Indicators

- Up arrow – moving forward
- Down arrow – moving backward
- Left arrow – turning left
- Right arrow – turning right
- Circle – toggled/stop state

## Technical Details

- Minimum safe distance: 22 cm
- Motor speed: 190 (MAX_SPEED)
- Servo angles: center 100°, left 170°, right 50°
- BLE Service UUID: `19B10000-E8F2-537E-4F6C-D104768A1214`
- BLE Characteristic UUID: `19B10001-E8F2-537E-4F6C-D104768A1214`

## Author

Made for Arduino UNO R4 WiFi with BLE control and basic autonomous awareness.
