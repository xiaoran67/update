#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ====== 直播源聚合处理工具 v1.00 ======
# ======= LiveSource-Collector =======
# ===========  基础版============
import urllib.request
from urllib.parse import urlparse
import re
import os
from datetime import datetime, timedelta, timezone
import random
import opencc

import socket
import time

# 初始化输出目录
os.makedirs('output', exist_ok=True)  # 创建输出目录，如果已存在则不会报错
print(f"创建输出目录: output")

# 繁体转简体函数
def traditional_to_simplified(text: str) -> str:
    converter = opencc.OpenCC('t2s')
    simplified_text = converter.convert(text)
    return simplified_text

# 打印版本说明
print()
print(f"=" * 31)
print(f"🐍 IPTV直播源聚合处理工具 v1.00")
print(f"📺 Live Source Collector Processing")
print(f"🔧 基于v0.00，基础版")
print(f"=" * 31)

# 记录脚本开始执行的时间
timestart = datetime.now()
print(f"\n⏰ 开始时间: {timestart.strftime('%Y%m%d %H:%M:%S')}")

# 读取文本文件内容到数组的函数
def read_txt_to_array(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
            return lines

    except FileNotFoundError:
        print(f"❌ 文件未找到: {file_name}")
        return []
    except Exception as e:
        print(f"❌ 读取文件错误 {file_name}: {e}")
        return []

# 从文本文件读取黑名单的函数
def read_blacklist_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    BlackList = [line.split(',')[1].strip() for line in lines if ',' in line]
    return BlackList

# 读取自动和手动维护的黑名单，合并为集合去重
blacklist_auto=read_blacklist_from_txt('assets/livesource/blacklist/blacklist_auto.txt') 
blacklist_manual=read_blacklist_from_txt('assets/livesource/blacklist/blacklist_manual.txt') 
combined_blacklist = set(blacklist_auto + blacklist_manual)

print(f"\n🔴 黑名单统计信息:")
print(f"   🔧 自动维护: {len(blacklist_auto)} 条")
print(f"   ✏️ 手动维护: {len(blacklist_manual)} 条")
print(f"   🔄 合并去重: {len(combined_blacklist)} 条")

# 显示前几条黑名单示例
print(f"   黑名单示例 (前3条):")
for i, url in enumerate(list(combined_blacklist)[:3]):
    print(f"     {i+1}. {url}")
if len(combined_blacklist) > 3:
    print(f"     ... 还有 {len(combined_blacklist) - 3} 条")

# ========= 频道分类存储变量定义 =========
# 初始化各种频道类别的空列表，用于存储对应频道的播放源信息

yangshi_lines = []      # 存储央视频道数据
weishi_lines = []       # 存储卫视频道数据

beijing_lines = []      # 北京
shanghai_lines = []     # 上海
guangdong_lines = []    # 广东
jiangsu_lines = []      # 江苏
zhejiang_lines = []     # 浙江
shandong_lines = []     # 山东
sichuan_lines = []      # 四川
henan_lines = []        # 河南
hunan_lines = []        # 湖南
chongqing_lines = []    # 重庆
tianjin_lines = []      # 天津
hubei_lines = []        # 湖北
anhui_lines = []        # 安徽
fujian_lines = []       # 福建
liaoning_lines = []     # 辽宁
shaanxi_lines = []      # 陕西
hebei_lines = []        # 河北
jiangxi_lines = []      # 江西
guangxi_lines = []      # 广西
yunnan_lines = []       # 云南
shanxi_lines = []       # 山西
heilongjiang_lines = [] # 黑龙江
jilin_lines = []        # 吉林
guizhou_lines = []      # 贵州
gansu_lines = []        # 甘肃
neimenggu_lines = []    # 内蒙古
xinjiang_lines = []     # 新疆
hainan_lines = []       # 海南
ningxia_lines = []      # 宁夏
qinghai_lines = []      # 青海
xizang_lines = []       # 西藏

hongkong_lines = []   # 香港
macau_lines = []      # 澳门
taiwan_lines = []      # 台湾

digital_lines = []     # 数字
movie_lines = []       # 电影
tv_drama_lines = []    # 电视剧
documentary_lines = [] # 纪录片
cartoon_lines = []     # 动画片
radio_lines = []       # 收音机
variety_lines = []     # 综艺
huya_lines = []        # 虎牙
douyu_lines = []       # 斗鱼
commentary_lines = []  # 解说
music_lines = []       # 音乐
food_lines = []        # 美食
travel_lines = []      # 旅游
health_lines = []      # 健康
finance_lines = []     # 财经
shopping_lines = []    # 购物
game_lines = []        # 游戏
news_lines = []        # 新闻
china_lines = []       # 中国
international_lines = [] # 国际
sports_lines = []      # 体育
tyss_lines = []        # 体育赛事
mgss_lines = []        # 咪咕赛事
traditional_opera_lines = [] # 戏曲频道
spring_festival_gala_lines = [] # 历届春晚
camera_lines = []      # 景区直播
favorite_lines = []    # 收藏频道

other_lines = []       # 其他未分类频道
other_lines_url = []    # 其他频道的URL列表

# 处理频道名称字符串的函数（主要用于处理CCTV频道名）
def process_name_string(input_str):
    parts = input_str.split(',')
    processed_parts = []
    for part in parts:
        processed_part = process_part(part)
        processed_parts.append(processed_part)
    result_str = ','.join(processed_parts)
    return result_str

# 处理单个频道名称部分的函数
def process_part(part_str):
    if "CCTV" in part_str  and "://" not in part_str:
        part_str=part_str.replace("IPV6", "")
        part_str=part_str.replace("PLUS", "+")
        part_str=part_str.replace("1080", "")
        filtered_str = ''.join(char for char in part_str if char.isdigit() or char == 'K' or char == '+')
        if not filtered_str.strip():
            filtered_str=part_str.replace("CCTV", "")
        if len(filtered_str) > 2 and re.search(r'4K|8K', filtered_str):
            filtered_str = re.sub(r'(4K|8K).*', r'\1', filtered_str)
            if len(filtered_str) > 2: 
                filtered_str = re.sub(r'(4K|8K)', r'(\1)', filtered_str)
        return "CCTV"+filtered_str
    elif "卫视" in part_str:
        pattern = r'卫视「.*」'
        result_str = re.sub(pattern, '卫视', part_str)
        return result_str
    return part_str

# 获取URL文件扩展名的函数
def get_url_file_extension(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    extension = os.path.splitext(path)[1]
    return extension

# 将M3U格式转换为TXT格式的函数
def convert_m3u_to_txt(m3u_content):
    lines = m3u_content.split('\n')
    txt_lines = []
    channel_name = ""
    for line in lines:
        if line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            channel_name = line.split(',')[-1].strip()
        elif line.startswith("http") or line.startswith("rtmp") or line.startswith("p3p") :
            txt_lines.append(f"{channel_name},{line.strip()}")
        if "#genre#" not in line and "," in line and "://" in line:
            pattern = r'^[^,]+,[^\s]+://[^\s]+$'
            if bool(re.match(pattern, line)):
                txt_lines.append(line)
    return '\n'.join(txt_lines)

# 检查URL是否已存在的函数
def check_url_existence(data_list, url):
    urls = [item.split(',')[1] for item in data_list]
    return url not in urls

# 清理URL的函数（移除$后的参数）
def clean_url(url):
    last_dollar_index = url.rfind('$')
    if last_dollar_index != -1:
        return url[:last_dollar_index]
    return url

# 需要从频道名称中移除的字符串列表
removal_list = ["_电信","电信","频道","频陆","备陆","壹陆","贰陆","叁陆","肆陆","伍陆","陆陆","柒陆",
    "肆柒","频英","频特","频国","频晴","频粤","高清","超清","标清","斯特","粤陆","国陆","频壹","频贰",
    "肆贰","频测","咪咕","闽特","高特","频高","频标","汝阳","频效","国标","粤标","频推","频流","粤高",
    "频限","实时","美推","频美","英陆","(北美)","「回看」","[超清]","「IPV4」","「IPV6」","_ITV","(HK)",
    "AKtv","HD","[HD]","(HD)","（HD）","{HD}","<HD>","-HD","[BD]","SD","[SD]","(SD)","{SD}", "<SD>",
    "[VGA]","4Gtv","1080","720","480","VGA","4K","(4K)","{4K}","<4K>","(VGA)","{VGA}","<VGA>",
    "「4gTV」","「LiTV」"]

# 清理频道名称的函数
def clean_channel_name(channel_name, removal_list):
    for item in removal_list:
        channel_name = channel_name.replace(item, "")
    if channel_name.endswith("HD"):
        channel_name = channel_name[:-2]
    if channel_name.endswith("台") and len(channel_name) > 3:
        channel_name = channel_name[:-1]
    return channel_name

# 处理单行频道信息的函数
def process_channel_line(line):
    if "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
        channel_name = line.split(',')[0].strip()
        channel_name = clean_channel_name(channel_name, removal_list)
        channel_name = traditional_to_simplified(channel_name)
        channel_address = clean_url(line.split(',')[1].strip())
        line = channel_name + "," + channel_address
        if channel_address not in combined_blacklist:
            # 央视
            if "CCTV" in channel_name and check_url_existence(yangshi_lines, channel_address):
                yangshi_lines.append(process_name_string(line.strip()))
            # 卫视
            elif channel_name in weishi_dictionary and check_url_existence(weishi_lines, channel_address):
                weishi_lines.append(process_name_string(line.strip()))
            # 北京
            elif channel_name in beijing_dictionary and check_url_existence(beijing_lines, channel_address):
                beijing_lines.append(process_name_string(line.strip()))
            # 上海
            elif channel_name in shanghai_dictionary and check_url_existence(shanghai_lines, channel_address):
                shanghai_lines.append(process_name_string(line.strip()))
            # 广东
            elif channel_name in guangdong_dictionary and check_url_existence(guangdong_lines, channel_address):
                guangdong_lines.append(process_name_string(line.strip()))
            # 江苏
            elif channel_name in jiangsu_dictionary and check_url_existence(jiangsu_lines, channel_address):
                jiangsu_lines.append(process_name_string(line.strip()))
            # 浙江
            elif channel_name in zhejiang_dictionary and check_url_existence(zhejiang_lines, channel_address):
                zhejiang_lines.append(process_name_string(line.strip()))
            # 山东
            elif channel_name in shandong_dictionary and check_url_existence(shandong_lines, channel_address):
                shandong_lines.append(process_name_string(line.strip()))
            # 四川
            elif channel_name in sichuan_dictionary and check_url_existence(sichuan_lines, channel_address):
                sichuan_lines.append(process_name_string(line.strip()))
            # 河南
            elif channel_name in henan_dictionary and check_url_existence(henan_lines, channel_address):
                henan_lines.append(process_name_string(line.strip()))
            # 湖南
            elif channel_name in hunan_dictionary and check_url_existence(hunan_lines, channel_address):
                hunan_lines.append(process_name_string(line.strip()))
            # 重庆
            elif channel_name in chongqing_dictionary and check_url_existence(chongqing_lines, channel_address):
                chongqing_lines.append(process_name_string(line.strip()))
            # 天津
            elif channel_name in tianjin_dictionary and check_url_existence(tianjin_lines, channel_address):
                tianjin_lines.append(process_name_string(line.strip()))
            # 湖北
            elif channel_name in hubei_dictionary and check_url_existence(hubei_lines, channel_address):
                hubei_lines.append(process_name_string(line.strip()))
            # 安徽
            elif channel_name in anhui_dictionary and check_url_existence(anhui_lines, channel_address):
                anhui_lines.append(process_name_string(line.strip()))
            # 福建
            elif channel_name in fujian_dictionary and check_url_existence(fujian_lines, channel_address):
                fujian_lines.append(process_name_string(line.strip()))
            # 辽宁
            elif channel_name in liaoning_dictionary and check_url_existence(liaoning_lines, channel_address):
                liaoning_lines.append(process_name_string(line.strip()))
            # 陕西
            elif channel_name in shaanxi_dictionary and check_url_existence(shaanxi_lines, channel_address):
                shaanxi_lines.append(process_name_string(line.strip()))
            # 河北
            elif channel_name in hebei_dictionary and check_url_existence(hebei_lines, channel_address):
                hebei_lines.append(process_name_string(line.strip()))
            # 江西
            elif channel_name in jiangxi_dictionary and check_url_existence(jiangxi_lines, channel_address):
                jiangxi_lines.append(process_name_string(line.strip()))
            # 广西
            elif channel_name in guangxi_dictionary and check_url_existence(guangxi_lines, channel_address):
                guangxi_lines.append(process_name_string(line.strip()))
            # 云南
            elif channel_name in yunnan_dictionary and check_url_existence(yunnan_lines, channel_address):
                yunnan_lines.append(process_name_string(line.strip()))
            # 山西
            elif channel_name in shanxi_dictionary and check_url_existence(shanxi_lines, channel_address):
                shanxi_lines.append(process_name_string(line.strip()))
            # 黑龙江
            elif channel_name in heilongjiang_dictionary and check_url_existence(heilongjiang_lines, channel_address):
                heilongjiang_lines.append(process_name_string(line.strip()))
            # 吉林
            elif channel_name in jilin_dictionary and check_url_existence(jilin_lines, channel_address):
                jilin_lines.append(process_name_string(line.strip()))
            # 贵州
            elif channel_name in guizhou_dictionary and check_url_existence(guizhou_lines, channel_address):
                guizhou_lines.append(process_name_string(line.strip()))
            # 甘肃
            elif channel_name in gansu_dictionary and check_url_existence(gansu_lines, channel_address):
                gansu_lines.append(process_name_string(line.strip()))
            # 内蒙古
            elif channel_name in neimenggu_dictionary and check_url_existence(neimenggu_lines, channel_address):
                neimenggu_lines.append(process_name_string(line.strip()))
            # 新疆
            elif channel_name in xinjiang_dictionary and check_url_existence(xinjiang_lines, channel_address):
                xinjiang_lines.append(process_name_string(line.strip()))
            # 海南
            elif channel_name in hainan_dictionary and check_url_existence(hainan_lines, channel_address):
                hainan_lines.append(process_name_string(line.strip()))
            # 宁夏
            elif channel_name in ningxia_dictionary and check_url_existence(ningxia_lines, channel_address):
                ningxia_lines.append(process_name_string(line.strip()))
            # 青海
            elif channel_name in qinghai_dictionary and check_url_existence(qinghai_lines, channel_address):
                qinghai_lines.append(process_name_string(line.strip()))
            # 西藏
            elif channel_name in xizang_dictionary and check_url_existence(xizang_lines, channel_address):
                xizang_lines.append(process_name_string(line.strip()))
            # 香港
            elif channel_name in hongkong_dictionary and check_url_existence(hongkong_lines, channel_address):
                hongkong_lines.append(process_name_string(line.strip()))
            # 澳门
            elif channel_name in macau_dictionary and check_url_existence(macau_lines, channel_address):
                macau_lines.append(process_name_string(line.strip()))
            # 台湾
            elif channel_name in taiwan_dictionary and check_url_existence(taiwan_lines, channel_address):
                taiwan_lines.append(process_name_string(line.strip()))
            # 数字
            elif channel_name in digital_dictionary and check_url_existence(digital_lines, channel_address):
                digital_lines.append(process_name_string(line.strip()))
            # 电影
            elif channel_name in movie_dictionary and check_url_existence(movie_lines, channel_address):
                movie_lines.append(process_name_string(line.strip()))
            # 电视剧
            elif channel_name in tv_drama_dictionary and check_url_existence(tv_drama_lines, channel_address):
                tv_drama_lines.append(process_name_string(line.strip()))
            # 纪录片
            elif channel_name in documentary_dictionary and check_url_existence(documentary_lines, channel_address):
                documentary_lines.append(process_name_string(line.strip()))
            # 动画片
            elif channel_name in cartoon_dictionary and check_url_existence(cartoon_lines, channel_address):
                cartoon_lines.append(process_name_string(line.strip()))
            # 收音机
            elif channel_name in radio_dictionary and check_url_existence(radio_lines, channel_address):
                radio_lines.append(process_name_string(line.strip()))
            # 综艺
            elif channel_name in variety_dictionary and check_url_existence(variety_lines, channel_address):
                variety_lines.append(process_name_string(line.strip()))
            # 虎牙
            elif channel_name in huya_dictionary and check_url_existence(huya_lines, channel_address):
                huya_lines.append(process_name_string(line.strip()))
            # 斗鱼
            elif channel_name in douyu_dictionary and check_url_existence(douyu_lines, channel_address):
                douyu_lines.append(process_name_string(line.strip()))
            # 解说
            elif channel_name in commentary_dictionary and check_url_existence(commentary_lines, channel_address):
                commentary_lines.append(process_name_string(line.strip()))
            # 音乐
            elif channel_name in music_dictionary and check_url_existence(music_lines, channel_address):
                music_lines.append(process_name_string(line.strip()))
            # 美食
            elif channel_name in food_dictionary and check_url_existence(food_lines, channel_address):
                food_lines.append(process_name_string(line.strip()))
            # 旅游
            elif channel_name in travel_dictionary and check_url_existence(travel_lines, channel_address):
                travel_lines.append(process_name_string(line.strip()))
            # 健康
            elif channel_name in health_dictionary and check_url_existence(health_lines, channel_address):
                health_lines.append(process_name_string(line.strip()))
            # 财经
            elif channel_name in finance_dictionary and check_url_existence(finance_lines, channel_address):
                finance_lines.append(process_name_string(line.strip()))
            # 购物
            elif channel_name in shopping_dictionary and check_url_existence(shopping_lines, channel_address):
                shopping_lines.append(process_name_string(line.strip()))
            # 游戏
            elif channel_name in game_dictionary and check_url_existence(game_lines, channel_address):
                game_lines.append(process_name_string(line.strip()))
            # 新闻
            elif channel_name in news_dictionary and check_url_existence(news_lines, channel_address):
                news_lines.append(process_name_string(line.strip()))
            # 中国
            elif channel_name in china_dictionary and check_url_existence(china_lines, channel_address):
                china_lines.append(process_name_string(line.strip()))
            # 国际
            elif channel_name in international_dictionary and check_url_existence(international_lines, channel_address):
                international_lines.append(process_name_string(line.strip()))
            # 体育
            elif channel_name in sports_dictionary and check_url_existence(sports_lines, channel_address):
                sports_lines.append(process_name_string(line.strip()))
            # 体育赛事
#            elif any(tyss_dictionary in channel_name for tyss_dictionary in tyss_dictionary) and check_url_existence(tyss_lines, channel_address):  #体育赛事（2025新增）
#                tyss_lines.append(process_name_string(line.strip()))
            elif any(tyss_keyword in channel_name for tyss_keyword in tyss_dictionary) and check_url_existence(tyss_lines, channel_address):
                tyss_lines.append(process_name_string(line.strip()))
            # 咪咕赛事
#            elif any(mgss_dictionary in channel_name for mgss_dictionary in mgss_dictionary) and check_url_existence(mgss_lines, channel_address):  #咪咕赛事（2025新增）
#                mgss_lines.append(process_name_string(line.strip()))
            elif any(mgss_keyword in channel_name for mgss_keyword in mgss_dictionary) and check_url_existence(mgss_lines, channel_address):
                mgss_lines.append(process_name_string(line.strip()))
            # 戏曲频道
            elif channel_name in traditional_opera_dictionary and check_url_existence(traditional_opera_lines, channel_address):
                traditional_opera_lines.append(process_name_string(line.strip()))
            # 历届春晚
            elif channel_name in spring_festival_gala_dictionary and check_url_existence(spring_festival_gala_lines, channel_address):
                spring_festival_gala_lines.append(process_name_string(line.strip()))
            # 景区直播
            elif channel_name in camera_dictionary and check_url_existence(camera_lines, channel_address):
                camera_lines.append(process_name_string(line.strip()))
            # 收藏频道
            elif channel_name in favorite_dictionary and check_url_existence(favorite_lines, channel_address):
                favorite_lines.append(process_name_string(line.strip()))
            # 未匹配到任何分类，放入other_lines
            else:
                if channel_address not in other_lines_url:
                    other_lines_url.append(channel_address)
                    other_lines.append(line.strip())

# 获取随机User-Agent的函数
def get_random_user_agent():
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
    ]
    return random.choice(USER_AGENTS)

# 处理单个URL的函数
def process_url(url):
    try:
        other_lines.append("◆◆◆　"+url)
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
        with urllib.request.urlopen(req) as response:
            data = response.read()
            text = data.decode('utf-8')
            text = text.strip()
            is_m3u = text.startswith("#EXTM3U") or text.startswith("#EXTINF")
            if get_url_file_extension(url)==".m3u" or get_url_file_extension(url)==".m3u8" or is_m3u:
                text=convert_m3u_to_txt(text)
            lines = text.split('\n')
            print(f"行数: {len(lines)}")
            for line in lines:
                if  "#genre#" not in line and "," in line and "://" in line and "tvbus://" not in line and "/udp/" not in line:
                    channel_name, channel_address = line.split(',', 1)
                    if "#" not in channel_address:
                        process_channel_line(line)
                    else:
                        url_list = channel_address.split('#')
                        for channel_url in url_list:
                            newline=f'{channel_name},{channel_url}'
                            process_channel_line(newline)
            other_lines.append('\n')

    except Exception as e:
        print(f"❌处理URL时发生错误：{e}")

# 获取当前工作目录
current_directory = os.getcwd()

# ========= 频道字典文件读取 =========
# 读取各种频道的字典文件（用于频道分类）
print(f"\n📋 加载频道字典...")

yangshi_dictionary = read_txt_to_array('assets/livesource/主频道/CCTV.txt')
weishi_dictionary = read_txt_to_array('assets/livesource/主频道/卫视.txt')

beijing_dictionary = read_txt_to_array('assets/livesource/地方台/北京.txt')
shanghai_dictionary = read_txt_to_array('assets/livesource/地方台/上海.txt')
guangdong_dictionary = read_txt_to_array('assets/livesource/地方台/广东.txt')
jiangsu_dictionary = read_txt_to_array('assets/livesource/地方台/江苏.txt')
zhejiang_dictionary = read_txt_to_array('assets/livesource/地方台/浙江.txt')
shandong_dictionary = read_txt_to_array('assets/livesource/地方台/山东.txt')
sichuan_dictionary = read_txt_to_array('assets/livesource/地方台/四川.txt')
henan_dictionary = read_txt_to_array('assets/livesource/地方台/河南.txt')
hunan_dictionary = read_txt_to_array('assets/livesource/地方台/湖南.txt')
chongqing_dictionary = read_txt_to_array('assets/livesource/地方台/重庆.txt')
tianjin_dictionary = read_txt_to_array('assets/livesource/地方台/天津.txt')
hubei_dictionary = read_txt_to_array('assets/livesource/地方台/湖北.txt')
anhui_dictionary = read_txt_to_array('assets/livesource/地方台/安徽.txt')
fujian_dictionary = read_txt_to_array('assets/livesource/地方台/福建.txt')
liaoning_dictionary = read_txt_to_array('assets/livesource/地方台/辽宁.txt')
shaanxi_dictionary = read_txt_to_array('assets/livesource/地方台/陕西.txt')
hebei_dictionary = read_txt_to_array('assets/livesource/地方台/河北.txt')
jiangxi_dictionary = read_txt_to_array('assets/livesource/地方台/江西.txt')
guangxi_dictionary = read_txt_to_array('assets/livesource/地方台/广西.txt')
yunnan_dictionary = read_txt_to_array('assets/livesource/地方台/云南.txt')
shanxi_dictionary = read_txt_to_array('assets/livesource/地方台/山西.txt')
heilongjiang_dictionary = read_txt_to_array('assets/livesource/地方台/黑龙江.txt')
jilin_dictionary = read_txt_to_array('assets/livesource/地方台/吉林.txt')
guizhou_dictionary = read_txt_to_array('assets/livesource/地方台/贵州.txt')
gansu_dictionary = read_txt_to_array('assets/livesource/地方台/甘肃.txt')
neimenggu_dictionary = read_txt_to_array('assets/livesource/地方台/内蒙.txt')
xinjiang_dictionary = read_txt_to_array('assets/livesource/地方台/新疆.txt')
hainan_dictionary = read_txt_to_array('assets/livesource/地方台/海南.txt')
ningxia_dictionary = read_txt_to_array('assets/livesource/地方台/宁夏.txt')
qinghai_dictionary = read_txt_to_array('assets/livesource/地方台/青海.txt')
xizang_dictionary = read_txt_to_array('assets/livesource/地方台/西藏.txt')

hongkong_dictionary = read_txt_to_array('assets/livesource/地方台/香港.txt')
macau_dictionary = read_txt_to_array('assets/livesource/地方台/澳门.txt')
taiwan_dictionary = read_txt_to_array('assets/livesource/地方台/台湾.txt')

digital_dictionary = read_txt_to_array('assets/livesource/主频道/数字.txt')
movie_dictionary = read_txt_to_array('assets/livesource/主频道/电影.txt')
tv_drama_dictionary = read_txt_to_array('assets/livesource/主频道/电视剧.txt')
documentary_dictionary = read_txt_to_array('assets/livesource/主频道/纪录片.txt')
cartoon_dictionary = read_txt_to_array('assets/livesource/主频道/动画片.txt')
radio_dictionary = read_txt_to_array('assets/livesource/主频道/收音机.txt')
variety_dictionary = read_txt_to_array('assets/livesource/主频道/综艺.txt')
huya_dictionary = read_txt_to_array('assets/livesource/主频道/虎牙.txt')
douyu_dictionary = read_txt_to_array('assets/livesource/主频道/斗鱼.txt')
commentary_dictionary = read_txt_to_array('assets/livesource/主频道/解说.txt')
music_dictionary = read_txt_to_array('assets/livesource/主频道/音乐.txt')
food_dictionary = read_txt_to_array('assets/livesource/主频道/美食.txt')
travel_dictionary = read_txt_to_array('assets/livesource/主频道/旅游.txt')
health_dictionary = read_txt_to_array('assets/livesource/主频道/健康.txt')
finance_dictionary = read_txt_to_array('assets/livesource/主频道/财经.txt')
shopping_dictionary = read_txt_to_array('assets/livesource/主频道/购物.txt')
game_dictionary = read_txt_to_array('assets/livesource/主频道/游戏.txt')
news_dictionary = read_txt_to_array('assets/livesource/主频道/新闻.txt')
china_dictionary = read_txt_to_array('assets/livesource/主频道/中国.txt')
international_dictionary = read_txt_to_array('assets/livesource/主频道/国际.txt')
sports_dictionary = read_txt_to_array('assets/livesource/主频道/体育.txt')
tyss_dictionary = read_txt_to_array('assets/livesource/主频道/体育赛事.txt')
mgss_dictionary = read_txt_to_array('assets/livesource/主频道/咪咕赛事.txt')
traditional_opera_dictionary = read_txt_to_array('assets/livesource/主频道/戏曲.txt')
spring_festival_gala_dictionary = read_txt_to_array('assets/livesource/主频道/春晚.txt')
camera_dictionary = read_txt_to_array('assets/livesource/主频道/直播中国.txt')
favorite_dictionary = read_txt_to_array('assets/livesource/主频道/收藏频道.txt')

# 打印所有字典加载情况
print(f"✅ 字典加载完成:")
print(f"   央视: {len(yangshi_dictionary)} 条")
print(f"   卫视: {len(weishi_dictionary)} 条")
print(f"   地方台: 31个分类已加载")
print(f"   港澳台: 3个分类已加载")
print(f"   其他分类: 27个分类已加载")

# 加载频道名称修正字典的函数
def load_corrections_name(filename):
    corrections = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和以#开头的注释行
                if not line or line.startswith('#'):
                    continue
                parts = line.strip().split(',')
                if len(parts) < 2:
                    continue  # 跳过不完整的行
                correct_name = parts[0]
                for name in parts[1:]:
                    if name:  # 跳过空的别名
                        corrections[name] = correct_name

    except FileNotFoundError:
        print(f"❌ 修正字典文件未找到: {filename}")
    except Exception as e:
        print(f"❌ 加载修正字典错误: {e}")
    return corrections

# 加载名称修正字典
corrections_name = load_corrections_name('assets/livesource/corrections_name.txt')
print(f"\n🔄 频道更名修正字典:")
print(f"   加载了 {len(corrections_name)} 条修正规则")
if corrections_name:
    print(f"   修正规则示例 (前3条):")
    for i, (wrong_name, correct_name) in enumerate(list(corrections_name.items())[:3]):
        print(f"     {i+1}. '{wrong_name}' → '{correct_name}'")
    if len(corrections_name) > 3:
        print(f"     ... 还有 {len(corrections_name) - 3} 条修正规则")
else:
    print(f"   未加载到有效的修正规则")

# 修正频道名称数据的函数
def correct_name_data(corrections, data):
    corrected_data = []
    for line in data:
        line = line.strip()
        if ',' not in line:
            continue
        name, url = line.split(',', 1)
        if name in corrections and name != corrections[name]:
            name = corrections[name]
        corrected_data.append(f"{name},{url}")
    return corrected_data

# 按指定顺序排序数据的函数
def sort_data(order, data):
    order_dict = {name: i for i, name in enumerate(order)}
    def sort_key(line):
        name = line.split(',')[0]
        return order_dict.get(name, len(order))
    sorted_data = sorted(data, key=sort_key)
    return sorted_data

# 读取URL列表文件
urls = read_txt_to_array('assets/livesource/urls-daily.txt')
print(f"\n📋 发现 {len(urls)} 个数据订阅源")
for url in urls:
    if url.startswith("http"):
        if "{MMdd}" in url:
            current_date_str = datetime.now().strftime("%m%d")
            url=url.replace("{MMdd}", current_date_str)
        if "{MMdd-1}" in url:
            yesterday_date_str = (datetime.now() - timedelta(days=1)).strftime("%m%d")
            url=url.replace("{MMdd-1}", yesterday_date_str)
        print(f"📡 处理URL: {url}")
        process_url(url)

# 从字符串中提取数字的函数（用于排序）
def extract_number(s):
    num_str = s.split(',')[0].split('-')[1]
    numbers = re.findall(r'\d+', num_str)
    return int(numbers[-1]) if numbers else 999

# 自定义排序函数（优先4K、8K频道）
def custom_sort(s):
    if "CCTV-4K" in s:
        return 2
    elif "CCTV-8K" in s:
        return 3
    elif "(4K)" in s:
        return 1
    else:
        return 0

# 处理白名单自动文件
print(f"\n🟢 处理白名单自动文件...")
whitelist_auto_lines = read_txt_to_array('assets/livesource/blacklist/whitelist_auto.txt')

# 打印白名单统计信息
print(f"   读取到 {len(whitelist_auto_lines)} 条记录")

# 统计有效白名单记录
valid_whitelist_count = 0
valid_whitelist_samples = []

for i, whitelist_line in enumerate(whitelist_auto_lines):
    if i < 2:  # 跳过前两行（标题和日期行）
        continue
    # 跳过表头行
    if whitelist_line.startswith("RespoTime,whitelist,#genre#"):
        continue
    # 处理真正的白名单行
    if "#genre#" not in whitelist_line and "," in whitelist_line and "://" in whitelist_line:
        whitelist_parts = whitelist_line.split(",")
        if len(whitelist_parts) >= 3:
            valid_whitelist_count += 1
            # 保存示例
            if len(valid_whitelist_samples) < 3:
                valid_whitelist_samples.append(whitelist_line)
            try:
                response_time = float(whitelist_parts[0].replace("ms", ""))
            except ValueError:
                print(f"response_time转换失败: {whitelist_line}")
                response_time = 60000
            if response_time < 2000:
                process_channel_line(",".join(whitelist_parts[1:]))

print(f"   有效白名单记录: {valid_whitelist_count} 条")
if valid_whitelist_samples:
    print(f"   白名单示例 (前3条):")
    for i, line in enumerate(valid_whitelist_samples[:3]):
        print(f"     {i+1}. {line[:80]}..." if len(line) > 80 else f"     {i+1}. {line}")
    if valid_whitelist_count > 3:
        print(f"     ... 还有 {valid_whitelist_count - 3} 条")

# 遍历自动测试生成的播放源白名单
for whitelist_line in whitelist_auto_lines:
    if  "#genre#" not in whitelist_line and "," in whitelist_line and "://" in whitelist_line:
        whitelist_parts = whitelist_line.split(",")
        try:
            response_time = float(whitelist_parts[0].replace("ms", ""))
        except ValueError:
            print(f"response_time转换失败: {whitelist_line}")
            response_time = 60000
        if response_time < 2000:
            process_channel_line(",".join(whitelist_parts[1:]))

# 获取HTTP响应的函数（带重试机制）
def get_http_response(url, timeout=8, retries=2, backoff_factor=1.0):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
                return data.decode('utf-8')
        except urllib.error.HTTPError as e:
            print(f"[HTTPError] Code: {e.code}, URL: {url}")
            break
        except urllib.error.URLError as e:
            print(f"[URLError] Reason: {e.reason}, Attempt: {attempt + 1}")
        except socket.timeout:
            print(f"[Timeout] URL: {url}, Attempt: {attempt + 1}")
        except Exception as e:
            print(f"[Exception] {type(e).__name__}: {e}, Attempt: {attempt + 1}")
            if attempt < retries - 1:
                time.sleep(backoff_factor * (2 ** attempt))
    return None

# 将日期格式规范化为MM-DD格式的函数
def normalize_date_to_md(text):
    text = text.strip()
    def format_md(m):
        month = int(m.group(1))
        day = int(m.group(2))
        after = m.group(3) or ''
        if not after.startswith(' '):
            after = ' ' + after
        return f"{month:02d}-{day:02d}{after}"
    text = re.sub(r'^0?(\d{1,2})/0?(\d{1,2})(.*)', format_md, text)
    text = re.sub(r'^\d{4}-0?(\d{1,2})-0?(\d{1,2})(.*)', format_md, text)
    text = re.sub(r'^0?(\d{1,2})月0?(\d{1,2})日(.*)', format_md, text)
    return text

# 规范化体育赛事行的日期格式
normalized_tyss_lines = [normalize_date_to_md(s) for s in tyss_lines]

# ========= AKTV特殊处理 =========
aktv_lines = []  # 存储AKTV频道数据
aktv_url = "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/assets/livesource/blacklist/whitelist_manual.txt"  # AKTV源地址
aktv_text = get_http_response(aktv_url)
if aktv_text:
    print(f" ")
    print(f"📺 AKTV成功获取内容")
    aktv_text = convert_m3u_to_txt(aktv_text)
    aktv_lines = aktv_text.strip().split('\n')
else:
    print(f"⚠️ AKTV请求失败，从本地获取！")
    aktv_lines = read_txt_to_array('assets/livesource/手工区/AKTV.txt')

print(f"AKTV频道统计:")
print(f"   获取到 {len(aktv_lines)} 条AKTV频道记录")
if aktv_lines:
    print(f"   AKTV频道示例 (前3条):")
    for i, line in enumerate(aktv_lines[:3]):
        print(f"     {i+1}. {line[:60]}..." if len(line) > 60 else f"     {i+1}. {line}")
    if len(aktv_lines) > 3:
        print(f"     ... 还有 {len(aktv_lines) - 3} 条")

# 过滤包含特定关键词的行的函数
def filter_lines(lines, exclude_keywords):
    return [line for line in lines if not any(keyword in line for keyword in exclude_keywords)]

# 生成体育赛事HTML页面的函数
def generate_playlist_html(data_list, output_file='playlist.html'):
    html_head = '''
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">        
        <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6061710286208572"
     crossorigin="anonymous"></script>
        <!-- Setup Google Analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-BS1Z4F5BDN"></script>
        <script> 
        window.dataLayer = window.dataLayer || []; 
        function gtag(){dataLayer.push(arguments);} 
        gtag('js', new Date()); 
        gtag('config', 'G-BS1Z4F5BDN'); 
        </script>
        <title>最新体育赛事</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background: #f9f9f9; }
            .item { margin-bottom: 20px; padding: 12px; background: #fff; border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.06); }
            .title { font-weight: bold; font-size: 1.1em; color: #333; margin-bottom: 5px; }
            .url-wrapper { display: flex; align-items: center; gap: 10px; }
            .url {
                max-width: 80%;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                font-size: 0.9em;
                color: #555;
                background: #f0f0f0;
                padding: 6px;
                border-radius: 4px;
                flex-grow: 1;
            }
            .copy-btn {
                background-color: #007BFF;
                border: none;
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.8em;
            }
            .copy-btn:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
    <h2>📋 最新体育赛事列表</h2>
    '''

    html_body = ''
    for idx, entry in enumerate(data_list):
        if ',' not in entry:
            continue
        info, url = entry.split(',', 1)
        url_id = f"url_{idx}"
        html_body += f'''
        <div class="item">
            <div class="title">🕒 {info}</div>
            <div class="url-wrapper">
                <div class="url" id="{url_id}">{url}</div>
                <button class="copy-btn" onclick="copyToClipboard('{url_id}')">复制</button>
            </div>
        </div>
        '''

    html_tail = '''
    <script>
        function copyToClipboard(id) {
            const el = document.getElementById(id);
            const text = el.textContent;
            navigator.clipboard.writeText(text).then(() => {
                alert("已复制链接！");
            }).catch(err => {
                alert("复制失败: " + err);
            });
        }
    </script>
    </body>
    </html>
    '''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_head + html_body + html_tail)
    print(f"✅ 网页已生成：{output_file}")

