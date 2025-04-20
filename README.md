# 遥控器资源文件（res）分析工具

本项目是对遥控器资源文件（res）格式的分析和相关工具的实现。

## 文件格式分析

详细的格式分析可在 [res文件格式分析报告_修正版.md](res文件格式分析报告_修正版.md) 查看。

res文件是一种资源打包文件，结构如下：
- 前4字节：条目数量（大端序）
- 接下来每条目44字节，包含文件名、大小和偏移量等信息
- 数据区存储实际文件内容

**注意**：在分析的`sys/sound_1_vbc2_en/res`文件中，声明有35个条目，但其中2个条目（beep_1.au和beep_2.au）实际上不存在，数据区中只存储了33个实际的WAV文件。

## 提供的工具

1. **find_wav_files.py** - 原始分析脚本，输出CSV文件
   - 生成wav_files.csv：所有WAV文件的起点、大小和终点
   - 生成entry_analysis.csv：44字节条目与WAV文件的对应关系分析

2. **res文件分析修正.py** - 修正后的分析脚本，排除不存在的文件
   - 生成corrected_analysis.csv：所有实际存在文件的详细信息

3. **extract_wav_files.py** - 原始提取工具
   - 会尝试提取所有35个条目对应的文件（包括不存在的文件）

4. **extract_wav_files_corrected.py** - 修正后的提取工具
   - 排除beep_1.au和beep_2.au这两个不存在的文件
   - 使用方法：`python3 extract_wav_files_corrected.py <res文件路径> [输出目录]`
   - 示例：`python3 extract_wav_files_corrected.py sys/sound_1_vbc2_en/res extracted_wav`

## 条目结构

每个44字节条目的结构：
1. **字节0-27**：文件名（ASCII字符串，空字节填充）
2. **字节28-31**（4字节）：保留字段（通常为0）
3. **字节32-35**（4字节）：文件大小（字节）
4. **字节36-39**（4字节）：累积偏移量（相对于数据区起始位置）
5. **字节40-43**（4字节）：可能的校验和或标识符

## 特殊情况处理

在处理res文件时，需要特别注意：
- 条目表中可能存在指向不存在文件的条目
- 需要根据文件名或其他特征识别并跳过这些条目
- 我们的分析表明，排除这些不存在的文件后，条目表中的信息与实际文件的位置完全匹配

## 使用示例

```bash
# 运行修正后的分析脚本
python3 res文件分析修正.py

# 使用修正后的提取工具提取文件
python3 extract_wav_files_corrected.py sys/sound_1_vbc2_en/res extracted_wav

# 检查提取出的文件
ls -la extracted_wav
```

提取出的文件为标准WAV格式，可以使用任何音频播放器播放。 