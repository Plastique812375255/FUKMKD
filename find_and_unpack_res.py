#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
res文件批量解包工具

该脚本遍历sys目录，找到所有包含res文件的文件夹，
然后在根目录下创建resUnpack文件夹，在里面建立同名的文件夹，
将res文件解包到对应的文件夹，并生成CSV文件记录文件名、偏移量和大小。

用法: python3 find_and_unpack_res.py [sys目录路径]

参数:
  sys目录路径  - 指定要搜索的sys目录路径，默认为当前目录下的'sys'
"""

import os
import sys
import csv
import struct
import shutil
import argparse
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
            
            # 检查偏移量和大小是否有效
            is_valid = True
            if absolute_offset + file_size > len(data):
                is_valid = False
                print(f"警告: 条目 '{filename}' 超出文件范围")
            
            # 添加到结果列表
            result['entries'].append({
                'index': i + 1,
                'filename': filename,
                'reserved': reserved,
                'file_size': file_size,
                'offset_in_data': file_offset,
                'checksum': checksum,
                'absolute_offset': absolute_offset,
                'is_valid': is_valid
            })
            
            offset += 44
        
        return data, result
    
    except Exception as e:
        print(f"错误: 无法分析res文件 {res_file_path}: {e}")
        return None, result

def extract_files_from_res(res_file_path, output_dir, create_csv=True):
    """
    从res文件中提取所有文件，并可选择性地创建CSV文件
    
    参数:
        res_file_path: res文件路径
        output_dir: 输出目录
        create_csv: 是否创建CSV文件
    """
    # 分析res文件
    data, result = analyze_res_file(res_file_path)
    if data is None:
        return False
    
    entries = result['entries']
    data_start = result['data_start']
    
    print(f"\n处理res文件: {res_file_path}")
    print(f"条目数量: {result['entry_count']}")
    print(f"有效条目: {sum(1 for e in entries if e['is_valid'])}")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 如果需要创建CSV文件
    if create_csv:
        csv_path = os.path.join(output_dir, "files_list.csv")
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                # 写入CSV头
                csv_writer.writerow(["文件名", "偏移量", "大小(字节)"])
                
                # 写入每个条目的信息
                for entry in entries:
                    if entry['is_valid']:
                        csv_writer.writerow([
                            entry['filename'],
                            entry['offset_in_data'],
                            entry['file_size']
                        ])
            
            print(f"已创建文件列表CSV: {csv_path}")
        except Exception as e:
            print(f"创建CSV文件时出错: {e}")
    
    # 提取文件
    extracted_count = 0
    skipped_count = 0
    
    for entry in entries:
        # 跳过无效条目
        if not entry['is_valid']:
            skipped_count += 1
            continue
        
        # 提取文件内容
        file_start = entry['absolute_offset']
        file_size = entry['file_size']
        file_end = file_start + file_size
        
        # 确保不超出文件范围
        if file_end <= len(data):
            file_data = data[file_start:file_end]
            
            # 保存到输出目录
            output_path = os.path.join(output_dir, entry['filename'])
            
            # 确保目录存在（处理文件名中可能包含的路径）
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            try:
                with open(output_path, 'wb') as out_file:
                    out_file.write(file_data)
                
                extracted_count += 1
            except Exception as e:
                print(f"错误: 无法保存 {entry['filename']}: {e}")
    
    print(f"已提取 {extracted_count} 个文件，跳过 {skipped_count} 个无效条目。")
    return True

def find_res_files_and_unpack(sys_dir="sys"):
    """
    找到所有包含res文件的文件夹，并解包到对应的目录
    
    参数:
        sys_dir: 要搜索的sys目录路径
    """
    # 确保sys目录存在
    if not os.path.exists(sys_dir) or not os.path.isdir(sys_dir):
        print(f"错误: 未找到指定的sys文件夹: {sys_dir}")
        return False
    
    # 创建resUnpack目录
    resunpack_dir = Path("resUnpack")
    if resunpack_dir.exists():
        print("resUnpack目录已存在，将继续使用")
    else:
        os.makedirs(resunpack_dir)
        print(f"已创建 {resunpack_dir} 目录")
    
    # 遍历sys目录查找res文件
    res_files_found = []
    
    for root, dirs, files in os.walk(sys_dir):
        for file in files:
            if file == "res":
                res_path = os.path.join(root, file)
                res_files_found.append(res_path)
    
    if not res_files_found:
        print("未找到任何res文件")
        return False
    
    print(f"找到 {len(res_files_found)} 个res文件")
    
    # 处理每个res文件
    for res_path in res_files_found:
        # 计算相对路径并创建对应的输出目录
        rel_path = os.path.relpath(os.path.dirname(res_path), sys_dir)
        output_dir = resunpack_dir / rel_path
        
        print(f"\n处理: {res_path}")
        print(f"输出目录: {output_dir}")
        
        # 解包res文件
        extract_files_from_res(res_path, output_dir)
    
    print("\n所有res文件处理完成！")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='res文件批量解包工具')
    parser.add_argument('sys_dir', nargs='?', default='sys', 
                        help='要搜索的sys目录路径，默认为当前目录下的"sys"')
    
    args = parser.parse_args()
    find_res_files_and_unpack(args.sys_dir) 