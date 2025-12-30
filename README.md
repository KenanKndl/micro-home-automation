# PIC16F877A Home Automation System (Assembly)

This project implements a distributed Home Automation System using two **PIC16F877A** microcontrollers communicating over **UART**. The system is divided into two functional nodes: a Central Control Unit (Board 1) and an Environment/Actuator Node (Board 2).

The project is written entirely in **MPASM Assembly**.

## 🏗 System Architecture

The system operates on a Master-Slave architecture:
* **Board 1 (Master/UI):** Handles user input (Keypad), displays system status (LCD), and regulates local temperature (Fan/Heater logic). It requests data from Board 2.
* **Board 2 (Slave/Sensor):** Monitors environmental data (Pressure/Temperature/Light) and controls a Stepper Motor (representing blinds/curtains) based on day/night cycles or manual commands.

### Communication
* **Protocol:** UART (Asynchronous Serial)
* **Baud Rate:** 9600 bps
* **Connection:** `TX` of Board 1 connects to `RX` of Board 2, and vice versa.

---

## 🖥 Board 1: Control & UI Node
*Filename: `Board1.asm` (or Main Board)*

This board acts as the interface for the user.

### Features
* **User Interface:** 4x4 Keypad for menu navigation and setting thresholds.
* **Display:** 2x16 LCD screen showing current temperature (Local & Remote), pressure, and lighting status.
* **Temperature Control:** Reads a local temperature sensor (e.g., LM35 or DS18B20) and controls a **Fan/Heater** relay to maintain a target temperature (e.g., 20.00°C).
* **Master Logic:** Sends polling commands to Board 2 to fetch remote sensor data.

---

## ⚙️ Board 2: Sensor & Actuator Node
*Filename: `Board2.asm`*

This board handles external environmental sensing and physical actuation.

### Features
* **I2C Integration:** Drivers for **BMP180** Sensor (Reads Temperature & Atmospheric Pressure).
* **ADC Sensors:**
    * **LDR (Light Dependent Resistor):** Detects Day/Night cycles.
    * **Potentiometer:** Manual override input for motor position.
* **Stepper Motor Control:**
    * **Night Mode:** Automatically rotates motor to "Closed" position when LDR < Threshold.
    * **Day Mode:** Motor position follows the Potentiometer value.
    * **Soft-Start/Stop:** Includes acceleration logic (Step tables).

### Pinout (Board 2)

| Component | PIN | PORT | Function |
| :--- | :--- | :--- | :--- |
| **Stepper Motor** | RB0-RB3 | PORTB | Motor Coils |
| **BMP180** | RC3, RC4 | PORTC | I2C (SCL/SDA) |
| **UART** | RC6, RC7 | PORTC | TX / RX |
| **LDR** | RA3 (AN3) | PORTA | Light Sensor |
| **Potentiometer** | RA0 (AN0) | PORTA | Manual Position |

---

## 📡 UART Command Protocol

Board 1 sends 1-byte commands to Board 2 to request data.

| Command Hex | Macro Name | Action |
| :--- | :--- | :--- |
| `0x01` | `CMD_GET_CUR_FRAC` | Get Motor Current Pos (Fraction) |
| `0x02` | `CMD_GET_CUR_INT` | Get Motor Current Pos (Integer) |
| `0x03` | `CMD_GET_TEMP_FRAC` | Get BMP180 Temp (Fraction) |
| `0x04` | `CMD_GET_TEMP_INT` | Get BMP180 Temp (Integer) |
| `0x05` | `CMD_GET_PRES_FRAC` | Get BMP180 Pressure (Fraction) |
| `0x06` | `CMD_GET_PRES_INT` | Get BMP180 Pressure (Integer) |
| `0x08` | `CMD_GET_LIGHT_INT` | Get LDR Light Level |

---

## 🛠 Compilation & Build

### Requirements
* **Toolchain:** GPASM (GNU PIC Assembler) or MPLAB IDE (v8.92 or X).
* **Device:** PIC16F877A
* **Frequency:** 20 MHz (HS Oscillator)

### How to Compile
```bash
# Compile Board 1
gpasm Board1.asm

# Compile Board 2
gpasm Board2.asm