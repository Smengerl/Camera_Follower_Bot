import cv2
import numpy as np
import pytest

from camera_follower_bot import camera_processor as cp


def test_cv2_open_and_close():
    """Attempt to open the default camera and close it. Skip if no camera available."""
    cap = cv2.VideoCapture(cp.CAMERA_ID)
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


class _FakeBBox:
    def __init__(self, origin_x, origin_y, width, height):
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.width = width
        self.height = height


class _FakeCategory:
    def __init__(self, score):
        self.score = score


class _FakeDetection:
    def __init__(self, bbox, score):
        self.bounding_box = bbox
        self.categories = [_FakeCategory(score)]


class _FakeResults:
    def __init__(self, detections):
        self.detections = detections


def _fake_detector(detections):
    class FakeDetector:
        def detect(self, _img):
            return _FakeResults(detections)

    return FakeDetector()


def test_process_frame_multi_face_picks_closest_confident():
    """Among confident faces, follow the one closest to the frame center;
    a dead-center face below MIN_DETECTION_SCORE is ignored."""
    h, w = 480, 640
    img = np.zeros((h, w, 3), dtype=np.uint8)
    cx, cy = w // 2, h // 2
    bw = bh = 40

    far = _FakeDetection(_FakeBBox(10, 10, bw, bh), 0.95)                      # confident, top-left
    near = _FakeDetection(_FakeBBox(cx - bw // 2 + 20, cy - bh // 2 + 10, bw, bh), 0.90)  # confident, near center
    center_weak = _FakeDetection(_FakeBBox(cx - bw // 2, cy - bh // 2, bw, bh), 0.20)     # centered but low score

    _, error_x, error_y = cp.process_frame(img, _fake_detector([far, near, center_weak]), cx, cy)

    # target must be `near`, whose center is (cx + 20, cy + 10)
    assert (error_x, error_y) == (-20, -10)


def test_process_frame_all_faces_below_threshold_returns_none():
    h, w = 480, 640
    img = np.zeros((h, w, 3), dtype=np.uint8)
    cx, cy = w // 2, h // 2

    weak = _FakeDetection(_FakeBBox(cx - 20, cy - 20, 40, 40), 0.30)
    _, error_x, error_y = cp.process_frame(img, _fake_detector([weak]), cx, cy)

    assert error_x is None
    assert error_y is None
