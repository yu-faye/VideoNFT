import os
import cv2
import torch
import json
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MODEL_VERSION = "Salesforce/blip-image-captioning-base"
processor = BlipProcessor.from_pretrained(MODEL_VERSION)
model = BlipForConditionalGeneration.from_pretrained(MODEL_VERSION).to(device)

def add_watermark(frame, text="WATERMARK"):
    cv2.putText(frame, text, (10, 50),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1, color=(0, 0, 255), thickness=2)
    return frame

def describe_frame(frame):
    # 使用 BLIP 为当前帧生成一句描述
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_frame)
    inputs = processor(pil_image, return_tensors="pt").to(device)
    with torch.no_grad():
        caption_ids = model.generate(**inputs, max_new_tokens=20)
    return processor.decode(caption_ids[0], skip_special_tokens=True)

def process_video_for_watermark(video_path, output_path="output_detected.mp4", frame_skip=30):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("无法打开视频文件:", video_path)
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    out_writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'),
                                 fps, (frame_width, frame_height))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 每隔 frame_skip 帧，使用 BLIP 生成描述并作为水印加入
        if frame_idx % frame_skip == 0:
            wm_text = describe_frame(frame)
            frame = add_watermark(frame, text=wm_text)

        out_writer.write(frame)
        frame_idx += 1

    cap.release()
    out_writer.release()

def describe_video_by_interval(video_path, interval=30):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("无法打开视频文件:", video_path)
        return None

    frame_count = 0
    descriptions = {"model_version": MODEL_VERSION, "frames": []}

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % interval == 0:
            caption = describe_frame(frame)
            descriptions["frames"].append({
                "frame_index": frame_count,
                "caption": caption
            })
        frame_count += 1

    cap.release()
    return descriptions

def batch_process_videos(input_folder="dataset", output_folder="fingerprint"):
    os.makedirs(output_folder, exist_ok=True)
    for filename in os.listdir(input_folder):
        if filename.lower().endswith((".mp4", ".mov", ".avi")):
            video_path = os.path.join(input_folder, filename)
            base_name = os.path.splitext(filename)[0]
            target_dir = os.path.join(output_folder, base_name)

            # 如果已生成过，跳过
            if os.path.exists(target_dir):
                print(f"跳过已处理文件: {filename}")
                continue

            os.makedirs(target_dir, exist_ok=True)
            watermarked_video_path = os.path.join(target_dir, "output_detected.mp4")
            process_video_for_watermark(video_path, watermarked_video_path, frame_skip=30)

            desc_data = describe_video_by_interval(video_path, interval=30)
            if desc_data:
                desc_path = os.path.join(target_dir, "video_descriptions.json")
                with open(desc_path, "w", encoding="utf-8") as f:
                    json.dump(desc_data, f, ensure_ascii=False, indent=2)
                print(f"完成处理: {filename}")

if __name__ == "__main__":
    batch_process_videos("dataset", "fingerprint")