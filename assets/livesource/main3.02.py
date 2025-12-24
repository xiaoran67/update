#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ====== 直播源聚合处理工具 v3.02 ======
# ======= LiveSource-Collector =======
# ========= 基于v2.00，重构版 =========

# ========= 模块导入区 =========
import urllib.request
from urllib.parse import urlparse
import re  # 正则
import os
from datetime import datetime, timedelta, timezone
import random
import opencc  # 简繁转换
import socket
import time

# ========= 初始化输出目录 =========
os.makedirs('output', exist_ok=True)  # 创建输出目录，如果已存在则不会报错
print(f"📁 创建输出目录: output")

# ========= 频道分类配置 =========
# 基于v2.00的所有分类，重构的结构化配置方式
CHANNEL_CONFIG = {
    # 主频道
    "yangshi": {"lines": [], "title": "🌐央视频道", "file": "主频道/CCTV.txt"},
    "weishi": {"lines": [], "title": "📡卫视频道", "file": "主频道/卫视.txt"},
    
    # 地方台（省级）
    "beijing": {"lines": [], "title": "🏛️北京频道", "file": "地方台/北京.txt"},
    "shanghai": {"lines": [], "title": "🏙️上海频道", "file": "地方台/上海.txt"},
    "guangdong": {"lines": [], "title": "🦁广东频道", "file": "地方台/广东.txt"},
    "jiangsu": {"lines": [], "title": "🍃江苏频道", "file": "地方台/江苏.txt"},
    "zhejiang": {"lines": [], "title": "🧵浙江频道", "file": "地方台/浙江.txt"},
    "shandong": {"lines": [], "title": "⛰️山东频道", "file": "地方台/山东.txt"},
    "sichuan": {"lines": [], "title": "🐼四川频道", "file": "地方台/四川.txt"},
    "henan": {"lines": [], "title": "⚔️河南频道", "file": "地方台/河南.txt"},
    "hunan": {"lines": [], "title": "🌶️湖南频道", "file": "地方台/湖南.txt"},
    "chongqing": {"lines": [], "title": "🍲重庆频道", "file": "地方台/重庆.txt"},
    "tianjin": {"lines": [], "title": "🚢天津频道", "file": "地方台/天津.txt"},
    "hubei": {"lines": [], "title": "🌉湖北频道", "file": "地方台/湖北.txt"},
    "anhui": {"lines": [], "title": "🌾安徽频道", "file": "地方台/安徽.txt"},
    "fujian": {"lines": [], "title": "🌊福建频道", "file": "地方台/福建.txt"},
    "liaoning": {"lines": [], "title": "🏭辽宁频道", "file": "地方台/辽宁.txt"},
    "shaanxi": {"lines": [], "title": "🗿陕西频道", "file": "地方台/陕西.txt"},
    "hebei": {"lines": [], "title": "⛩️河北频道", "file": "地方台/河北.txt"},
    "jiangxi": {"lines": [], "title": "🍶江西频道", "file": "地方台/江西.txt"},
    "guangxi": {"lines": [], "title": "💃广西频道", "file": "地方台/广西.txt"},
    "yunnan": {"lines": [], "title": "☁️云南频道", "file": "地方台/云南.txt"},
    "shanxi": {"lines": [], "title": "🏮山西频道", "file": "地方台/山西.txt"},
    "heilongjiang": {"lines": [], "title": "❄️黑·龙·江", "file": "地方台/黑龙江.txt"},
    "jilin": {"lines": [], "title": "🎎吉林频道", "file": "地方台/吉林.txt"},
    "guizhou": {"lines": [], "title": "🌈贵州频道", "file": "地方台/贵州.txt"},
    "gansu": {"lines": [], "title": "🐫甘肃频道", "file": "地方台/甘肃.txt"},
    "neimenggu": {"lines": [], "title": "🐎内·蒙·古", "file": "地方台/内蒙古.txt"},
    "xinjiang": {"lines": [], "title": "🍇新疆频道", "file": "地方台/新疆.txt"},
    "hainan": {"lines": [], "title": "🏝️海南频道", "file": "地方台/海南.txt"},
    "ningxia": {"lines": [], "title": "🕌宁夏频道", "file": "地方台/宁夏.txt"},
    "qinghai": {"lines": [], "title": "🐑青海频道", "file": "地方台/青海.txt"},
    "xizang": {"lines": [], "title": "🐐西藏频道", "file": "地方台/西藏.txt"},
    
    # 港澳台
    "hongkong": {"lines": [], "title": "🇭🇰香港频道", "file": "地方台/香港.txt"},
    "macau": {"lines": [], "title": "🇲🇴澳门频道", "file": "地方台/澳门.txt"},
    "taiwan": {"lines": [], "title": "🇨🇳台湾频道", "file": "地方台/台湾.txt"},
    
    # 定制分类
    "digital": {"lines": [], "title": "📶数字频道", "file": "主频道/数字.txt"},
    "movie": {"lines": [], "title": "🎬电影频道", "file": "主频道/电影.txt"},
    "tv_drama": {"lines": [], "title": "📺电·视·剧", "file": "主频道/电视剧.txt"},
    "documentary": {"lines": [], "title": "📽️纪·录·片", "file": "主频道/纪录片.txt"},
    "cartoon": {"lines": [], "title": "🦊动·画·片", "file": "主频道/动画片.txt"},
    "radio": {"lines": [], "title": "📻收·音·机", "file": "主频道/收音机.txt"},
    "variety": {"lines": [], "title": "🎭综艺频道", "file": "主频道/综艺.txt"},
    "huya": {"lines": [], "title": "🐯虎牙直播", "file": "主频道/虎牙.txt"},
    "douyu": {"lines": [], "title": "🐠斗鱼直播", "file": "主频道/斗鱼.txt"},
    "commentary": {"lines": [], "title": "🎤解说频道", "file": "主频道/解说.txt"},
    "music": {"lines": [], "title": "🎵音乐频道", "file": "主频道/音乐.txt"},
    "food": {"lines": [], "title": "🍜美食频道", "file": "主频道/美食.txt"},
    "travel": {"lines": [], "title": "✈️旅游频道", "file": "主频道/旅游.txt"},
    "health": {"lines": [], "title": "🏥健康频道", "file": "主频道/健康.txt"},
    "finance": {"lines": [], "title": "💰财经频道", "file": "主频道/财经.txt"},
    "shopping": {"lines": [], "title": "🛍️购物频道", "file": "主频道/购物.txt"},
    "game": {"lines": [], "title": "🎮游戏频道", "file": "主频道/游戏.txt"},
    "news": {"lines": [], "title": "📰新闻频道", "file": "主频道/新闻.txt"},
    "china": {"lines": [], "title": "🇨🇳中国综合", "file": "主频道/中国.txt"},
    "international": {"lines": [], "title": "🌐国际频道", "file": "主频道/国际.txt"},
    "sports": {"lines": [], "title": "⚽️体育频道", "file": "主频道/体育.txt"},
    "tyss": {"lines": [], "title": "🏆️体育赛事", "file": "主频道/体育赛事.txt"},
    "mgss": {"lines": [], "title": "🏈咪咕赛事", "file": "主频道/咪咕赛事.txt"},
    "traditional_opera": {"lines": [], "title": "🎭戏曲频道", "file": "主频道/戏曲.txt"},
    "spring_festival_gala": {"lines": [], "title": "🧨历届春晚", "file": "主频道/春晚.txt"},
    "camera": {"lines": [], "title": "🏞️景区直播", "file": "主频道/直播中国.txt"},
    "favorite": {"lines": [], "title": "⭐收藏频道", "file": "主频道/收藏频道.txt"},
}

