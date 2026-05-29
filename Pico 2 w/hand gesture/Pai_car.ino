/*
  ria_z_car_ble_receiver.ino

  Arduino UNO R4 WiFi + RC Car Platform
  BLE Peripheral firmware for Physical AI RC Car control

  BLE device name:
    RIA_Z_01, RIA_Z_02, ..., RIA_Z_18

  Command packet format:
    "07:F" -> Team 07, Forward
    "07:L" -> Team 07, Curve Left Forward
    "07:R" -> Team 07, Curve Right Forward
    "07:S" -> Team 07, Stop

  Pico side behavior:
    Pico sends the current command periodically.
    Example:
      07:F, 07:F, 07:F, ...

  Safety rule:
    If no valid command is received for AUTO_STOP_MS,
    the car stops automatically.
*/

#include <ArduinoBLE.h>


// =========================================================
// Instructor setting
// Change this number before uploading to each UNO R4 WiFi.
// Example:
//   TEAM_ID = 1  -> BLE name: RIA_Z_01
//   TEAM_ID = 7  -> BLE name: RIA_Z_07
// =========================================================
const uint8_t TEAM_ID = 7;


// =========================================================
// BLE UUIDs
// Must be the same as the Pico 2 W module: ria_z_ble_car.py
// =========================================================
const char SERVICE_UUID[] = "19b10000-e8f2-537e-4f6c-d104768a1214";
const char COMMAND_UUID[] = "19b10001-e8f2-537e-4f6c-d104768a1214";

BLEService carService(SERVICE_UUID);

// Max command string length is enough for "07:F".
// We set 12 for a little margin.
BLEStringCharacteristic commandChar(COMMAND_UUID, BLEWrite, 12);


// =========================================================
// Motor pins
// Current RC car platform uses the same motor pin mapping:
//
// Right motor: DIR = 7, PWM = 9
// Left  motor: DIR = 8, PWM = 10
// =========================================================
const int RIGHT_DIR_PIN = 7;
const int RIGHT_PWM_PIN = 9;
const int LEFT_DIR_PIN  = 8;
const int LEFT_PWM_PIN  = 10;


// =========================================================
// Motor direction setting
// If the car moves backward when "F" is received,
// swap these two values.
// =========================================================
const int MOTOR_FORWARD_LEVEL  = LOW;
const int MOTOR_BACKWARD_LEVEL = HIGH;


// =========================================================
// Speed settings
// Range: 0 ~ 255
//
// FORWARD_SPEED:
//   Speed for straight forward.
//
// TURN_OUTER_SPEED:
//   Speed of the outer wheel during curve turn.
//
// TURN_INNER_SPEED:
//   Speed of the inner wheel during curve turn.
//
// Example for left curve:
//   left wheel  = TURN_INNER_SPEED
//   right wheel = TURN_OUTER_SPEED
// =========================================================
const int FORWARD_SPEED    = 90;
const int TURN_OUTER_SPEED = 90;
const int TURN_INNER_SPEED = 40;


// =========================================================
// Safety setting
// If no valid command is received within this time,
// the car stops automatically.
// This function is NOT removed.
// =========================================================
const unsigned long AUTO_STOP_MS = 400;


// =========================================================
// State variables
// =========================================================
unsigned long lastValidCommandTime = 0;

bool motorRunning = false;

// Current command state.
// Initial state is Stop.
char currentCommand = 'S';


void setup() {
  Serial.begin(115200);

  // Do not block forever when Serial Monitor is not open.
  unsigned long startWait = millis();
  while (!Serial && millis() - startWait < 2000) {
    ;
  }

  pinMode(RIGHT_DIR_PIN, OUTPUT);
  pinMode(RIGHT_PWM_PIN, OUTPUT);
  pinMode(LEFT_DIR_PIN, OUTPUT);
  pinMode(LEFT_PWM_PIN, OUTPUT);

  currentCommand = 'S';
  stopMotors();

  if (!BLE.begin()) {
    Serial.println("BLE begin failed");

    while (1) {
      stopMotors();
      delay(1000);
    }
  }

  char localName[16];
  snprintf(localName, sizeof(localName), "RIA_Z_%02d", TEAM_ID);

  BLE.setLocalName(localName);
  BLE.setDeviceName(localName);
  BLE.setAdvertisedService(carService);

  carService.addCharacteristic(commandChar);
  BLE.addService(carService);

  commandChar.writeValue("");

  BLE.advertise();

  Serial.println("RIA Z BLE Car ready");
  Serial.print("Team ID: ");
  Serial.println(TEAM_ID);
  Serial.print("BLE name: ");
  Serial.println(localName);
  Serial.print("AUTO_STOP_MS: ");
  Serial.println(AUTO_STOP_MS);
  Serial.print("FORWARD_SPEED: ");
  Serial.println(FORWARD_SPEED);
  Serial.print("TURN_OUTER_SPEED: ");
  Serial.println(TURN_OUTER_SPEED);
  Serial.print("TURN_INNER_SPEED: ");
  Serial.println(TURN_INNER_SPEED);
  Serial.println("Waiting for Pico 2 W connection...");
}


