import cv2
import os
from watermark_utils import message_to_bits, embed_bits_in_bgr

def embed_limited_frames():
    input_video = "input_color.mp4"          # 你的彩色原视频
    output_video = "watermarked_limited.mp4"
    WATERMARK_MSG = "Hello"                  # 要嵌入的水印文本
    FRAMES_TO_WATERMARK = 10                 # 仅对前10帧加水印
    CHANNEL_INDEX = 0                        # 0=B,1=G,2=R (默认B通道)
    
    if not os.path.exists(input_video):
        print(f"[错误] 找不到输入视频: {input_video}")
        return

    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        print("[错误] 无法打开输入视频.")
        return

    # 基本信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # mp4编码(有损),若想无损可用FFV1/HuffYUV等
    
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height), isColor=True)

    wm_bits = message_to_bits(WATERMARK_MSG)
    frame_idx = 0
    total_used_bits = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_idx += 1

        if len(frame.shape) < 3 or frame.shape[2] != 3:
            # 保证是三通道
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        if frame_idx <= FRAMES_TO_WATERMARK:
            # 只在前10帧中嵌入水印
            frame_embedded, used_bits_count = embed_bits_in_bgr(frame, wm_bits, channel_index=CHANNEL_INDEX)
            out.write(frame_embedded)
            total_used_bits += used_bits_count
        else:
            # 其余帧原样写入
            out.write(frame)

    cap.release()
    out.release()

    print(f"[完成] 已生成带部分帧水印的视频: {output_video}")
    print(f"在前 {FRAMES_TO_WATERMARK} 帧共写入比特数: {total_used_bits}")

if __name__ == "__main__":
    embed_limited_frames()
