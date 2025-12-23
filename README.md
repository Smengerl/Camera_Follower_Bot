# Camera Follower Bot

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](#)
[![License](https://img.shields.io/badge/license-MIT-green)](#)

Lightweight camera follower that detects faces/poses and drives a microcontroller via serial to track them. This repository contains a more robust, testable, and scriptable rework of the original "camera follower robot" project by Will Cogley https://willcogley.notion.site/ .

Table of Contents
-----------------
- Features
- Quickstart
  - Initial setup (venv & model)
- Usage
- Development
- Contributing
- License

Features
--------
- Real-time camera processing using MediaPipe / OpenCV
- Simple CLI for running and configuring the processor
- Reconnect/backoff logic for serial communication
- Unit tests and pytest configuration
- Helper scripts to setup venv, run tests, and run the processor

Prerequisites
-------------
- Python 3.8 or newer
- Camera device (USB or built-in)
- Optional: a microcontroller listening on a serial port to receive commands

Quickstart
----------
1. Create the virtual environment and install dependencies (scripted):

```bash
./scripts/setup.sh
```

2. Download the MediaPipe BlazeFace TFLite model and place it into `models/`.
   See `models/README.txt` for instructions and an example filename (`blaze_face_short_range.tflite`).

3. Run the camera processor and point it to the model file:

```bash
./scripts/run_camera.sh --model-path models/blaze_face_short_range.tflite
```

Usage
-----
- Run tests (uses the repo venv python):

```bash
./scripts/test.sh
```

- Run the processor:

```bash
./scripts/run_camera.sh
```

Options
-------
- `--model-path` Path to a TFLite model file (default: see project defaults)
- `--serial-port` Serial device path (default: see project defaults)
- `--baud` Serial baud rate (default: see project defaults)
- `--camera-id` Camera device id (integer passed to OpenCV)
- `--no-serial` Run without serial hardware (useful for testing)

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
