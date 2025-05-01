import cv2
import os
from watermark_utils import extract_bits_from_bgr, bits_to_message

def verify_limited_frames():
    watermarked_video = "watermarked_limited.mp4"
    CHANNEL_INDEX = 0        # 与嵌入时一致 (0=B)
    FRAMES_TO_CHECK = 10     # 只对前10帧提取水印
    WATERMARK_LENGTH_BIT = 40  # "Hello" 5字节=40位(演示)
    
    if not os.path.exists(watermarked_video):
        print(f"[错误] 找不到水印后视频: {watermarked_video}")
        return

    cap = cv2.VideoCapture(watermarked_video)
    if not cap.isOpened():
        print("[错误] 无法打开视频.")
        return

    frame_idx = 0
    extracted_bits = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx > FRAMES_TO_CHECK:
            # 超过10帧就不再读取, 因为只在前10帧有水印
            break

        if len(frame.shape) < 3 or frame.shape[2] != 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        # 提取通道LSB
        bits_segment = extract_bits_from_bgr(frame, CHANNEL_INDEX)
        extracted_bits.extend(bits_segment)

    cap.release()

    # 假设知道水印实际只用到40位, 可只截取前40位解析
    # 若不知道长度, 也可盲取200位看看是否能出现"Hello"
    needed_bits = WATERMARK_LENGTH_BIT
    actual_bits = extracted_bits[:needed_bits]

    recovered = bits_to_message(actual_bits)
    print(f"[验证] 从前{FRAMES_TO_CHECK}帧提取的前{needed_bits}bit, 还原文本 = {repr(recovered)}")

if __name__ == "__main__":
    verify_limited_frames()
