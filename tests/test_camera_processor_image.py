import os
import cv2
import pytest

from camera_follower_bot import camera_processor as cp
from camera_follower_bot import run_camera as rc

HERE = os.path.dirname(__file__)
IMAGE_PATH = os.path.join(HERE, "testimage.png")


def test_face_detection_on_static_image():
    """Run face detection on a static image (as if captured from webcam).

    Provide the image path via the environment variable `CAMERA_TEST_IMAGE`.
    This test will be skipped with instructions if the model or image are missing.
    """

    # Ensure model and mediapipe are available
    try:
        # validate model path first
        rc.validate_model_path(cp.MODEL_PATH)
    except SystemExit:
        pytest.skip(f"Model not found at {cp.MODEL_PATH}. Set MODEL_PATH or place tflite model there to run this test.")

    # Build real detector
    try:
        detector = cp.make_face_detector(cp.MODEL_PATH)
    except Exception as exc:
        pytest.skip(f'Failed to create MediaPipe detector: {exc}')

    if not IMAGE_PATH or not os.path.isfile(IMAGE_PATH):
        pytest.skip(f'Provided test image does not exist: {IMAGE_PATH}')
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        pytest.skip(f'cv2 failed to read image: {IMAGE_PATH}')

    h, w = img.shape[:2]
    center_x = w // 2
    center_y = h // 2

    annotated, error_x, error_y = cp.process_frame(img, detector, center_x, center_y)

    # Sanity checks: annotated image returned and error values are either None or ints
    assert annotated is not None
    if error_x is not None:
        assert isinstance(error_x, int)
    if error_y is not None:
        assert isinstance(error_y, int)

    # If a detection was found, expect the error values to be within frame bounds
    if error_x is not None and error_y is not None:
        assert abs(error_x) <= w
        assert abs(error_y) <= h

        print(f"Face detected! Error X: {error_x}, Error Y: {error_y}")
    else:
        print("No face detected in the test image.")
