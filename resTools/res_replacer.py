#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
res文件资源替换工具

该脚本用于替换res文件中的WAV音频文件和BMP图像文件。
可以替换单个文件或批量替换指定目录下的所有匹配文件。
支持替换不同大小的文件，会自动调整所有文件的偏移量信息。

用法: python3 res_replacer.py <res文件路径> <要替换的文件> <替换用的文件> [--backup]
      python3 res_replacer.py <res文件路径> --batch-replace <替换配置文件> [--backup]

参数:
  res文件路径       - res文件的完整路径
  要替换的文件      - 要替换的文件名称(在res内部的名称)
  替换用的文件      - 用来替换的新文件路径
  --batch-replace  - 批量替换模式，使用配置文件定义多个替换
  --backup         - 在替换前创建备份文件
  --force          - 强制替换，即使文件大小不同
"""

import os
import sys
import struct
import argparse
import shutil
import json
import csv
from pathlib import Path
from datetime import datetime

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
    分析res文件结构，返回文件内容和条目信息
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
                'absolute_offset': absolute_offset,
                'entry_offset': offset  # 记录条目在res文件中的偏移量，用于后续更新
            })
            
            offset += 44
        
        return data, result
    
    except Exception as e:
        print(f"错误: 无法分析res文件: {e}")
        return None, result

def verify_file_type(file_path, expected_ext):
    """验证文件类型是否符合预期"""
    _, ext = os.path.splitext(file_path.lower())
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        return False
    
    if ext != expected_ext.lower():
        print(f"警告: 文件扩展名不符合预期 (预期: {expected_ext}, 实际: {ext})")
        response = input("是否继续替换? (y/n): ")
        if response.lower() != 'y':
            return False
    
    return True

def replace_file_in_res(res_file_path, target_filename, replacement_file_path, create_backup=True, force_replace=False):
    """
    在res文件中替换指定文件
    
    参数:
        res_file_path: res文件路径
        target_filename: 要替换的文件名
        replacement_file_path: 替换用的文件路径
        create_backup: 是否创建备份
        force_replace: 强制替换，即使文件大小不同
    
    返回:
        成功返回True，失败返回False
    """
    print(f"\n正在处理: {res_file_path}")
    print(f"目标文件: {target_filename}")
    print(f"替换文件: {replacement_file_path}")
    
    # 验证替换文件是否存在
    if not os.path.exists(replacement_file_path):
        print(f"错误: 替换文件不存在: {replacement_file_path}")
        return False
    
    # 验证替换文件类型
    _, target_ext = os.path.splitext(target_filename.lower())
    if not verify_file_type(replacement_file_path, target_ext):
        return False
    
    # 分析res文件
    res_data, res_info = analyze_res_file(res_file_path)
    if res_data is None:
        return False
    
    # 寻找目标文件
    target_entry = None
    target_index = -1
    for i, entry in enumerate(res_info['entries']):
        if entry['filename'].lower() == target_filename.lower():
            target_entry = entry
            target_index = i
            break
    
    if target_entry is None:
        print(f"错误: 在res文件中未找到目标文件: {target_filename}")
        return False
    
    # 加载替换文件数据
    try:
        with open(replacement_file_path, 'rb') as f:
            replacement_data = f.read()
        
        replacement_size = len(replacement_data)
        print(f"原始文件大小: {target_entry['file_size']} 字节")
        print(f"替换文件大小: {replacement_size} 字节")
        
        # 检查文件大小
        size_diff = replacement_size - target_entry['file_size']
        if size_diff != 0:
            if not force_replace:
                print(f"警告: 替换文件大小与原始文件不同 (差异: {size_diff} 字节)")
                response = input("是否继续替换? (y/n): ")
                if response.lower() != 'y':
                    return False
            print(f"将更新所有后续文件的偏移量以适应大小变化")
        
        # 创建备份
        if create_backup:
            backup_path = f"{res_file_path}.{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
            shutil.copy2(res_file_path, backup_path)
            print(f"已创建备份: {backup_path}")
        
        # 创建新的res文件数据
        # 我们需要从头重建整个文件，而不只是替换数据部分
        
        # 1. 更新目标文件的大小
        new_entries = res_info['entries'].copy()
        new_entries[target_index]['file_size'] = replacement_size
        
        # 2. 更新所有后续文件的偏移量
        if size_diff != 0:
            # 从目标文件之后的条目开始更新
            for i in range(target_index + 1, len(new_entries)):
                new_entries[i]['offset_in_data'] += size_diff
        
        # 3. 创建新的文件头和条目表
        data_start = res_info['data_start']
        new_header = struct.pack('>I', res_info['entry_count'])
        new_entries_data = bytearray()
        
        for entry in new_entries:
            # 文件名部分（28字节）
            filename_bytes = entry['filename'].encode('ascii')
            filename_padded = filename_bytes + b'\x00' * (28 - len(filename_bytes))
            
            # 其他字段（4 x 4 = 16字节）
            entry_data = struct.pack('>IIII', 
                entry['reserved'], 
                entry['file_size'], 
                entry['offset_in_data'], 
                entry['checksum'])
            
            new_entries_data.extend(filename_padded)
            new_entries_data.extend(entry_data)
        
        # 4. 准备数据区
        new_data_section = bytearray()
        
        # 遍历所有条目，添加文件数据
        current_offset = 0
        for i, entry in enumerate(new_entries):
            # 验证当前偏移量是否与条目中的偏移量匹配
            if entry['offset_in_data'] != current_offset:
                print(f"警告: 文件 {entry['filename']} 的偏移量不一致(期望:{current_offset}, 实际:{entry['offset_in_data']})")
                # 我们使用条目中指定的偏移量
                if current_offset < entry['offset_in_data']:
                    # 添加填充数据
                    padding_size = entry['offset_in_data'] - current_offset
                    new_data_section.extend(b'\x00' * padding_size)
                    current_offset = entry['offset_in_data']
            
            # 如果是目标文件，添加替换文件的数据
            if i == target_index:
                new_data_section.extend(replacement_data)
            else:
                # 否则，从原始文件中提取数据
                start_pos = res_info['data_start'] + entry['offset_in_data']
                end_pos = start_pos + entry['file_size']
                original_data = res_data[start_pos:end_pos]
                new_data_section.extend(original_data)
            
            # 更新当前偏移量
            current_offset += entry['file_size']
        
        # 5. 组合新的res文件
        new_res_data = bytearray()
        new_res_data.extend(new_header)
        new_res_data.extend(new_entries_data)
        new_res_data.extend(new_data_section)
        
        # 6. 写入新的res文件
        with open(res_file_path, 'wb') as f:
            f.write(new_res_data)
        
        print(f"成功替换文件: {target_filename}")
        
        if size_diff != 0:
            print(f"文件大小变化: {size_diff:+} 字节")
            print(f"已更新 {len(new_entries) - target_index - 1} 个后续文件的偏移量")
            
        return True
    
    except Exception as e:
        print(f"替换文件时出错: {e}")
        return False

def batch_replace_files(res_file_path, config_file, create_backup=True, force_replace=False):
    """
    批量替换res文件中的文件
    
    参数:
        res_file_path: res文件路径
        config_file: 包含替换配置的文件路径（CSV或JSON）
        create_backup: 是否创建备份
        force_replace: 强制替换，即使文件大小不同
    """
    # 验证配置文件存在
    if not os.path.exists(config_file):
        print(f"错误: 配置文件不存在: {config_file}")
        return False
    
    # 读取配置
    replace_configs = []
    _, ext = os.path.splitext(config_file.lower())
    
    try:
        if ext == '.json':
            with open(config_file, 'r', encoding='utf-8') as f:
                replace_configs = json.load(f)
        elif ext == '.csv':
            with open(config_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'target_file' in row and 'replacement_file' in row:
                        replace_configs.append({
                            'target_file': row['target_file'],
                            'replacement_file': row['replacement_file']
                        })
        else:
            print(f"错误: 不支持的配置文件格式: {ext}")
            return False
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return False
    
    if not replace_configs:
        print("错误: 配置文件中没有有效的替换配置")
        return False
    
    print(f"从配置文件中读取了 {len(replace_configs)} 个替换项")
    
    # 创建备份（只创建一次）
    if create_backup:
        backup_path = f"{res_file_path}.{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
        shutil.copy2(res_file_path, backup_path)
        print(f"已创建备份: {backup_path}")
    
    # 逐个替换文件
    success_count = 0
    for i, config in enumerate(replace_configs):
        target_file = config['target_file']
        replacement_file = config['replacement_file']
        
        print(f"\n处理替换项 {i+1}/{len(replace_configs)}: {target_file}")
        
        # 我们在批量模式不再创建备份，因为上面已经创建了一个
        if replace_file_in_res(res_file_path, target_file, replacement_file, 
                               create_backup=False, force_replace=force_replace):
            success_count += 1
    
    print(f"\n完成批量替换: 成功 {success_count}/{len(replace_configs)}")
    return success_count > 0

def create_sample_config():
    """创建示例配置文件"""
    csv_config = Path("replace_config_sample.csv")
    json_config = Path("replace_config_sample.json")
    
    # 创建CSV示例
    try:
        with open(csv_config, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['target_file', 'replacement_file'])
            writer.writerow(['batt_alarmb.wav', 'path/to/new_batt_alarmb.wav'])
            writer.writerow(['batt_alarml.wav', 'path/to/new_batt_alarml.wav'])
            writer.writerow(['logo_700.bmp', 'path/to/new_logo.bmp'])
        print(f"已创建CSV配置示例: {csv_config}")
    except Exception as e:
        print(f"创建CSV配置示例时出错: {e}")
    
    # 创建JSON示例
    try:
        config = [
            {
                "target_file": "batt_alarmb.wav",
                "replacement_file": "path/to/new_batt_alarmb.wav"
            },
            {
                "target_file": "batt_alarml.wav",
                "replacement_file": "path/to/new_batt_alarml.wav"
            },
            {
                "target_file": "logo_700.bmp",
                "replacement_file": "path/to/new_logo.bmp"
            }
        ]
        with open(json_config, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"已创建JSON配置示例: {json_config}")
    except Exception as e:
        print(f"创建JSON配置示例时出错: {e}")

def main():
    parser = argparse.ArgumentParser(description='res文件资源替换工具')
    parser.add_argument('res_file', nargs='?', help='res文件路径')
    parser.add_argument('target_file', nargs='?', help='要替换的文件名')
    parser.add_argument('replacement_file', nargs='?', help='替换用的文件路径')
    parser.add_argument('--batch-replace', help='批量替换模式，指定配置文件路径')
    parser.add_argument('--backup', action='store_true', help='创建备份文件')
    parser.add_argument('--force', action='store_true', help='强制替换，即使文件大小不同')
    parser.add_argument('--create-sample-config', action='store_true', help='创建示例配置文件')
    
    args = parser.parse_args()
    
    # 创建示例配置
    if args.create_sample_config:
        create_sample_config()
        return
    
    # 批量替换模式
    if args.batch_replace:
        if not args.res_file:
            print("错误: 必须指定res文件路径")
            return
        batch_replace_files(args.res_file, args.batch_replace, args.backup, args.force)
        return
    
    # 单文件替换模式
    if not (args.res_file and args.target_file and args.replacement_file):
        print("使用方法:")
        print("  单文件替换: python3 res_replacer.py <res文件路径> <要替换的文件> <替换用的文件> [--backup] [--force]")
        print("  批量替换: python3 res_replacer.py <res文件路径> --batch-replace <配置文件> [--backup] [--force]")
        print("  创建示例配置: python3 res_replacer.py --create-sample-config")
        return
    
    replace_file_in_res(args.res_file, args.target_file, args.replacement_file, 
                       args.backup, args.force)

if __name__ == "__main__":
    main() 