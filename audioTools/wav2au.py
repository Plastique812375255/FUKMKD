#!/usr/bin/env python3
# wav2au.py - 将标准WAV文件转换为特殊.au格式

import struct
import sys
import wave
import numpy as np

def encode_adpcm_sample(sample, predictor, step_index):
    """将PCM样本编码为ADPCM nibble"""
    step_size_table = [
        7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34,
        37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143,
        157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494,
        544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552,
        1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026,
        4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442,
        11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623,
        27086, 29794, 32767
    ]
    
    # 计算差值
    diff = sample - predictor
    
    # 确定nibble值
    nibble = 0
    if diff < 0:
        nibble = 8
        diff = -diff
    
    # 量化差值
    step_size = step_size_table[step_index]
    delta = step_size >> 3
    
    if diff >= step_size:
        nibble |= 4
        diff -= step_size
        delta += step_size
    
    step_size >>= 1
    if diff >= step_size:
        nibble |= 2
        diff -= step_size
        delta += step_size
    
    step_size >>= 1
    if diff >= step_size:
        nibble |= 1
        delta += step_size
    
    # 计算新的预测值
    if nibble & 8:
        predictor -= delta
    else:
        predictor += delta
    
    # 限制在16位有符号范围内
    predictor = max(min(predictor, 32767), -32768)
    
    # 调整步长索引
    step_index_table = [-1, -1, -1, -1, 2, 4, 6, 8]
    step_index += step_index_table[nibble & 7]
    step_index = max(min(step_index, 88), 0)
    
    return nibble, predictor, step_index

def read_wav_file(filename):
    """从WAV文件读取PCM样本"""
    with wave.open(filename, 'rb') as wav_file:
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        
        if n_channels != 1 or sample_width != 2:
            raise ValueError("仅支持16位单声道WAV文件")
        
        frames = wav_file.readframes(wav_file.getnframes())
        
    # 将字节转换为16位整数样本
    samples = np.frombuffer(frames, dtype=np.int16)
    return samples

def encode_wav_to_au(pcm_samples, original_header=None):
    """将PCM样本编码为AU格式"""
    # 使用原始文件的头部或创建一个默认头部
    if original_header is not None:
        header = original_header
    else:
        # 创建一个简单的AU文件头 (16字节)
        header = bytearray([
            0x10, 0x90, 0x00, 0x00,  # 可能是格式标识符
            0x00, 0x10, 0x09, 0x19,  # 可能包含采样率信息
            0x00, 0x00, 0x00, 0x09,  # 可能包含其他元数据
            0x11, 0x09, 0x91, 0x90   # 可能包含初始编码状态
        ])
    
    # 初始化编码参数
    predictor = 0
    step_index = 0
    encoded_bytes = bytearray()
    
    # 每次处理两个样本，生成一个字节
    for i in range(0, len(pcm_samples), 2):
        # 处理第一个样本 (高4位)
        nibble_high, predictor, step_index = encode_adpcm_sample(
            pcm_samples[i], predictor, step_index)
        
        # 处理第二个样本 (低4位)，确保不超出样本范围
        if i + 1 < len(pcm_samples):
            nibble_low, predictor, step_index = encode_adpcm_sample(
                pcm_samples[i + 1], predictor, step_index)
        else:
            nibble_low = 0  # 如果是奇数个样本，最后一个低4位填0
        
        # 合并两个nibble为一个字节
        encoded_byte = (nibble_high << 4) | nibble_low
        encoded_bytes.append(encoded_byte)
    
    # 组合头部和编码后的数据
    return header + encoded_bytes

def get_au_header(filename):
    """获取.au文件的头部"""
    with open(filename, 'rb') as f:
        header = f.read(16)  # 假设头部是16字节
    return header

def convert_wav_to_au(input_file, output_file, original_au_file=None):
    """将WAV文件转换为AU文件"""
    pcm_samples = read_wav_file(input_file)
    
    original_header = None
    if original_au_file:
        original_header = get_au_header(original_au_file)
    
    encoded_data = encode_wav_to_au(pcm_samples, original_header)
    
    with open(output_file, 'wb') as f:
        f.write(encoded_data)
    
    print(f"转换完成: {input_file} -> {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"用法: {sys.argv[0]} 输入文件.wav 输出文件.au [原始AU文件(用于提取头部)]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    original_au_file = None
    
    if len(sys.argv) >= 4:
        original_au_file = sys.argv[3]
    
    convert_wav_to_au(input_file, output_file, original_au_file) 