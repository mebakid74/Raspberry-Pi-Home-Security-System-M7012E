import cv2
import time
import os
import pandas as pd
from datetime import datetime
import numpy as np
import imutils
from picamera.array import PiRGBArray
from picamera import PiCamera

# Initialize the Pi Camera
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30
raw_capture = PiRGBArray(camera, size=(640, 480))

# Load the Haar cascade classifier for face detection
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# Initialize variables
first_frame = None
status_list = [None, None]
times = []
df = pd.DataFrame(columns=["Start", "End"])

# Define the directory path for the captured folder
captured = "Pi Camera/captured"
if not os.path.exists(captured):
    os.makedirs(captured)
    os.makedirs(os.path.join(captured, "colorframe"))
    os.makedirs(os.path.join(captured, "deltaframe"))
    os.makedirs(os.path.join(captured, "grayframe"))
    os.makedirs(os.path.join(captured, "thresholdframe"))
    os.makedirs(os.path.join(captured, "video"))

# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'H264')
out = None

start_time = time.time()
flag = 1

mode = int(input("Enter 1 for Motion Detection, 2 for Intrusion Detection: "))

# Main loop
for frame in camera.capture_continuous(raw_capture, format="bgr", use_video_port=True):
    frame = frame.array
    frame = imutils.resize(frame, width=500)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if first_frame is None:
        print("Starting background model...")
        first_frame = gray.copy().astype("float")
        raw_capture.truncate(0)
        continue

    delta_frame = cv2.absdiff(first_frame.astype(np.uint8), gray)
    thresh_frame = cv2.threshold(delta_frame, 30, 255, cv2.THRESH_BINARY)[1]
    thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

    status = 0

    if mode == 1:
        (cnts, _) = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in cnts:
            if cv2.contourArea(contour) < 10000:
                continue
            status = 1
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 3)
            cv2.putText(frame, "Unauthorized person", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            
            # Start recording if not already recording
            if out is None:  
                print("Started Recording Intrusion Video")
                out = cv2.VideoWriter(os.path.join(captured, "video", f'video_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.avi'), fourcc, 20.0, (640, 480))
    else:
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5)
        for (x, y, w, h) in faces:
            frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 3)
            status = 1
            
            cv2.putText(frame, "Motion Detected", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            
            # Start recording if not already recording
            if out is None:  
                print("Started Recording Motion Video")
                out = cv2.VideoWriter(os.path.join(captured, "video", f'video_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.avi'), fourcc, 20.0, (640, 480))

    status_list.append(status)
    status_list = status_list[-2:]

    if status_list[-1] == 1 and status_list[-2] == 0:
        times.append(datetime.now())
        start_time = time.time()

        # Debug output
        print("Capturing frame...")

        print("Intruder has Entered")
        color_frame_path = os.path.join(captured, "colorframe", f"intruder_color_frame_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        cv2.imwrite(color_frame_path, frame)
        print("Color Frame captured!")

        gray_frame_path = os.path.join(captured, "grayframe", f"intruder_gray_frame_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        cv2.imwrite(gray_frame_path, gray)
        print("Gray Frame captured!")

        delta_frame_path = os.path.join(captured, "deltaframe", f"intruder_delta_frame_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        cv2.imwrite(delta_frame_path, delta_frame)
        print("Delta Frame captured!")

        threshold_frame_path = os.path.join(captured, "thresholdframe", f"intruder_thresh_frame_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        cv2.imwrite(threshold_frame_path, thresh_frame)
        print("Threshold Frame captured!")

        flag = 0

    if status_list[-1] == 0 and status_list[-2] == 1:
        times.append(datetime.now())
        flag = 1
        print("Intruder has Exited")

    elapsed_time = time.time() - start_time

    if elapsed_time > 3 and flag == 0:
        print("Intruder has been Detected")
        flag = 1

    cv2.imshow("Gray Frame", gray)
    cv2.imshow("Delta Frame", delta_frame)
    cv2.imshow("Threshold Frame", thresh_frame)
    cv2.imshow("Color Frame", frame)

    # Wait for keyPress for 1 millisecond
    key = cv2.waitKey(1) & 0xFF

    # If "q" is pressed on the keyboard, 
    # exit this loop
    if key == ord('q'):
        break

    # Clear the stream in preparation for the next frame
    raw_capture.truncate(0)

# Release resources
cv2.destroyAllWindows()