# ========= 分类显示顺序 =========
CATEGORY_ORDER = [
    # 主频道
    "yangshi", "weishi",
    
    # 地方台
    "beijing", "shanghai", "guangdong", "jiangsu", "zhejiang",
    "shandong", "sichuan", "henan", "hunan", "chongqing",
    "tianjin", "hubei", "anhui", "fujian", "liaoning", "shaanxi",
    "hebei", "jiangxi", "guangxi", "yunnan", "shanxi", "heilongjiang",
    "jilin", "guizhou", "gansu", "neimenggu", "xinjiang", "hainan",
    "ningxia", "qinghai", "xizang",
    
    # 港澳台
    "hongkong", "macau", "taiwan",
    
    # 定制分类
    "digital", "movie", "tv_drama", "documentary", "cartoon", "radio",
    "variety", "huya", "douyu", "commentary", "music", "food", "travel",
    "health", "finance", "shopping", "game", "news", "china", "international",
    "sports", "tyss", "mgss", "traditional_opera", "spring_festival_gala",
    "camera", "favorite",
]

# ========= 全局状态类 =========
class GlobalState:
    def __init__(self):
        self.start_time = None
        self.processed_urls = set()  # 全局URL去重集合
        self.combined_blacklist = set()  # 合并黑名单
        self.corrections_name = {}  # 频道名称纠错字典
        self.other_lines = []  # 其他频道行
        self.other_lines_url = set()  # 其他频道URL（用于去重）
        self.manual_sources = {}  # 手工区源
        
        # 统计信息
        self.stats = {
            'total_processed': 0,  # 总处理URL数
            'blacklisted': 0,      # 黑名单过滤数
            'categories': {}       # 各分类统计
        }

g = GlobalState()

# ========= 工具函数 =========
def traditional_to_simplified(text: str) -> str:
    """繁体转简体"""
    converter = opencc.OpenCC('t2s')
    return converter.convert(text)

def get_beijing_time():
    """获取北京时间"""
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=8)

def read_txt_to_array(file_name):
    """读取文本文件内容到数组"""
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            lines = [line.strip() for line in lines if line.strip()]
            return lines
    except FileNotFoundError:
        print(f"❌ 文件未找到: {file_name}")
        return []
    except Exception as e:
        print(f"❌ 读取文件错误 {file_name}: {e}")
        return []

def get_random_user_agent():
    """获取随机User-Agent"""
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
    ]
    return random.choice(USER_AGENTS)

def clean_url(url):
    """清理URL（移除$后的参数）"""
    last_dollar_index = url.rfind('$')
    if last_dollar_index != -1:
        return url[:last_dollar_index]
    return url

def get_url_file_extension(url):
    """获取URL文件扩展名"""
    parsed_url = urlparse(url)
    path = parsed_url.path
    extension = os.path.splitext(path)[1]
    return extension

def convert_m3u_to_txt(m3u_content):
    """将M3U格式转换为TXT格式"""
    lines = m3u_content.split('\n')
    txt_lines = []
    channel_name = ""
    for line in lines:
        if line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            channel_name = line.split(',')[-1].strip()
        elif line.startswith("http") or line.startswith("rtmp") or line.startswith("p3p"):
            txt_lines.append(f"{channel_name},{line.strip()}")
        
        if "#genre#" not in line and "," in line and "://" in line:
            pattern = r'^[^,]+,[^\s]+://[^\s]+$'
            if bool(re.match(pattern, line)):
                txt_lines.append(line)
    
    return '\n'.join(txt_lines)

def process_name_string(input_str):
    """处理频道名称字符串（主要用于处理CCTV频道名）"""
    parts = input_str.split(',')
    processed_parts = []
    for part in parts:
        processed_part = process_part(part)
        processed_parts.append(processed_part)
    result_str = ','.join(processed_parts)
    return result_str

