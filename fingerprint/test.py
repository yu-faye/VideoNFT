import cv2
import torch
import torchvision
import torchvision.transforms as T
import lpips  # 请先通过 pip install lpips 安装
import numpy as np
import json
import hashlib
import matplotlib.pyplot as plt

# -------------------------------
# 1. 目标检测部分：提取主要目标
# -------------------------------
# 加载预训练的 Faster R-CNN 检测模型（在CPU上运行，如果有GPU可自行设置device）
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True).to(device)
model.eval()

# 定义图像转换，将 numpy 数组转换为 tensor（值在[0,1]）
transform = T.Compose([
    T.ToTensor()
])

def detect_main_object(image, score_threshold=0.5):
    """
    对传入图像进行目标检测，返回主要目标的裁剪区域、类别和边框。
    参数:
      image: BGR格式的 numpy 数组（例如 cv2.imread 读取的图片）
      score_threshold: 置信度过滤阈值，小于此值的检测结果会被忽略
    返回:
      (cropped, label, box)
         cropped: 裁剪后的主要目标区域（RGB格式）
         label: 目标类别（整数，对应 COCO 标签）
         box: 边框 [x1, y1, x2, y2]
      如果未检测到有效目标，返回 None
    """
    # 将 BGR 转为 RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_tensor = transform(image_rgb).to(device)
    with torch.no_grad():
        prediction = model([image_tensor])[0]
    
    scores = prediction['scores'].detach().cpu().numpy()
    if len(scores) == 0:
        return None
    # 筛选置信度大于阈值的检测结果
    valid_idx = np.where(scores > score_threshold)[0]
    if valid_idx.size == 0:
        return None
    # 选取置信度最高的目标
    best_idx = valid_idx[np.argmax(scores[valid_idx])]
    box = prediction['boxes'][best_idx].detach().cpu().numpy()  # [x1, y1, x2, y2]
    label = prediction['labels'][best_idx].item()
    # 裁剪目标区域
    x1, y1, x2, y2 = box.astype(int)
    cropped = image_rgb[y1:y2, x1:x2]
    return cropped, label, box

# -------------------------------
# 2. LPIPS 局部纹理相似性计算
# -------------------------------
def prepare_for_lpips(crop, size=(64, 64)):
    """
    对裁剪区域进行预处理：
      - 调整大小为固定尺寸（默认64x64）
      - 转换为 Tensor，并归一化至 [-1,1]（符合 LPIPS 模型输入要求）
    返回值: Tensor，形状为 [1, 3, H, W]
    """
    crop_resized = cv2.resize(crop, size)
    crop_tensor = T.ToTensor()(crop_resized)  # 范围[0,1]
    crop_tensor = crop_tensor * 2 - 1           # 映射到 [-1,1]
    return crop_tensor.unsqueeze(0)  # 增加 batch 维度

# 初始化全局的 LPIPS 模型（使用 alex 网络）
loss_fn_alex = lpips.LPIPS(net='alex').to(device)

# -------------------------------
# 3. 视频处理与特征提取，生成视频指纹
# -------------------------------
def process_video(video_path, frame_skip=30):
    """
    读取视频文件，按 frame_skip 采帧（例如每隔30帧采一帧），并对相邻帧进行目标检测与局部纹理相似性计算。
    返回：
      features_list: 包含每个有效帧对的特征（字典列表）
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("无法打开视频文件:", video_path)
        return []
    
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    
    print("共读取帧数：", len(frames))
    features_list = []
    
    # 采帧处理：每隔 frame_skip 帧取一帧进行比对，确保视频长度足够
    for i in range(0, len(frames) - frame_skip, frame_skip):
        frame1 = frames[i]
        frame2 = frames[i + frame_skip]
        
        # 对两帧分别进行目标检测
        det1 = detect_main_object(frame1)
        det2 = detect_main_object(frame2)
        
        if det1 is None or det2 is None:
            print("帧 {} 或 帧 {} 未检测到有效目标".format(i, i + frame_skip))
            continue
        
        crop1, label1, box1 = det1
        crop2, label2, box2 = det2
        
        # 若检测到的目标类别不同，则跳过该对帧
        if label1 != label2:
            print("帧 {} 与 帧 {} 检测目标类别不同：{} vs {}".format(i, i + frame_skip, label1, label2))
            continue
        
        # 使用 LPIPS 模型计算两个裁剪区域的距离
        tensor1 = prepare_for_lpips(crop1)
        tensor2 = prepare_for_lpips(crop2)
        tensor1 = tensor1.to(device)
        tensor2 = tensor2.to(device)
        with torch.no_grad():
            distance = loss_fn_alex(tensor1, tensor2)
        similarity = 1 / (1 + distance.item())  # 简单映射，将距离转为 [0,1] 内的相似度
        
        # 对边框进行归一化（相对于图像宽高），便于后续比较
        h, w, _ = frame1.shape
        norm_box = [float(box1[0]) / w, float(box1[1]) / h, float(box1[2]) / w, float(box1[3]) / h]
        
        # 保存该帧对的特征
        feature = {
            "frame_index": i,
            "label": label1,
            "norm_bbox": norm_box,
            "similarity": similarity
        }
        features_list.append(feature)
        print("帧 {} 与 帧 {} -> Label: {}，归一化边框: {}，相似度: {:.4f}".format(i, i+frame_skip, label1, norm_box, similarity))
    
    return features_list

def compute_video_fingerprint(video_path, frame_skip=30):
    """
    读取视频文件，提取多帧的特征信息后，利用哈希（SHA256）生成视频指纹。
    返回：
      hash_fingerprint: 十六进制字符串形式的视频指纹
      features: 特征字典列表（可用于后续调试或验证）
    """
    features = process_video(video_path, frame_skip=frame_skip)
    if not features:
        print("未提取到有效特征，无法生成视频指纹。")
        return None, None
    
    # 将特征列表转换为 JSON 字符串（确保 key 排序一致）
    features_json = json.dumps(features, sort_keys=True)
    # 使用 SHA256 生成哈希值
    hash_fingerprint = hashlib.sha256(features_json.encode('utf-8')).hexdigest()
    return hash_fingerprint, features

# -------------------------------
# 4. 主函数：执行视频处理并输出视频指纹
# -------------------------------
if __name__ == '__main__':
    video_file = 'input.mp4'
    # 这里 frame_skip 根据视频帧率和需求设置（例如每隔30帧采一帧）
    hash_fp, features = compute_video_fingerprint(video_file, frame_skip=30)
    if hash_fp is not None:
        print("最终视频哈希指纹:", hash_fp)
    else:
        print("视频指纹生成失败。")
