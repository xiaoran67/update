import urllib.request
from urllib.parse import urlparse
import re
import os
from datetime import datetime, timedelta, timezone
import random
import opencc
import socket
import time
import hashlib

# ======= 硬编码配置区域 ========
# 输入路径配置
SOURCE_BASE = "scripts/livesource"
BLACKLIST_DIR = "scripts/livesource/blacklist"
MAIN_CHANNELS_DIR = "scripts/livesource/主频道"
LOCAL_CHANNELS_DIR = "scripts/livesource/地方台"
MANUAL_DIR = "scripts/livesource/手工区"
ASSETS_DIR = "scripts/livesource"

# 输出路径配置
OUTPUT_BASE = "output/livesource"
OUTPUT_DIR = "output/livesource"

# 输出文件路径
FULL_OUTPUT = "output/livesource/full.txt"
LITE_OUTPUT = "output/livesource/lite.txt"
CUSTOM_OUTPUT = "output/livesource/custom.txt"
OTHERS_OUTPUT = "output/livesource/others.txt"

# 手工区文件路径
MANUAL_GAT = "scripts/livesource/手工区/港澳台.txt"
MANUAL_CCTV = "scripts/livesource/手工区/优质央视.txt"
MANUAL_WS = "scripts/livesource/手工区/优质卫视.txt"
MANUAL_ABOUT = "scripts/livesource/手工区/about.txt"
MANUAL_AKTV = "scripts/livesource/手工区/AKTV.txt"
MANUAL_RECOMMEND = "scripts/livesource/手工区/今日推荐.txt"
MANUAL_CHANNEL = "scripts/livesource/手工区/今日推台.txt"

# 其他配置
REQUEST_TIMEOUT = 10
REQUEST_RETRIES = 3
REQUEST_BACKOFF_FACTOR = 1.5

REMOVAL_LIST = [
    "_电信", "电信", "高清", "频道", "-HD", "-BD", "英陆", "_ITV", "(北美)", "(HK)", 
    "AKtv", "「IPV4」", "「IPV6」", "频陆", "备陆", "壹陆", "贰陆", "叁陆", "肆陆", 
    "伍陆", "陆陆", "柒陆", "频晴", "频粤", "[超清]", "高清", "超清", "标清", "斯特",
    "粤陆", "国陆", "肆柒", "频英", "频特", "频国", "频壹", "频贰", "肆贰", "频测",
    "咪咕", "闽特", "高特", "频高", "频标", "汝阳", "[HD]", "[BD]", "[SD]", "[VGA]"
]

CRITICAL_FILES = ['full.txt', 'custom.txt']
URL_PATTERNS_TO_SKIP = ['tvbus://', '/udp/', 'rtsp://', 'rtp://']

# ====== 初始化设置 ======
os.makedirs(OUTPUT_DIR, exist_ok=True)
# 使用北京时间
beijing_tz = timezone(timedelta(hours=8))

# ====== 核心工具函数 ======
def read_txt_to_array(file_name):
    """读取文本文件到数组"""
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"⚠️ 文件未找到: {file_name}")
        return []
    except Exception as e:
        print(f"❌ 读取文件错误 {file_name}: {e}")
        return []

def traditional_to_simplified(text: str) -> str:
    """繁体转简体"""
    try:
        converter = opencc.OpenCC('t2s')
        return converter.convert(text)
    except Exception as e:
        print(f"❌ 繁简转换错误: {e}")
        return text

def read_blacklist_from_txt(file_path):
    """读取黑名单"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return [line.split(',')[1].strip() for line in file if ',' in line]
    except Exception as e:
        print(f"❌ 读取黑名单错误 {file_path}: {e}")
        return []

def get_url_hash(url):
    """获取URL的哈希值用于去重"""
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def should_skip_url(url):
    """检查URL是否应该跳过"""
    return any(pattern in url for pattern in URL_PATTERNS_TO_SKIP)

def is_valid_url(url):
    """验证URL格式"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

# ====== 频道名称处理函数 ======
def clean_channel_name(channel_name, removal_list):
    """清理频道名称中的特定字符"""
    for item in removal_list:
        channel_name = channel_name.replace(item, "")
    
    if channel_name.endswith("HD"):
        channel_name = channel_name[:-2]
    if channel_name.endswith("台") and len(channel_name) > 3:
        channel_name = channel_name[:-1]
    
    return channel_name.strip()

def process_name_string(input_str):
    """处理频道名称字符串"""
    try:
        parts = input_str.split(',')
        processed_parts = []
        
        for part in parts:
            if "CCTV" in part and "://" not in part:
                part = part.replace("IPV6", "").replace("PLUS", "+").replace("1080", "")
                filtered_str = ''.join(char for char in part if char.isdigit() or char in 'K+')
                
                if not filtered_str.strip():
                    filtered_str = part.replace("CCTV", "")
                
                if len(filtered_str) > 2 and re.search(r'4K|8K', filtered_str):
                    filtered_str = re.sub(r'(4K|8K).*', r'\1', filtered_str)
                    if len(filtered_str) > 2: 
                        filtered_str = re.sub(r'(4K|8K)', r'(\1)', filtered_str)
                
                processed_parts.append("CCTV" + filtered_str)
            elif "卫视" in part:
                processed_parts.append(re.sub(r'卫视「.*」', '卫视', part))
            else:
                processed_parts.append(part)
        
        return ','.join(processed_parts)
    except Exception as e:
        print(f"❌ 处理频道名称错误: {e}, 输入: {input_str}")
        return input_str

# ====== URL处理函数 ======
def get_url_file_extension(url):
    """获取URL文件扩展名"""
    try:
        parsed_url = urlparse(url)
        return os.path.splitext(parsed_url.path)[1]
    except Exception as e:
        print(f"❌ 解析URL扩展名错误: {e}")
        return ""

def clean_url(url):
    """清理URL中的$符号及之后内容"""
    try:
        last_dollar_index = url.rfind('$')
        return url[:last_dollar_index] if last_dollar_index != -1 else url
    except Exception as e:
        print(f"❌ 清理URL错误: {e}")
        return url

def check_url_existence(data_list, url):
    """检查URL是否已存在"""
    try:
        urls = [item.split(',')[1] for item in data_list if ',' in item]
        return url not in urls
    except Exception as e:
        print(f"❌ 检查URL存在性错误: {e}")
        return True

def convert_m3u_to_txt(m3u_content):
    """M3U格式转TXT格式"""
    try:
        lines = m3u_content.split('\n')
        txt_lines = []
        channel_name = ""
        
        for line in lines:
            if line.startswith("#EXTM3U"):
                continue
            elif line.startswith("#EXTINF"):
                channel_name = line.split(',')[-1].strip()
            elif line.startswith(("http", "rtmp", "p3p")):
                if channel_name:
                    txt_lines.append(f"{channel_name},{line.strip()}")
            
            if "#genre#" not in line and "," in line and "://" in line:
                pattern = r'^[^,]+,[^\s]+://[^\s]+$'
                if bool(re.match(pattern, line)):
                    txt_lines.append(line)
        
        return '\n'.join(txt_lines)
    except Exception as e:
        print(f"❌ 转换M3U到TXT错误: {e}")
        return m3u_content