def process_part(part_str):
    """处理单个频道名称部分"""
    if "CCTV" in part_str and "://" not in part_str:
        part_str = part_str.replace("IPV6", "")
        part_str = part_str.replace("PLUS", "+")
        part_str = part_str.replace("1080", "")
        filtered_str = ''.join(char for char in part_str if char.isdigit() or char == 'K' or char == '+')
        if not filtered_str.strip():
            filtered_str = part_str.replace("CCTV", "")
        if len(filtered_str) > 2 and re.search(r'4K|8K', filtered_str):
            filtered_str = re.sub(r'(4K|8K).*', r'\1', filtered_str)
            if len(filtered_str) > 2: 
                filtered_str = re.sub(r'(4K|8K)', r'(\1)', filtered_str)
        return "CCTV" + filtered_str 
    elif "卫视" in part_str:
        pattern = r'卫视「.*」'
        result_str = re.sub(pattern, '卫视', part_str)
        return result_str
    return part_str

# ========= 频道名称清理 =========
REMOVAL_LIST = [
    "_电信", "电信", "频道", "频陆", "备陆", "壹陆", "贰陆", "叁陆", "肆陆", "伍陆",
    "陆陆", "柒陆", "肆柒", "频英", "频特", "频国", "频晴", "频粤", "高清", "超清",
    "标清", "斯特", "粤陆", "国陆", "频壹", "频贰", "肆贰", "频测", "咪咕", "闽特",
    "高特", "频高", "频标", "汝阳", "频效", "国标", "粤标", "频推", "频流", "粤高",
    "频限", "实时", "美推", "频美", "英陆", "(北美)", "「回看」", "[超清]", "「IPV4」",
    "「IPV6」", "_ITV", "(HK)", "AKtv", "HD", "[HD]", "(HD)", "（HD）", "{HD}", "<HD>",
    "-HD", "[BD]", "SD", "[SD]", "(SD)", "{SD}", "<SD>", "[VGA]", "4Gtv", "1080",
    "720", "480", "VGA", "4K", "(4K)", "{4K}", "<4K>", "(VGA)", "{VGA}", "<VGA>",
    "「4gTV」", "「LiTV」"
]

def clean_channel_name(channel_name, removal_list=REMOVAL_LIST):
    """清理频道名称"""
    for item in removal_list:
        channel_name = channel_name.replace(item, "")

    if channel_name.endswith("HD"):
        channel_name = channel_name[:-2]
    
    if channel_name.endswith("台") and len(channel_name) > 3:
        channel_name = channel_name[:-1]

    return channel_name

def correct_name_data(corrections, data):
    """修正频道名称数据"""
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

def sort_data(order, data):
    """按指定顺序排序数据"""
    order_dict = {name: i for i, name in enumerate(order)}
    def sort_key(line):
        name = line.split(',')[0]
        return order_dict.get(name, len(order))
    sorted_data = sorted(data, key=sort_key)
    return sorted_data

# ========= 字典文件加载 =========
def load_dictionaries():
    """加载所有频道字典"""
    print(f"\n📚 加载频道字典...")
    dictionaries = {}
    
    for category_id, config in CHANNEL_CONFIG.items():
        file_path = os.path.join('assets/livesource', config['file'])
        if os.path.exists(file_path):
            dictionaries[category_id] = read_txt_to_array(file_path)
            print(f"   ✅ {config['title']}: {len(dictionaries[category_id])}条")
        else:
            dictionaries[category_id] = []
            print(f"   ⚠️  {file_path}: 文件不存在")
    
    print(f"✅ 字典加载完成，共 {len(dictionaries)} 个分类")
    return dictionaries

def load_corrections_name():
    """加载频道名称修正字典"""
    filename = 'assets/livesource/corrections_name.txt'
    corrections = {}
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释行
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) >= 2:
                    correct_name = parts[0]
                    for name in parts[1:]:
                        if name:
                            corrections[name] = correct_name
    except FileNotFoundError:
        print(f"⚠️  修正字典文件未找到: {filename}")
    except Exception as e:
        print(f"❌ 加载修正字典错误: {e}")
    
    print(f"✅ 修正字典加载: {len(corrections)} 条规则")
    if corrections:
        print(f"📝 示例规则:")
        for i, (wrong_name, correct_name) in enumerate(list(corrections.items())[:3]):
            print(f"  {i+1}. '{wrong_name}' → '{correct_name}'")
        if len(corrections) > 3:
            print(f"  ... 还有 {len(corrections) - 3} 条")
    
    return corrections

def load_blacklist():
    """加载黑名单"""
    print(f"\n🚫 加载黑名单...")
    
    def read_blacklist_from_txt(file_path):
        blacklist = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            for line in lines:
                if ',' in line:
                    url = line.split(',')[1].strip()
                    cleaned_url = clean_url(url)
                    blacklist.add(cleaned_url)
        except Exception as e:
            print(f"❌ 读取黑名单错误 {file_path}: {e}")
        return blacklist
    
    # 读取自动和手动维护的黑名单
    blacklist_auto = read_blacklist_from_txt('assets/livesource/blacklist/blacklist_auto.txt') 
    blacklist_manual = read_blacklist_from_txt('assets/livesource/blacklist/blacklist_manual.txt') 
    
    # 合并黑名单
    combined_blacklist = set(blacklist_auto.union(blacklist_manual))
    
    print(f"🔧 自动维护: {len(blacklist_auto)} 条")
    print(f"✏️ 手动维护: {len(blacklist_manual)} 条")
    print(f"🔄 合并去重: {len(combined_blacklist)} 条")
    
    # 显示示例
    if combined_blacklist:
        print(f"📋 黑名单示例 (前3条):")
        for i, url in enumerate(list(combined_blacklist)[:3]):
            print(f"  {i+1}. {url[:80]}..." if len(url) > 80 else f"  {i+1}. {url}")
        if len(combined_blacklist) > 3:
            print(f"  ... 还有 {len(combined_blacklist) - 3} 条")
    
    return combined_blacklist

