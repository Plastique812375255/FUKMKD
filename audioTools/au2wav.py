#!/usr/bin/env python3
# au2wav.py - 将特殊.au格式转换为标准WAV格式

import struct
import sys
import wave
import numpy as np
import os

def decode_adpcm_sample(nibble, predictor, step_index):
    """解码单个ADPCM样本为PCM值"""
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
    
    # 从nibble计算差值
    diff = step_size_table[step_index] >> 3
    if nibble & 1:
        diff += step_size_table[step_index] >> 2
    if nibble & 2:
        diff += step_size_table[step_index] >> 1
    if nibble & 4:
        diff += step_size_table[step_index]
    if nibble & 8:
        diff = -diff
    
    # 计算新的预测值
    predictor += diff
    
    # 限制在16位有符号范围内
    predictor = max(min(predictor, 32767), -32768)
    
    # 调整步长索引
    step_index_table = [-1, -1, -1, -1, 2, 4, 6, 8]
    step_index += step_index_table[nibble & 7]
    step_index = max(min(step_index, 88), 0)
    
    return predictor, step_index

def decode_au_file(filename):
    """解码.au文件为PCM样本"""
    with open(filename, 'rb') as f:
        data = f.read()
    
    # 假设头部是16字节
    header_size = 16
    header = data[:header_size]
    encoded_data = data[header_size:]
    
    # 初始化解码参数
    predictor = 0
    step_index = 0
    pcm_samples = []
    
    # 解码每个字节（每个字节包含两个4位样本）
    for byte in encoded_data:
        # 解码高4位
        nibble_high = (byte >> 4) & 0x0F
        predictor, step_index = decode_adpcm_sample(nibble_high, predictor, step_index)
        pcm_samples.append(predictor)
        
        # 解码低4位
        nibble_low = byte & 0x0F
        predictor, step_index = decode_adpcm_sample(nibble_low, predictor, step_index)
        pcm_samples.append(predictor)
    
    return np.array(pcm_samples, dtype=np.int16)

def save_wav(pcm_data, output_file, sample_rate):
    """将PCM样本保存为WAV文件"""
    with wave.open(output_file, 'wb') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位样本
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data.tobytes())

def convert_au_to_wav(input_file, output_file, sample_rate):
    """将.au文件转换为.wav文件"""
    pcm_data = decode_au_file(input_file)
    save_wav(pcm_data, output_file, sample_rate)
    print(f"转换完成: {input_file} -> {output_file} (采样率: {sample_rate}Hz)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"用法: {sys.argv[0]} 输入文件.au 输出文件.wav [采样率(默认8000)]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    sample_rate = 8000  # 默认采样率
    
    if len(sys.argv) >= 4:
        try:
            sample_rate = int(sys.argv[3])
        except ValueError:
            print("采样率必须是整数，使用默认值8000")
    
    convert_au_to_wav(input_file, output_file, sample_rate) 