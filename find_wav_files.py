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
    
    entries.append({
        'index': i,
        'filename': filename,
        'raw_values': values,
        'entry_offset': offset
    })
    
    offset += 44

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

# 将结果输出为CSV
with open('wav_files.csv', 'w', newline='') as csvfile:
    fieldnames = ['序号', '起点', '大小', '终点']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    for i, riff in enumerate(riff_positions):
        writer.writerow({
            '序号': i+1,
            '起点': riff['start'],
            '大小': riff['size'],
            '终点': riff['end']
        })

print("CSV文件已创建: wav_files.csv")

# 根据分析的结果，尝试确定条目结构和文件偏移量的精确关系
print("\n分析44字节条目的准确结构:")

# 创建一个比较详细的CSV文件
with open('entry_analysis.csv', 'w', newline='') as csvfile:
    fieldnames = ['序号', '文件名', 'value1', 'value2(文件大小)', 'value3(累积偏移量)', 'value4', '计算出的起点', '实际起点', '差异']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    
    cumulative_offset = 0
    for i, entry in enumerate(entries):
        # 寻找匹配的RIFF块
        matching_riff = None
        for riff in riff_positions:
            # 根据分析，values[1]应该是文件大小，values[2]应该与偏移量相关
            if abs(entry['raw_values'][1] - riff['size']) < 10:  # 允许少量误差
                if matching_riff is None or abs(entry['raw_values'][2] - cumulative_offset) < abs(entry['raw_values'][2] - matching_riff['start']):
                    matching_riff = riff
        
        if matching_riff:
            # 计算文件的起始位置，假设values[2]是截至当前文件的累积偏移量
            calculated_start = data_start + entry['raw_values'][2]
            
            writer.writerow({
                '序号': i+1,
                '文件名': entry['filename'],
                'value1': entry['raw_values'][0],
                'value2(文件大小)': entry['raw_values'][1],
                'value3(累积偏移量)': entry['raw_values'][2],
                'value4': entry['raw_values'][3],
                '计算出的起点': calculated_start,
                '实际起点': matching_riff['start'],
                '差异': calculated_start - matching_riff['start']
            })
            
            print(f"条目 {i+1}: {entry['filename']}")
            print(f"  值1: {entry['raw_values'][0]} (可能是标志位或未使用)")
            print(f"  值2: {entry['raw_values'][1]} (文件大小: {matching_riff['size']}字节)")
            print(f"  值3: {entry['raw_values'][2]} (累积偏移量，相对于数据区)")
            print(f"  值4: {entry['raw_values'][3]} (可能是校验值或其他标识)")
            print(f"  计算出的起点: {calculated_start} (0x{calculated_start:X})")
            print(f"  实际文件起点: {matching_riff['start']} (0x{matching_riff['start']:X})")
            print(f"  差异: {calculated_start - matching_riff['start']}")
            
            cumulative_offset = entry['raw_values'][2] + entry['raw_values'][1]
        else:
            print(f"条目 {i+1}: {entry['filename']} - 未找到匹配的RIFF块")

print("\n条目结构分析完成，详细结果已保存到entry_analysis.csv") 