# ========= 核心处理函数 =========
def process_channel_line(line, dictionaries, is_manual=False):
    """处理单行频道信息（v2.00逻辑，使用配置化结构）"""
    # 检查是否为有效的频道行
    if "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
        # 分割行，获取原始频道名称和URL
        parts = line.split(',', 1)
        if len(parts) < 2:
            return
        
        channel_name = parts[0].strip()
        channel_address = parts[1].strip()
        
        # 清理URL
        channel_address = clean_url(channel_address)
        
        # 黑名单检查
        if channel_address in g.combined_blacklist:
            print(f"🚫 黑名单过滤: {channel_name}")
            g.stats['blacklisted'] += 1
            return
        
        # 全局URL去重检查
        if channel_address in g.processed_urls:
            print(f"🔄 URL去重: {channel_name}")
            return
        
        g.processed_urls.add(channel_address)
        g.stats['total_processed'] += 1
        
        # 清理频道名称
        channel_name = clean_channel_name(channel_name)
        # 繁体转简体
        channel_name = traditional_to_simplified(channel_name)
        
        # 频道名称纠错
        if channel_name in g.corrections_name:
            corrected_name = g.corrections_name[channel_name]
            if corrected_name != channel_name:
                print(f"🔧 名称纠错: {channel_name} -> {corrected_name}")
                channel_name = corrected_name
        
        # 重新组合行
        processed_line = channel_name + "," + channel_address
        
        # 按配置顺序匹配分类
        matched = False
        
        # 优先处理特殊分类
        # 1. 央视频道（CCTV关键词匹配）
        if "CCTV" in channel_name:
            CHANNEL_CONFIG["yangshi"]["lines"].append(process_name_string(processed_line))
            matched = True
        
        # 2. 卫视频道（精确匹配）
        elif not matched and channel_name in dictionaries.get("weishi", []):
            CHANNEL_CONFIG["weishi"]["lines"].append(process_name_string(processed_line))
            matched = True
        
        # 3. 体育赛事（关键词匹配）
        elif not matched and any(tyss_keyword in channel_name for tyss_keyword in dictionaries.get("tyss", [])):
            CHANNEL_CONFIG["tyss"]["lines"].append(process_name_string(processed_line))
            matched = True
        
        # 4. 咪咕赛事（关键词匹配）
        elif not matched and any(mgss_keyword in channel_name for mgss_keyword in dictionaries.get("mgss", [])):
            CHANNEL_CONFIG["mgss"]["lines"].append(process_name_string(processed_line))
            matched = True
        
        # 5. 定制分类（精确匹配）
        if not matched:
            for category_id in CATEGORY_ORDER:
                if category_id in ["yangshi", "weishi", "tyss", "mgss"]:
                    continue  # 已经处理过
                    
                config = CHANNEL_CONFIG[category_id]
                dict_list = dictionaries.get(category_id, [])
                
                if channel_name in dict_list:
                    config["lines"].append(process_name_string(processed_line))
                    matched = True
                    break
        
        # 如果未匹配到任何分类，放入other_lines
        if not matched:
            if channel_address not in g.other_lines_url:
                g.other_lines_url.add(channel_address)
                g.other_lines.append(processed_line)

def process_url(url, dictionaries):
    """处理单个URL（基于v2.00逻辑）"""
    try:
        g.other_lines.append("◆◆◆　" + url)
        req = urllib.request.Request(url)
        req.add_header('User-Agent', get_random_user_agent())

        with urllib.request.urlopen(req) as response:
            data = response.read()
            text = data.decode('utf-8')
            text = text.strip()
            
            # 判断是否为M3U格式
            is_m3u = text.startswith("#EXTM3U") or text.startswith("#EXTINF")
            if get_url_file_extension(url) in [".m3u", ".m3u8"] or is_m3u:
                text = convert_m3u_to_txt(text)

            lines = text.split('\n')
            print(f"行数: {len(lines)}")

            for line in lines:
                if "#genre#" not in line and "," in line and "://" in line and "tvbus://" not in line and "/udp/" not in line:
                    channel_name, channel_address = line.split(',', 1)
                    if "#" not in channel_address:
                        process_channel_line(line, dictionaries)
                    else:
                        url_list = channel_address.split('#')
                        for channel_url in url_list:
                            newline = f'{channel_name},{channel_url}'
                            process_channel_line(newline, dictionaries)

            g.other_lines.append('\n')

    except Exception as e:
        print(f"❌ 处理URL时发生错误：{e}")

# ========= 白名单处理 =========
def process_whitelist(dictionaries):
    """处理白名单自动文件（基于v2.00逻辑）"""
    print(f"\n🟢 处理白名单自动文件...")
    whitelist_auto_lines = read_txt_to_array('assets/livesource/blacklist/whitelist_auto.txt')
    
    print(f"📖 读取到 {len(whitelist_auto_lines)} 条记录")
    print(f"⏭️ 跳过标题行和表头...")
    
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
                    print(f"❌ response_time转换失败: {whitelist_line}")
                    response_time = 60000
                
                # 只处理响应时间小于2秒的高质量源
                if response_time < 2000:
                    process_channel_line(",".join(whitelist_parts[1:]), dictionaries)
    
    print(f"有效白名单记录: {valid_whitelist_count} 条")
    if valid_whitelist_samples:
        print(f"📋 白名单示例 (前3条):")
        for i, line in enumerate(valid_whitelist_samples[:3]):
            truncated = line[:80] + "..." if len(line) > 80 else line
            print(f"  {i+1}. {truncated}")
        if valid_whitelist_count > 3:
            print(f"  ... 还有 {valid_whitelist_count - 3} 条")
    print()

