import os
import sys
import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import Image, ImageFormat
from src.camera_follower_bot.serial_manager import SerialManager


# ---------------------------
# Configuration / constants
# ---------------------------
CAMERA_ID = 0 # Default camera index for OpenCV
ROTATE_CAMERA = True # Rotate camera image by 180 degrees
FLIP_CAMERA = True # Flip camera image horizontally

HERE = os.path.dirname(__file__)
MODEL_PATH = os.path.join(HERE, "../../models/blaze_face_short_range.tflite")

MAX_STDOUT_DISPLAY_LINE_LENGTH = 80  # Maximum characters to display per stdout line
MAX_STDOUT_DISPLAY_LINE_NUMBERS = 10  # Maximum lines to display of stdout buffer





def make_face_detector(model_path: str):
    """Create and return a MediaPipe FaceDetector configured for IMAGE mode.

    Keeping creation in one function makes it easier to swap models or options.
    """
    BaseOptions = mp.tasks.BaseOptions
    FaceDetector = mp.tasks.vision.FaceDetector
    FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.IMAGE,
    )
    detector = FaceDetector.create_from_options(options)
    return detector



def open_camera(camera_id: int):
    """Open camera and return capture plus frame center coordinates.

    Returns: (cap, frame_width, frame_height, center_x, center_y)
    """
    cap = cv2.VideoCapture(camera_id)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    center_x = frame_width // 2
    center_y = frame_height // 2
    return cap, frame_width, frame_height, center_x, center_y




def process_frame(frame, detector, center_x, center_y, rotate_camera: bool = ROTATE_CAMERA, flip_camera: bool = FLIP_CAMERA):
    """Process a BGR OpenCV frame, run face detection and return (annotated_frame, error_x, error_y).

    Steps:
    - rotate / flip to match camera orientation (parametrizable)
    - convert BGR->RGB and build MediaPipe Image
    - detect faces and annotate frame with bbox + confidence
    - compute pixel error relative to frame center
    """
    # Normalize orientation to match how the camera is mounted
    if rotate_camera:
        frame = cv2.rotate(frame, cv2.ROTATE_180)
    if flip_camera:
        frame = cv2.flip(frame, 1)

    # Convert BGR to RGB for mediapipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # OpenCV-Frame → MediaPipe Image
    mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)

    # Run face detection (returns a DetectionResults object)
    results = detector.detect(mp_image)

    error_x = None
    error_y = None

    # Draw detections and compute offsets if any faces found
    if results.detections:
        for detection in results.detections:
            bbox = detection.bounding_box

            # Draw bounding box
            cv2.rectangle(
                frame,
                (bbox.origin_x, bbox.origin_y),
                (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height),
                (0, 255, 0),
                2,
            )

            # Draw confidence label (first category)
            score = detection.categories[0].score
            label = f"{score:.2f}"
            cv2.putText(
                frame,
                label,
                (bbox.origin_x, max(10, bbox.origin_y - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )

            # Compute bounding box center
            face_x = int((bbox.origin_x + bbox.width / 2))
            face_y = int((bbox.origin_y + bbox.height / 2))

            # Pixel error: positive means target is left/up relative to center
            error_x = center_x - face_x
            error_y = center_y - face_y

            # (optional) draw a red dot at face center
            # cv2.circle(frame, (face_x, face_y), 5, (0, 0, 255), -1)

    return frame, error_x, error_y


def main():
    # Serial manager handles reconnects with backoff
    serial_mgr = SerialManager()
    # Try an immediate connect
    serial_mgr.connect()
    last_send = 0

    # Create face detector
    detector = make_face_detector(MODEL_PATH)

    # Open camera and compute center
    cap, frame_width, frame_height, center_x, center_y = open_camera(CAMERA_ID)

    frames_sent_since_reconnect = 0

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            annotated, error_x, error_y = process_frame(frame, detector, center_x, center_y, ROTATE_CAMERA, FLIP_CAMERA)

            # Attempt non-blocking reconnects if needed
            serial_mgr.reconnect_if_needed()
            
            if not serial_mgr.is_connected():
                # Show human-friendly error text on frame
                frames_sent_since_reconnect = 0
                cv2.putText(
                    img=annotated,
                    text=f"Not connected (Port: {serial_mgr.port}, Baud: {serial_mgr.baud}) - Press Esc to exit",
                    org=(10, 25),
                    color=(0, 0, 255),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=0.7)
            else:
                cv2.putText(
                    img=annotated,
                    text=f"Connected - Frames sent: {frames_sent_since_reconnect} - Press Esc to exit",
                    org=(10, 25),
                    color=(255, 255, 255),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=0.7)

            if error_x is not None and error_y is not None:

                # Show human-friendly error text on frame
                text = f"Error X: {error_x} px, Error Y: {error_y} px"

                # Throttle serial sending to ~100Hz
                now = time.time()
                if now - last_send >= 0.01:
                    # send via manager (will silently drop if disconnected)
                    serial_mgr.send_position(error_x, error_y)
                    last_send = now
                    frames_sent_since_reconnect += 1
            else:
               text = f"No face detected"
                 
            # Display detection results
            cv2.putText(
                img=annotated,
                text=text,
                org=(10, frame_height - 20),
                color=(255, 255, 255),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=0.7,
            )

            # Read any available stdout from the device
            serial_mgr.read_stdout()

            # Display stdout from the device (last MAX_STDOUT_DISPLAY_LINES lines)
            stdout_lines = serial_mgr.get_stdout_buffer(max_lines=MAX_STDOUT_DISPLAY_LINE_NUMBERS)
            if stdout_lines:
                y_offset = 80  # Start below connection status
                for idx, line in enumerate(stdout_lines):
                    # Truncate long lines to fit on screen
                    display_line = line[:MAX_STDOUT_DISPLAY_LINE_LENGTH] if len(line) > MAX_STDOUT_DISPLAY_LINE_LENGTH else line
                    cv2.putText(
                        img=annotated,
                        text=display_line,
                        org=(10, y_offset + idx * 20),
                        color=(255, 255, 255) if serial_mgr.is_connected() else (100, 100, 100),
                        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                        fontScale=0.7,
                    )

            # Display the annotated frame
            cv2.imshow('Mediapipe Face Tracking', annotated)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
                break
    finally:
        # Gracefully close serial connection (will relax servos)
        serial_mgr.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()


# Cameraside notes:
# - X error: negative if Right, Positive if Left
# - Y error: Positive if Up, Negative if Down
# Servos:
#  - X direction: Right is 90>140, Left is 40>90
#  - Y direction: Up is 90>140, Down is 40>140

# Therefore:
# X: if negative: LR++, if positive, LR--
# Y: if negative: UD--, if positive, UD++

# Neck:
# X: 90+ is Right, 90- is Left
# Y: 90+ is UP, 90- is DOWN

# Therefore:
# X: If LR target is 40>90, Eyes looking left, Neck must turn left: BaseX--
# Y: If UD target is 90>140, Eyes looking up, Neck must look up: BaseY++

# BaseX=40 centres LR=50
# BaseX=130 centres LR=140

# BaseY=140 centres UD=140
# BaseY=40 centres UD=40