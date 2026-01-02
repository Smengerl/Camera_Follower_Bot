
# About

Camera Follower Bot is a Python-based system for real-time face and pose tracking with a webcam, controlling a microcontroller to follow detected targets.

<!--
Suggested GitHub Topics/Tags:
robotics, computer-vision, python, opencv, mediapipe, microcontroller, raspberry-pi-pico, micropython, face-detection, pose-estimation, serial-communication, automation, hardware, camera, tracking, real-time
-->
# Camera Follower Bot

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](#)
[![License](https://img.shields.io/badge/license-MIT-green)](#)

## Project Overview

Camera Follower Bot is a lightweight, real-time camera tracking system that detects faces and poses, then drives a microcontroller via serial communication to physically track them. This project is a robust, testable, and scriptable rework of the original "camera follower robot" project by Will Cogley (https://willcogley.notion.site/).

It is designed for hobbyists and developers who want to build a camera-based tracking robot using Python, MediaPipe, OpenCV, and a microcontroller such as the Raspberry Pi Pico running MicroPython.

Table of Contents
- Features
- Usage
- Development
- Contributing
- License

Features/improvements
--------
- Real-time camera processing using MediaPipe / OpenCV
- Simple CLI for running and configuring the processor
- Reconnect/backoff logic for serial communication with Raspberry Pi running the robot
- Displaying of robot logs on computer preview window
- Unit tests and pytest configuration
- Migrated to new MediaPipe APIs
- Helper scripts to setup venv, run tests, and run the processor


Prerequisites
-------------
- Python 3.8 or newer

Hardware Requirements
---------------------
- A Raspberry Pi Pico or similar microcontroller running MicroPython, connected via serial port to receive commands
- Webcam connected to host computer

Usage
----------
1. Create the virtual environment and install dependencies (scripted):

```bash
./scripts/setup.sh
```

2. Download the MediaPipe BlazeFace TFLite model and place it into `models/`.
   See `models/README.txt` for instructions and an example filename (`blaze_face_short_range.tflite`).


3. Run tests (uses the repo venv python):

```bash
./scripts/test.sh
```

4. Connect a microcontroller runnning micro python via USB to Serial and upload the files in `src/camera_follower_bot/rpi_pico_code/` to the device. Make sure to have `src/camera_follower_bot/rpi_pico_code/follower_bot.py` to be auto started (e.g. renaming it to main.py when uploaded). Reboot the microcontoller and leave it connected to your computer.

5. Run the camera processor on your computer and point it to the model file:

```bash
./scripts/run_camera.sh --model-path models/blaze_face_short_range.tflite
```

6. Check if the camera preview window opens and the computer connects to the microcontroller (visible when you see the microcontroller's output). If this fails, adapt your settings/parameters (see below)

Options
-------
- `--model-path` Path to a TFLite model file (default: see project defaults)
- `--serial-port` Serial device path (default: see project defaults)
- `--baud` Serial baud rate (default: see project defaults)
- `--camera-id` Camera device id (integer passed to OpenCV)
- `--no-serial` Run without serial hardware (useful for testing)
- `--rotate180` / `--no-rotate180` Rotate camera image by 180 degrees (default: enabled)
- `--flip` / `--no-flip` Flip camera image horizontally (default: enabled)
- `--forward-serial-stdio` Tunnel all data read or written via serial to stdout


Development
-----------
- The package lives under `src/camera_follower_bot`. Tests live in `tests/` and `pytest.ini` adds `src` to PYTHONPATH.
- To run tests using the venv python explicitly:

```bash
.venv/bin/python -m pytest
```

- To run the main module directly (developer use):

```bash
.venv/bin/python -m camera_follower_bot.run_camera
```

Contributing
------------
- Open an issue or a PR. Keep changes small and include tests where appropriate.
- If adding dependencies, please update `requirements.txt` and add a short note in the PR describing the reason.

License
-------
This project is distributed under the MIT license. See `LICENSE` for details.
