#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
res文件解包工具 - 修正版本

本工具可以解析并提取任意res文件中的内容。
不对文件内容进行任何格式识别，直接基于条目表中的位置信息提取文件。

用法: python3 res_unpacker_revised.py <res文件路径> [输出目录] [--list]

选项:
  --list     仅列出文件信息，不提取
  --verbose  显示详细信息
"""
import struct
import os
import sys
import argparse

def extract_filename(data):
    """从字节数据中提取文件名（空字节终止的字符串）"""
    filename = ""
    for b in data:
        if b == 0:
            break
        filename += chr(b)
    return filename

def analyze_res_file(res_file_path, verbose=False):
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
        
        if verbose:
            print(f"文件大小: {len(data)} 字节")
            print(f"条目数量: {entry_count}")
            print(f"数据区起始位置: {data_start} (0x{data_start:X})")
        
        # 解析条目表
        offset = 4  # 跳过文件头4字节
        for i in range(entry_count):
            if offset + 44 > len(data):
                if verbose:
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
                if verbose:
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
        print(f"错误: 无法分析res文件: {e}")
        return None, result

def extract_files_from_res(res_file_path, output_dir="extracted", list_only=False, verbose=False):
    """
    从res文件中提取所有文件，无需进行文件类型验证
    
    参数:
        res_file_path: res文件路径
        output_dir: 输出目录
        list_only: 如果为True，仅列出文件而不提取
        verbose: 如果为True，打印详细信息
    """
    # 分析res文件
    data, result = analyze_res_file(res_file_path, verbose)
    if data is None:
        return False
    
    entries = result['entries']
    data_start = result['data_start']
    
    # 打印条目信息
    print(f"\nres文件: {res_file_path}")
    print(f"条目数量: {result['entry_count']}")
    print(f"有效条目: {sum(1 for e in entries if e['is_valid'])}")
    print(f"数据区起始位置: {data_start} (0x{data_start:X})")
    print("\n{:<5} {:<30} {:<10} {:<15} {:<15}".format(
        "序号", "文件名", "大小(字节)", "偏移量", "状态"))
    print("-" * 80)
    
    # 检查偏移量的连续性
    expected_offset = 0
    for entry in entries:
        status = ""
        
        if not entry['is_valid']:
            status = "无效(超出范围)"
        else:
            # 验证偏移量的连续性
            if entry['offset_in_data'] != expected_offset:
                status = f"偏移量不连续(期望:{expected_offset})"
            else:
                status = "有效"
        
        print("{:<5} {:<30} {:<10} {:<15} {:<15}".format(
            entry['index'],
            entry['filename'],
            entry['file_size'],
            entry['offset_in_data'],
            status
        ))
        
        expected_offset = entry['offset_in_data'] + entry['file_size']
    
    # 如果仅列出文件，到此结束
    if list_only:
        return True
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 提取文件
    print(f"\n正在提取文件到 {output_dir}...")
    
    extracted_count = 0
    skipped_count = 0
    error_count = 0
    
    for entry in entries:
        # 跳过无效条目
        if not entry['is_valid']:
            print(f"跳过: {entry['filename']} (条目无效，超出文件范围)")
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
                
                print(f"已提取: {entry['filename']} ({file_size} 字节)")
                extracted_count += 1
            except Exception as e:
                print(f"错误: 无法保存 {entry['filename']}: {e}")
                error_count += 1
        else:
            print(f"错误: {entry['filename']} 超出文件范围")
            error_count += 1
    
    print(f"\n提取完成! 共提取了 {extracted_count} 个文件，跳过 {skipped_count} 个文件，错误 {error_count} 个。")
    return True

def main():
    parser = argparse.ArgumentParser(description='res文件解包工具 - 修正版本')
    parser.add_argument('res_file', help='res文件路径')
    parser.add_argument('output_dir', nargs='?', default='extracted_res', help='输出目录')
    parser.add_argument('--list', action='store_true', help='仅列出文件，不提取')
    parser.add_argument('--verbose', '-v', action='store_true', help='打印详细信息')
    
    args = parser.parse_args()
    
    extract_files_from_res(
        args.res_file,
        args.output_dir,
        args.list,
        args.verbose
    )

if __name__ == "__main__":
    main() 