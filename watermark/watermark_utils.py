import numpy as np

def message_to_bits(msg: str) -> list:
    """
    将字符串转换为比特序列 (list of 0/1).
    每个字符8位 (ASCII).
    """
    bits = []
    for char in msg:
        val = ord(char)
        for i in range(8):
            bits.append((val >> i) & 1)
    return bits

def bits_to_message(bits: list) -> str:
    """
    将比特序列还原为字符串(ASCII).
    每8位构成1个字符.
    """
    chars = []
    for b in range(0, len(bits), 8):
        byte_val = 0
        for i in range(8):
            byte_val |= (bits[b + i] << i)
        chars.append(chr(byte_val))
    return "".join(chars)

def embed_bits_in_bgr(frame_bgr: np.ndarray, bits: list, channel_index=0) -> tuple:
    """
    在一帧 BGR 彩色图像中, 针对某个通道 channel_index (0=B,1=G,2=R),
    使用LSB方法嵌入 bits (0/1序列).
    返回 (frame_embedded, used_bits_count).

    - frame_bgr: shape=(h,w,3), BGR格式.
    - bits: 要嵌入的比特序列.
    - channel_index: 0=蓝通道B,1=绿通道G,2=红通道R.

    注意: 超过可用像素数则截断.
    """
    h, w, c = frame_bgr.shape
    if c != 3:
        raise ValueError("输入frame_bgr必须是BGR三通道图像")

    max_bits = h * w
    bits_to_write = bits[:max_bits]
    used_bits_count = len(bits_to_write)

    # 拿到指定通道数据
    channel_data = frame_bgr[:, :, channel_index].flatten().astype(np.uint16)

    # 写LSB
    for i in range(used_bits_count):
        channel_data[i] = (channel_data[i] & 0xFE) | bits_to_write[i]

    channel_data = channel_data.astype(np.uint8).reshape((h, w))

    # 生成嵌入后图像
    frame_embedded = frame_bgr.copy()
    frame_embedded[:, :, channel_index] = channel_data

    return frame_embedded, used_bits_count

def extract_bits_from_bgr(frame_bgr: np.ndarray, channel_index=0) -> list:
    """
    从BGR帧的某个通道LSB提取比特序列, 返回list of 0/1.
    """
    h, w, c = frame_bgr.shape
    if c != 3:
        raise ValueError("输入frame_bgr必须是3通道BGR图像")

    channel_data = frame_bgr[:, :, channel_index].flatten()
    bits = [(val & 1) for val in channel_data]
    return bits
