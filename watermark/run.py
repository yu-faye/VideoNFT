import cv2
import numpy as np

# 视频参数配置
fps = 24            # 帧率
duration = 2        # 视频时长（秒）
width, height = 1920, 1080
total_frames = fps * duration

# 创建 VideoWriter 对象，指定输出文件名、编码格式、帧率和分辨率
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 使用 'mp4v' 编码
video_writer = cv2.VideoWriter('white.mp4', fourcc, fps, (width, height))

# 准备单帧白色画面
white_frame = np.ones((height, width, 3), dtype=np.uint8) * 255

# 写入多帧，全程都是白色画面
for _ in range(total_frames):
    video_writer.write(white_frame)

video_writer.release()
print("white.mp4 已成功生成！")
