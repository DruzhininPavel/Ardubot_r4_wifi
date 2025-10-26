/*
 * BLE Robot Controller for Arduino UNO R4 WiFi
 * Control a robot over Bluetooth Low Energy with obstacle detection
 * Show commands on the LED matrix and in the Serial monitor
 */

#include <ArduinoBLE.h>
#include "Arduino_LED_Matrix.h"
#include "AFMotor_R4.h"
#include "NewPing.h"
#include "Servo.h"

// Ultrasonic sensor pin configuration
#define TRIG_PIN A0
#define ECHO_PIN A1
#define MAX_DISTANCE 200
#define MAX_SPEED 190
#define MAX_SPEED_OFFSET 20
#define RIGHT_ENCODER A2
#define LEFT_ENCODER A3
#define MIN_SAFE_DISTANCE 22  // Minimum safe distance in cm

ArduinoLEDMatrix matrix;
NewPing sonar(TRIG_PIN, ECHO_PIN, MAX_DISTANCE);
AF_DCMotor motor1(1);
AF_DCMotor motor2(2);
Servo myservo;

// BLE Service and Characteristic
BLEService robotService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEStringCharacteristic commandCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLEWrite, 20);

// Robot state variables
boolean goesForward = false;
boolean robotEnabled = true;  // Flag for switch button
int distance = 100;
int right_encoder = 0;
int left_encoder = 0;

// LED matrix patterns (12x8)
// Up arrow (forward)
const uint32_t arrowUp[3] = {
  0x00040E1F,
  0x0E040404,
  0x04040000
};

// Down arrow (backward)
const uint32_t arrowDown[3] = {
  0x00040404,
  0x04040E1F,
  0x0E040000
};

// Left arrow
const uint32_t arrowLeft[3] = {
  0x00040C1C,
  0x0C040404,
  0x0C1C0C04
};

// Right arrow
const uint32_t arrowRight[3] = {
  0x00040C04,
  0x0C040C1C,
  0x1C0C0400
};

// Circle for SWITCH state
const uint32_t circle[3] = {
  0x000E1111,
  0x11110E00,
  0x00000000
};

// Blank frame
const uint32_t blank[3] = {
  0x00000000,
  0x00000000,
  0x00000000
};

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("BLE Robot Controller for Arduino UNO R4 WiFi");
  Serial.println("=========================================");

  // Initialize LED matrix
  matrix.begin();
  matrix.loadFrame(blank);

  // Initialize servo
  myservo.attach(10);
  myservo.write(100);  // Center position
  delay(1000);

  // Initial distance check
  distance = readPing();
  delay(100);

  // Initialize BLE
  if (!BLE.begin()) {
    Serial.println("Failed to initialize BLE!");
    while (1);
  }

  // Configure BLE peripheral
  BLE.setLocalName("ardubotr4");
  BLE.setDeviceName("ardubotr4");
  BLE.setAdvertisedService(robotService);

  // Add characteristic to service
  robotService.addCharacteristic(commandCharacteristic);
  BLE.addService(robotService);

  // Start BLE advertising
  BLE.advertise();

  Serial.println("BLE device is ready!");
  Serial.println("Device name: ardubotr4");
  Serial.println("Waiting for central...");
}

void loop() {
  // Wait for central to connect
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to central: ");
    Serial.println(central.address());

    // While central is connected
    while (central.connected()) {
      // Check if a command was written
      if (commandCharacteristic.written()) {
        String command = commandCharacteristic.value();
        handleCommand(command);
      }
    }

    // When central disconnects
    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
    matrix.loadFrame(blank);
  }
}

// ============== SENSOR AND MOTOR HELPERS ==============

// Read distance from ultrasonic sensor
int readPing() {
  delay(70);
  int cm = sonar.ping_cm();
  if (cm == 0) {
    cm = 250;  // If no echo, assume no obstacle
  }
  return cm;
}

// Update encoder readings
void updateEncoders() {
  right_encoder = digitalRead(RIGHT_ENCODER);
  left_encoder = digitalRead(LEFT_ENCODER);
  Serial.print("Left: ");
  Serial.print(left_encoder);
  Serial.print(" Right: ");
  Serial.println(right_encoder);
}

// Stop motors
void moveStop() {
  motor1.run(RELEASE);
  motor2.run(RELEASE);
  goesForward = false;
  updateEncoders();
}

// Drive forward (with obstacle check)
void moveForward() {
  distance = readPing();

  if (distance <= MIN_SAFE_DISTANCE) {
    Serial.print("OBSTACLE! Distance: ");
    Serial.print(distance);
    Serial.println(" cm");
    moveStop();
    return;
  }

  goesForward = true;
  motor1.run(FORWARD);
  motor2.run(FORWARD);
  motor1.setSpeed(MAX_SPEED);
  motor2.setSpeed(MAX_SPEED);
  updateEncoders();
}

// Drive backward
void moveBackward() {
  goesForward = false;
  motor1.run(BACKWARD);
  motor2.run(BACKWARD);
  motor1.setSpeed(MAX_SPEED);
  motor2.setSpeed(MAX_SPEED);
  updateEncoders();
}

// Turn right
void turnRight() {
  motor1.run(BACKWARD);
  motor2.run(FORWARD);
  motor1.setSpeed(MAX_SPEED);
  motor2.setSpeed(MAX_SPEED);
  delay(300);
  moveStop();
  updateEncoders();
}

// Turn left
void turnLeft() {
  motor1.run(FORWARD);
  motor2.run(BACKWARD);
  motor1.setSpeed(MAX_SPEED);
  motor2.setSpeed(MAX_SPEED);
  delay(300);
  moveStop();
  updateEncoders();
}

// Look right with servo
int lookRight() {
  myservo.write(50);
  delay(500);
  int dist = readPing();
  delay(100);
  myservo.write(100);
  return dist;
}

// Look left with servo
int lookLeft() {
  myservo.write(170);
  delay(500);
  int dist = readPing();
  delay(100);
  myservo.write(100);
  return dist;
}

// ============== BLE COMMAND HANDLING ==============

// Handle received command
void handleCommand(String command) {
  Serial.print("Received command: ");
  Serial.println(command);

  command.trim();
  command.toLowerCase();

  // If robot is disabled (switch), ignore all commands except 'switch'
  if (!robotEnabled && command != "switch" && command != "stop") {
    Serial.println("-> Robot disabled. Send 'switch' to enable");
    return;
  }

  if (command == "forward" || command == "up") {
    Serial.println("-> FORWARD");
    matrix.loadFrame(arrowUp);
    moveForward();
  }
  else if (command == "backward" || command == "down" || command == "back") {
    Serial.println("-> BACKWARD");
    matrix.loadFrame(arrowDown);
    moveBackward();
  }
  else if (command == "left") {
    Serial.println("-> LEFT");
    matrix.loadFrame(arrowLeft);
    turnLeft();
  }
  else if (command == "right") {
    Serial.println("-> RIGHT");
    matrix.loadFrame(arrowRight);
    turnRight();
  }
  else if (command == "switch" || command == "stop") {
    robotEnabled = !robotEnabled;  // Toggle enabled state
    if (robotEnabled) {
      Serial.println("-> ROBOT ENABLED");
    } else {
      Serial.println("-> ROBOT STOPPED (switch)");
      moveStop();
    }
    matrix.loadFrame(circle);
    delay(500);
    matrix.loadFrame(blank);
  }
  else {
    Serial.print("-> Unknown command: ");
    Serial.println(command);
    matrix.loadFrame(blank);
  }
}