# 自定义体育赛事排序函数（数字前缀的倒序，其他正序）
def custom_tyss_sort(lines):
    digit_prefix = []
    others = []
    for line in lines:
        name_part = line.split(',')[0].strip()
        if name_part and name_part[0].isdigit():
            digit_prefix.append(line)
        else:
            others.append(line)
    digit_prefix_sorted = sorted(digit_prefix, reverse=True)
    others_sorted = sorted(others)

    return digit_prefix_sorted + others_sorted

# 过滤体育赛事文本中的特定关键词
keywords_to_exclude_tiyu_txt = ["玉玉软件", "榴芒电视","公众号","麻豆","「回看」"]
normalized_tyss_lines = filter_lines(normalized_tyss_lines, keywords_to_exclude_tiyu_txt)

# 去重并排序
normalized_tyss_lines = custom_tyss_sort(set(normalized_tyss_lines))

# 过滤体育赛事HTML中的特定关键词
keywords_to_exclude_tiyu = ["玉玉软件", "榴芒电视","公众号","咪视通","麻豆","「回看」"]
filtered_tyss_lines = filter_lines(normalized_tyss_lines, keywords_to_exclude_tiyu)
print(f"\n🏆 体育赛事处理完成：原始 {len(tyss_lines)} 条，过滤后 {len(filtered_tyss_lines)} 条")

