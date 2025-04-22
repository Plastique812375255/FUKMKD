#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
res文件标识符分析工具

分析res文件中每个条目最后4个字节(标识符/校验值)的模式
"""

import os
import sys
import struct
import binascii
import argparse
from collections import Counter, defaultdict

def extract_filename(data):
    """从字节数据中提取文件名（空字节终止的字符串）"""
    filename = ""
    for b in data:
        if b == 0:
            break
        filename += chr(b)
    return filename

def analyze_res_identifiers(res_file_path):
    """
    分析res文件中所有条目的标识符/校验值
    """
    try:
        with open(res_file_path, 'rb') as f:
            data = f.read()
        
        # 读取条目数量
        entry_count = struct.unpack('>I', data[:4])[0]
        print(f"文件: {res_file_path}")
        print(f"条目数量: {entry_count}")
        
        # 计算数据区开始位置
        data_start = 4 + entry_count * 44
        
        # 解析条目表
        entries = []
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
            identifier = values[3]
            
            # 添加到条目列表
            entries.append({
                'index': i + 1,
                'filename': filename,
                'extension': os.path.splitext(filename)[1].lower(),
                'reserved': reserved,
                'file_size': file_size,
                'file_offset': file_offset,
                'identifier': identifier,
                'identifier_hex': f"{identifier:08x}",
                'identifier_bytes': entry_data[40:44].hex(' ')
            })
            
            offset += 44
        
        return entries
    
    except Exception as e:
        print(f"错误: 无法分析res文件: {e}")
        return []

def print_identifier_stats(entries):
    """打印标识符的统计信息"""
    if not entries:
        print("无条目可分析")
        return
    
    print("\n=== 标识符字节模式分析 ===")
    
    # 分析末尾字节
    last_bytes = [int(e['identifier_hex'][6:8], 16) for e in entries]
    last_byte_counter = Counter(last_bytes)
    print(f"\n末尾字节(第4字节)分布:")
    for byte, count in last_byte_counter.most_common():
        percentage = (count / len(entries)) * 100
        print(f"  0x{byte:02x}: {count}次 ({percentage:.1f}%)")
    
    # 分析倒数第二个字节
    second_last_bytes = [int(e['identifier_hex'][4:6], 16) for e in entries]
    second_last_byte_counter = Counter(second_last_bytes)
    print(f"\n倒数第二字节(第3字节)分布:")
    for byte, count in second_last_byte_counter.most_common():
        percentage = (count / len(entries)) * 100
        print(f"  0x{byte:02x}: {count}次 ({percentage:.1f}%)")
    
    # 按扩展名分组分析
    by_extension = defaultdict(list)
    for entry in entries:
        by_extension[entry['extension']].append(entry)
    
    print("\n按文件类型分析最后两个字节模式:")
    for ext, ext_entries in by_extension.items():
        print(f"\n扩展名: {ext}")
        patterns = [e['identifier_hex'][4:8] for e in ext_entries]
        pattern_counter = Counter(patterns)
        for pattern, count in pattern_counter.most_common(5):  # 只显示前5个最常见模式
            percentage = (count / len(ext_entries)) * 100
            print(f"  0x{pattern}: {count}次 ({percentage:.1f}%)")
    
    # 按索引号检查是否有规律
    print("\n按索引号分析标识符变化:")
    last_id = None
    diffs = []
    
    for i in range(1, min(11, len(entries))):  # 只分析前10个条目
        entry = entries[i-1]
        current_id = entry['identifier']
        print(f"  {i:2d}. {entry['filename']}: 0x{entry['identifier_hex']} ({entry['identifier_bytes']})")
        
        if last_id is not None:
            diff = current_id - last_id
            diffs.append(diff)
            print(f"     与上一个差值: {diff}")
        
        last_id = current_id
    
    # 检查前缀字节是否有规律
    print("\n前两个字节分析:")
    prefix_patterns = [e['identifier_hex'][:4] for e in entries]
    prefix_counter = Counter(prefix_patterns)
    print("最常见的前缀模式:")
    for pattern, count in prefix_counter.most_common(10):  # 只显示前10个最常见前缀
        percentage = (count / len(entries)) * 100
        print(f"  0x{pattern}: {count}次 ({percentage:.1f}%)")
    
    # 检查是否和文件大小相关
    print("\n检查标识符与文件大小的关系:")
    size_samples = min(5, len(entries))
    for i in range(size_samples):
        entry = entries[i]
        print(f"  {entry['filename']}: 大小={entry['file_size']}字节, 标识符=0x{entry['identifier_hex']}")
    
    # 检查是否和文件位置相关
    print("\n检查标识符与文件偏移量的关系:")
    for i in range(size_samples):
        entry = entries[i]
        print(f"  {entry['filename']}: 偏移量={entry['file_offset']}, 标识符=0x{entry['identifier_hex']}")

def calculate_possible_hashes(entries):
    """尝试计算可能的哈希值关系"""
    print("\n=== 尝试找出哈希计算方法 ===")
    
    for i in range(min(5, len(entries))):
        entry = entries[i]
        filename = entry['filename']
        identifier = entry['identifier']
        file_size = entry['file_size']
        file_offset = entry['file_offset']
        
        print(f"\n文件: {filename}")
        print(f"标识符: 0x{identifier:08x}")
        
        # 测试CRC32
        filename_crc = binascii.crc32(filename.encode())
        print(f"文件名CRC32: 0x{filename_crc:08x}")
        
        # 测试名称+大小组合
        name_size_str = f"{filename}:{file_size}"
        name_size_crc = binascii.crc32(name_size_str.encode())
        print(f"文件名+大小CRC32: 0x{name_size_crc:08x}")
        
        # 测试名称+偏移量组合
        name_offset_str = f"{filename}:{file_offset}"
        name_offset_crc = binascii.crc32(name_offset_str.encode())
        print(f"文件名+偏移量CRC32: 0x{name_offset_crc:08x}")
        
        # 测试扩展名特殊标记
        ext = os.path.splitext(filename)[1].lower()
        last_two_bytes = identifier & 0xFFFF
        print(f"扩展名: {ext}, 最后两个字节: 0x{last_two_bytes:04x}")

def main():
    parser = argparse.ArgumentParser(description='res文件标识符分析工具')
    parser.add_argument('res_file', help='要分析的res文件路径')
    
    args = parser.parse_args()
    
    entries = analyze_res_identifiers(args.res_file)
    if entries:
        print_identifier_stats(entries)
        calculate_possible_hashes(entries)

if __name__ == '__main__':
    main() 