# ========= AKTV特殊处理 =========
def process_aktv(dictionaries):
    """处理AKTV直播源（基于v2.00逻辑）"""
    print(f"📺 获取AKTV直播源...")
    
    # AKTV源地址
    aktv_url = "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/assets/livesource/blacklist/whitelist_manual.txt"
    
    # 尝试从网络获取
    def get_http_response(url, timeout=8, retries=2):
        headers = {'User-Agent': get_random_user_agent()}
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    data = response.read()
                    return data.decode('utf-8')
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(1.0 * (2 ** attempt))
                else:
                    print(f"❌ HTTP请求失败: {e}")
        return None
    
    aktv_text = get_http_response(aktv_url)
    aktv_lines = []
    
    if aktv_text:
        print(f"✅ AKTV成功获取内容")
        aktv_text = convert_m3u_to_txt(aktv_text)
        aktv_lines = aktv_text.strip().split('\n')
    else:
        print(f"⚠️ AKTV请求失败，从本地获取！")
        aktv_lines = read_txt_to_array('assets/livesource/手工区/AKTV.txt')
    
    print(f"处理AKTV数据，共 {len(aktv_lines)} 行")
    
    # 统计信息
    print(f"📊 AKTV频道统计:")
    if aktv_lines:
        print(f"📋 AKTV频道示例 (前3条):")
        for i, line in enumerate(aktv_lines[:3]):
            truncated = line[:60] + "..." if len(line) > 60 else line
            print(f"  {i+1}. {truncated}")
        if len(aktv_lines) > 3:
            print(f"  ... 还有 {len(aktv_lines) - 3} 条")
    
    # 处理AKTV数据
    for line in aktv_lines:
        process_channel_line(line, dictionaries)

# ========= 手工区处理 =========
def process_manual_sources():
    """处理手工区高质量源（基于v2.00逻辑）"""
    print(f"\n🔧 处理手工区高质量源...")
    
    # 手工区文件列表
    manual_files = {
        'zhejiang': '浙江频道.txt',
        'guangdong': '广东频道.txt',
        'hubei': '湖北频道.txt',
        'shanghai': '上海频道.txt',
        'jiangsu': '江苏频道.txt'
    }
    
    total_manual = 0
    for region, filename in manual_files.items():
        filepath = f'assets/livesource/手工区/{filename}'
        lines = read_txt_to_array(filepath)
        if lines:
            print(f"✅ {filename}: {len(lines)} 条")
            # 直接添加到对应分类的行中
            if region in CHANNEL_CONFIG:
                CHANNEL_CONFIG[region]["lines"].extend(lines)
                total_manual += len(lines)
        else:
            print(f"⚠️  {filename}: 文件为空或不存在")
    
    print(f"手工区总计: {total_manual} 条")

# ========= 体育赛事处理 =========
def normalize_date_to_md(text):
    """将日期格式规范化为MM-DD格式（基于v2.00逻辑）"""
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

def filter_lines(lines, exclude_keywords):
    """过滤包含特定关键词的行"""
    return [line for line in lines if not any(keyword in line for keyword in exclude_keywords)]

def custom_tyss_sort(lines):
    """自定义体育赛事排序函数（数字前缀的倒序，其他正序）"""
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

def generate_playlist_html(data_list, output_file='output/tiyu.html'):
    """生成体育赛事HTML页面（基于v2.00逻辑）"""
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
    print(f"✅ 体育赛事网页已生成：{output_file}")

def process_tyss_data():
    """处理体育赛事数据（基于v2.00逻辑）"""
    print(f"\n🏆 处理体育赛事数据...")
    
    # 从配置中获取体育赛事行
    tyss_lines = CHANNEL_CONFIG["tyss"]["lines"]
    
    if not tyss_lines:
        print(f"⚠️  没有找到体育赛事数据")
        return None
    
    # 日期格式化
    normalized_tyss_lines = [normalize_date_to_md(s) for s in tyss_lines]
    
    # 过滤关键词
    keywords_to_exclude_tiyu_txt = ["玉玉软件", "榴芒电视", "公众号", "麻豆", "「回看」"]
    keywords_to_exclude_tiyu = ["玉玉软件", "榴芒电视", "公众号", "咪视通", "麻豆", "「回看」"]
    
    # 应用过滤
    normalized_tyss_lines = filter_lines(normalized_tyss_lines, keywords_to_exclude_tiyu_txt)
    
    # 去重并排序
    normalized_tyss_lines = custom_tyss_sort(set(normalized_tyss_lines))
    
    # 进一步过滤
    filtered_tyss_lines = filter_lines(normalized_tyss_lines, keywords_to_exclude_tiyu)
    
    print(f"✅ 体育赛事处理完成：原始 {len(tyss_lines)} 条，过滤后 {len(filtered_tyss_lines)} 条")
    
    # 生成HTML文件
    generate_playlist_html(filtered_tyss_lines, 'output/tiyu.html')
    
    # 生成TXT文件
    with open('output/tiyu.txt', 'w', encoding='utf-8') as f:
        for line in filtered_tyss_lines:
            f.write(line + '\n')
    print(f"✅ 体育赛事文本已生成: output/tiyu.txt")
    
    return filtered_tyss_lines

# ========= 今日推荐和版本信息 =========
def get_random_url(file_path):
    """从文件中随机获取URL（基于v2.00逻辑）"""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if ',' in line:
                    url = line.strip().split(',')[-1]
                    urls.append(url)
    except Exception as e:
        print(f"❌ 读取随机URL文件错误 {file_path}: {e}")
    return random.choice(urls) if urls else ""