# 生成体育赛事HTML文件
generate_playlist_html(filtered_tyss_lines, 'output/tiyu.html')

# 生成体育赛事TXT文件
with open('output/tiyu.txt', 'w', encoding='utf-8') as f:
    for line in filtered_tyss_lines:
        f.write(line + '\n')
print(f"✅ 文本已生成: output/tiyu.txt")

# 从文件中随机获取URL的函数
def get_random_url(file_path):
    urls = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            url = line.strip().split(',')[-1]
            urls.append(url)    
    return random.choice(urls) if urls else None

# ========= 今日推荐和版本信息 =========
print(f"\n🕒 生成今日推荐和版本信息")
# 获取北京时间
utc_time = datetime.now(timezone.utc)
beijing_time = utc_time + timedelta(hours=8)
formatted_time = beijing_time.strftime("%Y%m%d %H:%M:%S")

# 生成今日推荐信息
MTV1 = "💯推荐," + get_random_url('assets/livesource/手工区/今日推荐.txt')
MTV2 = "🤫低调," + get_random_url('assets/livesource/手工区/今日推荐.txt')
MTV3 = "🟢使用," + get_random_url('assets/livesource/手工区/今日推荐.txt')
MTV4 = "⚠️禁止," + get_random_url('assets/livesource/手工区/今日推荐.txt')
MTV5 = "🚫贩卖," + get_random_url('assets/livesource/手工区/今日推荐.txt')

