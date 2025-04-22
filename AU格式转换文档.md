# AU音频文件转换文档

本文档介绍项目中特殊.au格式音频文件的分析、转换和处理方法。

## 1. 文件格式分析

通过对.au文件二进制内容分析，得出以下结论：

- 这些.au文件使用类似IMA ADPCM的压缩编码方式
- 采样率为22.05kHz
- 文件头长度为16字节
- 每个.au文件包含不同的音频内容，如数字、词汇等
- 音频内容为单声道
- 这些文件与Sun公司的AU格式没有任何关系，仅使用相同的扩展名

## 2. 转换工具

项目包含以下Python脚本用于处理.au格式：

### 2.1 au2wav.py

将.au文件转换为标准WAV格式。

**用法：**
```
python au2wav.py 输入文件.au 输出文件.wav [采样率]
```

**参数说明：**
- `输入文件.au`：源.au文件路径
- `输出文件.wav`：目标WAV文件路径
- `采样率`：可选参数，默认为8000Hz，但实际应使用22050Hz

**示例：**
```
python au2wav.py resUnpack/voice_01_vbc2_en/on.au on.wav 22050
```

### 2.2 wav2au.py

将WAV文件转换回特殊.au格式。

**用法：**
```
python wav2au.py 输入文件.wav 输出文件.au [原始AU文件]
```

**参数说明：**
- `输入文件.wav`：源WAV文件路径
- `输出文件.au`：目标.au文件路径
- `原始AU文件`：可选参数，用于提取原始文件头

**示例：**
```
python wav2au.py edited_on.wav new_on.au resUnpack/voice_01_vbc2_en/on.au
```

### 2.3 convert_all_au.py

批量转换所有.au文件为WAV格式，并记录文件头信息。

**用法：**
```
python convert_all_au.py
```

**功能：**
- 处理`resUnpack`目录下所有.au文件
- 保持目录结构，输出到`auConvert`目录
- 记录每个文件头的十六进制表示
- 在每个目录下生成`file_headers.csv`文件记录文件头信息

### 2.4 convert_wav_to_au.py

批量将WAV文件转换回.au格式，使用原始文件头。

**用法：**
```
python convert_wav_to_au.py
```

**功能：**
- 处理`auConvert`目录下所有WAV文件
- 使用原始文件头重建.au文件
- 输出到`auConverted`目录，保持目录结构

## 3. 转换流程

### 3.1 提取和转换

1. 从res文件中提取.au文件到resUnpack目录
2. 运行`convert_all_au.py`批量转换为WAV格式：
   ```
   python convert_all_au.py
   ```
3. 在`auConvert`目录中找到生成的WAV文件

### 3.2 编辑音频

1. 使用标准音频编辑软件（如Audacity）编辑WAV文件
2. 保存编辑后的WAV文件，确保：
   - 保持22.05kHz采样率
   - 保持16位深度
   - 保持单声道格式

### 3.3 转换回.au格式

1. 运行`convert_wav_to_au.py`批量转换WAV为.au：
   ```
   python convert_wav_to_au.py
   ```
2. 在`auConverted`目录中找到生成的.au文件
3. 将.au文件复制回目标位置

## 4. 创建新的音频

如果需要创建全新的音频文件：

1. 使用录音软件录制新音频，确保：
   - 22.05kHz采样率
   - 16位深度
   - 单声道格式
2. 保存为WAV格式
3. 使用现有类似内容的.au文件作为模板：
   ```
   python wav2au.py 新录制的音频.wav 新的文件.au 现有类似内容的文件.au
   ```

## 5. 注意事项

- 原始.au文件的文件头对于正确播放非常重要
- 转换回.au文件时尽量使用原始文件头
- 修改音频内容时应保持音频时长与原始相近
- 新创建的音频文件需要适当的文件头才能正常工作
- 对于没有原始文件头的新录制音频，可使用类似内容文件的文件头
- 部分特殊音频文件可能有其他数据结构要求，需特别注意

## 6. 文件头信息

在每个子目录的`file_headers.csv`文件中，记录了所有原始.au文件的文件头十六进制表示。请在需要时参考这些信息。 