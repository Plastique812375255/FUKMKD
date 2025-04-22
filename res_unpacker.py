#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
res文件解包工具 - 通用版本

本工具可以解析并提取任意res文件中的内容。
用法: python3 res_unpacker.py <res文件路径> [输出目录] [--list] [--ignore-missing]

选项:
  --list            仅列出文件信息，不提取
  --ignore-missing  忽略不存在的文件（仅提取有效文件）
  --all             提取所有文件，包括可能不存在的文件
"""
import struct
import os
import sys
import argparse
import binascii

def print_hex_dump(data, offset=0, length=16):
    """以16进制格式打印数据"""
    if not data:
        return

    result = []
    for i in range(0, len(data), length):
        chunk = data[i:i+length]
        hex_str = ' '.join(f"{b:02x}" for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        result.append(f"{offset+i:08x}  {hex_str:<{length*3}}  |{ascii_str}|")
    return '\n'.join(result)

def extract_filename(data):
    """从字节数据中提取文件名（空字节终止的字符串）"""
    filename = ""
    for b in data:
        if b == 0:
            break
        filename += chr(b)
    return filename

def detect_file_type(data):
    """尝试检测文件类型"""
    if not data:
        return "空文件"
    
    # 检查常见的文件魔数
    if data.startswith(b'RIFF'):
        try:
            if data[8:12] == b'WAVE':
                return "WAV 音频文件"
            return "RIFF 文件"
        except:
            return "RIFF 文件 (不完整)"
    elif data.startswith(b'\xff\xd8'):
        return "JPEG 图像"
    elif data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "PNG 图像"
    elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return "GIF 图像"
    elif data.startswith(b'.snd'):
        return "AU 音频文件"
    
    # 如果无法通过魔数识别，尝试通过内容猜测
    try:
        # 检查是否为文本文件
        if all(32 <= b <= 126 or b in (9, 10, 13) for b in data[:min(32, len(data))]):
            return "文本文件"
    except:
        pass
    
    # 计算熵值来判断是否为压缩或加密数据
    entropy = 0
    byte_counts = {}
    for b in data[:1024]:  # 使用前1024字节计算
        byte_counts[b] = byte_counts.get(b, 0) + 1
    
    for count in byte_counts.values():
        prob = count / min(1024, len(data))
        entropy -= prob * (prob.bit_length() or 1)
    
    if entropy > 7.5:
        return "压缩或加密数据"
    
    return "未知格式"

def is_file_valid(file_offset, file_size, data):
    """
    检查文件是否有效
    通常文件应该有一些可识别的头部或内容
    """
    if file_size <= 0:
        return False
    
    try:
        file_data = data[file_offset:file_offset+min(64, file_size)]
        # 检查数据是否全为0或全为同一字节
        if len(set(file_data)) <= 1:
            return False
        
        # 简单检查是否有常见文件头
        if any(file_data.startswith(header) for header in 
              [b'RIFF', b'\xff\xd8', b'\x89PNG', b'GIF', b'.snd', b'PK']):
            return True
        
        # 更复杂的检测可以在这里添加
        
        # 默认情况下，如果文件有合理大小且数据不全为同一字节，认为是有效的
        return file_size > 32 and file_size < 10*1024*1024  # 32字节至10MB
    except:
        return False

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
            
            # 检查是否为有效文件
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
                'is_valid': is_valid,
                'looks_empty': not is_file_valid(absolute_offset, file_size, data) if is_valid else True
            })
            
            offset += 44
        
        return data, result
    
    except Exception as e:
        print(f"错误: 无法分析res文件: {e}")
        return None, result

def extract_files_from_res(res_file_path, output_dir="extracted", 
                          list_only=False, ignore_missing=False, 
                          extract_all=False, verbose=False):
    """
    从res文件中提取所有文件
    
    参数:
        res_file_path: res文件路径
        output_dir: 输出目录
        list_only: 如果为True，仅列出文件而不提取
        ignore_missing: 如果为True，跳过看起来不存在的文件
        extract_all: 如果为True，提取所有文件，包括可能不存在的文件
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
    print(f"可能空文件: {sum(1 for e in entries if e['is_valid'] and e['looks_empty'])}")
    print(f"数据区起始位置: {data_start} (0x{data_start:X})")
    print("\n{:<5} {:<30} {:<10} {:<10} {:<10} {:<20}".format(
        "序号", "文件名", "大小(字节)", "偏移量", "状态", "可能的文件类型"))
    print("-" * 90)
    
    # 计算偏移量的期望值，用于验证文件的连续性
    expected_offset = 0
    for entry in entries:
        status = ""
        file_type = ""
        
        if not entry['is_valid']:
            status = "无效(超出范围)"
        elif entry['looks_empty']:
            status = "可能为空"
        else:
            # 提取数据判断文件类型
            file_data = data[entry['absolute_offset']:entry['absolute_offset']+min(64, entry['file_size'])]
            file_type = detect_file_type(file_data)
            
            # 验证偏移量的连续性
            if entry['offset_in_data'] != expected_offset:
                status = f"偏移量不连续(期望:{expected_offset})"
            else:
                status = "有效"
        
        print("{:<5} {:<30} {:<10} {:<10} {:<10} {:<20}".format(
            entry['index'],
            entry['filename'],
            entry['file_size'],
            entry['offset_in_data'],
            status,
            file_type
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
        
        # 跳过空文件（如果指定）
        if ignore_missing and entry['looks_empty']:
            print(f"跳过: {entry['filename']} (看起来是空文件)")
            skipped_count += 1
            continue
        
        # 提取文件内容
        file_start = entry['absolute_offset']
        file_size = entry['file_size']
        file_end = file_start + file_size
        
        # 确保不超出文件范围
        if file_end <= len(data):
            file_data = data[file_start:file_end]
            
            # 检查文件是否为空或全0
            if not extract_all and all(b == 0 for b in file_data[:min(32, len(file_data))]):
                print(f"跳过: {entry['filename']} (文件内容全为0)")
                skipped_count += 1
                continue
            
            # 保存到输出目录
            output_path = os.path.join(output_dir, entry['filename'])
            
            # 确保目录存在（处理文件名中可能包含的路径）
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            try:
                with open(output_path, 'wb') as out_file:
                    out_file.write(file_data)
                
                file_type = detect_file_type(file_data[:64])
                print(f"已提取: {entry['filename']} ({file_size} 字节, {file_type})")
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
    parser = argparse.ArgumentParser(description='res文件解包工具')
    parser.add_argument('res_file', help='res文件路径')
    parser.add_argument('output_dir', nargs='?', default='extracted', help='输出目录')
    parser.add_argument('--list', action='store_true', help='仅列出文件，不提取')
    parser.add_argument('--ignore-missing', action='store_true', help='忽略不存在的文件')
    parser.add_argument('--all', action='store_true', help='提取所有文件，包括可能不存在的文件')
    parser.add_argument('--verbose', '-v', action='store_true', help='打印详细信息')
    
    args = parser.parse_args()
    
    extract_files_from_res(
        args.res_file,
        args.output_dir,
        args.list,
        args.ignore_missing,
        args.all,
        args.verbose
    )

if __name__ == "__main__":
    main() 