about_video1 = "https://gitee.com/xiaoran67/update/raw/master/assets/livesource/about1080p.mp4"
about_video2 = "https://gitlab.com/xiaoran67/update/-/raw/main/assets/livesource/about1080p.mp4"

# 生成版本信息
version = formatted_time + "," + get_random_url('assets/livesource/手工区/今日推台.txt')
about = "👨潇然," + get_random_url('assets/livesource/手工区/今日推台.txt')

# 处理手工添加的频道源
print(f"\n🔧 处理手工区高质量源...")

# 读取并统计各个手工区文件
zhejiang_manual = read_txt_to_array('assets/livesource/手工区/浙江频道.txt')
guangdong_manual = read_txt_to_array('assets/livesource/手工区/广东频道.txt')
hubei_manual = read_txt_to_array('assets/livesource/手工区/湖北频道.txt')
shanghai_manual = read_txt_to_array('assets/livesource/手工区/上海频道.txt')
jiangsu_manual = read_txt_to_array('assets/livesource/手工区/江苏频道.txt')

# 打印手工区统计信息
print(f"   浙江频道: {len(zhejiang_manual)} 条")
print(f"   广东频道: {len(guangdong_manual)} 条")
print(f"   湖北频道: {len(hubei_manual)} 条")
print(f"   上海频道: {len(shanghai_manual)} 条")
print(f"   江苏频道: {len(jiangsu_manual)} 条")
print(f"   手工区总计: {len(zhejiang_manual) + len(guangdong_manual) + len(hubei_manual) + len(shanghai_manual) + len(jiangsu_manual)} 条")

