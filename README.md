[![Twitter: @NorowaretaGemu](https://img.shields.io/badge/X-@NorowaretaGemu-blue.svg?style=flat)](https://x.com/NorowaretaGemu)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<div align="center">
  <a href="https://ko-fi.com/cursedentertainment">
    <img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="ko-fi" style="width: 20%;"/>
  </a>
</div>
<div align="center">
  <img alt="C++" src="https://img.shields.io/badge/c++%20-%23323330.svg?&style=for-the-badge&logo=c%2B%2B&logoColor=white"/>
</div>

<div align="center">
  <img alt="Arduino" src="https://img.shields.io/badge/-Arduino-323330?style=for-the-badge&logo=arduino&logoColor=white"/>
</div>

<div align="center">
  <img alt="Git" src="https://img.shields.io/badge/git%20-%23323330.svg?&style=for-the-badge&logo=git&logoColor=white"/>
  <img alt="Shell" src="https://img.shields.io/badge/Shell-%23323330.svg?&style=for-the-badge&logo=gnu-bash&logoColor=white"/>
</div>



---

# MILA
## MINIATURE INTEGRATED LOGIC AUTOMATON
### A DREAM Robotics Agent

- Robot Type: Tank

<div align="center">
  <img src="images/mila_avatar.jpg" alt="MILA avatar: a human representation of the robot" width="320"/>
  <p><i>MILA</i></p>
</div>

<div align="center">
  <img src="images/mila-robot-front.png" alt="MILA Robot front view" width="400"/>
  <img src="images/mila-robot-angle.png" alt="MILA Robot angled view" width="400"/>
  <img src="images/mila-robot-side.png" alt="MILA Robot side view" width="400"/>
  <img src="images/mila-robot-top.png" alt="MILA Robot top view" width="400"/>
</div>

---

### Software
- [Arduino IDE](https://docs.arduino.cc/software/ide/)

---

## Related Projects (DREAM Robotics Ecosystem)

- [WHIP-Robot-v00](https://github.com/CursedPrograms/WHIP-Robot-v00)
- [KIDA-Robot-v00](https://github.com/CursedPrograms/KIDA-Robot-v00)
- [KIDA-Robot-v01](https://github.com/CursedPrograms/KIDA-Robot-v01)
- [NORA-Robot-v00](https://github.com/CursedPrograms/NORA-Robot-v00)
- [IDA-Robot-v01](https://github.com/CursedPrograms/IDA-Robot-v00)
- [ARM-Robot-v01](https://github.com/CursedPrograms/ARM-Robot-v01)
- [RIFT](https://github.com/CursedPrograms/RIFT)
- [DREAM](https://github.com/CursedPrograms/DREAM)

---

## Overview

**Website: <https://cursedprograms.github.io/MILA/>**

MILA is a small tank-chassis robot you can drive over WiFi. It hosts its own web dashboard, streams live sensor data, and can steer itself around obstacles.

- **Drive modes:** WASD (car-style), TANK (independent tracks) and OBSTACLE (autonomous).
- **Live telemetry:** front, left and right distance, temperature, humidity and the last IR remote key.
- **WiFi dashboard:** served by the ESP8266 on port `5010`. MILA hosts her own access point at `192.168.4.1`, or joins NORA's network in fleet mode.
- **Safety:** a collision guard force-stops the robot in manual modes, and a watchdog stops it if the connection drops.
- **Speed:** cycle 100 / 75 / 50 / 25 % from the IR remote, or set an exact value from the dashboard slider.

---

## Hardware

- Small metal tank robot chassis
- UNO + WiFi R3 style board (ATmega328P + integrated ESP8266)
- 2S 18650 battery pack
- L298N motor driver
- MG95 servo
- HC-SR04 ultrasonic sensor
- 2× 5 V DC motors
- RGB LED
- AHT10 temperature & humidity sensor (I2C)
- Photoresistor module (digital out)
- Buzzer
- NEC IR receiver + remote

### Pinout (`scripts/MILA/MILA.ino`)

| Signal | Pin | | Signal | Pin |
|---|---|---|---|---|
| Ultrasonic TRIG / ECHO | 2 / 3 | | Servo | 11 |
| Right motor IN1 / IN2 / ENA | 4 / 5 / 9 | | Buzzer | 8 |
| Left motor IN3 / IN4 / ENB | 6 / 7 / 10 | | Light sensor (DO) | 12 |
| RGB LED R / G / B | A0 / A1 / A2 | | IR receiver | A3 |
| AHT10 SDA / SCL | A4 / A5 | | ESP8266 link | Serial (DIP 1 + 2) |

> [!WARNING]
> **Speed control and the servo share a timer.** ENA and ENB are on pins 9 and 10, which the Servo library takes over (Timer1). At 100 % speed the motors are switched fully on and work. At 75 / 50 / 25 % the PWM is lost, so the motors may barely move or stop, and the servo can twitch. Fix it by swapping four wires and the matching constants in `MILA.ino`: **ENA ↔ IN2** (ENA → 5, IN2 → 9) and **ENB ↔ IN3** (ENB → 6, IN3 → 10). Pins 5 and 6 are Timer0 PWM, which nothing else uses.

---

## Quick start

### DIP switches (UNO + WiFi R3 board)

The board's 8 DIP switches choose what the USB port and the two chips are connected to. Switch 8 is unused.

| What you're doing | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **Running MILA** (Arduino ↔ ESP8266) | ON | ON | off | off | off | off | off | off |
| **Upload `scripts/MILA`** (USB → ATmega328) | off | off | ON | ON | off | off | off | off |
| **Upload `scripts/esp8266`** (USB → ESP8266, flash mode) | off | off | off | off | ON | ON | ON | off |
| **ESP8266 Serial Monitor** (USB ↔ ESP8266) | off | off | off | off | ON | ON | off | off |
| USB ↔ ATmega328 ↔ ESP8266 all linked | ON | ON | ON | ON | off | off | off | off |

1. Set **3 + 4 ON** and upload `scripts/MILA`.
2. Set **5 + 6 + 7 ON** and upload `scripts/esp8266` (press reset if the upload won't start).
3. Set **1 + 2 ON**, everything else off, and power-cycle to drive her.

In the running setting the Arduino's serial goes to the ESP, not USB, so the Serial Monitor shows nothing. Use 3 + 4 to read her `DIST:` / `IR:` lines over USB.

> [!NOTE]
> Check this against the table printed on your board, as some clones differ slightly.

### Flash and connect

Flash the firmware from `scripts/esp8266` and `scripts/MILA` with the Arduino IDE (set the DIP switches above first), power the robot on, and join her WiFi network. Then open the dashboard in a browser, or run a desktop controller:

```
./run.sh                      # macOS / Linux / Git Bash
run.bat                       # Windows (cmd)
.\run.ps1                     # Windows (PowerShell)

./run.sh --host 192.168.4.1 --port 5010
```

If MILA joined NORA's network (fleet mode) she won't be at `192.168.4.1`. Press **SCAN NETWORK** in the C++, C# or F# controller, or start it with `--host auto`.

### Talking (in Brainfuck)
The robots talk in **Brainfuck**: every phrase is a Brainfuck program that prints its words (hello is `++++++++[>+++++++++++++<-]>.+.` → `hi`), and a robot says it by beeping the program on its buzzer, one tone per symbol, pitched to its own voice. The phrasebook (`talk_bf.h`) is generated by RIFT's `Fleet/brainfuck_talk.py`: phrases 0–6 (hello, how are you, happy, curious, sleepy, let's play, bye) and their replies 7–13. [RIFT](https://github.com/CursedPrograms/RIFT) runs the conversations between robots over WiFi and logs them on its dashboard; it asks MILA to speak with `GET /chirp?u=<0-13>`. Her UNO plays `TALK:<u>` (from the ESP8266) through her own beep(), a little higher than NORA, and respects MUTE; she only talks while stopped outside OBSTACLE mode. The ESP8266 forwards `/chirp` to the UNO and registers `talk:5010`, so RIFT includes her in the conversations.

### Driven by NORA (fleet IR link)
[NORA](https://github.com/CursedPrograms/NORA-Robot-v00) can drive MILA through her IR transmitter, from her web page, Python controller or Bluetooth. The frames are Samsung-format IR at address `0x0DA2`, with the fleet link's commands: `0x48` forward, `0x49` back, `0x4A` left, `0x4B` right, `0x4C` stop, `0x4D` obstacle mode, `0x4E` manual, `0x4F` speed. Driving switches her into WASD mode; `stop` also leaves OBSTACLE mode, and `speed` cycles the speed like the OK button. She stops once the link has been quiet for 500 ms. Link frames print as `LINK:0x..`.

## Desktop controllers

Every controller lives in [`scripts/`](scripts) and has a build-and-run script in `.sh`, `.bat` and `.ps1` form.

| Language | UI toolkit | Run | Radar & graphs | Gamepad |
|---|---|---|:---:|:---:|
| Python | pygame | `run.sh` | | |
| C++ | Win32 / GDI | `scripts/run-cpp.*` | ✓ | ✓ |
| C# | WinForms | `scripts/run-csharp.*` | ✓ | ✓ |
| F# (preview) | WinForms | `scripts/run-fsharp.*` | ✓ | ✓ |
| Rust | egui | `scripts/run-rust.*` | | |
| Go | Ebitengine | `scripts/run-go.*` | | |
| Julia | GLMakie | `scripts/run-julia.*` | | |

**Controls** (all controllers): `1` `2` `3` switch mode, `WASD` / arrow keys drive, `Q` `A` `E` `D` drive the tracks in TANK mode, `Space` stops, `Esc` quits. Everything is also clickable.

**The C++, C# and F# controllers** also have a proximity radar, live distance / temperature / humidity graphs with CSV export, an exact speed slider, network discovery (`--host auto`), remembered host / port / mode, and Xbox gamepad support (stick or D-pad to drive, triggers for speed, `A` to stop, bumpers to change mode).

## Analyzing a session (Fortran)

The **EXPORT CSV** button saves the whole session to `Documents\MILA-telemetry`. `scripts/fortran/telemetry_stats.f90` turns an export into a report: sample rate, time in each drive mode, per-sensor min / max / mean / standard deviation, outliers (beyond 3σ), connection gaps and close calls (front distance under 20 cm). It needs `gfortran` and picks the newest export by default:

```
scripts/run-fortran.sh              # or run-fortran.bat / run-fortran.ps1
scripts/run-fortran.sh my_run.csv
```

## Training data: teach MILA to drive herself

Drive her around by hand (IR remote, keyboard, gamepad or the dashboard), press **EXPORT CSV**, and `scripts/fortran/make_dataset.f90` turns the sessions into a dataset for imitation learning: each row pairs what the ultrasonic sensor saw with what the human was doing.

```
scripts/run-dataset.sh      # every export -> Documents\MILA-telemetry\datasets\drive_policy.csv
scripts/run-dataset.sh out.csv session1.csv session2.csv
```

- **Only human driving is kept** (`wasd` and `tank` modes). Obstacle mode (she drives herself) and moments the collision guard overrode you are dropped.
- **The label is the real motor state.** The Arduino now reports `MOTOR:<left>,<right>` (each -1 / 0 / +1), so the label is the same whichever input you used. The IR remote moves the motors directly and never shows up as a web command, which is why this is needed. It maps to 9 classes: `STOP`, `FORWARD`, `BACKWARD`, `LEFT`, `RIGHT`, `L_FWD`, `L_BWD`, `R_FWD`, `R_BWD`.
- **Features:** front distance, how it is changing (`d_dist`, 5-sample average and minimum), speed and mode. `dist_valid` is 0 when the sensor returned no echo, in which case `dist` is carried over from the last good reading.
- **No data leakage:** every export is its own session, and the last 20 % of each is marked `split=val`.
- Left/right distances are **not** features: the firmware only measures them during the obstacle-mode scan, so in human-driven data they are stale.

Columns: `session,t_s,split,mode,mode_id,dist,dist_valid,d_dist,dist_avg5,dist_min5,speed,motor_l,motor_r,action,action_id,next_action,next_action_id`. `action` is what you were doing at that sample and `next_action` what you did one sample (about 0.4 s) later, so use whichever suits your model. Load it with pandas, or anything that reads CSV.

**Reflash both boards** (`scripts/MILA` and `scripts/esp8266`) to get the motor columns. Exports from older firmware still work, but their labels come from the last web command only, so IR driving is invisible in them. The same reflash also makes the front sensor sample continuously in manual modes, so the distance no longer goes stale while you are stopped or turning.

## Testing without a robot

`scripts/sim` holds a mock MILA that serves the same endpoints as the firmware with simulated sensor data:

```
scripts/run-sim.sh
scripts/run-cpp.sh --host 127.0.0.1
```

## 📡 Who's nearby (ESP-NOW + Bluetooth LE)

Every robot sends a small **"I'm here"** beacon twice a second and listens for the others'. From the **signal strength** it knows roughly how close each one is, and from how that changes over time whether it's **coming closer, steady or leaving**:

| Signal | Zone |
| :--- | :--- |
| above −45 dBm | very close |
| −45 to −60 dBm | near |
| −60 to −75 dBm | medium |
| below −75 dBm | far |

It's coarse (walls, bodies and antenna angle all change it): for "who's around", not distance. Precise collision avoidance stays with the ultrasonic and ToF sensors.

**They tell each other what they're doing**, because a rising signal looks the same from both sides even when only one robot moves. Over ESP-NOW they say it **in Brainfuck**, like the fleet's conversations: each beacon carries a program that prints `park`, `go`, `wait` or `hand` (a human is driving), and the receiver runs it. Bluetooth adverts are too small for a program, so BLE carries the same state as one byte.

**Who makes way**, in self-driving modes only:

| The other robot... | So this one... |
| :--- | :--- |
| is parked | is the one closing in: steers away |
| is yielding | carries on, carefully |
| is driven by a human | makes way (it's unpredictable) |
| drives itself | follows the alphabet: KIDA00, KIDA01, NORA, WHIP; everyone makes way for MILA, who can't hear the others |
| is leaving | carries on |

Making way = stop for 2 s, turn away, then drive on (and not yield again for 5 s, so two robots that stay close don't take turns forever). While another robot is near, or coming closer, it drives slower with wider margins.

MILA's ESP8266 **sends** the beacon over ESP-NOW, with what she's doing said in Brainfuck (`go` in obstacle mode, `hand` when you drive her, `park` when she's stopped), so NORA and WHIP know where she is. Her ESP8266 can't report the signal strength of what it receives, so she can't avoid the others: **they always make way for her**. Code: `scripts/esp8266/esp8266.ino`.

---

## Screenshots

<div align="center">
  <img src="images/screenshots/controller-cpp.png" alt="C++ controller" width="420"/>
  <img src="images/screenshots/controller-csharp.png" alt="C# controller" width="420"/>
  <img src="images/screenshots/controller-python.png" alt="Python controller" width="260"/>
  <img src="images/screenshots/web-dashboard.png" alt="Web dashboard" width="640"/>
</div>

<p align="center"><i>C++ controller, C# controller, Python controller, Web dashboard. Running against MockMila (<code>scripts/sim</code>), so the telemetry is live.</i></p>

---

<br>
<div align="center">© Cursed Entertainment 2026</div>
<br>
<div align="center">
  <a href="https://cursed-entertainment.itch.io/" target="_blank">
    <img src="https://github.com/CursedPrograms/cursedentertainment/raw/main/images/logos/logo-wide-grey.png" alt="CursedEntertainment Logo" style="width:250px;">
  </a>
</div>
<br>
<div align="center">
  <a href="https://github.com/SynthWomb" target="_blank">
    <img src="https://github.com/SynthWomb/synth.womb/blob/main/logos/synthwomb07.png" alt="SynthWomb" style="width:200px;"/>
  </a>
</div>