# ========= 生成输出文件 =========
def generate_output_files(filtered_tyss_lines=None):
    """根据配置生成输出文件（基于v2.00逻辑，使用配置化结构）"""
    print(f"\n📝 生成输出文件...")
    
    # 读取手工区文件
    zhuanxiang_yangshi = read_txt_to_array('assets/livesource/手工区/优质央视.txt')
    zhuanxiang_weishi = read_txt_to_array('assets/livesource/手工区/优质卫视.txt')
    about_info = read_txt_to_array('assets/livesource/手工区/about.txt')
    aktv_lines = read_txt_to_array('assets/livesource/手工区/AKTV.txt')
    
    # 生成今日推荐和版本信息
    beijing_time = get_beijing_time()
    formatted_time = beijing_time.strftime("%Y%m%d %H:%M:%S")
    
    # 今日推荐
    MTV1 = "💯推荐," + (get_random_url('assets/livesource/手工区/今日推荐.txt') or "")
    MTV2 = "🤫低调," + (get_random_url('assets/livesource/手工区/今日推荐.txt') or "")
    MTV3 = "🟢使用," + (get_random_url('assets/livesource/手工区/今日推荐.txt') or "")
    MTV4 = "⚠️禁止," + (get_random_url('assets/livesource/手工区/今日推荐.txt') or "")
    MTV5 = "🚫贩卖," + (get_random_url('assets/livesource/手工区/今日推荐.txt') or "")
    
    # 版本信息
    version = formatted_time + "," + (get_random_url('assets/livesource/手工区/今日推台.txt') or "")
    about = "👨潇然," + (get_random_url('assets/livesource/手工区/今日推台.txt') or "")
    
    # 构建完整版播放列表
    playlist_full = []
    
    # 按配置顺序添加分类
    for category_id in CATEGORY_ORDER:
        if category_id in CHANNEL_CONFIG:
            config = CHANNEL_CONFIG[category_id]
            lines = config["lines"]
            if lines:
                # 对每个分类的行进行去重和排序
                dict_path = os.path.join('assets/livesource', config['file'])
                if os.path.exists(dict_path):
                    order_list = read_txt_to_array(dict_path)
                    sorted_lines = sort_data(order_list, correct_name_data(g.corrections_name, lines))
                    playlist_full.append(f"{config['title']},#genre#")
                    playlist_full.extend(sorted_lines)
                    playlist_full.append('')
                else:
                    # 如果没有字典文件，使用简单排序
                    playlist_full.append(f"{config['title']},#genre#")
                    playlist_full.extend(sorted(set(correct_name_data(g.corrections_name, lines))))
                    playlist_full.append('')
    
    # 添加专享央视和卫视
    if zhuanxiang_yangshi:
        playlist_full.append("👑专享央视,#genre#")
        playlist_full.extend(zhuanxiang_yangshi)
        playlist_full.append('')
    
    if zhuanxiang_weishi:
        playlist_full.append("☕️专享卫视,#genre#")
        playlist_full.extend(zhuanxiang_weishi)
        playlist_full.append('')
    
    # 添加体育赛事（如果已处理）
    if filtered_tyss_lines:
        playlist_full.append("🏆️体育赛事,#genre#")
        playlist_full.extend(filtered_tyss_lines)
        playlist_full.append('')
    