# 添加到对应的频道列表
zhejiang_lines += zhejiang_manual
guangdong_lines += guangdong_manual
hubei_lines += hubei_manual
shanghai_lines += shanghai_manual
jiangsu_lines += jiangsu_manual

print(f"\n📄 生成播放列表文件")

# 构建完整版播放列表
playlist_full =  ["🌐央视频道,#genre#"] + sort_data(yangshi_dictionary,correct_name_data(corrections_name,yangshi_lines)) + ['\n'] + \
        ["📡卫视频道,#genre#"] + sort_data(weishi_dictionary,set(correct_name_data(corrections_name,weishi_lines))) + ['\n'] + \
        ["🏛️北京频道,#genre#"] + sort_data(beijing_dictionary,list(set(correct_name_data(corrections_name,beijing_lines)))) + ['\n'] + \
        ["🏙️上海频道,#genre#"] + sort_data(shanghai_dictionary,list(set(correct_name_data(corrections_name,shanghai_lines)))) + ['\n'] + \
        ["🦁广东频道,#genre#"] + sort_data(guangdong_dictionary,list(set(correct_name_data(corrections_name,guangdong_lines)))) + ['\n'] + \
        ["🍃江苏频道,#genre#"] + sort_data(jiangsu_dictionary, list(set(correct_name_data(corrections_name, jiangsu_lines)))) + ['\n'] + \
        ["🧵浙江频道,#genre#"] + sort_data(zhejiang_dictionary, list(set(correct_name_data(corrections_name, zhejiang_lines)))) + ['\n'] + \
        ["⛰️山东频道,#genre#"] + sort_data(shandong_dictionary, list(set(correct_name_data(corrections_name, shandong_lines)))) + ['\n'] + \
        ["🐼四川频道,#genre#"] + sort_data(sichuan_dictionary, list(set(correct_name_data(corrections_name, sichuan_lines)))) + ['\n'] + \
        ["⚔️河南频道,#genre#"] + sort_data(henan_dictionary, list(set(correct_name_data(corrections_name,henan_lines)))) + ['\n'] + \
        ["🌶️湖南频道,#genre#"] + sort_data(hunan_dictionary, list(set(correct_name_data(corrections_name,hunan_lines)))) + ['\n'] + \
        ["🍲重庆频道,#genre#"] + sort_data(chongqing_dictionary, list(set(correct_name_data(corrections_name, chongqing_lines)))) + ['\n'] + \
        ["🚢天津频道,#genre#"] + sort_data(tianjin_dictionary, list(set(correct_name_data(corrections_name, tianjin_lines)))) + ['\n'] + \
        ["🌉湖北频道,#genre#"] + sort_data(hubei_dictionary, list(set(correct_name_data(corrections_name,hubei_lines)))) + ['\n'] + \
        ["🌾安徽频道,#genre#"] + sort_data(anhui_dictionary, list(set(correct_name_data(corrections_name, anhui_lines)))) + ['\n'] + \
        ["🌊福建频道,#genre#"] + sort_data(fujian_dictionary, list(set(correct_name_data(corrections_name, fujian_lines)))) + ['\n'] + \
        ["🏭辽宁频道,#genre#"] + sort_data(liaoning_dictionary, list(set(correct_name_data(corrections_name, liaoning_lines)))) + ['\n'] + \
        ["🗿陕西频道,#genre#"] + sort_data(shaanxi_dictionary, list(set(correct_name_data(corrections_name, shaanxi_lines)))) + ['\n'] + \
        ["⛩️河北频道,#genre#"] + sort_data(hebei_dictionary, list(set(correct_name_data(corrections_name, hebei_lines)))) + ['\n'] + \
        ["🍶江西频道,#genre#"] + sort_data(jiangxi_dictionary, list(set(correct_name_data(corrections_name, jiangxi_lines)))) + ['\n'] + \
        ["💃广西频道,#genre#"] + sort_data(guangxi_dictionary,list(set(correct_name_data(corrections_name,guangxi_lines)))) + ['\n'] + \
        ["☁️云南频道,#genre#"] + sort_data(yunnan_dictionary, list(set(correct_name_data(corrections_name, yunnan_lines)))) + ['\n'] + \
        ["🏮山西频道,#genre#"] + sort_data(shanxi_dictionary, list(set(correct_name_data(corrections_name, shanxi_lines)))) + ['\n'] + \
        ["❄️黑·龙·江,#genre#"] + sort_data(heilongjiang_dictionary, list(set(correct_name_data(corrections_name, heilongjiang_lines)))) + ['\n'] + \
        ["🎎吉林频道,#genre#"] + sort_data(jilin_dictionary, list(set(correct_name_data(corrections_name, jilin_lines)))) + ['\n'] + \
        ["🌈贵州频道,#genre#"] + sort_data(guizhou_dictionary, list(set(correct_name_data(corrections_name, guizhou_lines)))) + ['\n'] + \
        ["🐫甘肃频道,#genre#"] + sort_data(gansu_dictionary, list(set(correct_name_data(corrections_name, gansu_lines)))) + ['\n'] + \
        ["🐎内·蒙·古,#genre#"] + sort_data(neimenggu_dictionary, list(set(correct_name_data(corrections_name, neimenggu_lines)))) + ['\n'] + \
        ["🍇新疆频道,#genre#"] + sort_data(xinjiang_dictionary, list(set(correct_name_data(corrections_name, xinjiang_lines)))) + ['\n'] + \
        ["🏝️海南频道,#genre#"] + sort_data(hainan_dictionary, list(set(correct_name_data(corrections_name, hainan_lines)))) + ['\n'] + \
        ["🕌宁夏频道,#genre#"] + sort_data(ningxia_dictionary, list(set(correct_name_data(corrections_name, ningxia_lines)))) + ['\n'] + \
        ["🐑青海频道,#genre#"] + sort_data(qinghai_dictionary, list(set(correct_name_data(corrections_name, qinghai_lines)))) + ['\n'] + \
        ["🐐西藏频道,#genre#"] + sort_data(xizang_dictionary, list(set(correct_name_data(corrections_name, xizang_lines)))) + ['\n'] + \
        ["🇭🇰香港频道,#genre#"] + sort_data(hongkong_dictionary, list(set(correct_name_data(corrections_name, hongkong_lines)))) + ['\n'] + \
        ["🇲🇴澳门频道,#genre#"] + sort_data(macau_dictionary, list(set(correct_name_data(corrections_name, macau_lines)))) + ['\n'] + \
        ["🇨🇳台湾频道,#genre#"] + sort_data(taiwan_dictionary, list(set(correct_name_data(corrections_name, taiwan_lines)))) + ['\n'] + \
        ["🇨🇳中国综合,#genre#"] + sort_data(china_dictionary, list(set(correct_name_data(corrections_name, china_lines)))) + ['\n'] + \
        ["🌐国际频道,#genre#"] + sort_data(international_dictionary, list(set(correct_name_data(corrections_name, international_lines)))) + ['\n'] + \
        ["📶数字频道,#genre#"] + sort_data(digital_dictionary, list(set(correct_name_data(corrections_name, digital_lines)))) + ['\n'] + \
        ["🎬电影频道,#genre#"] + sort_data(movie_dictionary, list(set(correct_name_data(corrections_name, movie_lines)))) + ['\n'] + \
        ["📺电·视·剧,#genre#"] + sort_data(tv_drama_dictionary, list(set(correct_name_data(corrections_name, tv_drama_lines)))) + ['\n'] + \
        ["🦊动·画·片,#genre#"] + sort_data(cartoon_dictionary, list(set(correct_name_data(corrections_name, cartoon_lines)))) + ['\n'] + \
        ["📽️纪·录·片,#genre#"] + sort_data(documentary_dictionary, list(set(correct_name_data(corrections_name, documentary_lines)))) + ['\n'] + \
        ["📻收·音·机,#genre#"] + sort_data(radio_dictionary, list(set(correct_name_data(corrections_name, radio_lines)))) + ['\n'] + \
        ["🐯虎牙直播,#genre#"] + sort_data(huya_dictionary, list(set(correct_name_data(corrections_name, huya_lines)))) + ['\n'] + \
        ["🐠斗鱼直播,#genre#"] + sort_data(douyu_dictionary, list(set(correct_name_data(corrections_name, douyu_lines)))) + ['\n'] + \
        ["🎤解说频道,#genre#"] + sort_data(commentary_dictionary, list(set(correct_name_data(corrections_name, commentary_lines)))) + ['\n'] + \
        ["🎵音乐频道,#genre#"] + sort_data(music_dictionary, list(set(correct_name_data(corrections_name, music_lines)))) + ['\n'] + \
        ["🍜美食频道,#genre#"] + sort_data(food_dictionary, list(set(correct_name_data(corrections_name, food_lines)))) + ['\n'] + \
        ["✈️旅游频道,#genre#"] + sort_data(travel_dictionary, list(set(correct_name_data(corrections_name, travel_lines)))) + ['\n'] + \
        ["🏥健康频道,#genre#"] + sort_data(health_dictionary, list(set(correct_name_data(corrections_name, health_lines)))) + ['\n'] + \
        ["📰新闻频道,#genre#"] + sort_data(news_dictionary, list(set(correct_name_data(corrections_name, news_lines)))) + ['\n'] + \
        ["💰财经频道,#genre#"] + sort_data(finance_dictionary, list(set(correct_name_data(corrections_name, finance_lines)))) + ['\n'] + \
        ["🛍️购物频道,#genre#"] + sort_data(shopping_dictionary, list(set(correct_name_data(corrections_name, shopping_lines)))) + ['\n'] + \
        ["🎮游戏频道,#genre#"] + sort_data(game_dictionary,set(correct_name_data(corrections_name,game_lines))) + ['\n'] + \
        ["🎭戏曲频道,#genre#"] + sorted(set(correct_name_data(corrections_name, traditional_opera_lines))) + ['\n'] + \
        ["🎭综艺频道,#genre#"] + sorted(set(correct_name_data(corrections_name, variety_lines))) + ['\n'] + \
        ["🧨历届春晚,#genre#"] + sort_data(spring_festival_gala_dictionary,list(set(spring_festival_gala_lines)))  + ['\n'] + \
        ["⭐收藏频道,#genre#"] + sort_data(favorite_dictionary, list(set(correct_name_data(corrections_name, favorite_lines)))) + ['\n'] + \
        ["⚽️体育频道,#genre#"] + sort_data(sports_dictionary,set(correct_name_data(corrections_name,sports_lines))) + ['\n'] + \
        ["🏆️体育赛事,#genre#"] + normalized_tyss_lines + ['\n'] + \
        ["🏈咪咕赛事,#genre#"] + mgss_lines + ['\n'] + \
        ["👑专享央视,#genre#"] + read_txt_to_array('assets/livesource/手工区/优质央视.txt') + ['\n'] + \
        ["☕️专享卫视,#genre#"] + read_txt_to_array('assets/livesource/手工区/优质卫视.txt') + ['\n'] + \
        ["🏞️景区直播,#genre#"] + sorted(set(correct_name_data(corrections_name,camera_lines))) + ['\n'] + \
        ["📦其他频道,#genre#"] + sorted(set(other_lines)) + ['\n'] + \
        ["🕒更新时间,#genre#"] + [version] + [about] + [MTV1] + [MTV2] + [MTV3] + [MTV4] + [MTV5] + read_txt_to_array('assets/livesource/手工区/about.txt') + ['\n']

