#!/usr/bin/env python3
# convert_wav_to_au.py - 批量将WAV文件转换回AU格式，使用原始文件头

import os
import sys
import csv
import binascii
from wav2au import convert_wav_to_au

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_headers_from_csv(csv_path):
    """从CSV文件加载文件头信息"""
    headers = {}
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头
        for row in reader:
            if len(row) >= 2:
                filename = row[0]
                header_hex = row[1]
                headers[filename] = header_hex
    return headers

def hex_to_bytes(hex_string):
    """将十六进制字符串转换为字节"""
    return binascii.unhexlify(hex_string)

def process_directory(wav_dir, au_dir, original_headers):
    """处理目录中的所有WAV文件"""
    ensure_dir(au_dir)
    
    # 遍历目录中的所有文件
    for item in os.listdir(wav_dir):
        wav_path = os.path.join(wav_dir, item)
        
        # 如果是目录，递归处理
        if os.path.isdir(wav_path):
            # 找到对应的headers.csv文件
            csv_path = os.path.join(wav_path, 'file_headers.csv')
            if os.path.exists(csv_path):
                sub_headers = load_headers_from_csv(csv_path)
                sub_au_dir = os.path.join(au_dir, item)
                process_directory(wav_path, sub_au_dir, sub_headers)
            else:
                # 没有headers.csv文件，直接处理
                sub_au_dir = os.path.join(au_dir, item)
                process_directory(wav_path, sub_au_dir, {})
        
        # 如果是WAV文件，执行转换
        elif item.endswith('.wav'):
            au_filename = os.path.splitext(item)[0] + '.au'
            au_path = os.path.join(au_dir, au_filename)
            
            # 获取原始文件头
            header_bytes = None
            if au_filename in original_headers:
                header_hex = original_headers[au_filename]
                header_bytes = hex_to_bytes(header_hex)
            
            # 转换为AU格式
            print(f"转换: {wav_path} -> {au_path}")
            try:
                with open(wav_path, 'rb') as wav_file:
                    from wav2au import read_wav_file, encode_wav_to_au
                    pcm_samples = read_wav_file(wav_path)
                    encoded_data = encode_wav_to_au(pcm_samples, header_bytes)
                    
                    with open(au_path, 'wb') as f:
                        f.write(encoded_data)
                    
                    print(f"转换完成: {wav_path} -> {au_path}")
            except Exception as e:
                print(f"转换失败: {wav_path} -> {au_path}, 错误: {e}")

def main():
    """主函数"""
    wav_base = 'auConvert'
    au_base = 'auConverted'
    
    # 确保目标根目录存在
    ensure_dir(au_base)
    
    # 遍历auConvert中的所有目录
    for item in os.listdir(wav_base):
        wav_dir = os.path.join(wav_base, item)
        if os.path.isdir(wav_dir):
            # 找到对应的headers.csv文件
            csv_path = os.path.join(wav_dir, 'file_headers.csv')
            if os.path.exists(csv_path):
                headers = load_headers_from_csv(csv_path)
                au_dir = os.path.join(au_base, item)
                process_directory(wav_dir, au_dir, headers)
            else:
                # 没有headers.csv文件，直接处理
                au_dir = os.path.join(au_base, item)
                process_directory(wav_dir, au_dir, {})
    
    print("所有文件转换完成！")

if __name__ == "__main__":
    main() 