#    # 添加AKTV源
#    if aktv_lines:
#        playlist_full.append("🚀 FreeTV,#genre#")
#        playlist_full.extend(aktv_lines)
#        playlist_full.append('')
    
    # 添加其他分类
    if g.other_lines:
        playlist_full.append("📦其他频道,#genre#")
        playlist_full.extend(sorted(set(g.other_lines)))
        playlist_full.append('')
    
    # 添加更新时间
    playlist_full.append("🕒更新时间,#genre#")
    playlist_full.append(version)
    playlist_full.append(about)
    playlist_full.append(MTV1)
    playlist_full.append(MTV2)
    playlist_full.append(MTV3)
    playlist_full.append(MTV4)
    playlist_full.append(MTV5)
    playlist_full.extend(about_info)
    playlist_full.append('')
    
    # 构建精简版播放列表
    playlist_lite = []
    
    # 1. 央视频道
    yangshi_config = CHANNEL_CONFIG["yangshi"]
    yangshi_lines_list = yangshi_config["lines"]
    if yangshi_lines_list:
        yangshi_dict_path = os.path.join('assets/livesource', yangshi_config['file'])
        if os.path.exists(yangshi_dict_path):
            yangshi_order = read_txt_to_array(yangshi_dict_path)
            yangshi_sorted = sort_data(yangshi_order, correct_name_data(g.corrections_name, yangshi_lines_list))
            playlist_lite.append(f"{yangshi_config['title']},#genre#")
            playlist_lite.extend(yangshi_sorted)
            playlist_lite.append('')
    
    # 2. 卫视频道
    weishi_config = CHANNEL_CONFIG["weishi"]
    weishi_lines_list = weishi_config["lines"]
    if weishi_lines_list:
        weishi_dict_path = os.path.join('assets/livesource', weishi_config['file'])
        if os.path.exists(weishi_dict_path):
            weishi_order = read_txt_to_array(weishi_dict_path)
            weishi_sorted = sort_data(weishi_order, correct_name_data(g.corrections_name, weishi_lines_list))
            playlist_lite.append(f"{weishi_config['title']},#genre#")
            playlist_lite.extend(weishi_sorted)
            playlist_lite.append('')
    
    # 3. 地方台（合并为一个分类）
    print(f"🏠 合并地方台频道...")
    local_categories = [
        "beijing", "shanghai", "guangdong", "jiangsu", "zhejiang",
        "shandong", "sichuan", "henan", "hunan", "chongqing",
        "tianjin", "hubei", "anhui", "fujian", "liaoning", "shaanxi",
        "hebei", "jiangxi", "guangxi", "yunnan", "shanxi", "heilongjiang",
        "jilin", "guizhou", "gansu", "neimenggu", "xinjiang", "hainan",
        "ningxia", "qinghai", "xizang"
    ]
    
    all_local_lines = []
    for local_id in local_categories:
        if local_id in CHANNEL_CONFIG:
            local_config = CHANNEL_CONFIG[local_id]
            local_lines = local_config["lines"]
            if local_lines:
                local_dict_path = os.path.join('assets/livesource', local_config['file'])
                if os.path.exists(local_dict_path):
                    local_order = read_txt_to_array(local_dict_path)
                    local_sorted = sort_data(local_order, correct_name_data(g.corrections_name, local_lines))
                    all_local_lines.extend(local_sorted)
    
    if all_local_lines:
        playlist_lite.append("🏠地·方·台,#genre#")
        # 去重并保持顺序
        seen = set()
        deduplicated_lines = []
        for line in all_local_lines:
            if line not in seen:
                seen.add(line)
                deduplicated_lines.append(line)
        playlist_lite.extend(deduplicated_lines)
        playlist_lite.append('')
        print(f"地方台频道: {len(deduplicated_lines)} 个")
    
    # 4. 添加更新时间
    playlist_lite.append("🕒更新时间,#genre#")
    playlist_lite.append(version)
    playlist_lite.append(about)
    playlist_lite.append(MTV1)
    playlist_lite.append(MTV2)
    playlist_lite.append(MTV3)
    playlist_lite.append(MTV4)
    playlist_lite.append(MTV5)
    playlist_lite.extend(about_info)
    playlist_lite.append('')
    
    # ========= 构建定制版播放列表（与v2.00保持一致） =========
    playlist_custom = []
    
    # 1. 央视频道
    if 'yangshi_sorted' in locals():
        playlist_custom.append("🌐央视频道,#genre#")
        playlist_custom.extend(yangshi_sorted)
        playlist_custom.append('')
    
    # 2. 卫视频道
    if 'weishi_sorted' in locals():
        playlist_custom.append("📡卫视频道,#genre#")
        playlist_custom.extend(weishi_sorted)
        playlist_custom.append('')
    
    # 3. 地方台
    if all_local_lines:
        playlist_custom.append("🏠地·方·台,#genre#")
        playlist_custom.extend(deduplicated_lines)
        playlist_custom.append('')
    
    # 4. 港澳台
    for category_id in ["hongkong", "macau", "taiwan"]:
        if category_id in CHANNEL_CONFIG:
            config = CHANNEL_CONFIG[category_id]
            lines = config["lines"]
            if lines:
                dict_path = os.path.join('assets/livesource', config['file'])
                if os.path.exists(dict_path):
                    order_list = read_txt_to_array(dict_path)
                    sorted_lines = sort_data(order_list, correct_name_data(g.corrections_name, lines))
                    playlist_custom.append(f"{config['title']},#genre#")
                    playlist_custom.extend(sorted_lines)
                    playlist_custom.append('')
    
    # 5. 定制分类
    other_categories = [
        "digital", "movie", "tv_drama", "documentary", "cartoon", "radio",
        "variety", "huya", "douyu", "commentary", "music", "food", "travel",
        "health", "finance", "shopping", "game", "news", "china", "international",
        "sports", "traditional_opera", "spring_festival_gala", "favorite"
    ]
    
    for category_id in other_categories:
        if category_id in CHANNEL_CONFIG:
            config = CHANNEL_CONFIG[category_id]
            lines = config["lines"]
            if lines:
                dict_path = os.path.join('assets/livesource', config['file'])
                if os.path.exists(dict_path):
                    order_list = read_txt_to_array(dict_path)
                    sorted_lines = sort_data(order_list, correct_name_data(g.corrections_name, lines))
                    playlist_custom.append(f"{config['title']},#genre#")
                    playlist_custom.extend(sorted_lines)
                    playlist_custom.append('')
                else:
                    # 如果没有字典文件，使用简单排序
                    playlist_custom.append(f"{config['title']},#genre#")
                    playlist_custom.extend(sorted(set(correct_name_data(g.corrections_name, lines))))
                    playlist_custom.append('')
    
    # 6. 体育赛事和咪咕赛事
    if filtered_tyss_lines:
        playlist_custom.append("🏆️体育赛事,#genre#")
        playlist_custom.extend(filtered_tyss_lines)
        playlist_custom.append('')
    
    mgss_config = CHANNEL_CONFIG["mgss"]
    if mgss_config["lines"]:
        mgss_dict_path = os.path.join('assets/livesource', mgss_config['file'])
        if os.path.exists(mgss_dict_path):
            mgss_order = read_txt_to_array(mgss_dict_path)
            mgss_sorted = sort_data(mgss_order, correct_name_data(g.corrections_name, mgss_config["lines"]))
            playlist_custom.append("🏈咪咕赛事,#genre#")
            playlist_custom.extend(mgss_sorted)
            playlist_custom.append('')
    
    # 7. 专享央视和卫视
    if zhuanxiang_yangshi:
        playlist_custom.append("👑专享央视,#genre#")
        playlist_custom.extend(zhuanxiang_yangshi)
        playlist_custom.append('')
    
    if zhuanxiang_weishi:
        playlist_custom.append("☕️专享卫视,#genre#")
        playlist_custom.extend(zhuanxiang_weishi)
        playlist_custom.append('')
    
    # 8. 景区直播
    camera_config = CHANNEL_CONFIG["camera"]
    if camera_config["lines"]:
        playlist_custom.append("🏞️景区直播,#genre#")
        playlist_custom.extend(sorted(set(correct_name_data(g.corrections_name, camera_config["lines"]))))
        playlist_custom.append('')
    
    # 9. 其他分类
    if g.other_lines:
        playlist_custom.append("📦其他频道,#genre#")
        playlist_custom.extend(sorted(set(g.other_lines)))
        playlist_custom.append('')
    
    # 10. 更新时间
    playlist_custom.append("🕒更新时间,#genre#")
    playlist_custom.append(version)
    playlist_custom.append(about)
    playlist_custom.append(MTV1)
    playlist_custom.append(MTV2)
    playlist_custom.append(MTV3)
    playlist_custom.append(MTV4)
    playlist_custom.append(MTV5)
    playlist_custom.extend(about_info)
    playlist_custom.append('')
    
    # 定义输出文件名
    output_full = "output/full.txt"
    output_lite = "output/lite.txt"
    output_custom = "output/custom.txt"
    output_others = "output/others.txt"
    
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
            for line in g.other_lines:
                f.write(line + '\n')
        print(f"✅ 未分类频道列表已保存: {output_others}")
        
    except Exception as e:
        print(f"❌ 保存文件时发生错误：{e}")
        return 0, 0, 0

    # 返回统计信息
    return len(playlist_full), len(playlist_lite), len(playlist_custom)