# 构建精简版播放列表
playlist_lite =  ["🌐央视频道,#genre#"] + sort_data(yangshi_dictionary,correct_name_data(corrections_name,yangshi_lines)) + ['\n'] + \
        ["📡卫视频道,#genre#"] + sort_data(weishi_dictionary,set(correct_name_data(corrections_name,weishi_lines))) + ['\n'] + \
        ["🏠地·方·台,#genre#"] + \
        sort_data(beijing_dictionary, list(set(correct_name_data(corrections_name, beijing_lines)))) + \
        sort_data(shanghai_dictionary, list(set(correct_name_data(corrections_name, shanghai_lines)))) + \
        sort_data(guangdong_dictionary, list(set(correct_name_data(corrections_name, guangdong_lines)))) + \
        sort_data(jiangsu_dictionary, list(set(correct_name_data(corrections_name, jiangsu_lines)))) + \
        sort_data(zhejiang_dictionary, list(set(correct_name_data(corrections_name, zhejiang_lines)))) + \
        sort_data(shandong_dictionary, list(set(correct_name_data(corrections_name, shandong_lines)))) + \
        sort_data(sichuan_dictionary, list(set(correct_name_data(corrections_name, sichuan_lines)))) + \
        sort_data(henan_dictionary, list(set(correct_name_data(corrections_name,henan_lines)))) + \
        sort_data(hunan_dictionary, list(set(correct_name_data(corrections_name,hunan_lines)))) + \
        sort_data(chongqing_dictionary, list(set(correct_name_data(corrections_name, chongqing_lines)))) + \
        sort_data(tianjin_dictionary, list(set(correct_name_data(corrections_name, tianjin_lines)))) + \
        sort_data(hubei_dictionary, list(set(correct_name_data(corrections_name,hubei_lines)))) + \
        sort_data(anhui_dictionary, list(set(correct_name_data(corrections_name, anhui_lines)))) + \
        sort_data(fujian_dictionary, list(set(correct_name_data(corrections_name, fujian_lines)))) + \
        sort_data(liaoning_dictionary, list(set(correct_name_data(corrections_name, liaoning_lines)))) + \
        sort_data(shaanxi_dictionary, list(set(correct_name_data(corrections_name, shaanxi_lines)))) + \
        sort_data(hebei_dictionary, list(set(correct_name_data(corrections_name, hebei_lines)))) + \
        sort_data(jiangxi_dictionary, list(set(correct_name_data(corrections_name, jiangxi_lines)))) + \
        sort_data(guangxi_dictionary,list(set(correct_name_data(corrections_name,guangxi_lines)))) + \
        sort_data(yunnan_dictionary, list(set(correct_name_data(corrections_name, yunnan_lines)))) + \
        sort_data(shanxi_dictionary, list(set(correct_name_data(corrections_name, shanxi_lines)))) + \
        sort_data(heilongjiang_dictionary, list(set(correct_name_data(corrections_name, heilongjiang_lines)))) + \
        sort_data(jilin_dictionary, list(set(correct_name_data(corrections_name, jilin_lines)))) + \
        sort_data(guizhou_dictionary, list(set(correct_name_data(corrections_name, guizhou_lines)))) + \
        sort_data(gansu_dictionary, list(set(correct_name_data(corrections_name, gansu_lines)))) + \
        sort_data(neimenggu_dictionary, list(set(correct_name_data(corrections_name, neimenggu_lines)))) + \
        sort_data(xinjiang_dictionary, list(set(correct_name_data(corrections_name, xinjiang_lines)))) + \
        sort_data(hainan_dictionary, list(set(correct_name_data(corrections_name, hainan_lines)))) + \
        sort_data(ningxia_dictionary, list(set(correct_name_data(corrections_name, ningxia_lines)))) + \
        sort_data(qinghai_dictionary, list(set(correct_name_data(corrections_name, qinghai_lines)))) + \
        sort_data(xizang_dictionary, list(set(correct_name_data(corrections_name, xizang_lines)))) + \
        ['\n'] + \
        ["🕒更新时间,#genre#"] + [version] + [about] + [MTV1] + [MTV2] + [MTV3] + [MTV4] + [MTV5] + read_txt_to_array('assets/livesource/手工区/about.txt') + ['\n']

