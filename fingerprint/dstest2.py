import os
import cv2
import json
import torch
import hashlib
import numpy as np
import clip
from PIL import Image

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load YOLOv5 model
yolov5_model = torch.hub.load('ultralytics/yolov5', 'yolov5x', pretrained=True).to(device)

# Load CLIP model for AI特征提取
clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)

def detect_objects(image):
    # Convert OpenCV image (BGR) to RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = yolov5_model(rgb_image)
    detections = results.pandas().xyxy[0]  # Get detections as a Pandas DataFrame
    return detections

def extract_clip_embedding(frame):
    # 将BGR转RGB并转换为PIL Image
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    inp = clip_preprocess(pil).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = clip_model.encode_image(inp)
    emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy().tolist()[0]

# Add watermark to the frame
# Add max_items 参数，默认只在水印中展示最高的 3 条信息
def add_watermark(frame, features,
                  max_items=3,
                  position=(10, 30),
                  font_scale=0.5,
                  font_color=(0, 255, 255),
                  thickness=1):
    y_offset = position[1]
    # 只保留置信度最高的 max_items 条
    for feature in features[:max_items]:
        label = feature['label']
        confidence = feature['confidence']
        text = f"{label} ({confidence:.2f})"
        cv2.putText(frame, text, (position[0], y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, font_color, thickness)
        y_offset += 20
    return frame

# Video processing and object detection
# Video processing 增加 max_watermarks 控制参数
def process_video(video_path,
                  output_path="output_detected.mp4",
                  frame_skip=30,
                  max_watermarks=3):
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
            clip_emb = extract_clip_embedding(frame)

            # 构建所有检测结果列表
            frame_features = [{
                "label": row['name'],
                "confidence": row['confidence'],
                "bbox": [row['xmin'], row['ymin'], row['xmax'], row['ymax']]
            } for _, row in detections.iterrows()]

            # 根据 confidence 排序，仅保留 top-K
            frame_features = sorted(frame_features,
                                    key=lambda x: x['confidence'],
                                    reverse=True)[:max_watermarks]

            # 仅添加水印，不绘制检测框
            frame = add_watermark(frame, frame_features, max_items=max_watermarks)

            saved_features.append({
                "frame": frame_idx,
                "detections": frame_features,
                "clip_embedding": clip_emb
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
        # 新增：保存每30帧的分类结果到 CSV 文件
        import csv
        csv_file = "yolo_classes.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["frame", "class1", "class2", "class3"])
            for item in features:
                labels = [det["label"] for det in item["detections"]]
                # 如果少于3个分类，用空字符串补齐
                labels += [""] * (3 - len(labels))
                writer.writerow([item["frame"], labels[0], labels[1], labels[2]])
        print(f"Classification results saved to {csv_file}")

        print("Video frame object detection completed.")
        for f in features:
            print(f)
        video_hash = generate_hash(features)
        print("Final video fingerprint:", video_hash)
        # 将指纹嵌入视频元数据，输出供区块链上传
        meta_out = "output_detected_meta.mp4"
        os.system(f"ffmpeg -i output_detected.mp4 -metadata comment=\"{video_hash}\" -codec copy {meta_out}")
        print("Video with embedded metadata:", meta_out)
    else:
        print("Processing failed.")