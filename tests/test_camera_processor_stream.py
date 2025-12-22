import cv2
import numpy as np
import pytest

from camera_follower_bot import camera_processor as cp


def test_cv2_open_and_close():
    """Attempt to open the default camera and close it. Skip if no camera available."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        pytest.skip("No camera available on this system")
    # If opened, release and ensure it's closed
    cap.release()
    assert not cap.isOpened()


def test_process_frame_with_fake_detector():
    """Test process_frame using a synthetic image and a fake detector.

    We create a blank image and a fake detection whose bounding box
    is centered in the frame; process_frame should return zero errors.
    """
    h, w = 480, 640
    img = np.zeros((h, w, 3), dtype=np.uint8)

    center_x = w // 2
    center_y = h // 2

    # fake detection objects matching expected structure
    class FakeBBox:
        def __init__(self, origin_x, origin_y, width, height):
            self.origin_x = origin_x
            self.origin_y = origin_y
            self.width = width
            self.height = height

    class FakeCategory:
        def __init__(self, score=0.9):
            self.score = score

    class FakeDetection:
        def __init__(self, bbox, score=0.9):
            self.bounding_box = bbox
            self.categories = [FakeCategory(score)]

    class FakeResults:
        def __init__(self, detections):
            self.detections = detections

    # bounding box centered in the frame
    bw, bh = 40, 60
    bbox = FakeBBox(center_x - bw // 2, center_y - bh // 2, bw, bh)
    detection = FakeDetection(bbox, score=0.98)
    results = FakeResults([detection])

    class FakeDetector:
        def detect(self, img_arg):
            # ignore input and return our fake results
            return results

    det = FakeDetector()

    annotated, error_x, error_y = cp.process_frame(img, det, center_x, center_y)

    assert error_x == 0
    assert error_y == 0