# ====== 网络请求函数 ======
def get_http_response(url, timeout=None, retries=None, backoff_factor=None):
    """带重试的HTTP请求"""
    timeout = timeout or REQUEST_TIMEOUT
    retries = retries or REQUEST_RETRIES
    backoff_factor = backoff_factor or REQUEST_BACKOFF_FACTOR
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
                return data.decode('utf-8')
        except urllib.error.HTTPError as e:
            print(f"❌ [HTTP错误] 代码: {e.code}, URL: {url}")
            break
        except urllib.error.URLError as e:
            print(f"⚠️ [URL错误] 原因: {e.reason}, 尝试: {attempt + 1}/{retries}")
        except socket.timeout:
            print(f"⏰ [超时] URL: {url}, 尝试: {attempt + 1}/{retries}")
        except Exception as e:
            print(f"⚠️ [异常] {type(e).__name__}: {e}, 尝试: {attempt + 1}/{retries}")
        
        if attempt < retries - 1:
            sleep_time = backoff_factor * (2 ** attempt)
            print(f"⏳ 等待 {sleep_time} 秒后重试...")
            time.sleep(sleep_time)
    
    return None

# ====== 数据排序和纠错 ======
def load_corrections_name(filename):
    """加载频道名称纠错数据"""
    corrections = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    correct_name = parts[0]
                    for name in parts[1:]:
                        corrections[name] = correct_name
        print(f"✅ 纠错数据加载: {len(corrections)} 条规则")
    except Exception as e:
        print(f"❌ 加载纠错数据错误 {filename}: {e}")
    return corrections

def correct_name_data(corrections, data):
    """纠正频道名称"""
    corrected_data = []
    for line in data:
        try:
            if ',' not in line:
                continue
            name, url = line.split(',', 1)
            if name in corrections and name != corrections[name]:
                name = corrections[name]
            corrected_data.append(f"{name},{url}")
        except Exception as e:
            print(f"⚠️ 纠正名称错误: {e}, 行: {line}")
    return corrected_data

def sort_data(order, data):
    """按指定顺序排序数据"""
    try:
        order_dict = {name: i for i, name in enumerate(order)}
        def sort_key(line):
            try:
                name = line.split(',')[0]
                return order_dict.get(name, len(order))
            except:
                return len(order)
        return sorted(data, key=sort_key)
    except Exception as e:
        print(f"⚠️ 排序数据错误: {e}")
        return data

