#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
res文件标识符验证工具

尝试通过不同方法重新生成标识符并与原始值比较
"""

import os
import sys
import struct
import binascii
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

def extract_entries(res_file_path):
    """提取res文件中的所有条目信息"""
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
                'index': i,
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
        
        return entries, data_start
    
    except Exception as e:
        print(f"错误: 无法提取res文件条目: {e}")
        return [], 0

def try_regenerate_identifiers(entries, res_file_path):
    """尝试使用不同方法重新生成标识符并验证"""
    # 获取res文件版本（基于文件名）
    res_name = os.path.basename(os.path.dirname(res_file_path))
    
    # 解析版本号
    version_byte = 0x00  # 默认值
    
    if "sound_1" in res_name:
        version_byte = 0x01
    elif "sound_2" in res_name:
        version_byte = 0x02
    elif "voice" in res_name:
        version_byte = 0x00
    
    print(f"\nres文件: {res_name}")
    print(f"使用版本字节: 0x{version_byte:02x}")
    
    # 添加详细信息：输出前20个文件的条目详情
    print("\n前20个条目详细信息:")
    print(f"{'索引':^5} | {'文件名':^20} | {'第三字节':^8} | {'标识符':^10} | {'大小':^10} | {'偏移量':^10}")
    print("-" * 70)
    
    for i, entry in enumerate(entries[:20]):
        third_byte = (entry['identifier'] >> 8) & 0xFF
        print(f"{entry['index']:^5} | {entry['filename']:^20} | 0x{third_byte:02x} | {entry['identifier_hex']} | {entry['file_size']:^10} | {entry['file_offset']:^10}")

    # 分析第三字节递增模式
    third_byte_base, block_sizes = analyze_third_byte_pattern(entries)
    
    # 分析前两个字节的模式
    analyze_first_two_bytes(entries)

    # 检查最后一个字节是否匹配
    correct_last_byte = 0
    total_entries = len(entries)
    
    for entry in entries:
        id_last_byte = entry['identifier'] & 0xFF
        if id_last_byte == version_byte:
            correct_last_byte += 1
    
    last_byte_accuracy = (correct_last_byte / total_entries) * 100 if total_entries > 0 else 0
    print(f"\n验证最后字节: {correct_last_byte}/{total_entries} 正确 ({last_byte_accuracy:.1f}%)")
    
    # 收集第三个字节(倒数第二个字节)的扩展名关系
    ext_to_bytes = {}
    for entry in entries:
        ext = entry['extension']
        third_byte = (entry['identifier'] >> 8) & 0xFF
        
        if ext not in ext_to_bytes:
            ext_to_bytes[ext] = []
        
        if third_byte not in ext_to_bytes[ext]:
            ext_to_bytes[ext].append(third_byte)
    
    print("\n扩展名与第三个字节的关系:")
    for ext, bytes_list in sorted(ext_to_bytes.items()):
        bytes_list.sort()  # 对字节列表排序
        bytes_str = ", ".join([f"0x{b:02x}" for b in bytes_list])
        print(f"  {ext}: {bytes_str}")
    
    # 提取前两个字节的列表，供方法7使用
    first_two_bytes_list = [(entry['index'], (entry['identifier'] >> 16) & 0xFFFF) for entry in entries]
    
    # 验证多种标识符生成方法
    generation_methods = [
        ("方法1: 简单索引乘法", generate_id_method1),
        ("方法2: 基于文件名哈希", generate_id_method2),
        ("方法3: 基于文件名和大小", generate_id_method3),
        ("方法4: 基于文件名和偏移量", generate_id_method4),
        ("方法5: 基于文件索引+偏移量", generate_id_method5),
        ("方法6: 固定前两字节+类型匹配", generate_id_method6),
        ("方法7: 第三字节递增模式", lambda fn, ext, idx, offset, size, data, ver: 
         generate_id_method7(fn, ext, idx, offset, size, data, ver, third_byte_base, block_sizes, first_two_bytes_list))
    ]
    
    # 检查文件数据（前100字节）是否包含在标识符计算中
    try:
        with open(res_file_path, 'rb') as f:
            res_data = f.read()
        
        data_start = 4 + len(entries) * 44
        
        # 提取每个文件的前100字节用于测试
        for entry in entries:
            if entry['file_offset'] + 100 <= len(res_data) - data_start:
                file_data = res_data[data_start + entry['file_offset']:data_start + entry['file_offset'] + min(100, entry['file_size'])]
                entry['file_data'] = file_data
            else:
                entry['file_data'] = b''
    except:
        print("无法读取文件数据用于测试")
        for entry in entries:
            entry['file_data'] = b''
    
    print("\n尝试不同的标识符生成方法:")
    
    best_method = None
    best_accuracy = 0
    best_matches = 0
    
    for method_name, method_func in generation_methods:
        print(f"\n{method_name}:")
        
        correct_identifiers = 0
        partial_matches = 0
        
        for entry in entries:
            # 生成标识符
            generated_id = method_func(
                entry['filename'], 
                entry['extension'],
                entry['index'],
                entry['file_offset'],
                entry['file_size'],
                entry['file_data'],
                version_byte
            )
            
            original_id = entry['identifier']
            
            # 检查完全匹配
            if generated_id == original_id:
                correct_identifiers += 1
            
            # 检查部分匹配（最后两个字节）
            if (generated_id & 0xFFFF) == (original_id & 0xFFFF):
                partial_matches += 1
        
        full_accuracy = (correct_identifiers / total_entries) * 100 if total_entries > 0 else 0
        partial_accuracy = (partial_matches / total_entries) * 100 if total_entries > 0 else 0
        
        print(f"  完全匹配: {correct_identifiers}/{total_entries} ({full_accuracy:.1f}%)")
        print(f"  部分匹配(最后两字节): {partial_matches}/{total_entries} ({partial_accuracy:.1f}%)")
        
        if correct_identifiers > best_matches:
            best_method = method_name
            best_accuracy = full_accuracy
            best_matches = correct_identifiers
    
    if best_method:
        print(f"\n最佳方法: {best_method} (准确率: {best_accuracy:.1f}%)")
    else:
        print("\n没有找到有效的生成方法")
    
    # 检查前两个字节的规律
    print("\n前两个字节与文件索引关系:")
    for i in range(min(10, len(entries))):
        entry = entries[i]
        first_two_bytes = (entry['identifier'] >> 16) & 0xFFFF
        print(f"  索引 {i:2d}: 0x{first_two_bytes:04x} (文件: {entry['filename']})")

def analyze_third_byte_pattern(entries):
    """分析第三字节的递增模式"""
    print("\n第三字节递增模式分析:")
    
    # 提取所有条目的第三字节
    third_bytes = [(entry['index'], (entry['identifier'] >> 8) & 0xFF, entry['filename']) for entry in entries]
    
    # 分析递增模式
    prev_byte = None
    transitions = []
    consecutive_same = 0
    byte_counts = {}
    
    for idx, byte, filename in third_bytes:
        # 记录每个字节值出现的次数
        if byte not in byte_counts:
            byte_counts[byte] = 0
        byte_counts[byte] += 1
        
        # 检查变化
        if prev_byte is not None:
            if byte == prev_byte:
                consecutive_same += 1
            else:
                # 记录变化点
                diff = byte - prev_byte
                transitions.append((idx, prev_byte, byte, diff, consecutive_same + 1, filename))
                consecutive_same = 0
        
        prev_byte = byte
    
    # 添加最后一组
    if prev_byte is not None and consecutive_same > 0:
        transitions.append((third_bytes[-1][0], prev_byte, prev_byte, 0, consecutive_same + 1, 
                           third_bytes[-1][2]))
    
    # 报告模式
    print(f"总共有 {len(byte_counts)} 个不同的第三字节值")
    print(f"字节值频率: {', '.join([f'0x{b:02x}:{c}次' for b, c in sorted(byte_counts.items())])}")
    
    print("\n字节值变化点:")
    print(f"{'索引':^5} | {'从':^5} | {'到':^5} | {'差值':^5} | {'连续相同':^8} | {'变化点文件'}")
    print("-" * 65)
    
    for idx, from_byte, to_byte, diff, count, filename in transitions:
        print(f"{idx:^5} | 0x{from_byte:02x} | 0x{to_byte:02x} | {diff:^5} | {count:^8} | {filename}")
    
    # 验证是否存在规律性递增
    increments = [t[3] for t in transitions if t[3] > 0]
    base_third_byte = third_bytes[0][1] if third_bytes else 0
    block_sizes = [t[4] for t in transitions]
    
    if increments and all(inc == increments[0] for inc in increments):
        print(f"\n发现规律递增模式: 第三字节每次增加 {increments[0]}")
        
        # 检查每个递增块的大小是否有规律
        if all(size == block_sizes[0] for size in block_sizes):
            print(f"每个值连续出现 {block_sizes[0]} 次后递增")
        else:
            print(f"块大小不规律: {', '.join([str(s) for s in block_sizes])}")
    else:
        print("\n没有发现固定的递增模式")
    
    return base_third_byte, block_sizes

def analyze_first_two_bytes(entries):
    """分析前两个字节的模式"""
    print("\n前两个字节模式分析:")
    
    # 提取前两个字节和其他属性
    bytes_data = []
    for entry in entries:
        first_two_bytes = (entry['identifier'] >> 16) & 0xFFFF
        bytes_data.append({
            'index': entry['index'],
            'filename': entry['filename'],
            'first_two_bytes': first_two_bytes,
            'first_byte': (first_two_bytes >> 8) & 0xFF,
            'second_byte': first_two_bytes & 0xFF,
            'offset': entry['file_offset'],
            'size': entry['file_size']
        })
    
    # 输出前30个条目的详细信息
    print(f"{'索引':^5} | {'文件名':^15} | {'前两字节':^8} | {'第一字节':^8} | {'第二字节':^8} | {'偏移量':^10} | {'大小':^10}")
    print("-" * 80)
    
    for data in bytes_data[:30]:
        print(f"{data['index']:^5} | {data['filename']:^15} | 0x{data['first_two_bytes']:04x} | 0x{data['first_byte']:02x} | 0x{data['second_byte']:02x} | {data['offset']:^10} | {data['size']:^10}")
    
    # 检查与索引的关系
    print("\n检查前两字节与索引的关系:")
    for i in range(min(10, len(bytes_data))):
        data = bytes_data[i]
        print(f"索引 {i:3d}: 0x{data['first_two_bytes']:04x}, 差值(前一个): {data['first_two_bytes'] - bytes_data[i-1]['first_two_bytes'] if i > 0 else 'N/A'}")
    
    # 检查与文件名的关系
    print("\n检查前两字节与文件名的关系:")
    for i in range(min(10, len(bytes_data))):
        data = bytes_data[i]
        filename_crc = binascii.crc32(data['filename'].encode()) & 0xFFFF
        print(f"文件 {data['filename']:10s}: 实际值=0x{data['first_two_bytes']:04x}, 文件名CRC32=0x{filename_crc:04x}, 匹配: {data['first_two_bytes'] == filename_crc}")
    
    # 检查与偏移量的关系
    print("\n检查前两字节与偏移量的关系:")
    matches = 0
    for i in range(min(10, len(bytes_data))):
        data = bytes_data[i]
        offset_derived = ((data['offset'] >> 8) ^ (data['offset'] & 0xFF)) & 0xFF
        match = (data['first_two_bytes'] & 0xFF) == offset_derived
        if match:
            matches += 1
        print(f"偏移量 {data['offset']}: 低字节=0x{data['second_byte']:02x}, 偏移量派生=0x{offset_derived:02x}, 匹配: {match}")
    
    # 检查与大小的关系
    print("\n检查前两字节与文件大小的关系:")
    matches = 0
    for i in range(min(10, len(bytes_data))):
        data = bytes_data[i]
        size_derived = ((data['size'] >> 8) ^ (data['size'] & 0xFF)) & 0xFF
        match = (data['first_two_bytes'] & 0xFF) == size_derived
        if match:
            matches += 1
        print(f"大小 {data['size']}: 低字节=0x{data['second_byte']:02x}, 大小派生=0x{size_derived:02x}, 匹配: {match}")
        
    # 检查高位字节的规律
    high_bytes = [data['first_byte'] for data in bytes_data]
    unique_high_bytes = set(high_bytes)
    print(f"\n高位字节统计: 共有{len(unique_high_bytes)}个不同值")
    
    high_byte_counts = {}
    for byte in high_bytes:
        if byte not in high_byte_counts:
            high_byte_counts[byte] = 0
        high_byte_counts[byte] += 1
    
    for byte, count in sorted(high_byte_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"0x{byte:02x}: 出现{count}次 ({count/len(high_bytes)*100:.1f}%)")
    
    # 检查低位字节的规律
    low_bytes = [data['second_byte'] for data in bytes_data]
    unique_low_bytes = set(low_bytes)
    print(f"\n低位字节统计: 共有{len(unique_low_bytes)}个不同值")
    
    low_byte_counts = {}
    for byte in low_bytes:
        if byte not in low_byte_counts:
            low_byte_counts[byte] = 0
        low_byte_counts[byte] += 1
    
    for byte, count in sorted(low_byte_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"0x{byte:02x}: 出现{count}次 ({count/len(low_bytes)*100:.1f}%)")
    
    # 检查前两字节是否有特定的位模式
    print("\n检查前两字节的位模式:")
    
    # 分析第一字节的位模式
    first_byte_patterns = {}
    for data in bytes_data:
        byte = data['first_byte']
        pattern = bin(byte)[2:].zfill(8)
        if pattern not in first_byte_patterns:
            first_byte_patterns[pattern] = 0
        first_byte_patterns[pattern] += 1
    
    sorted_patterns = sorted(first_byte_patterns.items(), key=lambda x: -x[1])
    for pattern, count in sorted_patterns[:5]:
        byte_value = int(pattern, 2)
        print(f"第一字节模式 {pattern} (0x{byte_value:02x}): 出现{count}次 ({count/len(bytes_data)*100:.1f}%)")
    
    # 分析第二字节的位模式
    second_byte_patterns = {}
    for data in bytes_data:
        byte = data['second_byte']
        pattern = bin(byte)[2:].zfill(8)
        if pattern not in second_byte_patterns:
            second_byte_patterns[pattern] = 0
        second_byte_patterns[pattern] += 1
    
    sorted_patterns = sorted(second_byte_patterns.items(), key=lambda x: -x[1])
    for pattern, count in sorted_patterns[:5]:
        byte_value = int(pattern, 2)
        print(f"第二字节模式 {pattern} (0x{byte_value:02x}): 出现{count}次 ({count/len(bytes_data)*100:.1f}%)")

# 各种标识符生成方法
def generate_id_method1(filename, ext, index, offset, size, data, version):
    """方法1: 简单索引乘法"""
    # 使用索引生成前两个字节
    first_two_bytes = ((index * 0x1234 + 0x5678) & 0xFFFF)
    
    # 基于扩展名和版本确定第三个字节
    if version == 0x01:  # sound_1
        if ext == '.wav':
            third_byte = 0xaa + (index % 10)  # 0xaa-0xb4范围
        elif ext == '.au':
            third_byte = 0xab  # .au文件固定使用0xab
        else:
            third_byte = 0xaf  # 其他文件类型
    elif version == 0x02:  # sound_2
        third_byte = 0x0e + (index % 20)  # 0x0e-0x22范围
    else:  # voice
        third_byte = 0xcd + (index % 26)  # 0xcd-0xe7范围
    
    # 组合成完整的标识符
    identifier = (first_two_bytes << 16) | (third_byte << 8) | version
    
    return identifier

def generate_id_method2(filename, ext, index, offset, size, data, version):
    """方法2: 基于文件名哈希"""
    # 使用文件名的CRC32的低16位作为前两个字节
    filename_crc = binascii.crc32(filename.encode()) & 0xFFFF
    
    # 确定第三个字节
    if version == 0x01:  # sound_1
        if ext == '.wav':
            third_byte = 0xaa + (index % 10)
        else:
            third_byte = 0xab
    elif version == 0x02:  # sound_2
        third_byte = 0x0e + (index % 20)
    else:  # voice
        third_byte = 0xcd + (index % 26)
    
    # 组合成完整的标识符
    identifier = (filename_crc << 16) | (third_byte << 8) | version
    
    return identifier

def generate_id_method3(filename, ext, index, offset, size, data, version):
    """方法3: 基于文件名和大小"""
    # 使用文件名和大小的组合哈希的低16位
    name_size_str = f"{filename}:{size}"
    name_size_crc = binascii.crc32(name_size_str.encode()) & 0xFFFF
    
    # 确定第三个字节
    if version == 0x01:  # sound_1
        if ext == '.wav':
            third_byte = 0xaa + (index % 10)
        else:
            third_byte = 0xab
    elif version == 0x02:  # sound_2
        third_byte = 0x0e + (index % 20)
    else:  # voice
        third_byte = 0xcd + (index % 26)
    
    # 组合成完整的标识符
    identifier = (name_size_crc << 16) | (third_byte << 8) | version
    
    return identifier

def generate_id_method4(filename, ext, index, offset, size, data, version):
    """方法4: 基于文件名和偏移量"""
    # 使用文件名和偏移量的组合哈希的低16位
    name_offset_str = f"{filename}:{offset}"
    name_offset_crc = binascii.crc32(name_offset_str.encode()) & 0xFFFF
    
    # 确定第三个字节
    if version == 0x01:  # sound_1
        if ext == '.wav':
            third_byte = 0xaa + (index % 10)
        else:
            third_byte = 0xab
    elif version == 0x02:  # sound_2
        third_byte = 0x0e + (index % 20)
    else:  # voice
        third_byte = 0xcd + (index % 26)
    
    # 组合成完整的标识符
    identifier = (name_offset_crc << 16) | (third_byte << 8) | version
    
    return identifier

def generate_id_method5(filename, ext, index, offset, size, data, version):
    """方法5: 基于文件索引+偏移量"""
    # 使用索引和偏移量的组合计算前两个字节
    value = (index * 0x10000 + offset) & 0xFFFFFFFF
    first_bytes = (value >> 8) & 0xFFFF
    
    # 确定第三个字节（与扩展名关联）
    if version == 0x01:  # sound_1
        if ext == '.wav':
            third_byte = 0xaa + (index % 10)
        else:
            third_byte = 0xab
    elif version == 0x02:  # sound_2
        third_byte = 0x0e + (index % 20)
    else:  # voice
        third_byte = 0xcd + (index % 26)
    
    # 组合成完整的标识符
    identifier = (first_bytes << 16) | (third_byte << 8) | version
    
    return identifier

def generate_id_method6(filename, ext, index, offset, size, data, version):
    """方法6: 提取文件数据前两个字节+类型匹配"""
    # 尝试从文件前两个字节获取值（如果可用）
    if len(data) >= 2:
        first_bytes = (data[0] << 8) | data[1]
    else:
        # 回退到使用文件名的哈希
        first_bytes = binascii.crc32(filename.encode()) & 0xFFFF
    
    # 确定第三个字节
    if version == 0x01:  # sound_1
        if ext == '.wav':
            third_byte = 0xaa + (index % 10)
        else:
            third_byte = 0xab
    elif version == 0x02:  # sound_2
        third_byte = 0x0e + (index % 20)
    else:  # voice
        third_byte = 0xcd + (index % 26)
    
    # 组合成完整的标识符
    identifier = (first_bytes << 16) | (third_byte << 8) | version
    
    return identifier

def generate_id_method7(filename, ext, index, offset, size, data, version, base_third_byte, block_sizes, first_two_bytes_list):
    """方法7: 基于第三字节递增模式"""
    # 计算第三字节的值
    # 从基础值开始，每个区块分配相同的第三字节值
    block_index = 0
    current_third_byte = base_third_byte
    current_index = 0
    
    for block_size in block_sizes:
        if current_index + block_size > index:
            # 当前索引在这个区块中
            break
        current_index += block_size
        current_third_byte += 1
        block_index += 1
    
    # 前两个字节直接使用原始值列表中的值
    first_two_bytes = None
    for idx, bytes_value in first_two_bytes_list:
        if idx == index:
            first_two_bytes = bytes_value
            break
    
    if first_two_bytes is None:
        # 如果找不到匹配的索引，则使用文件名哈希
        first_two_bytes = binascii.crc32(filename.encode()) & 0xFFFF
    
    # 组合成完整的标识符
    identifier = (first_two_bytes << 16) | (current_third_byte << 8) | version
    
    return identifier

def main():
    parser = argparse.ArgumentParser(description='res文件标识符验证工具')
    parser.add_argument('res_file', help='要分析的res文件路径')
    
    args = parser.parse_args()
    
    entries, data_start = extract_entries(args.res_file)
    if entries:
        try_regenerate_identifiers(entries, args.res_file)

if __name__ == '__main__':
    main() 