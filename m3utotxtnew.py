import requests
import os
from collections import defaultdict
import re

# 文件 URL 列表
urls = [
    'https://gh.tryxd.cn/https://raw.githubusercontent.com/clion007/livetv/refs/heads/main/m3u/scu.m3u',
    'https://gh.tryxd.cn/https://raw.githubusercontent.com/fanmingming/live/refs/heads/main/tv/m3u/ipv6.m3u',
    'https://gh.tryxd.cn/https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u',
    'https://gh.tryxd.cn/https://raw.githubusercontent.com/suxuang/myIPTV/main/ipv6.m3u',
    'https://7220.kstore.space/sxrtv.txt',
    'https://huangsuming.github.io/iptv/list/tvlist.txt',
    'http://gg.7749.org/z/i/gdss.txt',
]

# 初始化字典
all_channels_dict = defaultdict(list)

# 遍历 URL 列表并处理每个 m3u 文件
for url in urls:
    try:
        # 发送请求获取文件内容，添加超时设置（15秒）
        response = requests.get(url, timeout=15)
        # 检查响应状态码，非200则抛出异常
        response.raise_for_status()
        m3u_content = response.text
        print(f"成功获取 {url} 的内容")
    except requests.exceptions.RequestException as e:
        # 捕获所有请求相关异常（连接错误、超时、HTTP错误等）
        print(f"处理 URL {url} 时出错: {str(e)}")
        continue  # 跳过当前错误URL，继续处理下一个

    # 初始化频道信息
    channels = []
    group_title = ""
    channel_name = ""
    tvg_logo = ""
    tvg_id = ""

    # 提取频道信息
    for i, line in enumerate(m3u_content.splitlines()):
        line = line.strip()
        
        if line.startswith("#EXTINF:"):
            # 使用正则从 #EXTINF 行提取信息
            match = re.match(r'#EXTINF:-1.*?group-title="([^"]+)".*?tvg-name="([^"]+)".*?tvg-logo="([^"]+)"', line)
            if match:
                group_title = match.group(1)  # 提取分组信息
                channel_name = match.group(2)  # 提取频道名称
                tvg_logo = match.group(3)     # 提取频道 Logo URL
            else:
                # 备选提取方式，兼容不同格式的EXTINF行
                channel_info = line.split(",")
                if len(channel_info) > 1:
                    channel_name = channel_info[1].split(" ")[0]
                # 提取group-title
                group_title_items = [item.split("group-title=")[1].split('"')[1] 
                                   for item in channel_info if "group-title=" in item]
                group_title = group_title_items[0] if group_title_items else group_title
        elif line.startswith(("http://", "https://")):
            # 处理流媒体 URL 行
            streaming_url = line
            if channel_name and streaming_url:  # 确保频道名称和 URL 非空
                # 存储频道信息
                channels.append({
                    "channel_name": channel_name,
                    "group_title": group_title,
                    "tvg_logo": tvg_logo,
                    "streaming_url": streaming_url,
                    "line_index": i
                })
            # 清空临时数据以便下一个频道
            channel_name = ""
            group_title = ""
            tvg_logo = ""

    # 将当前文件的频道添加到总字典中
    for channel in channels:
        all_channels_dict[channel["group_title"]].append(channel)

# 确保输出目录存在
os.makedirs(os.path.dirname("TMP/TMP1.txt"), exist_ok=True)

# 输出到文件
output_file_path = "TMP/TMP1.txt"
with open(output_file_path, "w", encoding="utf-8") as output_file:
    prev_group_title = None
    for group_title, channels_in_group in all_channels_dict.items():
        # 按行索引排序，保持原文件顺序
        sorted_channels_in_group = sorted(channels_in_group, key=lambda x: x["line_index"])
        
        # 输出分组标题
        if group_title != prev_group_title:
            if prev_group_title:
                output_file.write("\n")  # 在分组间添加空行
            if group_title:
                output_file.write(f"{group_title},#genre#\n")
            prev_group_title = group_title
        
        # 输出频道信息
        for channel in sorted_channels_in_group:
            channel_name = channel["channel_name"]
            streaming_url = channel["streaming_url"]

            if channel_name and streaming_url:
                output_file.write(f"{channel_name}, {streaming_url}\n")

print(f"提取完成,结果已保存到 {output_file_path}")
