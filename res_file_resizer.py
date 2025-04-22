#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
res资源文件查询和调整工具

该脚本用于查询res文件中资源的大小，以及调整WAV音频文件和BMP图像文件的大小。
虽然res_replacer.py现在支持不同大小文件的替换，但有时仍需要调整文件大小以满足特定需求。

用法:
  python3 res_file_resizer.py --check <res文件路径> <文件名>          # 查询文件大小
  python3 res_file_resizer.py --list-files <res文件路径>              # 列出所有文件
  python3 res_file_resizer.py --audio <输入WAV文件> <输出WAV文件> <目标大小>
  python3 res_file_resizer.py --image <输入BMP文件> <输出BMP文件> <目标大小>

参数:
  --check        查询res文件中指定文件的大小
  --list-files   列出res文件中的所有文件及其大小
  --audio        调整WAV音频文件大小
  --image        调整BMP图像文件大小
"""

import os
import sys
import struct
import argparse
import wave
import numpy as np
from PIL import Image
import io
from pathlib import Path

def extract_filename(data):
    """从字节数据中提取文件名（空字节终止的字符串）"""
    filename = ""
    for b in data:
        if b == 0:
            break
        filename += chr(b)
    return filename

def analyze_res_file(res_file_path):
    """
    分析res文件结构，返回条目信息
    """
    result = {
        'entries': [],
        'data_start': 0,
        'file_size': 0,
        'entry_count': 0
    }
    
    try:
        with open(res_file_path, 'rb') as f:
            data = f.read()
        
        result['file_size'] = len(data)
        
        # 读取条目数量
        entry_count = struct.unpack('>I', data[:4])[0]
        result['entry_count'] = entry_count
        
        # 计算数据区开始位置
        data_start = 4 + entry_count * 44
        result['data_start'] = data_start
        
        # 解析条目表
        offset = 4  # 跳过文件头4字节
        for i in range(entry_count):
            if offset + 44 > len(data):
                print(f"警告: 条目表不完整，期望读取条目 {i+1}/{entry_count}")
                break
                
            entry_data = data[offset:offset+44]
            
            # 提取文件名
            filename = extract_filename(entry_data[:28])
            
            # 提取其他值
            values = struct.unpack('>IIII', entry_data[28:44])
            reserved = values[0]
            file_size = values[1]
            file_offset = values[2]
            checksum = values[3]
            
            # 计算文件在res中的实际位置
            absolute_offset = data_start + file_offset
            
            # 添加到结果列表
            result['entries'].append({
                'index': i + 1,
                'filename': filename,
                'reserved': reserved,
                'file_size': file_size,
                'offset_in_data': file_offset,
                'checksum': checksum,
                'absolute_offset': absolute_offset
            })
            
            offset += 44
        
        return data, result
    
    except Exception as e:
        print(f"错误: 无法分析res文件: {e}")
        return None, result

def get_file_size_in_res(res_file_path, target_filename):
    """
    获取res文件中指定文件的大小
    
    参数:
        res_file_path: res文件路径
        target_filename: 要查找的文件名
    
    返回:
        文件大小（字节）或None（如果未找到）
    """
    _, res_info = analyze_res_file(res_file_path)
    
    # 查找目标文件
    for entry in res_info['entries']:
        if entry['filename'].lower() == target_filename.lower():
            return entry['file_size']
    
    return None

def list_files_in_res(res_file_path):
    """
    列出res文件中的所有文件及其大小
    
    参数:
        res_file_path: res文件路径
    """
    _, res_info = analyze_res_file(res_file_path)
    
    if not res_info['entries']:
        print(f"未在 {res_file_path} 中找到任何文件")
        return
    
    print(f"\nres文件: {res_file_path}")
    print(f"条目数量: {res_info['entry_count']}")
    print("\n{:<5} {:<30} {:<10}".format("序号", "文件名", "大小(字节)"))
    print("-" * 50)
    
    for entry in res_info['entries']:
        print("{:<5} {:<30} {:<10}".format(
            entry['index'],
            entry['filename'],
            entry['file_size']
        ))

def resize_wav_file(input_file, output_file, target_size):
    """
    调整WAV音频文件的大小
    
    参数:
        input_file: 输入WAV文件路径
        output_file: 输出WAV文件路径
        target_size: 目标文件大小（字节）
    
    返回:
        成功返回True，失败返回False
    """
    try:
        # 打开原始WAV文件
        with wave.open(input_file, 'rb') as wav_in:
            # 获取WAV文件参数
            n_channels = wav_in.getnchannels()
            sample_width = wav_in.getsampwidth()
            framerate = wav_in.getframerate()
            n_frames = wav_in.getnframes()
            
            # 读取所有音频数据
            wav_data = wav_in.readframes(n_frames)
        
        # 计算WAV文件头大小（通常为44字节）
        header_size = 44
        
        # 计算调整后的数据大小
        adjusted_data_size = target_size - header_size
        
        # 原始数据大小
        original_data_size = len(wav_data)
        
        if adjusted_data_size <= 0:
            print(f"错误: 目标大小 {target_size} 字节太小，无法容纳WAV文件头")
            return False
        
        # 创建调整后的WAV文件
        with wave.open(output_file, 'wb') as wav_out:
            wav_out.setnchannels(n_channels)
            wav_out.setsampwidth(sample_width)
            wav_out.setframerate(framerate)
            
            if adjusted_data_size >= original_data_size:
                # 目标大小大于或等于原始数据大小，需要添加静音
                # 首先写入原始数据
                wav_out.writeframes(wav_data)
                
                # 计算需要添加的静音数据大小
                padding_size = adjusted_data_size - original_data_size
                
                # 添加静音（根据采样宽度创建相应的静音数据）
                silence = b'\x00' * padding_size
                wav_out.writeframes(silence)
                
                print(f"已添加 {padding_size} 字节的静音到文件末尾")
            else:
                # 目标大小小于原始数据大小，需要截断
                # 根据采样宽度计算采样点数量，确保裁剪点在采样点边界
                samples_to_keep = adjusted_data_size // (sample_width * n_channels)
                truncated_data = wav_data[:samples_to_keep * sample_width * n_channels]
                wav_out.writeframes(truncated_data)
                
                print(f"已将音频截断为原始长度的 {len(truncated_data)/original_data_size:.2%}")
        
        # 验证输出文件大小
        output_size = os.path.getsize(output_file)
        print(f"原始文件大小: {os.path.getsize(input_file)} 字节")
        print(f"目标文件大小: {target_size} 字节")
        print(f"输出文件大小: {output_size} 字节")
        
        if output_size != target_size:
            print(f"警告: 输出文件大小 ({output_size} 字节) 与目标大小 ({target_size} 字节) 不一致")
            print("可能需要手动调整文件以达到精确大小")
        
        return True
    
    except Exception as e:
        print(f"调整WAV文件大小时出错: {e}")
        return False

def resize_bmp_file(input_file, output_file, target_size):
    """
    调整BMP图像文件的大小
    
    参数:
        input_file: 输入BMP文件路径
        output_file: 输出BMP文件路径
        target_size: 目标文件大小（字节）
    
    返回:
        成功返回True，失败返回False
    """
    try:
        # 打开原始图像
        with Image.open(input_file) as img:
            # 确保为BMP格式
            if img.format != "BMP":
                print(f"警告: 输入文件不是BMP格式，将转换为BMP格式")
                img = img.convert("RGB")
            
            # 获取图像尺寸和模式
            width, height = img.size
            mode = img.mode
            
            # 将图像保存为BMP格式到内存缓冲区
            buffer = io.BytesIO()
            img.save(buffer, format="BMP")
            buffer.seek(0)
            bmp_data = buffer.read()
            
            # 计算BMP头大小（通常为54字节）
            header_size = 54
            
            # 计算调整大小所需的填充字节数
            padding_size = target_size - len(bmp_data)
            
            if padding_size < 0:
                print(f"错误: 原始BMP文件 ({len(bmp_data)} 字节) 大于目标大小 ({target_size} 字节)")
                print("请尝试降低图像质量或减小尺寸后再试")
                return False
            
            # 创建调整后的BMP文件
            with open(output_file, 'wb') as f:
                # 写入原始BMP数据
                f.write(bmp_data)
                
                # 如果需要，添加填充以达到目标大小
                if padding_size > 0:
                    # 添加填充字节（0值）到文件末尾
                    f.write(b'\x00' * padding_size)
                    print(f"已添加 {padding_size} 字节的填充到文件末尾")
            
            # 验证输出文件大小
            output_size = os.path.getsize(output_file)
            print(f"原始文件大小: {os.path.getsize(input_file)} 字节")
            print(f"目标文件大小: {target_size} 字节")
            print(f"输出文件大小: {output_size} 字节")
            
            if output_size != target_size:
                print(f"警告: 输出文件大小 ({output_size} 字节) 与目标大小 ({target_size} 字节) 不一致")
            
            return True
    
    except Exception as e:
        print(f"调整BMP文件大小时出错: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='res资源文件查询和调整工具')
    
    # 创建互斥组
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--audio', action='store_true', help='调整WAV音频文件')
    group.add_argument('--image', action='store_true', help='调整BMP图像文件')
    group.add_argument('--check', action='store_true', help='查询res文件中指定文件的大小')
    group.add_argument('--list-files', action='store_true', help='列出res文件中的所有文件及其大小')
    
    # 添加其他参数
    parser.add_argument('input', help='输入文件路径或res文件路径')
    parser.add_argument('output', nargs='?', help='输出文件路径或要查找的文件名')
    parser.add_argument('size', nargs='?', type=int, help='目标文件大小（字节）')
    
    args = parser.parse_args()
    
    # 检查模式
    if args.check:
        if not args.output:
            print("错误: 必须指定要查找的文件名")
            return
        
        file_size = get_file_size_in_res(args.input, args.output)
        if file_size is not None:
            print(f"文件 '{args.output}' 在res文件 '{args.input}' 中的大小为 {file_size} 字节")
        else:
            print(f"错误: 在res文件 '{args.input}' 中未找到文件 '{args.output}'")
        
        return
    
    # 列出文件模式
    if args.list_files:
        list_files_in_res(args.input)
        return
    
    # 调整大小模式
    if (args.audio or args.image) and not (args.output and args.size):
        print("错误: 调整大小模式需要指定输出文件路径和目标大小")
        return
    
    if args.audio:
        resize_wav_file(args.input, args.output, args.size)
    elif args.image:
        resize_bmp_file(args.input, args.output, args.size)

if __name__ == "__main__":
    main() 