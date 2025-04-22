#!/usr/bin/env python3
# convert_all_au.py - 批量转换所有.au文件为WAV格式并记录文件头信息

import os
import sys
import shutil
import csv
import binascii
from au2wav import convert_au_to_wav

# 固定采样率为22050Hz
SAMPLE_RATE = 22050

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_file_header_hex(file_path):
    """获取文件头16字节的16进制表示"""
    with open(file_path, 'rb') as f:
        header_bytes = f.read(16)
    return binascii.hexlify(header_bytes).decode('utf-8')

def process_directory(src_dir, dest_dir):
    """处理目录中的所有.au文件"""
    ensure_dir(dest_dir)
    
    # 记录所有文件头信息的CSV数据
    csv_data = [["文件名", "文件头(十六进制)"]]
    
    # 遍历目录中的所有文件
    for item in os.listdir(src_dir):
        src_path = os.path.join(src_dir, item)
        
        # 如果是目录，递归处理
        if os.path.isdir(src_path):
            process_directory(src_path, os.path.join(dest_dir, item))
        
        # 如果是.au文件并且不是dummy.au，执行转换
        elif item.endswith('.au') and item != 'dummy.au':
            # 获取文件头信息
            header_hex = get_file_header_hex(src_path)
            csv_data.append([item, header_hex])
            
            # 创建对应的WAV文件路径
            wav_filename = os.path.splitext(item)[0] + '.wav'
            wav_path = os.path.join(dest_dir, wav_filename)
            
            # 转换为WAV格式
            print(f"转换: {src_path} -> {wav_path}")
            convert_au_to_wav(src_path, wav_path, SAMPLE_RATE)
    
    # 如果有文件被处理，写入CSV文件
    if len(csv_data) > 1:
        csv_path = os.path.join(dest_dir, 'file_headers.csv')
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(csv_data)
        print(f"文件头信息已保存到: {csv_path}")

def main():
    """主函数"""
    src_base = 'resUnpack'
    dest_base = 'auConvert'
    
    # 确保目标根目录存在
    ensure_dir(dest_base)
    
    # 遍历resUnpack中的所有目录
    for item in os.listdir(src_base):
        src_dir = os.path.join(src_base, item)
        if os.path.isdir(src_dir):
            dest_dir = os.path.join(dest_base, item)
            process_directory(src_dir, dest_dir)
    
    print("所有文件转换完成！")

if __name__ == "__main__":
    main() 