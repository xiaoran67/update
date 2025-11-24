import requests  
import os  
import time  
import re  
from collections import defaultdict  
  
# 合并后的函数，接受URL列表，下载M3U文件，提取并处理频道信息  
def fetch_m3u_channels_and_save(urls, output_file_path):  
    all_channels = defaultdict(list)  # 用于存储所有提取的频道信息，按分组组织  
  
    for url in urls:  
        try:  
            # 下载M3U文件（这里为了简化，不直接保存到磁盘，而是读取内容到内存中）  
            response = requests.get(url, timeout=15)  
            response.raise_for_status()  # 确保请求成功  
  
            m3u_content = response.text  
            lines = m3u_content.splitlines()  
  
            # 提取当前M3U文件中的频道信息  
            for i in range(len(lines)):  
                line = lines[i].strip()  
                if line.startswith('#EXTINF:-1'):  
                    # 提取分组信息  
                    group_match = re.search(r'group-title="([^"]*)"', line)  
                    group = group_match.group(1) if group_match else "未分组"  
  
                    # 提取频道名称  
                    name_match = re.search(r'tvg-name="([^"]*)"', line)  
                    name = name_match.group(1) if name_match else line.split(',')[-1].split(' - ')[0].strip()  
  
                    # 获取URL（假设URL在下一行）  
                    url = lines[i + 1].strip() if i + 1 < len(lines) and lines[i + 1].startswith(('http://', 'https://')) else ""  
  
                    # 添加到频道列表中  
                    if url:  
                        all_channels[group].append((name, url))  
  
        except requests.exceptions.Timeout:  
            print(f"Request to {url} timed out.")  
        except requests.exceptions.RequestException as e:  
            print(f"An error occurred while requesting {url}: {e}")  
  
    # 输出到文件  
    with open(output_file_path, "w", encoding="utf-8") as output_file:  
        for group_title, channels_in_group in all_channels.items():  
            if group_title:  
                output_file.write(f"{group_title},#genre#\n")  
            for name, url in channels_in_group:  
                output_file.write(f"{name},{url}\n")  
  
    print(f"提取完成,结果已保存到 {output_file_path}")  
  
if __name__ == "__main__":  
    # 定义多个M3U文件的URL  
    urls = [  
        'https://raw.githubusercontent.com/torysuper/IPTV-P/refs/heads/Files/Adult.m3u',
    ]  
  
    # 指定输出文件的名称  
    output_file_path = "TMP/TMP.txt"  
  
    # 确保输出目录存在  
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)  
  
    # 调用函数从M3U URLs获取内容，提取频道信息，并保存到TXT文件  
    fetch_m3u_channels_and_save(urls, output_file_path)
