import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import Image, ImageFormat
import serial
import time

# Open serial connection 
ser = serial.Serial('/dev/cu.usbmodem101', 115200, timeout=1)  
time.sleep(2)  # Wait for RP2040 to reset after serial open
last_send=0

# Mediapipe setup
BaseOptions = mp.tasks.BaseOptions
FaceDetector = mp.tasks.vision.FaceDetector
FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Create a face detector instance with the video mode:
options = FaceDetectorOptions(
    base_options=BaseOptions(model_asset_path='/Users/simon/Coding/Camera_Follower_Bot/blaze_face_short_range.tflite'),
    running_mode=VisionRunningMode.IMAGE)
detector = FaceDetector.create_from_options(options) 
#mp_face_detection = mp.solutions.face_detection
#mp_drawing = mp.solutions.drawing_utils

# Open camera _________ CHANGE THIS VALUE TO SWAP CAMERA ______________
cap = cv2.VideoCapture(0)

# Get camera resolution
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
center_x = frame_width // 2
center_y = frame_height // 2




def send_position(error_x, error_y):
    # Format: "X:<val>,Y:<val>\n"
    try: 
        data = f"{int(error_x)},{int(error_y)}\n"
    except:
        return 
    ser.write(data.encode('utf-8'))

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Rotate 180 degrees
    frame = cv2.rotate(frame, cv2.ROTATE_180)
    frame = cv2.flip(frame, 1)

    # Convert BGR to RGB for mediapipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # OpenCV-Frame → MediaPipe Image
    mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)

    # Run face detection
    results = detector.detect(mp_image)

    error_x = None
    error_y = None

    # Draw detections and calculate offsets
    if results.detections:
        for detection in results.detections:
            # Draw bounding box
            bbox = detection.bounding_box

            cv2.rectangle(frame, (bbox.origin_x, bbox.origin_y), (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height), (0, 255, 0), 2)
            # optional: label mit Confidence falls vorhanden
            
            score = detection.categories[0].score
            label = f"{score:.2f}"
            cv2.putText(frame, label, (bbox.origin_x, max(10, bbox.origin_y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Get bounding box center
            face_x = int((bbox.origin_x + bbox.width / 2))
            face_y = int((bbox.origin_y + bbox.height / 2))

            # Calculate error from frame center
            error_x = center_x - face_x
            error_y = center_y - face_y

            # Draw a marker at the detected face center
            # cv2.circle(frame, (face_x, face_y), 5, (0, 0, 255), -1)

    # Draw center crosshair
    # cv2.drawMarker(frame, (center_x, center_y), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)

    now = time.time()
    if now - last_send >= 0.01:
        send_position(error_x, error_y)  # send example data
        last_send = now

    # Show error text
    if error_x is not None and error_y is not None:
        text = f"Error X: {error_x} px, Error Y: {error_y} px"
        cv2.putText(frame, text, (10, frame_height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Show window
    cv2.imshow('Mediapipe Face Tracking', frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()



# Cameraside:
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