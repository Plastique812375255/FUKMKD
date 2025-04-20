#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正res文件分析，排除不存在的beep_1.au和beep_2.au文件
"""
import struct
import os
import csv

# 读取res文件
with open('sys/sound_1_vbc2_en/res', 'rb') as f:
    data = f.read()

# 读取条目数量
num_entries = struct.unpack('>I', data[:4])[0]
print(f"文件中声明的条目数量: {num_entries}")

# 分析44字节的条目结构
entries = []
offset = 4  # 跳过条目数量的4个字节
for i in range(num_entries):
    entry_data = data[offset:offset+44]
    
    # 尝试提取文件名（空字节终止的字符串）
    filename = ""
    for j in range(28):  # 假设文件名最多28字节
        if entry_data[j] == 0:
            break
        filename += chr(entry_data[j])
    
    # 提取后面的字节，这些可能包含偏移量和大小信息
    values = struct.unpack('>IIII', entry_data[28:44])
    
    # 排除beep_1.au和beep_2.au这两个不存在的文件
    if filename not in ["beep_1.au", "beep_2.au"]:
        entries.append({
            'index': len(entries),
            'original_index': i,
            'filename': filename,
            'raw_values': values,
            'entry_offset': offset
        })
    else:
        print(f"跳过不存在的文件: {filename} (条目索引: {i+1})")
    
    offset += 44

print(f"排除不存在文件后的条目数量: {len(entries)}")

# 数据区开始的偏移量
data_start = 4 + num_entries * 44
print(f"数据区开始的偏移量: {data_start} (0x{data_start:X})")

# 查找所有RIFF魔数头
riff_positions = []
pos = 0
while True:
    pos = data.find(b'RIFF', pos)
    if pos == -1:
        break
    # 提取RIFF块大小（RIFF后面的4个字节，小端序）
    chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
    total_size = chunk_size + 8  # 加上RIFF和大小字段本身的8个字节
    
    riff_positions.append({
        'start': pos,
        'size': total_size,
        'end': pos + total_size
    })
    
    pos += 1

print(f"找到的RIFF块数量: {len(riff_positions)}")

# 验证条目数量与RIFF块数量是否匹配
print(f"条目数量 ({len(entries)}) {'匹配' if len(entries) == len(riff_positions) else '不匹配'} RIFF块数量 ({len(riff_positions)})")

# 创建一个比较详细的CSV文件
with open('corrected_analysis.csv', 'w', newline='') as csvfile:
    fieldnames = ['序号', '原始索引', '文件名', 'value1', 'value2(文件大小)', 'value3(偏移量)', 'value4', 
                 '计算出的起点', 'RIFF实际起点', '大小匹配', '偏移匹配']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    
    # 按顺序匹配条目和RIFF块
    for i, (entry, riff) in enumerate(zip(entries, riff_positions)):
        # 计算文件的起始位置
        calculated_start = data_start + entry['raw_values'][2]
        
        # 检查大小是否匹配
        size_matches = abs(entry['raw_values'][1] - riff['size']) < 10  # 允许小误差
        
        # 检查偏移量是否匹配
        offset_matches = abs(calculated_start - riff['start']) < 10  # 允许小误差
        
        writer.writerow({
            '序号': i+1,
            '原始索引': entry['original_index']+1,
            '文件名': entry['filename'],
            'value1': entry['raw_values'][0],
            'value2(文件大小)': entry['raw_values'][1],
            'value3(偏移量)': entry['raw_values'][2],
            'value4': entry['raw_values'][3],
            '计算出的起点': calculated_start,
            'RIFF实际起点': riff['start'],
            '大小匹配': "是" if size_matches else "否",
            '偏移匹配': "是" if offset_matches else "否"
        })
        
        print(f"条目 {i+1} (原始索引: {entry['original_index']+1}): {entry['filename']}")
        print(f"  值1: {entry['raw_values'][0]} (可能是标志位或未使用)")
        print(f"  值2: {entry['raw_values'][1]} (文件大小: {riff['size']}字节, {'匹配' if size_matches else '不匹配'})")
        print(f"  值3: {entry['raw_values'][2]} (偏移量，相对于数据区)")
        print(f"  值4: {entry['raw_values'][3]} (可能是校验值或其他标识)")
        print(f"  计算出的起点: {calculated_start} (0x{calculated_start:X})")
        print(f"  实际RIFF起点: {riff['start']} (0x{riff['start']:X}) {'匹配' if offset_matches else '不匹配'}")
        print(f"  差异: {calculated_start - riff['start']}")

print("\n修正分析完成，详细结果已保存到corrected_analysis.csv") 