void loop() {
  BLE.poll();

  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to Pico 2 W: ");
    Serial.println(central.address());

    // Safety start state.
    currentCommand = 'S';
    stopMotors();

    // Give the connection a fresh timeout reference.
    lastValidCommandTime = millis();

    while (central.connected()) {
      BLE.poll();

      if (commandChar.written()) {
        String packet = commandChar.value();
        handlePacket(packet);
      }

      // Auto stop if command stream is lost.
      if (motorRunning && millis() - lastValidCommandTime > AUTO_STOP_MS) {
        Serial.println("Auto stop: command timeout");

        stopMotors();
        currentCommand = 'S';
      }
    }

    Serial.println("Disconnected from Pico 2 W");

    currentCommand = 'S';
    stopMotors();

    Serial.println("Waiting for Pico 2 W connection...");
  }
}


void handlePacket(String packet) {
  packet.trim();

  if (packet.length() < 4) {
    Serial.print("Invalid packet length: ");
    Serial.println(packet);
    return;
  }

  if (!isDigit(packet[0]) || !isDigit(packet[1]) || packet[2] != ':') {
    Serial.print("Invalid packet format: ");
    Serial.println(packet);
    return;
  }

  int receivedTeamId = (packet[0] - '0') * 10 + (packet[1] - '0');
  char cmd = packet[3];

  if (receivedTeamId != TEAM_ID) {
    Serial.print("Wrong team ID. Ignored: ");
    Serial.println(packet);
    return;
  }

  if (!isValidCommand(cmd)) {
    Serial.print("Unknown command. Stop for safety: ");
    Serial.println(packet);

    currentCommand = 'S';
    stopMotors();
    return;
  }

  // Very important:
  // Even if the same command is repeatedly received,
  // update this time to show that Pico is still alive.
  lastValidCommandTime = millis();

  // If command is the same as current state,
  // do not print or call motor function again.
  if (cmd == currentCommand) {
    return;
  }

  // Command changed.
  currentCommand = cmd;

  Serial.print("New command: ");
  Serial.println(currentCommand);

  executeCommand(currentCommand);
}


bool isValidCommand(char cmd) {
  return (cmd == 'F' || cmd == 'L' || cmd == 'R' || cmd == 'S');
}


void executeCommand(char cmd) {
  switch (cmd) {
    case 'F':
      moveForward();
      break;

    case 'L':
      curveLeftForward();
      break;

    case 'R':
      curveRightForward();
      break;

    case 'S':
      stopMotors();
      break;

    default:
      stopMotors();
      break;
  }
}


void setMotor(int leftSpeed, int rightSpeed) {
  leftSpeed = constrain(leftSpeed, -255, 255);
  rightSpeed = constrain(rightSpeed, -255, 255);

  if (leftSpeed >= 0) {
    digitalWrite(LEFT_DIR_PIN, MOTOR_FORWARD_LEVEL);
    analogWrite(LEFT_PWM_PIN, leftSpeed);
  } else {
    digitalWrite(LEFT_DIR_PIN, MOTOR_BACKWARD_LEVEL);
    analogWrite(LEFT_PWM_PIN, -leftSpeed);
  }

  if (rightSpeed >= 0) {
    digitalWrite(RIGHT_DIR_PIN, MOTOR_FORWARD_LEVEL);
    analogWrite(RIGHT_PWM_PIN, rightSpeed);
  } else {
    digitalWrite(RIGHT_DIR_PIN, MOTOR_BACKWARD_LEVEL);
    analogWrite(RIGHT_PWM_PIN, -rightSpeed);
  }

  motorRunning = (leftSpeed != 0 || rightSpeed != 0);
}


void moveForward() {
  setMotor(FORWARD_SPEED, FORWARD_SPEED);
}


void curveLeftForward() {
  // Curve left while moving forward.
  // Left wheel is slower, right wheel is faster.
  setMotor(TURN_INNER_SPEED, TURN_OUTER_SPEED);
}


void curveRightForward() {
  // Curve right while moving forward.
  // Left wheel is faster, right wheel is slower.
  setMotor(TURN_OUTER_SPEED, TURN_INNER_SPEED);
}


void stopMotors() {
  analogWrite(LEFT_PWM_PIN, 0);
  analogWrite(RIGHT_PWM_PIN, 0);

  motorRunning = false;
}