# 构建定制版播放列表
playlist_custom = ["🌐央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name,yangshi_lines)) + ['\n'] + \
        ["📡卫视频道,#genre#"] + sort_data(weishi_dictionary,set(correct_name_data(corrections_name,weishi_lines))) + ['\n'] + \
        ["🏠地·方·台,#genre#"] + \
        sort_data(beijing_dictionary, list(set(correct_name_data(corrections_name, beijing_lines)))) + \
        sort_data(shanghai_dictionary, list(set(correct_name_data(corrections_name, shanghai_lines)))) + \
        sort_data(guangdong_dictionary, list(set(correct_name_data(corrections_name, guangdong_lines)))) + \
        sort_data(jiangsu_dictionary, list(set(correct_name_data(corrections_name, jiangsu_lines)))) + \
        sort_data(zhejiang_dictionary, list(set(correct_name_data(corrections_name, zhejiang_lines)))) + \
        sort_data(shandong_dictionary, list(set(correct_name_data(corrections_name, shandong_lines)))) + \
        sort_data(sichuan_dictionary, list(set(correct_name_data(corrections_name, sichuan_lines)))) + \
        sort_data(henan_dictionary, list(set(correct_name_data(corrections_name,henan_lines)))) + \
        sort_data(hunan_dictionary, list(set(correct_name_data(corrections_name,hunan_lines)))) + \
        sort_data(chongqing_dictionary, list(set(correct_name_data(corrections_name, chongqing_lines)))) + \
        sort_data(tianjin_dictionary, list(set(correct_name_data(corrections_name, tianjin_lines)))) + \
        sort_data(hubei_dictionary, list(set(correct_name_data(corrections_name,hubei_lines)))) + \
        sort_data(anhui_dictionary, list(set(correct_name_data(corrections_name, anhui_lines)))) + \
        sort_data(fujian_dictionary, list(set(correct_name_data(corrections_name, fujian_lines)))) + \
        sort_data(liaoning_dictionary, list(set(correct_name_data(corrections_name, liaoning_lines)))) + \
        sort_data(shaanxi_dictionary, list(set(correct_name_data(corrections_name, shaanxi_lines)))) + \
        sort_data(hebei_dictionary, list(set(correct_name_data(corrections_name, hebei_lines)))) + \
        sort_data(jiangxi_dictionary, list(set(correct_name_data(corrections_name, jiangxi_lines)))) + \
        sort_data(guangxi_dictionary,list(set(correct_name_data(corrections_name,guangxi_lines)))) + \
        sort_data(yunnan_dictionary, list(set(correct_name_data(corrections_name, yunnan_lines)))) + \
        sort_data(shanxi_dictionary, list(set(correct_name_data(corrections_name, shanxi_lines)))) + \
        sort_data(heilongjiang_dictionary, list(set(correct_name_data(corrections_name, heilongjiang_lines)))) + \
        sort_data(jilin_dictionary, list(set(correct_name_data(corrections_name, jilin_lines)))) + \
        sort_data(guizhou_dictionary, list(set(correct_name_data(corrections_name, guizhou_lines)))) + \
        sort_data(gansu_dictionary, list(set(correct_name_data(corrections_name, gansu_lines)))) + \
        sort_data(neimenggu_dictionary, list(set(correct_name_data(corrections_name, neimenggu_lines)))) + \
        sort_data(xinjiang_dictionary, list(set(correct_name_data(corrections_name, xinjiang_lines)))) + \
        sort_data(hainan_dictionary, list(set(correct_name_data(corrections_name, hainan_lines)))) + \
        sort_data(ningxia_dictionary, list(set(correct_name_data(corrections_name, ningxia_lines)))) + \
        sort_data(qinghai_dictionary, list(set(correct_name_data(corrections_name, qinghai_lines)))) + \
        sort_data(xizang_dictionary, list(set(correct_name_data(corrections_name, xizang_lines)))) + \
        ['\n'] + \
        ["🇭🇰香港频道,#genre#"] + sort_data(hongkong_dictionary, list(set(correct_name_data(corrections_name, hongkong_lines)))) + ['\n'] + \
        ["🇲🇴澳门频道,#genre#"] + sort_data(macau_dictionary, list(set(correct_name_data(corrections_name, macau_lines)))) + ['\n'] + \
        ["🇨🇳台湾频道,#genre#"] + sort_data(taiwan_dictionary, list(set(correct_name_data(corrections_name, taiwan_lines)))) + ['\n'] + \
        ["🇨🇳中国综合,#genre#"] + sort_data(china_dictionary, list(set(correct_name_data(corrections_name, china_lines)))) + ['\n'] + \
        ["🌐国际频道,#genre#"] + sort_data(international_dictionary, list(set(correct_name_data(corrections_name, international_lines)))) + ['\n'] + \
        ["📶数字频道,#genre#"] + sort_data(digital_dictionary, list(set(correct_name_data(corrections_name, digital_lines)))) + ['\n'] + \
        ["🎬电影频道,#genre#"] + sort_data(movie_dictionary, list(set(correct_name_data(corrections_name, movie_lines)))) + ['\n'] + \
        ["📺电·视·剧,#genre#"] + sort_data(tv_drama_dictionary, list(set(correct_name_data(corrections_name, tv_drama_lines)))) + ['\n'] + \
        ["🦊动·画·片,#genre#"] + sort_data(cartoon_dictionary, list(set(correct_name_data(corrections_name, cartoon_lines)))) + ['\n'] + \
        ["📽️纪·录·片,#genre#"] + sort_data(documentary_dictionary, list(set(correct_name_data(corrections_name, documentary_lines)))) + ['\n'] + \
        ["📻收·音·机,#genre#"] + sort_data(radio_dictionary, list(set(correct_name_data(corrections_name, radio_lines)))) + ['\n'] + \
        ["🐯虎牙直播,#genre#"] + sort_data(huya_dictionary, list(set(correct_name_data(corrections_name, huya_lines)))) + ['\n'] + \
        ["🐠斗鱼直播,#genre#"] + sort_data(douyu_dictionary, list(set(correct_name_data(corrections_name, douyu_lines)))) + ['\n'] + \
        ["🎤解说频道,#genre#"] + sort_data(commentary_dictionary, list(set(correct_name_data(corrections_name, commentary_lines)))) + ['\n'] + \
        ["🎵音乐频道,#genre#"] + sort_data(music_dictionary, list(set(correct_name_data(corrections_name, music_lines)))) + ['\n'] + \
        ["🍜美食频道,#genre#"] + sort_data(food_dictionary, list(set(correct_name_data(corrections_name, food_lines)))) + ['\n'] + \
        ["✈️旅游频道,#genre#"] + sort_data(travel_dictionary, list(set(correct_name_data(corrections_name, travel_lines)))) + ['\n'] + \
        ["🏥健康频道,#genre#"] + sort_data(health_dictionary, list(set(correct_name_data(corrections_name, health_lines)))) + ['\n'] + \
        ["📰新闻频道,#genre#"] + sort_data(news_dictionary, list(set(correct_name_data(corrections_name, news_lines)))) + ['\n'] + \
        ["💰财经频道,#genre#"] + sort_data(finance_dictionary, list(set(correct_name_data(corrections_name, finance_lines)))) + ['\n'] + \
        ["🛍️购物频道,#genre#"] + sort_data(shopping_dictionary, list(set(correct_name_data(corrections_name, shopping_lines)))) + ['\n'] + \
        ["🎮游戏频道,#genre#"] + sort_data(game_dictionary,set(correct_name_data(corrections_name,game_lines))) + ['\n'] + \
        ["🎭戏曲频道,#genre#"] + sorted(set(correct_name_data(corrections_name, traditional_opera_lines))) + ['\n'] + \
        ["🎭综艺频道,#genre#"] + sorted(set(correct_name_data(corrections_name, variety_lines))) + ['\n'] + \
        ["🧨历届春晚,#genre#"] + sort_data(spring_festival_gala_dictionary,list(set(spring_festival_gala_lines)))  + ['\n'] + \
        ["⭐收藏频道,#genre#"] + sort_data(favorite_dictionary, list(set(correct_name_data(corrections_name, favorite_lines)))) + ['\n'] + \
        ["⚽️体育频道,#genre#"] + sort_data(sports_dictionary,set(correct_name_data(corrections_name,sports_lines))) + ['\n'] + \
        ["🏆️体育赛事,#genre#"] + normalized_tyss_lines + ['\n'] + \
        ["🏈咪咕赛事,#genre#"] + mgss_lines + ['\n'] + \
        ["👑专享央视,#genre#"] + read_txt_to_array('assets/livesource/手工区/优质央视.txt') + ['\n'] + \
        ["☕️专享卫视,#genre#"] + read_txt_to_array('assets/livesource/手工区/优质卫视.txt') + ['\n'] + \
        ["🏞️景区直播,#genre#"] + sorted(set(correct_name_data(corrections_name,camera_lines))) + ['\n'] + \
        ["📦其他频道,#genre#"] + sorted(set(other_lines)) + ['\n'] + \
        ["🕒更新时间,#genre#"] + [version] + [about] + [MTV1] + [MTV2] + [MTV3] + [MTV4] + [MTV5] + read_txt_to_array('assets/livesource/手工区/about.txt') + ['\n']

# 定义输出文件名
output_others = "output/others.txt"
output_full = "output/full.txt"
output_lite = "output/lite.txt"
output_custom = "output/custom.txt"

# 写入文件
try:
    with open(output_full, 'w', encoding='utf-8') as f:
        for line in playlist_full:
            f.write(line + '\n')
    print(f"✅ 完整版播放列表已保存: {output_full}")

    with open(output_lite, 'w', encoding='utf-8') as f:
        for line in playlist_lite:
            f.write(line + '\n')
    print(f"✅ 精简版播放列表已保存: {output_lite}")

    with open(output_custom, 'w', encoding='utf-8') as f:
        for line in playlist_custom:
            f.write(line + '\n')
    print(f"✅ 定制版播放列表已保存: {output_custom}")

    with open(output_others, 'w', encoding='utf-8') as f:
        for line in other_lines:
            f.write(line + '\n')
    print(f"✅ 未分类频道列表已保存: {output_others}")

except Exception as e:
    print(f"保存文件时发生错误：{e}")

# 读取频道Logo信息
channels_logos=read_txt_to_array('assets/livesource/logo.txt')

# 根据频道名称获取Logo URL的函数
def get_logo_by_channel_name(channel_name):
    for line in channels_logos:
        if not line.strip():
            continue
        name, url = line.split(',')
        if name == channel_name:
            return url
    return None

# 将TXT文件转换为M3U格式的函数
def make_m3u(txt_file, m3u_file):
    try:
        output_text = '#EXTM3U x-tvg-url="https://live.fanmingming.cn/e.xml"\n'
        with open(txt_file, "r", encoding='utf-8') as file:
            input_text = file.read()
        lines = input_text.strip().split("\n")
        group_name = ""
        for line in lines:
            parts = line.split(",")
            if len(parts) == 2 and "#genre#" in line:
                group_name = parts[0]
            elif len(parts) == 2:
                channel_name = parts[0]
                channel_url = parts[1]
                logo_url=get_logo_by_channel_name(channel_name)
                if logo_url is None:
                    output_text += f"#EXTINF:-1 group-title=\"{group_name}\",{channel_name}\n"
                    output_text += f"{channel_url}\n"
                else:
                    output_text += f"#EXTINF:-1  tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\"  group-title=\"{group_name}\",{channel_name}\n"
                    output_text += f"{channel_url}\n"
        with open(f"{m3u_file}", "w", encoding='utf-8') as file:
            file.write(output_text)

        print(f"▶️ M3U文件 '{m3u_file}' 生成成功。")
    except Exception as e:
        print(f"发生错误: {e}")

# 生成M3U文件
make_m3u(output_full, output_full.replace(".txt", ".m3u"))
make_m3u(output_lite, output_lite.replace(".txt", ".m3u"))
make_m3u(output_custom, output_custom.replace(".txt", ".m3u"))

# ========= 统计信息 =========

# 计算执行时间
print(f"\n📊 处理统计")
timeend = datetime.now()
elapsed_time = timeend - timestart
total_seconds = elapsed_time.total_seconds()
minutes = int(total_seconds // 60)
seconds = int(total_seconds % 60)
print(f"   开始时间: {timestart.strftime('%Y%m%d %H:%M:%S')}")
print(f"   结束时间: {timeend.strftime('%Y%m%d %H:%M:%S')}")
print(f"   执行时间: {minutes} 分 {seconds} 秒")

# 频道数据统计
print(f"\n📈 数据统计")
print(f"   黑名单条数: {len(combined_blacklist)}")
print(f"   其他源条数: {len(other_lines)}")
print(f"   完整版条数: {len(playlist_full)}")
print(f"   精简版条数: {len(playlist_lite)}")
print(f"   定制版条数: {len(playlist_custom)}")

# 频道分类统计
print(f"\n📝 分类统计:")

print(f"📺 主·频·道")
print(f"   🌐 央视频道: {len(yangshi_lines)}")
print(f"   📡 卫视频道: {len(weishi_lines)}")

print(f"🏠 地·方·台")
print(f"   🏛️ 北京频道: {len(beijing_lines)}")
print(f"   🏙️ 上海频道: {len(shanghai_lines)}")
print(f"   🦁 广东频道: {len(guangdong_lines)}")
print(f"   🍃 江苏频道: {len(jiangsu_lines)}")
print(f"   🧵 浙江频道: {len(zhejiang_lines)}")
print(f"   ⛰️ 山东频道: {len(shandong_lines)}")
print(f"   🐼 四川频道: {len(sichuan_lines)}")
print(f"   ⚔️ 河南频道: {len(henan_lines)}")
print(f"   🌶️ 湖南频道: {len(hunan_lines)}")
print(f"   🍲 重庆频道: {len(chongqing_lines)}")
print(f"   🚢 天津频道: {len(tianjin_lines)}")
print(f"   🌉 湖北频道: {len(hubei_lines)}")
print(f"   🌾 安徽频道: {len(anhui_lines)}")
print(f"   🌊 福建频道: {len(fujian_lines)}")
print(f"   🏭 辽宁频道: {len(liaoning_lines)}")
print(f"   🗿 陕西频道: {len(shaanxi_lines)}")
print(f"   ⛩️ 河北频道: {len(hebei_lines)}")
print(f"   🍶 江西频道: {len(jiangxi_lines)}")
print(f"   💃 广西频道: {len(guangxi_lines)}")
print(f"   ☁️ 云南频道: {len(yunnan_lines)}")
print(f"   🏮 山西频道: {len(shanxi_lines)}")
print(f"   ❄️ 黑·龙·江: {len(heilongjiang_lines)}")
print(f"   🎎 吉林频道: {len(jilin_lines)}")
print(f"   🌈 贵州频道: {len(guizhou_lines)}")
print(f"   🐫 甘肃频道: {len(gansu_lines)}")
print(f"   🐎 内·蒙·古: {len(neimenggu_lines)}")
print(f"   🍇 新疆频道: {len(xinjiang_lines)}")
print(f"   🏝️ 海南频道: {len(hainan_lines)}")
print(f"   🕌 宁夏频道: {len(ningxia_lines)}")
print(f"   🐑 青海频道: {len(qinghai_lines)}")
print(f"   🐐 西藏频道: {len(xizang_lines)}")

print(f"🇭🇰 港·澳·台")
print(f"   🇭🇰 香港频道: {len(hongkong_lines)}")
print(f"   🇲🇴 澳门频道: {len(macau_lines)}")
print(f"   🇨🇳 台湾频道: {len(taiwan_lines)}")

print(f"👑 定·制·台")
print(f"   📶 数字频道: {len(digital_lines)}")
print(f"   🎬 电影频道: {len(movie_lines)}")
print(f"   📺 电·视·剧: {len(tv_drama_lines)}")
print(f"   📽️ 纪·录·片: {len(documentary_lines)}")
print(f"   🦊 动·画·片: {len(cartoon_lines)}")
print(f"   📻 收·音·机: {len(radio_lines)}")
print(f"   🎭 综艺频道: {len(variety_lines)}")
print(f"   🐯 虎牙频道: {len(huya_lines)}")
print(f"   🐠 斗鱼频道: {len(douyu_lines)}")
print(f"   🎤 解说频道: {len(commentary_lines)}")
print(f"   🎵 音乐频道: {len(music_lines)}")
print(f"   🍜 美食频道: {len(food_lines)}")
print(f"   ✈️ 旅游频道: {len(travel_lines)}")
print(f"   🏥 健康频道: {len(health_lines)}")
print(f"   💰 财经频道: {len(finance_lines)}")
print(f"   🛍️ 购物频道: {len(shopping_lines)}")
print(f"   🎮 游戏频道: {len(game_lines)}")
print(f"   📰 新闻频道: {len(news_lines)}")
print(f"   🇨🇳 中国频道: {len(china_lines)}")
print(f"   🌐 国际频道: {len(international_lines)}")
print(f"   ⚽️ 体育频道: {len(sports_lines)}")
print(f"   🏆️ 体育赛事: {len(filtered_tyss_lines)}")
print(f"   🏈 咪咕赛事: {len(mgss_lines)}")
print(f"   🎭 戏曲频道: {len(traditional_opera_lines)}")
print(f"   🧨 历届春晚: {len(spring_festival_gala_lines)}")
print(f"   🏞️ 景区直播: {len(camera_lines)}")
print(f"   ⭐ 收藏频道: {len(favorite_lines)}")

print(f"\n📦 其他未分类: {len(other_lines)}")

print("\n🎉🎉🎉 全部处理完成!✅🚀")

# ====== 直播源聚合处理工具 v1.00 ======
