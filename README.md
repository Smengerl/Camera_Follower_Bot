# Camera Follower Bot

Small repository that runs a camera-based face/pose follower and communicates over serial to a controller.

## Quickstart

Prerequisites

- Python 3.8+ installed and on PATH
- git (optional)

Setup virtual environment and install dependencies

```bash
# create/recreate the venv and install requirements
./scripts/setup.sh

# activate (optional)
source .venv/bin/activate
```

Run tests

```bash
# uses the repo venv python to run pytest. Any parameter is optional
./scripts/test.sh -q
```

Run the camera processor

```bash
# runs the camera processor using the venv python. Any parameter is optional
./scripts/run_camera.sh --model-path ./blaze_face_short_range.tflite --camera-id 0
```

Notes

- `scripts/test.sh` and `scripts/run_camera.sh` call the `.venv` python directly so you don't need to activate the venv to run them.
- `pytest.ini` is configured to include `src` on the pythonpath so tests can import `camera_follower_bot`.
- If you prefer editable install instead of using PYTHONPATH, run:

```bash
.venv/bin/pip install -e .
```

Contributing

Feel free to open PRs and run tests locally using the above scripts.

## Initial setup (models and venv)

1. Create the virtual environment and install dependencies using the provided script:

```bash
./scripts/setup.sh
```

2. Download the BlazeFace TFLite model and place it into the `models/` directory.
	See `models/README.txt` for guidance on where to get the model and how to place it.

3. Run the camera processor and point it to the model file:

```bash
./scripts/run_camera.sh --model-path models/blaze_face_short_range.tflite --camera-id 0
```

If you prefer to keep the model in a different path, pass that path with `--model-path` when invoking the run script.
