#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取res文件中的所有音频文件
"""
import struct
import os
import sys

def extract_files_from_res(res_file_path, output_dir):
    """
    从res文件中提取所有的音频文件
    
    参数:
        res_file_path: res文件路径
        output_dir: 输出目录
    """
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 读取res文件
    with open(res_file_path, 'rb') as f:
        data = f.read()
    
    # 读取条目数量（大端序）
    num_entries = struct.unpack('>I', data[:4])[0]
    print(f"文件中声明的条目数量: {num_entries}")
    
    # 解析条目表
    entries = []
    offset = 4  # 跳过条目数量的4个字节
    for i in range(num_entries):
        entry_data = data[offset:offset+44]
        
        # 提取文件名（空字节终止的字符串）
        filename_bytes = entry_data[:28]
        filename = ""
        for j in range(28):
            if filename_bytes[j] == 0:
                break
            filename += chr(filename_bytes[j])
        
        # 提取文件大小和偏移量信息
        values = struct.unpack('>IIII', entry_data[28:44])
        
        entries.append({
            'index': i + 1,
            'filename': filename,
            'file_size': values[1],
            'offset_in_data': values[2],
            'reserved': values[0],
            'checksum': values[3]
        })
        
        offset += 44
    
    # 数据区开始的偏移量
    data_start = 4 + num_entries * 44
    print(f"数据区开始的偏移量: {data_start} (0x{data_start:X})")
    
    # 提取所有文件
    extracted_count = 0
    for entry in entries:
        file_start = data_start + entry['offset_in_data']
        file_size = entry['file_size']
        
        # 计算文件结束位置
        file_end = file_start + file_size
        
        # 确保不超出文件范围
        if file_end <= len(data):
            # 提取文件内容
            file_data = data[file_start:file_end]
            
            # 保存到输出目录
            output_path = os.path.join(output_dir, entry['filename'])
            with open(output_path, 'wb') as out_file:
                out_file.write(file_data)
            
            print(f"已提取: {entry['filename']} ({file_size} 字节)")
            extracted_count += 1
        else:
            print(f"警告: 文件 {entry['filename']} 超出范围，跳过")
    
    print(f"\n提取完成! 共提取了 {extracted_count} 个文件到 {output_dir} 目录")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python3 extract_wav_files.py <res文件路径> [输出目录]")
        print("示例: python3 extract_wav_files.py sys/sound_1_vbc2_en/res extracted_sounds")
        sys.exit(1)
    
    # 获取参数
    res_file_path = sys.argv[1]
    output_dir = "extracted_sounds"
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    # 提取文件
    extract_files_from_res(res_file_path, output_dir) 