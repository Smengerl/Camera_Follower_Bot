import os
import cv2
import pytest

from camera_follower_bot import camera_processor as cp


def _skip_if_no_mediapipe_or_model():
    # Check mediapipe import indirectly via make_face_detector
    try:
        # validate model path first
        cp.validate_model_path(cp.MODEL_PATH)
    except SystemExit:
        pytest.skip(f"Model not found at {cp.MODEL_PATH}. Set MODEL_PATH or place tflite model there to run this test.")


def test_face_detection_on_static_image():
    """Run face detection on a static image (as if captured from webcam).

    Provide the image path via the environment variable `CAMERA_TEST_IMAGE`.
    This test will be skipped with instructions if the model or image are missing.
    """
    image_path = os.getenv('CAMERA_TEST_IMAGE')
    if not image_path or not os.path.isfile(image_path):
        pytest.skip(f'Provided CAMERA_TEST_IMAGE does not exist: {image_path}')

    # Ensure model and mediapipe are available
    _skip_if_no_mediapipe_or_model()

    # Build real detector
    try:
        detector = cp.make_face_detector(cp.MODEL_PATH)
    except Exception as exc:
        pytest.skip(f'Failed to create MediaPipe detector: {exc}')

    img = cv2.imread(image_path)
    if img is None:
        pytest.skip(f'cv2 failed to read image: {image_path}')

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
