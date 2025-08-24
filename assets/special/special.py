#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
直播源自动整理工具
========================================
输入文件（存放路径：仓库根目录 → assets/special/）：
1. urls.txt       ：订阅源URL列表（空则用内置默认链接）
2. ExcludeList.txt：黑名单（过滤含指定内容的直播源，自动创建空文件）
3. rename.txt     ：名称映射规则（统一频道名，格式：目标名,待替换名1,待替换名2...）

输出文件（生成路径：仓库根目录 → output/special/）：
- live_special.txt：整理后的直播源（去重、名称标准化，格式：频道名,链接 或 纯链接）
"""

import os
import urllib.request


# 读取文本文件内容（自动过滤空行和注释行）
def read_txt_to_array(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return [
                line.strip() 
                for line in f.readlines() 
                if line.strip() and not line.startswith('#')
            ]
    except FileNotFoundError:
        print(f"提示：{file_path} 不存在，返回空列表")
        return []
    except Exception as e:
        print(f"读取{file_path}出错：{e}")
        return []


# ==================== 输入文件初始化 ====================
# 1. 黑名单文件（自动创建空文件）
exclude_file = os.path.join("assets", "special", "ExcludeList.txt")
if not os.path.exists(exclude_file):
    with open(exclude_file, 'w', encoding='utf-8') as f:
        f.write("")  # 创建空文件
    print(f"提示：{exclude_file} 不存在，已创建空文件")
excude_lines = read_txt_to_array(exclude_file)  # 加载黑名单

# 2. 订阅源列表（优先读urls.txt，空则用默认链接）
urls_file = os.path.join("assets", "special", "urls.txt")
subscribe_urls = read_txt_to_array(urls_file)
if not subscribe_urls:
    print("提示：urls.txt为空，启用内置默认订阅源")
    subscribe_urls = [
        "https://ua.fongmi.eu.org/box.php?url=http://sinopacifichk.com/tv/live",
        "https://ua.fongmi.eu.org/box.php?url=https://tv.iill.top/m3u.father",
    ]

# 3. 名称映射规则（rename.txt）
rename_file = os.path.join("assets", "special", "rename.txt")
name_mapping = {}  # 格式：{目标名: [待替换名列表]}
def load_name_mapping():
    global name_mapping
    for line in read_txt_to_array(rename_file):
        parts = [p.strip() for p in line.split(',') if p.strip()]
        if len(parts) >= 2:
            target_name = parts[0]
            replace_names = parts[1:]
            name_mapping[target_name] = replace_names
    print(f"已加载名称映射规则：共 {len(name_mapping)} 组")
load_name_mapping()


# ==================== 核心逻辑：处理订阅源 ====================
all_valid_lines = []  # 存储所有有效直播源（格式：频道名,链接 或 纯链接）

def process_m3u_content(content):
    """将M3U格式转换为标准文本格式（频道名,链接）"""
    converted = []
    current_name = ""
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith("#EXTINF"):
            current_name = line.split(',')[-1].strip()  # 提取频道名
        elif line.startswith(("http://", "https://", "rtmp://")):
            if current_name:
                converted.append(f"{current_name},{line}")
            else:
                converted.append(line)  # 无频道名则保留纯链接
    return converted

def fetch_and_process_url(url):
    """获取URL内容，解析并过滤有效直播源"""
    try:
        # 模拟浏览器请求头，避免被拦截
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=15) as res:  # 15秒超时
            content = res.read().decode('utf-8', errors='replace')  # 处理编码问题
            
            # 判断是否为M3U格式
            if content.startswith("#EXTM3U"):
                processed = process_m3u_content(content)
            else:
                processed = [line.strip() for line in content.split('\n') if line.strip()]
            
            # 过滤无效内容（黑名单、含#genre#、格式错误）
            for line in processed:
                if (line not in excude_lines) and \
                   ("#genre#" not in line) and \
                   ("," in line or "://" in line):
                    all_valid_lines.append(line)
        print(f"处理完成：{url}（累计有效条目：{len(all_valid_lines)}）")
    except Exception as e:
        print(f"处理URL失败：{url} → {str(e)[:50]}...")


# ==================== 主流程：输出整理结果 ====================
def main():
    print("=== 直播源自动整理工具启动 ===")
    
    # 1. 创建输出目录
    output_dir = os.path.join("output", "special")
    os.makedirs(output_dir, exist_ok=True)
    print(f"已确保输出目录存在：{output_dir}")
    
    # 2. 处理所有订阅源
    for url in subscribe_urls:
        if url.startswith(("http://", "https://")):  # 仅处理HTTP/HTTPS链接
            fetch_and_process_url(url)
    
    # 3. 应用名称映射规则
    processed_lines = []
    for line in all_valid_lines:
        if ',' in line:
            original_name, link = line.split(',', 1)  # 分割频道名和链接（仅分割第一个逗号）
            # 检查是否需要重命名
            renamed = False
            for target_name, replace_list in name_mapping.items():
                if original_name in replace_list:
                    processed_lines.append(f"{target_name},{link}")
                    renamed = True
                    break
            if not renamed:
                processed_lines.append(line)
        else:
            processed_lines.append(line)  # 纯链接直接保留
    
    # 4. 去重并保存结果
    unique_lines = list(set(processed_lines))  # 自动去重
    output_file = os.path.join(output_dir, "live_special.txt")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(unique_lines))
        print(f"\n=== 处理完成 ===")
        print(f"有效直播源数量：{len(unique_lines)}")
        print(f"结果已保存到：{output_file}")
    except Exception as e:
        print(f"保存文件失败：{e}")
        exit(1)


if __name__ == "__main__":
    main()