# ========= 生成M3U格式文件 =========
def make_m3u(txt_file, m3u_file):
    """将TXT文件转换为M3U格式（基于v2.00逻辑）"""
    try:
        channels_logos = read_txt_to_array('assets/livesource/logo.txt')
        
        def get_logo_by_channel_name(channel_name):
            for line in channels_logos:
                if not line.strip():
                    continue
                if ',' in line:
                    name, url = line.split(',', 1)
                    if name == channel_name:
                        return url
            return None
        
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
                logo_url = get_logo_by_channel_name(channel_name)
                
                if logo_url is None:
                    output_text += f"#EXTINF:-1 group-title=\"{group_name}\",{channel_name}\n"
                    output_text += f"{channel_url}\n"
                else:
                    output_text += f"#EXTINF:-1 tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\" group-title=\"{group_name}\",{channel_name}\n"
                    output_text += f"{channel_url}\n"
        
        with open(f"{m3u_file}", "w", encoding='utf-8') as file:
            file.write(output_text)
        
        print(f"▶️ M3U文件 '{m3u_file}' 生成成功。")
    except Exception as e:
        print(f"❌ 生成M3U文件错误: {e}")

# ========= 主函数 =========
def main():
    """主函数"""
    print()
    print(f"=" * 31)
    print(f"🐍 IPTV直播源聚合处理工具 v3.02")
    print(f"📺 Live Source Collector")
    print(f"🐉 基于v2.00，重构版")
    print(f"=" * 31)
    
    # 执行开始时间
    g.start_time = get_beijing_time()
    print(f"\n⏰ 开始时间: {g.start_time.strftime('%Y%m%d %H:%M:%S')}")
    
    # 1. 加载字典
    dictionaries = load_dictionaries()
    
    # 2. 加载黑名单
    g.combined_blacklist = load_blacklist()
    
    # 3. 加载修正字典
    g.corrections_name = load_corrections_name()
    
    # 4. 处理URL列表
    urls = read_txt_to_array('assets/livesource/urls-daily.txt')
    print(f"\n📡 开始处理 {len(urls)} 个数据订阅源")
    
    for url in urls:
        if url.startswith("http"):
            # 处理日期占位符
            if "{MMdd}" in url:
                current_date_str = get_beijing_time().strftime("%m%d")
                url = url.replace("{MMdd}", current_date_str)
            if "{MMdd-1}" in url:
                yesterday_date_str = (get_beijing_time() - timedelta(days=1)).strftime("%m%d")
                url = url.replace("{MMdd-1}", yesterday_date_str)
            print(f"📡 处理URL: {url}")

            process_url(url, dictionaries)
    
    print(f"✅ URL处理完成，共处理 {len(urls)} 个数据源")
    
    # 5. 处理白名单
    process_whitelist(dictionaries)
    
    # 6. 处理AKTV源
    process_aktv(dictionaries)
    
    # 7. 处理手工区源
    process_manual_sources()
    
    # 8. 处理体育赛事
    filtered_tyss_lines = process_tyss_data()
    
    # 9. 生成输出文件并获取统计值
    full_count, lite_count, custom_count = generate_output_files(filtered_tyss_lines)
    
    # 10. 生成M3U文件
    make_m3u("output/full.txt", "output/full.m3u")
    make_m3u("output/lite.txt", "output/lite.m3u")
    make_m3u("output/custom.txt", "output/custom.m3u")
    
    # 11. 统计信息
    # 计算执行时间
    timeend = get_beijing_time()
    elapsed_time = timeend - g.start_time
    total_seconds = elapsed_time.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)

    print(f"\n📊 处理统计:")
    print(f"   开始时间: {g.start_time.strftime('%Y%m%d %H:%M:%S')}")
    print(f"   结束时间: {timeend.strftime('%Y%m%d %H:%M:%S')}")
    print(f"   执行时间: {minutes}分{seconds}秒")

    # 计算处理速度
    if total_seconds > 0:
        channels_per_second = g.stats['total_processed'] / total_seconds
        print(f"   处理速度: {channels_per_second:.1f} 频道/秒")

    # URL去重统计
    processed_urls_count = len(g.processed_urls)
    blacklist_urls_count = len(g.combined_blacklist)
    total_processed_urls = processed_urls_count + blacklist_urls_count

    print(f"\n🔄 去重统计:")
    print(f"   唯一的URL数: {processed_urls_count}")
    print(f"   黑名单URL数: {blacklist_urls_count}")
    print(f"   总处理URL数: {total_processed_urls}")

    if total_processed_urls > 0:
        duplication_rate = (1 - processed_urls_count / total_processed_urls) * 100
        print(f"   🔄 去重率: {duplication_rate:.1f}%")

    # 频道数据统计
    print(f"\n📦 数据统计:")
    print(f"   黑名单条数: {len(g.combined_blacklist)}")
    print(f"   其他未分类: {len(g.other_lines)}")
    print(f"   体育赛事数: {len(filtered_tyss_lines) if filtered_tyss_lines else 0}")
    print(f"   完整版条数: {full_count}")
    print(f"   精简版条数: {lite_count}")
    print(f"   定制版条数: {custom_count}")

    # 频道分类统计
    print(f"\n📈 分类统计:")
    total_channels = 0
    for category_id in CATEGORY_ORDER:
        if category_id in CHANNEL_CONFIG:
            config = CHANNEL_CONFIG[category_id]
            count = len(config["lines"])
            if count > 0:
                print(f"   {config['title']}: {count}个频道")
                total_channels += count

    print(f"\n📊 总计: {total_channels} 个频道")

    print(f"\n🎉🎉🎉 全部处理完成!✅🚀")

# ========= 程序入口 =========
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n💡 提示:")
    print(f"  1. 修改 CHANNEL_CONFIG 可以增删改分类")
    print(f"  2. 修改 CATEGORY_ORDER 可以调整显示顺序")
    print(f"  3. 重新运行脚本即可应用新配置")
    print(f"=" * 31)

# ====== 直播源聚合处理工具 v3.02 ======