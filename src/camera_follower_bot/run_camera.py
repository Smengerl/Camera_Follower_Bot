#!/usr/bin/env python3
"""Run the camera processor with configurable options via CLI.

This script uses argparse to configure:
 - serial port device
 - baud rate
 - model path
 - camera id
 - --no-serial flag to run without hardware (useful for testing)

It patches the `CameraProcessor` module at runtime so the existing
`CameraProcessor.main()` can be used without modifying its signature.
"""
import argparse
import sys
import os


def build_parser():
    p = argparse.ArgumentParser(description='Run Camera Follower with configurable options')
    p.add_argument('--serial-port', default='/dev/cu.usbmodem101', help='Serial device path')
    p.add_argument('--baud', type=int, default=115200, help='Serial baud rate')
    p.add_argument('--model-path', default=None, help='Path to the MediaPipe TFLite model')
    p.add_argument('--camera-id', type=int, default=None, help='Camera device id (integer passed to OpenCV)')
    p.add_argument('--no-serial', action='store_true', help='Run without serial hardware (for testing)')
    p.add_argument('--rotate180', dest='rotate180', action='store_true', default=True, help='Rotate camera image by 180 degrees (default: enabled)')
    p.add_argument('--no-rotate180', dest='rotate180', action='store_false', help='Do not rotate camera image by 180 degrees')
    p.add_argument('--flip', dest='flip', action='store_true', default=True, help='Flip camera image horizontally (default: enabled)')
    p.add_argument('--no-flip', dest='flip', action='store_false', help='Do not flip camera image horizontally')
    return p


class DummySerialManager:
    """A no-op SerialManager used when --no-serial is selected.

    Implements the minimal methods used by CameraProcessor so the
    main loop runs but no data is sent.
    """
    def __init__(self, *args, **kwargs):
        self.port = kwargs.get('port') if kwargs else None
        from collections import deque
        self.stdout_buffer = deque(maxlen=100)

    def connect(self):
        return True

    def reconnect_if_needed(self):
        return None

    def is_connected(self):
        return False

    def send_position(self, error_x, error_y):
        print(f"[no-serial] {error_x},{error_y}")
        return True
    
    def read_stdout(self):
        return False
    
    def get_stdout_buffer(self, max_lines=None):
        return []
    
    def clear_stdout_buffer(self):
        pass


def validate_model_path(path: str):
    """Validate that the TFLite model exists and provide helpful instructions if not.

    If the model file is missing, print guidance where to obtain compatible
    MediaPipe BlazeFace models and exit the program with a non-zero code.
    """
    if not path:
        print("Error: MODEL_PATH is empty.")
        print_help_for_models()
        sys.exit(2)

    if not os.path.isfile(path):
        print(f"Error: Face model not found at: {path}")
        print_help_for_models()
        sys.exit(2)


def print_help_for_models():
    print("\nHow to obtain a compatible MediaPipe face detection model:")
    print(" - Use MediaPipe BlazeFace TFLite models (short/long range as needed).")
    print(" - Example sources:")
    print("     * https://github.com/google/mediapipe (search for blaze_face tflite assets)")
    print("     * Prebuilt TFLite files sometimes live on model zips or sample repos")
    print(" - Place the .tflite file locally and pass its path via --model-path or set MODEL_PATH.")
    print(" - If you use `run_camera.py`, pass --model-path /path/to/blaze_face_short_range.tflite")
    print("")


def check_dependencies():
    missing = []
    try:
        import cv2  # noqa: F401
    except Exception:
        missing.append('opencv-python')
    try:
        import mediapipe  # noqa: F401
    except Exception:
        missing.append('mediapipe')
    try:
        import numpy  # noqa: F401
    except Exception:
        missing.append('numpy')
    try:
        import serial  # noqa: F401
    except Exception:
        missing.append('pyserial')

    if missing:
        print('\nMissing required Python packages:')
        for pkg in missing:
            print(' -', pkg)
        print('\nInstall dependencies with:')
        print('  pip install -r requirements.txt')
        print('\nOr install missing packages directly, for example:')
        print('  pip install ' + ' '.join(missing))
        print('\nIf you need a ready set of pinned versions, see requirements.txt in this repo.')
        sys.exit(3)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    # Quick dependency check before importing heavy modules.
    check_dependencies()

    # Import here so CLI parsing works quickly even if heavy deps are missing
    import src.camera_follower_bot.camera_processor as camera_processor
    import src.camera_follower_bot.serial_manager as SM

    # Override model path and camera id if provided
    if args.model_path is not None:
        print("Setting MODEL_PATH to", args.model_path)
        camera_processor.MODEL_PATH = args.model_path
    if args.camera_id is not None:
        print("Setting CAMERA_ID to", args.camera_id)
        camera_processor.CAMERA_ID = args.camera_id
    # Set static attributes for process_frame
    if args.rotate180 is not None:
        print("Setting ROTATE_CAMERA to", args.rotate180)
        camera_processor.ROTATE_CAMERA = args.rotate180
    if args.flip is not None:
        print("Setting FLIP_CAMERA to", args.flip)
        camera_processor.FLIP_CAMERA = args.flip

    # Patch SerialManager used within CameraProcessor
    if args.no_serial:
        print("Running without serial hardware (no-serial mode)")
        camera_processor.SerialManager = DummySerialManager
    else:
        # Create a factory that returns a SerialManager configured with the CLI args
        def _factory():
            return SM.SerialManager(port=args.serial_port, baud=args.baud)

        camera_processor.SerialManager = _factory


    # Validate model path before creating the detector
    validate_model_path(camera_processor.MODEL_PATH)


    # Run the existing main loop
    camera_processor.main()


if __name__ == '__main__':
    main()
