import os
import cv2
import json
import torch
import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load YOLOv5 model
yolov5_model = torch.hub.load('ultralytics/yolov5', 'yolov5x', pretrained=True).to(device)

def detect_objects(image):
    # Convert OpenCV image (BGR) to RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = yolov5_model(rgb_image)
    detections = results.pandas().xyxy[0]  # Get detections as a Pandas DataFrame
    return detections

# Video processing and object detection
def process_video(video_path, output_path="output_detected.mp4", frame_skip=30):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Unable to open video file:", video_path)
        return None

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    out_writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps,
                                (frame_width, frame_height))

    frame_idx = 0
    saved_features = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_skip == 0:
            detections = detect_objects(frame)

            # Save detected objects and their confidence scores
            frame_features = []
            for _, row in detections.iterrows():
                frame_features.append({
                    "label": row['name'],
                    "confidence": row['confidence'],
                    "bbox": [row['xmin'], row['ymin'], row['xmax'], row['ymax']]
                })

                # Draw bounding boxes and labels on the frame
                cv2.rectangle(frame, (int(row['xmin']), int(row['ymin'])),
                                (int(row['xmax']), int(row['ymax'])), (0, 255, 0), 2)
                label = f"{row['name']} ({row['confidence']:.2f})"
                cv2.putText(frame, label, (int(row['xmin']), int(row['ymin']) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            saved_features.append({
                "frame": frame_idx,
                "detections": frame_features
            })

        out_writer.write(frame)
        frame_idx += 1

    cap.release()
    out_writer.release()
    return saved_features

def generate_hash(features):
    json_str = json.dumps(features, sort_keys=True)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

if __name__ == "__main__":
    video_path = "input.mp4"
    features = process_video(video_path)
    if features:
        print("Video frame object detection completed.")
        for f in features:
            print(f)
        video_hash = generate_hash(features)
        print("Final video fingerprint:", video_hash)
    else:
        print("Processing failed.")