# ====== 数据加载函数 ======
def load_all_dictionaries():
    """加载所有字典数据"""
    print("📚 加载字典数据...")
    
    dictionaries = {}
    
    # 主频道字典
    dictionaries['yangshi_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/CCTV.txt")
    dictionaries['weishi_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/卫视频道.txt")

    # 地方台字典
    dictionaries['beijing_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/北京频道.txt")
    dictionaries['shanghai_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/上海频道.txt")
    dictionaries['tianjin_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/天津频道.txt")
    dictionaries['chongqing_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/重庆频道.txt")
    dictionaries['guangdong_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/广东频道.txt")
    dictionaries['jiangsu_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/江苏频道.txt")
    dictionaries['zhejiang_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/浙江频道.txt")
    dictionaries['shandong_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/山东频道.txt")
    dictionaries['henan_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/河南频道.txt")
    dictionaries['sichuan_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/四川频道.txt")
    dictionaries['hebei_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/河北频道.txt")
    dictionaries['hunan_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/湖南频道.txt")
    dictionaries['hubei_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/湖北频道.txt")
    dictionaries['anhui_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/安徽频道.txt")
    dictionaries['fujian_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/福建频道.txt")
    dictionaries['shanxi1_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/陕西频道.txt")
    dictionaries['liaoning_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/辽宁频道.txt")
    dictionaries['jiangxi_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/江西频道.txt")
    dictionaries['heilongjiang_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/黑龙江频道.txt")
    dictionaries['jilin_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/吉林频道.txt")
    dictionaries['shanxi2_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/山西频道.txt")
    dictionaries['guangxi_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/广西频道.txt")
    dictionaries['yunnan_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/云南频道.txt")
    dictionaries['guizhou_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/贵州频道.txt")
    dictionaries['gansu_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/甘肃频道.txt")
    dictionaries['neimenggu_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/内蒙频道.txt")
    dictionaries['xinjiang_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/新疆频道.txt")
    dictionaries['hainan_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/海南频道.txt")
    dictionaries['ningxia_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/宁夏频道.txt")
    dictionaries['qinghai_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/青海频道.txt")
    dictionaries['xizang_dictionary'] = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/西藏频道.txt")

    # 定制频道字典
    dictionaries['news_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/新闻频道.txt")
    dictionaries['shuzi_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/数字频道.txt")
    dictionaries['dianying_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/电影频道.txt")
    dictionaries['jieshuo_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/解说频道.txt")
    dictionaries['zongyi_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/综艺频道.txt")
    dictionaries['huya_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/虎牙直播.txt")
    dictionaries['douyu_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/斗鱼直播.txt")
    dictionaries['xianggang_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/香港频道.txt")
    dictionaries['aomen_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/澳门频道.txt")
    dictionaries['china_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/中国频道.txt")
    dictionaries['guoji_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/国际频道.txt")
    dictionaries['gangaotai_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/港澳台.txt")
    dictionaries['dianshiju_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/电视剧.txt")
    dictionaries['radio_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/收音机.txt")
    dictionaries['donghuapian_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/动画片.txt")
    dictionaries['jilupian_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/记录片.txt")
    dictionaries['tiyu_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/体育频道.txt")
    dictionaries['tiyusaishi_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/体育赛事.txt")
    dictionaries['youxi_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/游戏频道.txt")
    dictionaries['xiqu_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/戏曲频道.txt")
    dictionaries['yinyue_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/音乐频道.txt")
    dictionaries['chunwan_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/春晚频道.txt")
    dictionaries['zhibozhongguo_dictionary'] = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/直播中国.txt")

    print(f"✅ 字典数据加载完成: CCTV({len(dictionaries['yangshi_dictionary'])}) 卫视({len(dictionaries['weishi_dictionary'])}) 地方台(27个) 定制频道(23个)")
    return dictionaries

def load_blacklist():
    """加载黑名单"""
    print("🔧 加载黑名单...")
    blacklist_auto = read_blacklist_from_txt(f"{BLACKLIST_DIR}/blacklist_auto.txt") 
    blacklist_manual = read_blacklist_from_txt(f"{BLACKLIST_DIR}/blacklist_manual.txt") 
    combined_blacklist = set(blacklist_auto + blacklist_manual)
    print(f"✅ 黑名单加载完成: {len(combined_blacklist)} 条记录")
    return combined_blacklist

# ====== 核心分发逻辑 ======
def process_channel_line(line, data_containers, dictionaries, blacklist):
    """处理单行频道数据并分类 - 支持同频道多分类且去重"""
    try:
        if "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
            channel_name = line.split(',')[0].strip()
            original_name = channel_name  # 保存原始名称
            channel_name = clean_channel_name(channel_name, REMOVAL_LIST)
            channel_name = traditional_to_simplified(channel_name)
            channel_address = clean_url(line.split(',')[1].strip())
            
            # 跳过黑名单和特定协议
            if channel_address in blacklist or should_skip_url(channel_address):
                return

            url_hash = get_url_hash(channel_address)
            processed_line = channel_name + "," + channel_address

            # 主频道分发 - 支持同频道多分类
            channel_added = False
            
            if "CCTV" in channel_name and check_url_existence(data_containers['yangshi_lines'], channel_address):
                data_containers['yangshi_lines'].append(process_name_string(processed_line))
                channel_added = True
            
            if channel_name in dictionaries['weishi_dictionary'] and check_url_existence(data_containers['weishi_lines'], channel_address):
                data_containers['weishi_lines'].append(process_name_string(processed_line))
                channel_added = True
            
            # 地方台分发 - 支持同频道多分类
            if channel_name in dictionaries['beijing_dictionary'] and check_url_existence(data_containers['beijing_lines'], channel_address):
                data_containers['beijing_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['shanghai_dictionary'] and check_url_existence(data_containers['shanghai_lines'], channel_address):
                data_containers['shanghai_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['tianjin_dictionary'] and check_url_existence(data_containers['tianjin_lines'], channel_address):
                data_containers['tianjin_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['chongqing_dictionary'] and check_url_existence(data_containers['chongqing_lines'], channel_address):
                data_containers['chongqing_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['guangdong_dictionary'] and check_url_existence(data_containers['guangdong_lines'], channel_address):
                data_containers['guangdong_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['jiangsu_dictionary'] and check_url_existence(data_containers['jiangsu_lines'], channel_address):
                data_containers['jiangsu_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['zhejiang_dictionary'] and check_url_existence(data_containers['zhejiang_lines'], channel_address):
                data_containers['zhejiang_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['shandong_dictionary'] and check_url_existence(data_containers['shandong_lines'], channel_address):
                data_containers['shandong_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['henan_dictionary'] and check_url_existence(data_containers['henan_lines'], channel_address):
                data_containers['henan_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['sichuan_dictionary'] and check_url_existence(data_containers['sichuan_lines'], channel_address):
                data_containers['sichuan_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['hebei_dictionary'] and check_url_existence(data_containers['hebei_lines'], channel_address):
                data_containers['hebei_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['hunan_dictionary'] and check_url_existence(data_containers['hunan_lines'], channel_address):
                data_containers['hunan_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['hubei_dictionary'] and check_url_existence(data_containers['hubei_lines'], channel_address):
                data_containers['hubei_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['anhui_dictionary'] and check_url_existence(data_containers['anhui_lines'], channel_address):
                data_containers['anhui_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['fujian_dictionary'] and check_url_existence(data_containers['fujian_lines'], channel_address):
                data_containers['fujian_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['shanxi1_dictionary'] and check_url_existence(data_containers['shanxi1_lines'], channel_address):
                data_containers['shanxi1_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['liaoning_dictionary'] and check_url_existence(data_containers['liaoning_lines'], channel_address):
                data_containers['liaoning_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['jiangxi_dictionary'] and check_url_existence(data_containers['jiangxi_lines'], channel_address):
                data_containers['jiangxi_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['heilongjiang_dictionary'] and check_url_existence(data_containers['heilongjiang_lines'], channel_address):
                data_containers['heilongjiang_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['jilin_dictionary'] and check_url_existence(data_containers['jilin_lines'], channel_address):
                data_containers['jilin_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['shanxi2_dictionary'] and check_url_existence(data_containers['shanxi2_lines'], channel_address):
                data_containers['shanxi2_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['guangxi_dictionary'] and check_url_existence(data_containers['guangxi_lines'], channel_address):
                data_containers['guangxi_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['yunnan_dictionary'] and check_url_existence(data_containers['yunnan_lines'], channel_address):
                data_containers['yunnan_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['guizhou_dictionary'] and check_url_existence(data_containers['guizhou_lines'], channel_address):
                data_containers['guizhou_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['gansu_dictionary'] and check_url_existence(data_containers['gansu_lines'], channel_address):
                data_containers['gansu_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['neimenggu_dictionary'] and check_url_existence(data_containers['neimenggu_lines'], channel_address):
                data_containers['neimenggu_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['xinjiang_dictionary'] and check_url_existence(data_containers['xinjiang_lines'], channel_address):
                data_containers['xinjiang_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['hainan_dictionary'] and check_url_existence(data_containers['hainan_lines'], channel_address):
                data_containers['hainan_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['ningxia_dictionary'] and check_url_existence(data_containers['ningxia_lines'], channel_address):
                data_containers['ningxia_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['qinghai_dictionary'] and check_url_existence(data_containers['qinghai_lines'], channel_address):
                data_containers['qinghai_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['xizang_dictionary'] and check_url_existence(data_containers['xizang_lines'], channel_address):
                data_containers['xizang_lines'].append(process_name_string(processed_line))
                channel_added = True
            
            # 定制频道分发
            if channel_name in dictionaries['news_dictionary'] and check_url_existence(data_containers['news_lines'], channel_address):
                data_containers['news_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['shuzi_dictionary'] and check_url_existence(data_containers['shuzi_lines'], channel_address):
                data_containers['shuzi_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['dianying_dictionary'] and check_url_existence(data_containers['dianying_lines'], channel_address):
                data_containers['dianying_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['jieshuo_dictionary'] and check_url_existence(data_containers['jieshuo_lines'], channel_address):
                data_containers['jieshuo_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['zongyi_dictionary'] and check_url_existence(data_containers['zongyi_lines'], channel_address):
                data_containers['zongyi_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['huya_dictionary'] and check_url_existence(data_containers['huya_lines'], channel_address):
                data_containers['huya_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['douyu_dictionary'] and check_url_existence(data_containers['douyu_lines'], channel_address):
                data_containers['douyu_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['xianggang_dictionary'] and check_url_existence(data_containers['xianggang_lines'], channel_address):
                data_containers['xianggang_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['aomen_dictionary'] and check_url_existence(data_containers['aomen_lines'], channel_address):
                data_containers['aomen_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['china_dictionary'] and check_url_existence(data_containers['china_lines'], channel_address):
                data_containers['china_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['guoji_dictionary'] and check_url_existence(data_containers['guoji_lines'], channel_address):
                data_containers['guoji_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['gangaotai_dictionary'] and check_url_existence(data_containers['gangaotai_lines'], channel_address):
                data_containers['gangaotai_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['dianshiju_dictionary'] and check_url_existence(data_containers['dianshiju_lines'], channel_address):
                data_containers['dianshiju_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['radio_dictionary'] and check_url_existence(data_containers['radio_lines'], channel_address):
                data_containers['radio_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['donghuapian_dictionary'] and check_url_existence(data_containers['donghuapian_lines'], channel_address):
                data_containers['donghuapian_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['jilupian_dictionary'] and check_url_existence(data_containers['jilupian_lines'], channel_address):
                data_containers['jilupian_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['tiyu_dictionary'] and check_url_existence(data_containers['tiyu_lines'], channel_address):
                data_containers['tiyu_lines'].append(process_name_string(processed_line))
                channel_added = True
            
            if any(tiyusaishi_item in channel_name for tiyusaishi_item in dictionaries['tiyusaishi_dictionary']) and check_url_existence(data_containers['tiyusaishi_lines'], channel_address):
                data_containers['tiyusaishi_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['youxi_dictionary'] and check_url_existence(data_containers['youxi_lines'], channel_address):
                data_containers['youxi_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['xiqu_dictionary'] and check_url_existence(data_containers['xiqu_lines'], channel_address):
                data_containers['xiqu_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['yinyue_dictionary'] and check_url_existence(data_containers['yinyue_lines'], channel_address):
                data_containers['yinyue_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['chunwan_dictionary'] and check_url_existence(data_containers['chunwan_lines'], channel_address):
                data_containers['chunwan_lines'].append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dictionaries['zhibozhongguo_dictionary'] and check_url_existence(data_containers['zhibozhongguo_lines'], channel_address):
                data_containers['zhibozhongguo_lines'].append(process_name_string(processed_line))
                channel_added = True
            
            # 其他频道分发 - 使用URL哈希去重
            if not channel_added and url_hash not in data_containers['others_lines_url']:
                data_containers['others_lines_url'].append(url_hash)
                data_containers['others_lines'].append(processed_line)

    except Exception as e:
        print(f"❌ 处理频道行错误: {e}, 行内容: {line}")

def process_url(url, data_containers, dictionaries, blacklist):
    """处理单个URL源"""
    try:
        print(f"🌐 处理URL: {url}")
        data_containers['others_lines'].append(f"◆◆◆ {url}")
        
        response_text = get_http_response(url)
        if not response_text:
            print(f"❌ 获取URL内容失败: {url}")
            data_containers['others_lines'].append(f"❌ 获取失败: {url}\n")
            return

        # 检查是否为M3U格式
        is_m3u = response_text.startswith("#EXTM3U") or response_text.startswith("#EXTINF")
        if get_url_file_extension(url) in [".m3u", ".m3u8"] or is_m3u:
            response_text = convert_m3u_to_txt(response_text)

        lines = response_text.split('\n')
        valid_lines = 0
        
        for line in lines:
            if ("#genre#" not in line and "," in line and "://" in line and 
                not should_skip_url(line)):
                
                try:
                    channel_name, channel_address = line.split(',', 1)
                    
                    # 处理带#号的加速源
                    if "#" not in channel_address:
                        process_channel_line(line, data_containers, dictionaries, blacklist)
                        valid_lines += 1
                    else:
                        url_list = channel_address.split('#')
                        for channel_url in url_list:
                            process_channel_line(f'{channel_name},{channel_url}', data_containers, dictionaries, blacklist)
                            valid_lines += 1
                except Exception as e:
                    print(f"⚠️ 处理行错误: {e}, 行: {line}")

        print(f"✅ 处理完成: {valid_lines} 个有效频道")
        data_containers['others_lines'].append(f"✅ 完成: {valid_lines} 个频道\n")

    except Exception as e:
        print(f"❌ 处理URL时发生错误 {url}: {e}")
        data_containers['others_lines'].append(f"❌ 错误: {e}\n")

# ====== 主处理流程函数 ======
def process_url_sources(data_containers, dictionaries, blacklist):
    """处理URL源"""
    print("🚀 开始处理直播源...")
    
    # 处理URL源
    urls = read_txt_to_array(f"{ASSETS_DIR}/urls-daily.txt")
    print(f"📡 发现 {len(urls)} 个URL源")
    
    for url in urls:
        if url.startswith("http"):
            # 处理日期变量 - 使用北京时间
            current_date_str = datetime.now(beijing_tz).strftime("%m%d")
            yesterday_date_str = (datetime.now(beijing_tz) - timedelta(days=1)).strftime("%m%d")
            
            if "{MMdd}" in url:
                url = url.replace("{MMdd}", current_date_str)
            if "{MMdd-1}" in url:
                url = url.replace("{MMdd-1}", yesterday_date_str)
            
            process_url(url, data_containers, dictionaries, blacklist)

def process_whitelist_and_manual(data_containers, dictionaries, blacklist):
    """处理白名单和手工区"""
    # 处理白名单
    print("📋 处理白名单...")
    whitelist_auto_lines = read_txt_to_array(f"{BLACKLIST_DIR}/whitelist_auto.txt")
    whitelist_count = 0
    for whitelist_line in whitelist_auto_lines:
        if ("#genre#" not in whitelist_line and "," in whitelist_line and 
            "://" in whitelist_line):
            whitelist_parts = whitelist_line.split(",")
            try:
                response_time = float(whitelist_parts[0].replace("ms", ""))
            except ValueError:
                response_time = 60000
            if response_time < 2000:  # 2秒以内的高响应源
                process_channel_line(",".join(whitelist_parts[1:]), data_containers, dictionaries, blacklist)
                whitelist_count += 1
    print(f"✅ 白名单处理完成: {whitelist_count} 个高速源")

    # 处理手工区
    print("🔧 处理手工区...")
    # 处理所有手工区文件
    manual_files = {
        '国际频道': 'guoji_lines',
        '港·澳·台': 'gangaotai_lines',
        '动·画·片': 'donghuapian_lines',
        '收·音·机': 'radio_lines',
        '记·录·片': 'jilupian_lines',
        '香港频道': 'xianggang_lines',
        '澳门频道': 'aomen_lines',
        '中国频道': 'china_lines',
        '湖北频道': 'hubei_lines', 
    }

    for region, target_list in manual_files.items():
        manual_file = f"{MANUAL_DIR}/{region}.txt"
        if os.path.exists(manual_file):
            manual_data = read_txt_to_array(manual_file)
            for line in manual_data:
                if "," in line and "://" in line:
                    process_channel_line(line, data_containers, dictionaries, blacklist)
            print(f"✅ 手工区 {region}: {len(manual_data)} 条记录")

    # 处理AKTV
    print("🌐 处理AKTV...")
    aktv_url = "https://aktv.space/live.m3u"
    aktv_text = get_http_response(aktv_url)
    if aktv_text:
        print("✅ AKTV成功获取内容")
        aktv_text = convert_m3u_to_txt(aktv_text)
        data_containers['aktv_lines'].extend(aktv_text.strip().split('\n'))
    else:
        print("⚠️ AKTV请求失败，从本地获取！")
        data_containers['aktv_lines'].extend(read_txt_to_array(MANUAL_AKTV))
    print(f"✅ AKTV处理完成: {len(data_containers['aktv_lines'])} 个频道")

def generate_output_files(data_containers, dictionaries):
    """生成输出文件"""
    print("📄 生成输出文件...")
    
    # 加载纠错数据
    corrections_name = load_corrections_name(f"{ASSETS_DIR}/corrections_name.txt")
    
    # 处理体育赛事日期格式
    def normalize_date_to_md(text):
        """日期格式标准化"""
        try:
            text = text.strip()
            def format_md(m):
                month = int(m.group(1))
                day = int(m.group(2))
                after = m.group(3) or ''
                if not after.startswith(' '):
                    after = ' ' + after
                return f"{month}-{day}{after}"

            text = re.sub(r'^0?(\d{1,2})/0?(\d{1,2})(.*)', format_md, text)
            text = re.sub(r'^\d{4}-0?(\d{1,2})-0?(\d{1,2})(.*)', format_md, text)
            text = re.sub(r'^0?(\d{1,2})月0?(\d{1,2})日(.*)', format_md, text)
            return text
        except Exception as e:
            print(f"⚠️ 日期格式化错误: {e}, 文本: {text}")
            return text

    normalized_tiyusaishi_lines = [normalize_date_to_md(s) for s in data_containers['tiyusaishi_lines']]

    # 生成版本信息 - 使用北京时间
    beijing_time = datetime.now(beijing_tz)
    formatted_time = beijing_time.strftime("%Y%m%d %H:%M:%S")

    def get_random_url(file_path):
        """随机获取URL"""
        urls = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    url = line.strip().split(',')[-1]
                    urls.append(url)    
        except Exception as e:
            print(f"⚠️ 读取文件 {file_path} 时发生错误：{e}")
        return random.choice(urls) if urls else ""

    version = formatted_time + "," + get_random_url(MANUAL_CHANNEL)
    about = "xiaoranmuze," + get_random_url(MANUAL_CHANNEL)
    daily_mtv = "今日推荐," + get_random_url(MANUAL_RECOMMEND)
    daily_mtv1 = "🔥低调," + get_random_url(MANUAL_RECOMMEND)
    daily_mtv2 = "🔥使用," + get_random_url(MANUAL_RECOMMEND)
    daily_mtv3 = "🔥禁止," + get_random_url(MANUAL_RECOMMEND)
    daily_mtv4 = "🔥贩卖," + get_random_url(MANUAL_RECOMMEND)

    # 生成全部源 (full.txt)
    all_lines_full = []
    all_lines_full.extend(["🌐央视频道,#genre#"] + sort_data(dictionaries['yangshi_dictionary'], correct_name_data(corrections_name, data_containers['yangshi_lines'])) + ['\n'])
    all_lines_full.extend(["📡卫视频道,#genre#"] + sort_data(dictionaries['weishi_dictionary'], correct_name_data(corrections_name, data_containers['weishi_lines'])) + ['\n'])

    # 地方台分类
    all_lines_full.extend(["☘️北京频道,#genre#"] + sort_data(dictionaries['beijing_dictionary'], set(correct_name_data(corrections_name, data_containers['beijing_lines']))) + ['\n'])
    all_lines_full.extend(["☘️上海频道,#genre#"] + sort_data(dictionaries['shanghai_dictionary'], set(correct_name_data(corrections_name, data_containers['shanghai_lines']))) + ['\n'])
    all_lines_full.extend(["☘️天津频道,#genre#"] + sort_data(dictionaries['tianjin_dictionary'], set(correct_name_data(corrections_name, data_containers['tianjin_lines']))) + ['\n'])
    all_lines_full.extend(["☘️重庆频道,#genre#"] + sort_data(dictionaries['chongqing_dictionary'], set(correct_name_data(corrections_name, data_containers['chongqing_lines']))) + ['\n'])
    all_lines_full.extend(["☘️广东频道,#genre#"] + sort_data(dictionaries['guangdong_dictionary'], set(correct_name_data(corrections_name, data_containers['guangdong_lines']))) + ['\n'])
    all_lines_full.extend(["☘️江苏频道,#genre#"] + sort_data(dictionaries['jiangsu_dictionary'], set(correct_name_data(corrections_name, data_containers['jiangsu_lines']))) + ['\n'])
    all_lines_full.extend(["☘️浙江频道,#genre#"] + sort_data(dictionaries['zhejiang_dictionary'], set(correct_name_data(corrections_name, data_containers['zhejiang_lines']))) + ['\n'])
    all_lines_full.extend(["☘️山东频道,#genre#"] + sort_data(dictionaries['shandong_dictionary'], set(correct_name_data(corrections_name, data_containers['shandong_lines']))) + ['\n'])
    all_lines_full.extend(["☘️河南频道,#genre#"] + sort_data(dictionaries['henan_dictionary'], set(correct_name_data(corrections_name, data_containers['henan_lines']))) + ['\n'])
    all_lines_full.extend(["☘️四川频道,#genre#"] + sort_data(dictionaries['sichuan_dictionary'], set(correct_name_data(corrections_name, data_containers['sichuan_lines']))) + ['\n'])
    all_lines_full.extend(["☘️河北频道,#genre#"] + sort_data(dictionaries['hebei_dictionary'], set(correct_name_data(corrections_name, data_containers['hebei_lines']))) + ['\n'])
    all_lines_full.extend(["☘️湖南频道,#genre#"] + sort_data(dictionaries['hunan_dictionary'], set(correct_name_data(corrections_name, data_containers['hunan_lines']))) + ['\n'])
    all_lines_full.extend(["☘️湖北频道,#genre#"] + sort_data(dictionaries['hubei_dictionary'], set(correct_name_data(corrections_name, data_containers['hubei_lines']))) + ['\n'])
    all_lines_full.extend(["☘️安徽频道,#genre#"] + sort_data(dictionaries['anhui_dictionary'], set(correct_name_data(corrections_name, data_containers['anhui_lines']))) + ['\n'])
    all_lines_full.extend(["☘️福建频道,#genre#"] + sort_data(dictionaries['fujian_dictionary'], set(correct_name_data(corrections_name, data_containers['fujian_lines']))) + ['\n'])
    all_lines_full.extend(["☘️陕西频道,#genre#"] + sort_data(dictionaries['shanxi1_dictionary'], set(correct_name_data(corrections_name, data_containers['shanxi1_lines']))) + ['\n'])
    all_lines_full.extend(["☘️辽宁频道,#genre#"] + sort_data(dictionaries['liaoning_dictionary'], set(correct_name_data(corrections_name, data_containers['liaoning_lines']))) + ['\n'])
    all_lines_full.extend(["☘️江西频道,#genre#"] + sort_data(dictionaries['jiangxi_dictionary'], set(correct_name_data(corrections_name, data_containers['jiangxi_lines']))) + ['\n'])
    all_lines_full.extend(["☘️黑龙江台,#genre#"] + sorted(set(correct_name_data(corrections_name, data_containers['heilongjiang_lines']))) + ['\n'])
    all_lines_full.extend(["☘️吉林频道,#genre#"] + sort_data(dictionaries['jilin_dictionary'], set(correct_name_data(corrections_name, data_containers['jilin_lines']))) + ['\n'])
    all_lines_full.extend(["☘️山西频道,#genre#"] + sort_data(dictionaries['shanxi2_dictionary'], set(correct_name_data(corrections_name, data_containers['shanxi2_lines']))) + ['\n'])
    all_lines_full.extend(["☘️广西频道,#genre#"] + sort_data(dictionaries['guangxi_dictionary'], set(correct_name_data(corrections_name, data_containers['guangxi_lines']))) + ['\n'])
    all_lines_full.extend(["☘️云南频道,#genre#"] + sort_data(dictionaries['yunnan_dictionary'], set(correct_name_data(corrections_name, data_containers['yunnan_lines']))) + ['\n'])
    all_lines_full.extend(["☘️贵州频道,#genre#"] + sort_data(dictionaries['guizhou_dictionary'], set(correct_name_data(corrections_name, data_containers['guizhou_lines']))) + ['\n'])
    all_lines_full.extend(["☘️甘肃频道,#genre#"] + sort_data(dictionaries['gansu_dictionary'], set(correct_name_data(corrections_name, data_containers['gansu_lines']))) + ['\n'])
    all_lines_full.extend(["☘️内蒙频道,#genre#"] + sort_data(dictionaries['neimenggu_dictionary'], set(correct_name_data(corrections_name, data_containers['neimenggu_lines']))) + ['\n'])
    all_lines_full.extend(["☘️新疆频道,#genre#"] + sort_data(dictionaries['xinjiang_dictionary'], set(correct_name_data(corrections_name, data_containers['xinjiang_lines']))) + ['\n'])
    all_lines_full.extend(["☘️海南频道,#genre#"] + sort_data(dictionaries['hainan_dictionary'], set(correct_name_data(corrections_name, data_containers['hainan_lines']))) + ['\n'])
    all_lines_full.extend(["☘️宁夏频道,#genre#"] + sort_data(dictionaries['ningxia_dictionary'], set(correct_name_data(corrections_name, data_containers['ningxia_lines']))) + ['\n'])
    all_lines_full.extend(["☘️青海频道,#genre#"] + sort_data(dictionaries['qinghai_dictionary'], set(correct_name_data(corrections_name, data_containers['qinghai_lines']))) + ['\n'])
    all_lines_full.extend(["☘️西藏频道,#genre#"] + sort_data(dictionaries['xizang_dictionary'], set(correct_name_data(corrections_name, data_containers['xizang_lines']))) + ['\n'])

    # 定制频道
    all_lines_full.extend(["📰新闻频道,#genre#"] + sort_data(dictionaries['news_dictionary'], set(correct_name_data(corrections_name, data_containers['news_lines']))) + ['\n'])
    all_lines_full.extend(["🎞️数字频道,#genre#"] + sort_data(dictionaries['shuzi_dictionary'], set(correct_name_data(corrections_name, data_containers['shuzi_lines']))) + ['\n'])
    all_lines_full.extend(["🎬电影频道,#genre#"] + sort_data(dictionaries['dianying_dictionary'], set(correct_name_data(corrections_name, data_containers['dianying_lines']))) + ['\n'])
    all_lines_full.extend(["🎙️解说频道,#genre#"] + sort_data(dictionaries['jieshuo_dictionary'], set(correct_name_data(corrections_name, data_containers['jieshuo_lines']))) + ['\n'])
    all_lines_full.extend(["🎤综艺频道,#genre#"] + sorted(set(correct_name_data(corrections_name, data_containers['zongyi_lines']))) + ['\n'])
    all_lines_full.extend(["🐯虎牙直播,#genre#"] + sort_data(dictionaries['huya_dictionary'], set(correct_name_data(corrections_name, data_containers['huya_lines']))) + ['\n'])
    all_lines_full.extend(["🐬斗鱼直播,#genre#"] + sort_data(dictionaries['douyu_dictionary'], set(correct_name_data(corrections_name, data_containers['douyu_lines']))) + ['\n'])
    all_lines_full.extend(["🇭🇰香港频道,#genre#"] + sort_data(dictionaries['xianggang_dictionary'], set(correct_name_data(corrections_name, data_containers['xianggang_lines']))) + ['\n'])
    all_lines_full.extend(["🇲🇴澳门频道,#genre#"] + sort_data(dictionaries['aomen_dictionary'], set(correct_name_data(corrections_name, data_containers['aomen_lines']))) + ['\n'])
    all_lines_full.extend(["🇨🇳中国频道,#genre#"] + sort_data(dictionaries['china_dictionary'], set(correct_name_data(corrections_name, data_containers['china_lines']))) + ['\n'])
    all_lines_full.extend(["🌎国际频道,#genre#"] + sort_data(dictionaries['guoji_dictionary'], set(correct_name_data(corrections_name, data_containers['guoji_lines']))) + ['\n'])
    all_lines_full.extend(["🇨🇳港·澳·台,#genre#"] + read_txt_to_array(MANUAL_GAT) + sort_data(dictionaries['gangaotai_dictionary'], set(correct_name_data(corrections_name, data_containers['gangaotai_lines']))) + data_containers['aktv_lines'] + ['\n'])
    all_lines_full.extend(["📺电·视·剧,#genre#"] + sort_data(dictionaries['dianshiju_dictionary'], set(correct_name_data(corrections_name, data_containers['dianshiju_lines']))) + ['\n'])
    all_lines_full.extend(["📻收·音·机,#genre#"] + sort_data(dictionaries['radio_dictionary'], set(correct_name_data(corrections_name, data_containers['radio_lines']))) + ['\n'])
    all_lines_full.extend(["🏕动·画·片,#genre#"] + sort_data(dictionaries['donghuapian_dictionary'], set(correct_name_data(corrections_name, data_containers['donghuapian_lines']))) + ['\n'])
    all_lines_full.extend(["📽️记·录·片,#genre#"] + sort_data(dictionaries['jilupian_dictionary'], set(correct_name_data(corrections_name, data_containers['jilupian_lines']))) + ['\n'])
    all_lines_full.extend(["⚽体育频道,#genre#"] + sort_data(dictionaries['tiyu_dictionary'], set(correct_name_data(corrections_name, data_containers['tiyu_lines']))) + ['\n'])
    all_lines_full.extend(["🏆体育赛事,#genre#"] + normalized_tiyusaishi_lines + ['\n'])
    all_lines_full.extend(["🎮游戏频道,#genre#"] + sorted(set(correct_name_data(corrections_name, data_containers['youxi_lines']))) + ['\n'])
    all_lines_full.extend(["🎭戏曲频道,#genre#"] + sort_data(dictionaries['xiqu_dictionary'], set(correct_name_data(corrections_name, data_containers['xiqu_lines']))) + ['\n'])
    all_lines_full.extend(["🎵音乐频道,#genre#"] + sort_data(dictionaries['yinyue_dictionary'], set(correct_name_data(corrections_name, data_containers['yinyue_lines']))) + ['\n'])
    all_lines_full.extend(["🎉春晚频道,#genre#"] + sort_data(dictionaries['chunwan_dictionary'], set(correct_name_data(corrections_name, data_containers['chunwan_lines']))) + ['\n'])
    all_lines_full.extend(["📡直播中国,#genre#"] + sort_data(dictionaries['zhibozhongguo_dictionary'], set(correct_name_data(corrections_name, data_containers['zhibozhongguo_lines']))) + ['\n'])

    # 手工区频道
    all_lines_full.extend(["✨优质央视,#genre#"] + read_txt_to_array(MANUAL_CCTV) + ['\n'])
    all_lines_full.extend(["🛰️优质卫视,#genre#"] + read_txt_to_array(MANUAL_WS) + ['\n'])

    # 其它和更新信息
    all_lines_full.extend(["📦漏网之鱼,#genre#"] + data_containers['others_lines'] + ['\n'])
    all_lines_full.extend(["🕒更新时间,#genre#"] + [version, about, daily_mtv, daily_mtv1, daily_mtv2, daily_mtv3, daily_mtv4] + read_txt_to_array(MANUAL_ABOUT) + ['\n'])

    # 精简源 (lite.txt)
    all_lines_lite = []
    all_lines_lite.extend(["央视频道,#genre#"] + sort_data(dictionaries['yangshi_dictionary'], correct_name_data(corrections_name, data_containers['yangshi_lines'])) + ['\n'])
    all_lines_lite.extend(["卫视频道,#genre#"] + sort_data(dictionaries['weishi_dictionary'], correct_name_data(corrections_name, data_containers['weishi_lines'])) + ['\n'])
    all_lines_lite.extend(["更新时间,#genre#"] + [version] + ['\n'])

    # 定制源 (custom.txt) - 智能合并地方台
    all_lines_custom = []
    all_lines_custom.extend(["🌐央视频道,#genre#"] + sort_data(dictionaries['yangshi_dictionary'], correct_name_data(corrections_name, data_containers['yangshi_lines'])) + ['\n'])
    all_lines_custom.extend(["📡卫视频道,#genre#"] + sort_data(dictionaries['weishi_dictionary'], correct_name_data(corrections_name, data_containers['weishi_lines'])) + ['\n'])

    # 智能合并地方台 - 保持结构且去重
    print("🔗 智能合并地方台频道...")
    
    # 定义所有地方台数据源
    local_sources = [
        ("北京", data_containers['beijing_lines']),
        ("上海", data_containers['shanghai_lines']),
        ("天津", data_containers['tianjin_lines']),
        ("重庆", data_containers['chongqing_lines']),
        ("广东", data_containers['guangdong_lines']),
        ("江苏", data_containers['jiangsu_lines']),
        ("浙江", data_containers['zhejiang_lines']),
        ("山东", data_containers['shandong_lines']),
        ("河南", data_containers['henan_lines']),
        ("四川", data_containers['sichuan_lines']),
        ("河北", data_containers['hebei_lines']),
        ("湖南", data_containers['hunan_lines']),
        ("湖北", data_containers['hubei_lines']),
        ("安徽", data_containers['anhui_lines']),
        ("福建", data_containers['fujian_lines']),
        ("陕西", data_containers['shanxi1_lines']),
        ("辽宁", data_containers['liaoning_lines']),
        ("江西", data_containers['jiangxi_lines']),
        ("黑龙江", data_containers['heilongjiang_lines']),
        ("吉林", data_containers['jilin_lines']),
        ("山西", data_containers['shanxi2_lines']),
        ("广西", data_containers['guangxi_lines']),
        ("云南", data_containers['yunnan_lines']),
        ("贵州", data_containers['guizhou_lines']),
        ("甘肃", data_containers['gansu_lines']),
        ("内蒙", data_containers['neimenggu_lines']),
        ("新疆", data_containers['xinjiang_lines']),
        ("海南", data_containers['hainan_lines']),
        ("宁夏", data_containers['ningxia_lines']),
        ("青海", data_containers['qinghai_lines']),
        ("西藏", data_containers['xizang_lines'])
    ]
    
    # 使用字典来去重，key是频道名称
    unique_channels = {}
    
    for region_name, channel_list in local_sources:
        for channel in channel_list:
            if ',' in channel:
                channel_name = channel.split(',')[0]
                # 如果这个频道还没出现过，或者这个地区有更好的版本，就更新
                if channel_name not in unique_channels:
                    unique_channels[channel_name] = channel
    
    # 转换为列表并排序
    merged_local_channels = sorted(unique_channels.values(), key=lambda x: x.split(',')[0])
    
    print(f"✅ 地方台智能合并完成: {len(merged_local_channels)} 个唯一频道")
    
    # 添加合并的地方台分类
    all_lines_custom.extend(["🏠地方台,#genre#"] + merged_local_channels + ['\n'])
    
    # 更新时间信息
    all_lines_custom.extend(["🕒更新时间,#genre#"] + [version, about, daily_mtv, daily_mtv1, daily_mtv2, daily_mtv3, daily_mtv4] + read_txt_to_array(MANUAL_ABOUT) + ['\n'])

    # 其它源 (others.txt)
    all_lines_others = []
    all_lines_others.extend(["漏网之鱼,#genre#"] + data_containers['others_lines'] + ['\n'])

    # 保存四个版本文件
    output_data = {
        'full': all_lines_full,
        'lite': all_lines_lite,
        'custom': all_lines_custom,
        'others': all_lines_others
    }

    for file_type, lines in output_data.items():
        file_path = {
            'full': FULL_OUTPUT,
            'lite': LITE_OUTPUT,
            'custom': CUSTOM_OUTPUT,
            'others': OTHERS_OUTPUT
        }[file_type]
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"✅ {file_type}源已保存: {file_path}")
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                lines_count = len(lines)
                print(f"   📊 大小: {file_size} 字节, 行数: {lines_count}")
                
        except Exception as e:
            print(f"❌ 保存{file_type}文件时发生错误：{e}")

    # 生成M3U文件
    def get_logo_by_channel_name(channel_name):
        """根据频道名称获取logo"""
        try:
            channels_logos = read_txt_to_array(f"{ASSETS_DIR}/logo.txt")
            for line in channels_logos:
                if not line.strip():
                    continue
                if ',' in line:
                    name, url = line.split(',', 1)
                    if name == channel_name:
                        return url
        except Exception as e:
            print(f"⚠️ 获取logo时发生错误：{e}")
        return None

    def make_m3u(txt_file, m3u_file):
        """生成M3U文件"""
        try:
            if not os.path.exists(txt_file):
                print(f"❌ TXT文件不存在: {txt_file}")
                return
                
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
                        output_text += f'#EXTINF:-1 group-title="{group_name}",{channel_name}\n{channel_url}\n'
                    else:
                        output_text += f'#EXTINF:-1 tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{group_name}",{channel_name}\n{channel_url}\n'

            with open(f"{m3u_file}", "w", encoding='utf-8') as file:
                file.write(output_text)
            print(f"✅ M3U文件生成: {m3u_file}")
        except Exception as e:
            print(f"❌ 生成M3U文件时发生错误：{e}")

    # 为完整版、精简版、定制版生成对应的M3U文件
    print("🎵 生成M3U文件...")
    make_m3u(FULL_OUTPUT, FULL_OUTPUT.replace(".txt", ".m3u"))
    make_m3u(LITE_OUTPUT, LITE_OUTPUT.replace(".txt", ".m3u"))
    make_m3u(CUSTOM_OUTPUT, CUSTOM_OUTPUT.replace(".txt", ".m3u"))

def generate_statistics(data_containers, timestart):
    """生成详细的统计信息"""
    # 使用北京时间
    timeend = datetime.now(beijing_tz)
    elapsed_time = timeend - timestart
    total_seconds = elapsed_time.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)

    print("\n📊 ======== 详细执行统计 =======")
    print(f"⏰ 开始时间: {timestart.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"⏰ 结束时间: {timeend.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"⏱️ 执行时间: {minutes}分{seconds}秒")

    # 主频道统计
    print("\n🎯 ======== 主频道统计 ========")
    print(f"🌐 央视源: {len(data_containers['yangshi_lines'])} 个")
    print(f"📡 卫视源: {len(data_containers['weishi_lines'])} 个")

    # 地方台详细统计
    print("\n🏠 ======== 地方台统计 ========")
    local_channels = {
        '北京频道': len(data_containers['beijing_lines']),
        '上海频道': len(data_containers['shanghai_lines']),
        '天津频道': len(data_containers['tianjin_lines']),
        '重庆频道': len(data_containers['chongqing_lines']),
        '广东频道': len(data_containers['guangdong_lines']),
        '江苏频道': len(data_containers['jiangsu_lines']),
        '浙江频道': len(data_containers['zhejiang_lines']),
        '山东频道': len(data_containers['shandong_lines']),
        '河南频道': len(data_containers['henan_lines']),
        '四川频道': len(data_containers['sichuan_lines']),
        '河北频道': len(data_containers['hebei_lines']),
        '湖南频道': len(data_containers['hunan_lines']),
        '湖北频道': len(data_containers['hubei_lines']),
        '安徽频道': len(data_containers['anhui_lines']),
        '福建频道': len(data_containers['fujian_lines']),
        '陕西频道': len(data_containers['shanxi1_lines']),
        '辽宁频道': len(data_containers['liaoning_lines']),
        '江西频道': len(data_containers['jiangxi_lines']),
        '黑龙江台': len(data_containers['heilongjiang_lines']),
        '吉林频道': len(data_containers['jilin_lines']),
        '山西频道': len(data_containers['shanxi2_lines']),
        '广西频道': len(data_containers['guangxi_lines']),
        '云南频道': len(data_containers['yunnan_lines']),
        '贵州频道': len(data_containers['guizhou_lines']),
        '甘肃频道': len(data_containers['gansu_lines']),
        '内蒙频道': len(data_containers['neimenggu_lines']),
        '新疆频道': len(data_containers['xinjiang_lines']),
        '海南频道': len(data_containers['hainan_lines']),
        '宁夏频道': len(data_containers['ningxia_lines']),
        '青海频道': len(data_containers['qinghai_lines']),
        '西藏频道': len(data_containers['xizang_lines'])
    }
    
    total_local = 0
    for region, count in local_channels.items():
        if count > 0:
            print(f"  🏠 {region}: {count} 个")
            total_local += count
    print(f"  📈 地方台总计: {total_local} 个")

    # 定制频道详细统计
    print("\n🎨 ======== 定制频道统计 ========")
    custom_channels = {
        '📰新闻频道': len(data_containers['news_lines']),
        '🎞️数字频道': len(data_containers['shuzi_lines']),
        '🎬电影频道': len(data_containers['dianying_lines']),
        '🎙️解说频道': len(data_containers['jieshuo_lines']),
        '🎤综艺频道': len(data_containers['zongyi_lines']),
        '🐯虎牙直播': len(data_containers['huya_lines']),
        '🐬斗鱼直播': len(data_containers['douyu_lines']),
        '🇭🇰香港频道': len(data_containers['xianggang_lines']),
        '🇲🇴澳门频道': len(data_containers['aomen_lines']),
        '🇨🇳中国频道': len(data_containers['china_lines']),
        '🌎国际频道': len(data_containers['guoji_lines']),
        '🇨🇳港澳台': len(data_containers['gangaotai_lines']),
        '📺电视剧': len(data_containers['dianshiju_lines']),
        '📻收音机': len(data_containers['radio_lines']),
        '🏕动画片': len(data_containers['donghuapian_lines']),
        '📽️纪录片': len(data_containers['jilupian_lines']),
        '⚽体育频道': len(data_containers['tiyu_lines']),
        '🏆体育赛事': len(data_containers['tiyusaishi_lines']),
        '🎮游戏频道': len(data_containers['youxi_lines']),
        '🎭戏曲频道': len(data_containers['xiqu_lines']),
        '🎵音乐频道': len(data_containers['yinyue_lines']),
        '🎉春晚频道': len(data_containers['chunwan_lines']),
        '📡直播中国': len(data_containers['zhibozhongguo_lines'])
    }    
    total_custom = 0
    for category, count in custom_channels.items():
        if count > 0:
            print(f"  🚀 {category}: {count} 个")
            total_custom += count
    print(f"  📈 定制频道总计: {total_custom} 个")

    # 其他分类统计
    print("\n📦 ======== 其他分类统计 ========")
    print(f"🚀 AKTV: {len(data_containers['aktv_lines'])} 个")
    print(f"🏆 赛事源: {len(data_containers['tiyusaishi_lines'])} 个")
    print(f"📦 其它源: {len(data_containers['others_lines'])} 个")

    # 总计统计
    print("\n📈 ======== 频道总计统计 ========")
    total_main = len(data_containers['yangshi_lines']) + len(data_containers['weishi_lines'])
    total_all = total_main + total_local + total_custom + len(data_containers['aktv_lines'])
    
    print(f"🎯 主频道总计: {total_main} 个")
    print(f"🏠 地方台总计: {total_local} 个") 
    print(f"🎨 定制频道总计: {total_custom} 个")
    print(f"🚀 特殊频道: {len(data_containers['aktv_lines'])} 个")
    print(f"📊 所有频道总计: {total_all} 个")

    # 最终检查所有输出文件
    print("\n🔍 ======== 文件输出检查 ========")
    all_files_ok = True
    output_files = {
        '完整版': FULL_OUTPUT,
        '精简版': LITE_OUTPUT,
        '定制版': CUSTOM_OUTPUT,
        '其他源': OTHERS_OUTPUT
    }
    
    for file_type, file_path in output_files.items():
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            line_count = 0
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    line_count = len(f.readlines())
            except:
                pass
                
            status = "✅" if file_size > 0 else "❌"
            print(f"  {status} {file_type}: {file_path}")
            print(f"     大小: {file_size:,} 字节, 行数: {line_count}")
            if file_size == 0:
                all_files_ok = False
        else:
            print(f"  ❌ {file_type}: {file_path} (文件不存在)")
            all_files_ok = False

    # 检查M3U文件
    print("\n🎵 ======== M3U文件检查 ========")
    for file_type in ['完整版', '精简版', '定制版']:
        txt_file = output_files[file_type]
        m3u_file = txt_file.replace(".txt", ".m3u")
        if os.path.exists(m3u_file):
            file_size = os.path.getsize(m3u_file)
            status = "✅" if file_size > 0 else "❌"
            print(f"  {status} {file_type}.m3u: {m3u_file}")
            print(f"     大小: {file_size:,} 字节")
        else:
            print(f"  ❌ {file_type}.m3u: {m3u_file} (文件不存在)")
            all_files_ok = False

    # 最终状态
    print("\n🎯 ======== 执行结果 ========")
    if all_files_ok:
        print("🎉 所有文件生成成功！")
        print(f"📊 总频道数: {total_all:,} 个")
        print(f"⏱️ 处理时间: {minutes}分{seconds}秒")
    else:
        print("⚠️ 部分文件生成有问题，请检查！")

    return total_all

# ====== 主函数 ======
def main():
    print(f"🚀 开始处理直播源 - 输入: {SOURCE_BASE}, 输出: {OUTPUT_BASE}")
    timestart = datetime.now(beijing_tz)
    
    # 1. 初始化所有数据容器
    data_containers = {
        # 主频道
        'yangshi_lines': [],  # CCTV
        'weishi_lines': [],   # 卫视频道
        
        # 地方台
        'beijing_lines': [], 'shanghai_lines': [], 'tianjin_lines': [], 
        'chongqing_lines': [], 'guangdong_lines': [], 'jiangsu_lines': [], 
        'zhejiang_lines': [], 'shandong_lines': [], 'henan_lines': [], 
        'sichuan_lines': [], 'hebei_lines': [], 'hunan_lines': [], 
        'hubei_lines': [], 'anhui_lines': [], 'fujian_lines': [], 
        'shanxi1_lines': [], 'liaoning_lines': [], 'jiangxi_lines': [], 
        'heilongjiang_lines': [], 'jilin_lines': [], 'shanxi2_lines': [], 
        'guangxi_lines': [], 'yunnan_lines': [], 'guizhou_lines': [], 
        'gansu_lines': [], 'neimenggu_lines': [], 'xinjiang_lines': [], 
        'hainan_lines': [], 'ningxia_lines': [], 'qinghai_lines': [], 'xizang_lines': [],
        
        # 定制频道
        'news_lines': [], 'shuzi_lines': [], 'dianying_lines': [], 
        'jieshuo_lines': [], 'zongyi_lines': [], 'huya_lines': [], 
        'douyu_lines': [], 'xianggang_lines': [], 'aomen_lines': [], 
        'china_lines': [], 'guoji_lines': [], 'gangaotai_lines': [], 
        'dianshiju_lines': [], 'radio_lines': [], 'donghuapian_lines': [], 
        'jilupian_lines': [], 'tiyu_lines': [], 'tiyusaishi_lines': [], 
        'youxi_lines': [], 'xiqu_lines': [], 'yinyue_lines': [], 
        'chunwan_lines': [], 'zhibozhongguo_lines': [],
        
        # 其他分类
        'others_lines': [], 'others_lines_url': [], 'aktv_lines': []
    }
    
    # 2. 加载字典数据
    dictionaries = load_all_dictionaries()
    
    # 3. 加载黑名单
    blacklist = load_blacklist()
    
    # 4. 处理URL源
    process_url_sources(data_containers, dictionaries, blacklist)
    
    # 5. 处理白名单和手工区
    process_whitelist_and_manual(data_containers, dictionaries, blacklist)
    
    # 6. 生成输出文件
    generate_output_files(data_containers, dictionaries)
    
    # 7. 生成统计信息
    generate_statistics(data_containers, timestart)

if __name__ == "__main__":
    main()