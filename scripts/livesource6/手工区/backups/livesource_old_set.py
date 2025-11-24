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
timestart = datetime.now(beijing_tz)

print(f"🚀 开始处理直播源 - 输入: {SOURCE_BASE}, 输出: {OUTPUT_BASE}")

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

# ====== 黑名单处理 ======
print("🔧 加载黑名单...")
blacklist_auto = read_blacklist_from_txt(f"{BLACKLIST_DIR}/blacklist_auto.txt") 
blacklist_manual = read_blacklist_from_txt(f"{BLACKLIST_DIR}/blacklist_manual.txt") 
combined_blacklist = set(blacklist_auto + blacklist_manual)
print(f"✅ 黑名单加载完成: {len(combined_blacklist)} 条记录")

# ====== 数据存储容器 - 完全使用Set去重 ======
# 主频道
yangshi_lines = [] #CCTV
yangshi_urls = set()  # CCTV URL去重Set
weishi_lines = [] #卫视频道
weishi_urls = set()   # 卫视URL去重Set

# 地方台 - 按照收视率顺序，每个分类都有对应的URL去重Set
beijing_lines = [] #北京频道
beijing_urls = set()
shanghai_lines = [] #上海频道
shanghai_urls = set()
tianjin_lines = [] #天津频道
tianjin_urls = set()
chongqing_lines = [] #重庆频道
chongqing_urls = set()
guangdong_lines = [] #广东频道
guangdong_urls = set()
jiangsu_lines = [] #江苏频道
jiangsu_urls = set()
zhejiang_lines = [] #浙江频道
zhejiang_urls = set()
shandong_lines = [] #山东频道
shandong_urls = set()
henan_lines = [] #河南频道
henan_urls = set()
sichuan_lines = [] #四川频道
sichuan_urls = set()
hebei_lines = [] #河北频道
hebei_urls = set()
hunan_lines = [] #湖南频道
hunan_urls = set()
hubei_lines = [] #湖北频道
hubei_urls = set()
anhui_lines = [] #安徽频道
anhui_urls = set()
fujian_lines = [] #福建频道
fujian_urls = set()
shanxi1_lines = [] #陕西频道
shanxi1_urls = set()
liaoning_lines = [] #辽宁频道
liaoning_urls = set()
jiangxi_lines = [] #江西频道
jiangxi_urls = set()
heilongjiang_lines = [] #黑龙江频道
heilongjiang_urls = set()
jilin_lines = [] #吉林频道
jilin_urls = set()
shanxi2_lines = [] #山西频道
shanxi2_urls = set()
guangxi_lines = [] #广西频道
guangxi_urls = set()
yunnan_lines = [] #云南频道
yunnan_urls = set()
guizhou_lines = [] #贵州频道
guizhou_urls = set()
gansu_lines = [] #甘肃频道
gansu_urls = set()
neimenggu_lines = [] #内蒙频道
neimenggu_urls = set()
xinjiang_lines = [] #新疆频道
xinjiang_urls = set()
hainan_lines = [] #海南频道
hainan_urls = set()
ningxia_lines = [] #宁夏频道
ningxia_urls = set()
qinghai_lines = [] #青海频道
qinghai_urls = set()
xizang_lines = [] #西藏频道
xizang_urls = set()

# 定制频道 - 按照个人喜好分类，每个分类都有对应的URL去重Set
news_lines = [] #新闻频道
news_urls = set()
shuzi_lines = [] #数字频道
shuzi_urls = set()
dianying_lines = [] #电影频道
dianying_urls = set()
jieshuo_lines = [] #解说频道
jieshuo_urls = set()
zongyi_lines = [] #综艺频道
zongyi_urls = set()
huya_lines = [] #虎牙直播
huya_urls = set()
douyu_lines = [] #斗鱼直播
douyu_urls = set()
xianggang_lines = [] #香港频道
xianggang_urls = set()
aomen_lines = [] #澳门频道
aomen_urls = set()
china_lines = [] #中国频道
china_urls = set()
guoji_lines = [] #国际频道
guoji_urls = set()
gangaotai_lines = [] #港澳台
gangaotai_urls = set()
dianshiju_lines = [] #电视剧
dianshiju_urls = set()
radio_lines = [] #收音机
radio_urls = set()
donghuapian_lines = [] #动画片
donghuapian_urls = set()
jilupian_lines = [] #记录片
jilupian_urls = set()
tiyu_lines = [] #体育频道
tiyu_urls = set()
tiyusaishi_lines = [] #体育赛事
tiyusaishi_urls = set()
youxi_lines = [] #游戏频道
youxi_urls = set()
xiqu_lines = [] #戏曲频道
xiqu_urls = set()
yinyue_lines = [] #音乐频道
yinyue_urls = set()
chunwan_lines = [] #春晚频道
chunwan_urls = set()
zhibozhongguo_lines = [] #直播中国
zhibozhongguo_urls = set()

# 其他分类
others_lines = []
others_urls = set()  # 完全使用Set存储URL哈希

# AKTV频道
aktv_lines = []

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

def check_url_existence(url_set, url):
    """检查URL是否已存在 - 使用Set优化版本"""
    try:
        return url not in url_set
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

# ====== 核心分发逻辑 - 完全Set去重 ======
def process_channel_line(line):
    """处理单行频道数据并分类 - 支持同频道多分类且完全Set去重"""
    try:
        if "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
            channel_name = line.split(',')[0].strip()
            original_name = channel_name  # 保存原始名称
            channel_name = clean_channel_name(channel_name, REMOVAL_LIST)
            channel_name = traditional_to_simplified(channel_name)
            channel_address = clean_url(line.split(',')[1].strip())
            
            # 跳过黑名单和特定协议
            if channel_address in combined_blacklist or should_skip_url(channel_address):
                return

            url_hash = get_url_hash(channel_address)
            processed_line = channel_name + "," + channel_address

            # 主频道分发 - 支持同频道多分类，完全Set去重
            channel_added = False
            
            if "CCTV" in channel_name and check_url_existence(yangshi_urls, channel_address):
                yangshi_urls.add(channel_address)
                yangshi_lines.append(process_name_string(processed_line))
                channel_added = True
            
            if channel_name in weishi_dictionary and check_url_existence(weishi_urls, channel_address):
                weishi_urls.add(channel_address)
                weishi_lines.append(process_name_string(processed_line))
                channel_added = True
            
            # 地方台分发 - 支持同频道多分类，完全Set去重
            if channel_name in beijing_dictionary and check_url_existence(beijing_urls, channel_address):
                beijing_urls.add(channel_address)
                beijing_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shanghai_dictionary and check_url_existence(shanghai_urls, channel_address):
                shanghai_urls.add(channel_address)
                shanghai_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in tianjin_dictionary and check_url_existence(tianjin_urls, channel_address):
                tianjin_urls.add(channel_address)
                tianjin_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in chongqing_dictionary and check_url_existence(chongqing_urls, channel_address):
                chongqing_urls.add(channel_address)
                chongqing_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in guangdong_dictionary and check_url_existence(guangdong_urls, channel_address):
                guangdong_urls.add(channel_address)
                guangdong_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jiangsu_dictionary and check_url_existence(jiangsu_urls, channel_address):
                jiangsu_urls.add(channel_address)
                jiangsu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in zhejiang_dictionary and check_url_existence(zhejiang_urls, channel_address):
                zhejiang_urls.add(channel_address)
                zhejiang_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shandong_dictionary and check_url_existence(shandong_urls, channel_address):
                shandong_urls.add(channel_address)
                shandong_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in henan_dictionary and check_url_existence(henan_urls, channel_address):
                henan_urls.add(channel_address)
                henan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in sichuan_dictionary and check_url_existence(sichuan_urls, channel_address):
                sichuan_urls.add(channel_address)
                sichuan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hebei_dictionary and check_url_existence(hebei_urls, channel_address):
                hebei_urls.add(channel_address)
                hebei_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hunan_dictionary and check_url_existence(hunan_urls, channel_address):
                hunan_urls.add(channel_address)
                hunan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hubei_dictionary and check_url_existence(hubei_urls, channel_address):
                hubei_urls.add(channel_address)
                hubei_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in anhui_dictionary and check_url_existence(anhui_urls, channel_address):
                anhui_urls.add(channel_address)
                anhui_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in fujian_dictionary and check_url_existence(fujian_urls, channel_address):
                fujian_urls.add(channel_address)
                fujian_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shanxi1_dictionary and check_url_existence(shanxi1_urls, channel_address):
                shanxi1_urls.add(channel_address)
                shanxi1_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in liaoning_dictionary and check_url_existence(liaoning_urls, channel_address):
                liaoning_urls.add(channel_address)
                liaoning_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jiangxi_dictionary and check_url_existence(jiangxi_urls, channel_address):
                jiangxi_urls.add(channel_address)
                jiangxi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in heilongjiang_dictionary and check_url_existence(heilongjiang_urls, channel_address):
                heilongjiang_urls.add(channel_address)
                heilongjiang_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jilin_dictionary and check_url_existence(jilin_urls, channel_address):
                jilin_urls.add(channel_address)
                jilin_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shanxi2_dictionary and check_url_existence(shanxi2_urls, channel_address):
                shanxi2_urls.add(channel_address)
                shanxi2_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in guangxi_dictionary and check_url_existence(guangxi_urls, channel_address):
                guangxi_urls.add(channel_address)
                guangxi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in yunnan_dictionary and check_url_existence(yunnan_urls, channel_address):
                yunnan_urls.add(channel_address)
                yunnan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in guizhou_dictionary and check_url_existence(guizhou_urls, channel_address):
                guizhou_urls.add(channel_address)
                guizhou_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gansu_dictionary and check_url_existence(gansu_urls, channel_address):
                gansu_urls.add(channel_address)
                gansu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in neimenggu_dictionary and check_url_existence(neimenggu_urls, channel_address):
                neimenggu_urls.add(channel_address)
                neimenggu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xinjiang_dictionary and check_url_existence(xinjiang_urls, channel_address):
                xinjiang_urls.add(channel_address)
                xinjiang_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hainan_dictionary and check_url_existence(hainan_urls, channel_address):
                hainan_urls.add(channel_address)
                hainan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in ningxia_dictionary and check_url_existence(ningxia_urls, channel_address):
                ningxia_urls.add(channel_address)
                ningxia_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in qinghai_dictionary and check_url_existence(qinghai_urls, channel_address):
                qinghai_urls.add(channel_address)
                qinghai_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xizang_dictionary and check_url_existence(xizang_urls, channel_address):
                xizang_urls.add(channel_address)
                xizang_lines.append(process_name_string(processed_line))
                channel_added = True
            
            # 定制频道分发 - 完全Set去重
            if channel_name in news_dictionary and check_url_existence(news_urls, channel_address):
                news_urls.add(channel_address)
                news_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shuzi_dictionary and check_url_existence(shuzi_urls, channel_address):
                shuzi_urls.add(channel_address)
                shuzi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dianying_dictionary and check_url_existence(dianying_urls, channel_address):
                dianying_urls.add(channel_address)
                dianying_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jieshuo_dictionary and check_url_existence(jieshuo_urls, channel_address):
                jieshuo_urls.add(channel_address)
                jieshuo_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in zongyi_dictionary and check_url_existence(zongyi_urls, channel_address):
                zongyi_urls.add(channel_address)
                zongyi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in huya_dictionary and check_url_existence(huya_urls, channel_address):
                huya_urls.add(channel_address)
                huya_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in douyu_dictionary and check_url_existence(douyu_urls, channel_address):
                douyu_urls.add(channel_address)
                douyu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xianggang_dictionary and check_url_existence(xianggang_urls, channel_address):
                xianggang_urls.add(channel_address)
                xianggang_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in aomen_dictionary and check_url_existence(aomen_urls, channel_address):
                aomen_urls.add(channel_address)
                aomen_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in china_dictionary and check_url_existence(china_urls, channel_address):
                china_urls.add(channel_address)
                china_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in guoji_dictionary and check_url_existence(guoji_urls, channel_address):
                guoji_urls.add(channel_address)
                guoji_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gangaotai_dictionary and check_url_existence(gangaotai_urls, channel_address):
                gangaotai_urls.add(channel_address)
                gangaotai_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dianshiju_dictionary and check_url_existence(dianshiju_urls, channel_address):
                dianshiju_urls.add(channel_address)
                dianshiju_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in radio_dictionary and check_url_existence(radio_urls, channel_address):
                radio_urls.add(channel_address)
                radio_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in donghuapian_dictionary and check_url_existence(donghuapian_urls, channel_address):
                donghuapian_urls.add(channel_address)
                donghuapian_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jilupian_dictionary and check_url_existence(jilupian_urls, channel_address):
                jilupian_urls.add(channel_address)
                jilupian_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in tiyu_dictionary and check_url_existence(tiyu_urls, channel_address):
                tiyu_urls.add(channel_address)
                tiyu_lines.append(process_name_string(processed_line))
                channel_added = True
            
            if any(tiyusaishi_item in channel_name for tiyusaishi_item in tiyusaishi_dictionary) and check_url_existence(tiyusaishi_urls, channel_address):
                tiyusaishi_urls.add(channel_address)
                tiyusaishi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in youxi_dictionary and check_url_existence(youxi_urls, channel_address):
                youxi_urls.add(channel_address)
                youxi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xiqu_dictionary and check_url_existence(xiqu_urls, channel_address):
                xiqu_urls.add(channel_address)
                xiqu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in yinyue_dictionary and check_url_existence(yinyue_urls, channel_address):
                yinyue_urls.add(channel_address)
                yinyue_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in chunwan_dictionary and check_url_existence(chunwan_urls, channel_address):
                chunwan_urls.add(channel_address)
                chunwan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in zhibozhongguo_dictionary and check_url_existence(zhibozhongguo_urls, channel_address):
                zhibozhongguo_urls.add(channel_address)
                zhibozhongguo_lines.append(process_name_string(processed_line))
                channel_added = True
            
            # 其他频道分发 - 完全Set去重
            if not channel_added and url_hash not in others_urls:
                others_urls.add(url_hash)
                others_lines.append(processed_line)

    except Exception as e:
        print(f"❌ 处理频道行错误: {e}, 行内容: {line}")

def process_url(url):
    """处理单个URL源"""
    try:
        print(f"🌐 处理URL: {url}")
        others_lines.append(f"◆◆◆ {url}")
        
        response_text = get_http_response(url)
        if not response_text:
            print(f"❌ 获取URL内容失败: {url}")
            others_lines.append(f"❌ 获取失败: {url}\n")
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
                        process_channel_line(line)
                        valid_lines += 1
                    else:
                        url_list = channel_address.split('#')
                        for channel_url in url_list:
                            process_channel_line(f'{channel_name},{channel_url}')
                            valid_lines += 1
                except Exception as e:
                    print(f"⚠️ 处理行错误: {e}, 行: {line}")

        print(f"✅ 处理完成: {valid_lines} 个有效频道")
        others_lines.append(f"✅ 完成: {valid_lines} 个频道\n")

    except Exception as e:
        print(f"❌ 处理URL时发生错误 {url}: {e}")
        others_lines.append(f"❌ 错误: {e}\n")

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

# ====== 加载字典数据 ======
print("📚 加载字典数据...")
# 主频道字典
yangshi_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/CCTV.txt")
weishi_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/卫视频道.txt")

# 地方台字典 - 按照收视率顺序
beijing_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/北京频道.txt")
shanghai_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/上海频道.txt")
tianjin_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/天津频道.txt")
chongqing_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/重庆频道.txt")
guangdong_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/广东频道.txt")
jiangsu_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/江苏频道.txt")
zhejiang_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/浙江频道.txt")
shandong_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/山东频道.txt")
henan_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/河南频道.txt")
sichuan_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/四川频道.txt")
hebei_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/河北频道.txt")
hunan_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/湖南频道.txt")
hubei_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/湖北频道.txt")
anhui_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/安徽频道.txt")
fujian_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/福建频道.txt")
shanxi1_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/陕西频道.txt")
liaoning_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/辽宁频道.txt")
jiangxi_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/江西频道.txt")
heilongjiang_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/黑龙江频道.txt")
jilin_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/吉林频道.txt")
shanxi2_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/山西频道.txt")
guangxi_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/广西频道.txt")
yunnan_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/云南频道.txt")
guizhou_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/贵州频道.txt")
gansu_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/甘肃频道.txt")
neimenggu_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/内蒙频道.txt")
xinjiang_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/新疆频道.txt")
hainan_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/海南频道.txt")
ningxia_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/宁夏频道.txt")
qinghai_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/青海频道.txt")
xizang_dictionary = read_txt_to_array(f"{LOCAL_CHANNELS_DIR}/西藏频道.txt")

# 定制频道字典 - 按照个人喜好分类
news_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/新闻频道.txt")
shuzi_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/数字频道.txt")
dianying_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/电影频道.txt")
jieshuo_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/解说频道.txt")
zongyi_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/综艺频道.txt")
huya_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/虎牙直播.txt")
douyu_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/斗鱼直播.txt")
xianggang_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/香港频道.txt")
aomen_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/澳门频道.txt")
china_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/中国频道.txt")
guoji_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/国际频道.txt")
gangaotai_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/港澳台.txt")
dianshiju_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/电视剧.txt")
radio_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/收音机.txt")
donghuapian_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/动画片.txt")
jilupian_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/记录片.txt")
tiyu_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/体育频道.txt")
tiyusaishi_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/体育赛事.txt")
youxi_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/游戏频道.txt")
xiqu_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/戏曲频道.txt")
yinyue_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/音乐频道.txt")
chunwan_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/春晚频道.txt")
zhibozhongguo_dictionary = read_txt_to_array(f"{MAIN_CHANNELS_DIR}/直播中国.txt")

# 加载纠错数据
corrections_name = load_corrections_name(f"{ASSETS_DIR}/corrections_name.txt")

print(f"✅ 字典数据加载完成: CCTV({len(yangshi_dictionary)}) 卫视({len(weishi_dictionary)}) 地方台(31个) 定制频道(23个)")

# ====== 主处理流程 ======
def main():
    print("🚀 开始处理直播源...")
    
    # 1. 处理URL源
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
            
            process_url(url)

    # 2. 处理白名单
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
                process_channel_line(",".join(whitelist_parts[1:]))
                whitelist_count += 1
    print(f"✅ 白名单处理完成: {whitelist_count} 个高速源")

    # 3. 处理手工区
    print("🔧 处理手工区...")
    # 处理所有手工区文件
    manual_files = {
        '国际频道': guoji_lines,
        '港·澳·台': gangaotai_lines,
        '动·画·片': donghuapian_lines,
        '收·音·机': radio_lines,
        '记·录·片': jilupian_lines,
        '香港频道': xianggang_lines,
        '澳门频道': aomen_lines,
        '中国频道': china_lines,
        '湖北频道': hubei_lines, 
    }

    for region, target_list in manual_files.items():
        manual_file = f"{MANUAL_DIR}/{region}.txt"
        if os.path.exists(manual_file):
            manual_data = read_txt_to_array(manual_file)
            for line in manual_data:
                if "," in line and "://" in line:
                    process_channel_line(line)  # 使用相同的处理逻辑确保去重
            print(f"✅ 手工区 {region}: {len(manual_data)} 条记录")

    # 4. 处理AKTV
    print("🌐 处理AKTV...")
    aktv_url = "https://aktv.space/live.m3u"
    aktv_text = get_http_response(aktv_url)
    if aktv_text:
        print("✅ AKTV成功获取内容")
        aktv_text = convert_m3u_to_txt(aktv_text)
        aktv_lines.extend(aktv_text.strip().split('\n'))
    else:
        print("⚠️ AKTV请求失败，从本地获取！")
        aktv_lines.extend(read_txt_to_array(MANUAL_AKTV))
    print(f"✅ AKTV处理完成: {len(aktv_lines)} 个频道")

    # 5. 处理体育赛事日期格式
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

    normalized_tiyusaishi_lines = [normalize_date_to_md(s) for s in tiyusaishi_lines]

    # 6. 生成版本信息 - 使用北京时间
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

    # 7. 生成输出文件
    print("📄 生成输出文件...")

    # 全部源 (full.txt)
    all_lines_full = []
    all_lines_full.extend(["🌐央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name, yangshi_lines)) + ['\n'])
    all_lines_full.extend(["📡卫视频道,#genre#"] + sort_data(weishi_dictionary, correct_name_data(corrections_name, weishi_lines)) + ['\n'])

    # 地方台分类 - 按照收视率顺序
    all_lines_full.extend(["☘️北京频道,#genre#"] + sort_data(beijing_dictionary, set(correct_name_data(corrections_name, beijing_lines))) + ['\n'])
    all_lines_full.extend(["☘️上海频道,#genre#"] + sort_data(shanghai_dictionary, set(correct_name_data(corrections_name, shanghai_lines))) + ['\n'])
    all_lines_full.extend(["☘️天津频道,#genre#"] + sort_data(tianjin_dictionary, set(correct_name_data(corrections_name, tianjin_lines))) + ['\n'])
    all_lines_full.extend(["☘️重庆频道,#genre#"] + sort_data(chongqing_dictionary, set(correct_name_data(corrections_name, chongqing_lines))) + ['\n'])
    all_lines_full.extend(["☘️广东频道,#genre#"] + sort_data(guangdong_dictionary, set(correct_name_data(corrections_name, guangdong_lines))) + ['\n'])
    all_lines_full.extend(["☘️江苏频道,#genre#"] + sort_data(jiangsu_dictionary, set(correct_name_data(corrections_name, jiangsu_lines))) + ['\n'])
    all_lines_full.extend(["☘️浙江频道,#genre#"] + sort_data(zhejiang_dictionary, set(correct_name_data(corrections_name, zhejiang_lines))) + ['\n'])
    all_lines_full.extend(["☘️山东频道,#genre#"] + sort_data(shandong_dictionary, set(correct_name_data(corrections_name, shandong_lines))) + ['\n'])
    all_lines_full.extend(["☘️河南频道,#genre#"] + sort_data(henan_dictionary, set(correct_name_data(corrections_name, henan_lines))) + ['\n'])
    all_lines_full.extend(["☘️四川频道,#genre#"] + sort_data(sichuan_dictionary, set(correct_name_data(corrections_name, sichuan_lines))) + ['\n'])
    all_lines_full.extend(["☘️河北频道,#genre#"] + sort_data(hebei_dictionary, set(correct_name_data(corrections_name, hebei_lines))) + ['\n'])
    all_lines_full.extend(["☘️湖南频道,#genre#"] + sort_data(hunan_dictionary, set(correct_name_data(corrections_name, hunan_lines))) + ['\n'])
    all_lines_full.extend(["☘️湖北频道,#genre#"] + sort_data(hubei_dictionary, set(correct_name_data(corrections_name, hubei_lines))) + ['\n'])
    all_lines_full.extend(["☘️安徽频道,#genre#"] + sort_data(anhui_dictionary, set(correct_name_data(corrections_name, anhui_lines))) + ['\n'])
    all_lines_full.extend(["☘️福建频道,#genre#"] + sort_data(fujian_dictionary, set(correct_name_data(corrections_name, fujian_lines))) + ['\n'])
    all_lines_full.extend(["☘️陕西频道,#genre#"] + sort_data(shanxi1_dictionary, set(correct_name_data(corrections_name, shanxi1_lines))) + ['\n'])
    all_lines_full.extend(["☘️辽宁频道,#genre#"] + sort_data(liaoning_dictionary, set(correct_name_data(corrections_name, liaoning_lines))) + ['\n'])
    all_lines_full.extend(["☘️江西频道,#genre#"] + sort_data(jiangxi_dictionary, set(correct_name_data(corrections_name, jiangxi_lines))) + ['\n'])
    all_lines_full.extend(["☘️黑龙江台,#genre#"] + sorted(set(correct_name_data(corrections_name, heilongjiang_lines))) + ['\n'])
    all_lines_full.extend(["☘️吉林频道,#genre#"] + sort_data(jilin_dictionary, set(correct_name_data(corrections_name, jilin_lines))) + ['\n'])
    all_lines_full.extend(["☘️山西频道,#genre#"] + sort_data(shanxi2_dictionary, set(correct_name_data(corrections_name, shanxi2_lines))) + ['\n'])
    all_lines_full.extend(["☘️广西频道,#genre#"] + sort_data(guangxi_dictionary, set(correct_name_data(corrections_name, guangxi_lines))) + ['\n'])
    all_lines_full.extend(["☘️云南频道,#genre#"] + sort_data(yunnan_dictionary, set(correct_name_data(corrections_name, yunnan_lines))) + ['\n'])
    all_lines_full.extend(["☘️贵州频道,#genre#"] + sort_data(guizhou_dictionary, set(correct_name_data(corrections_name, guizhou_lines))) + ['\n'])
    all_lines_full.extend(["☘️甘肃频道,#genre#"] + sort_data(gansu_dictionary, set(correct_name_data(corrections_name, gansu_lines))) + ['\n'])
    all_lines_full.extend(["☘️内蒙频道,#genre#"] + sort_data(neimenggu_dictionary, set(correct_name_data(corrections_name, neimenggu_lines))) + ['\n'])
    all_lines_full.extend(["☘️新疆频道,#genre#"] + sort_data(xinjiang_dictionary, set(correct_name_data(corrections_name, xinjiang_lines))) + ['\n'])
    all_lines_full.extend(["☘️海南频道,#genre#"] + sort_data(hainan_dictionary, set(correct_name_data(corrections_name, hainan_lines))) + ['\n'])
    all_lines_full.extend(["☘️宁夏频道,#genre#"] + sort_data(ningxia_dictionary, set(correct_name_data(corrections_name, ningxia_lines))) + ['\n'])
    all_lines_full.extend(["☘️青海频道,#genre#"] + sort_data(qinghai_dictionary, set(correct_name_data(corrections_name, qinghai_lines))) + ['\n'])
    all_lines_full.extend(["☘️西藏频道,#genre#"] + sort_data(xizang_dictionary, set(correct_name_data(corrections_name, xizang_lines))) + ['\n'])

    # 定制频道 - 按照个人喜好分类
    all_lines_full.extend(["📰新闻频道,#genre#"] + sort_data(news_dictionary, set(correct_name_data(corrections_name, news_lines))) + ['\n'])
    all_lines_full.extend(["🎞️数字频道,#genre#"] + sort_data(shuzi_dictionary, set(correct_name_data(corrections_name, shuzi_lines))) + ['\n'])
    all_lines_full.extend(["🎬电影频道,#genre#"] + sort_data(dianying_dictionary, set(correct_name_data(corrections_name, dianying_lines))) + ['\n'])
    all_lines_full.extend(["🎙️解说频道,#genre#"] + sort_data(jieshuo_dictionary, set(correct_name_data(corrections_name, jieshuo_lines))) + ['\n'])
    all_lines_full.extend(["🎤综艺频道,#genre#"] + sorted(set(correct_name_data(corrections_name, zongyi_lines))) + ['\n'])
    all_lines_full.extend(["🐯虎牙直播,#genre#"] + sort_data(huya_dictionary, set(correct_name_data(corrections_name, huya_lines))) + ['\n'])
    all_lines_full.extend(["🐬斗鱼直播,#genre#"] + sort_data(douyu_dictionary, set(correct_name_data(corrections_name, douyu_lines))) + ['\n'])
    all_lines_full.extend(["🇭🇰香港频道,#genre#"] + sort_data(xianggang_dictionary, set(correct_name_data(corrections_name, xianggang_lines))) + ['\n'])
    all_lines_full.extend(["🇲🇴澳门频道,#genre#"] + sort_data(aomen_dictionary, set(correct_name_data(corrections_name, aomen_lines))) + ['\n'])
    all_lines_full.extend(["🇨🇳中国频道,#genre#"] + sort_data(china_dictionary, set(correct_name_data(corrections_name, china_lines))) + ['\n'])
    all_lines_full.extend(["🌎国际频道,#genre#"] + sort_data(guoji_dictionary, set(correct_name_data(corrections_name, guoji_lines))) + ['\n'])
    all_lines_full.extend(["🇨🇳港·澳·台,#genre#"] + read_txt_to_array(MANUAL_GAT) + sort_data(gangaotai_dictionary, set(correct_name_data(corrections_name, gangaotai_lines))) + aktv_lines + ['\n'])
    all_lines_full.extend(["📺电·视·剧,#genre#"] + sort_data(dianshiju_dictionary, set(correct_name_data(corrections_name, dianshiju_lines))) + ['\n'])
    all_lines_full.extend(["📻收·音·机,#genre#"] + sort_data(radio_dictionary, set(correct_name_data(corrections_name, radio_lines))) + ['\n'])
    all_lines_full.extend(["🏕动·画·片,#genre#"] + sort_data(donghuapian_dictionary, set(correct_name_data(corrections_name, donghuapian_lines))) + ['\n'])
    all_lines_full.extend(["📽️记·录·片,#genre#"] + sort_data(jilupian_dictionary, set(correct_name_data(corrections_name, jilupian_lines))) + ['\n'])
    all_lines_full.extend(["⚽体育频道,#genre#"] + sort_data(tiyu_dictionary, set(correct_name_data(corrections_name, tiyu_lines))) + ['\n'])
    all_lines_full.extend(["🏆体育赛事,#genre#"] + normalized_tiyusaishi_lines + ['\n'])
    all_lines_full.extend(["🎮游戏频道,#genre#"] + sorted(set(correct_name_data(corrections_name, youxi_lines))) + ['\n'])
    all_lines_full.extend(["🎭戏曲频道,#genre#"] + sort_data(xiqu_dictionary, set(correct_name_data(corrections_name, xiqu_lines))) + ['\n'])
    all_lines_full.extend(["🎵音乐频道,#genre#"] + sort_data(yinyue_dictionary, set(correct_name_data(corrections_name, yinyue_lines))) + ['\n'])
    all_lines_full.extend(["🎉春晚频道,#genre#"] + sort_data(chunwan_dictionary, set(correct_name_data(corrections_name, chunwan_lines))) + ['\n'])
    all_lines_full.extend(["📡直播中国,#genre#"] + sort_data(zhibozhongguo_dictionary, set(correct_name_data(corrections_name, zhibozhongguo_lines))) + ['\n'])

    # 手工区频道
    all_lines_full.extend(["✨优质央视,#genre#"] + read_txt_to_array(MANUAL_CCTV) + ['\n'])
    all_lines_full.extend(["🛰️优质卫视,#genre#"] + read_txt_to_array(MANUAL_WS) + ['\n'])

    # 其它和更新信息
    all_lines_full.extend(["📦漏网之鱼,#genre#"] + others_lines + ['\n'])
    all_lines_full.extend(["🕒更新时间,#genre#"] + [version, about, daily_mtv, daily_mtv1, daily_mtv2, daily_mtv3, daily_mtv4] + read_txt_to_array(MANUAL_ABOUT) + ['\n'])

    # 精简源 (lite.txt)
    all_lines_lite = []
    all_lines_lite.extend(["央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name, yangshi_lines)) + ['\n'])
    all_lines_lite.extend(["卫视频道,#genre#"] + sort_data(weishi_dictionary, correct_name_data(corrections_name, weishi_lines)) + ['\n'])
    all_lines_lite.extend(["更新时间,#genre#"] + [version] + ['\n'])

    # 定制源 (custom.txt)
    all_lines_custom = []
    all_lines_custom.extend(["🌐央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name, yangshi_lines)) + ['\n'])
    all_lines_custom.extend(["📡卫视频道,#genre#"] + sort_data(weishi_dictionary, correct_name_data(corrections_name, weishi_lines)) + ['\n'])
    all_lines_custom.extend(["🕒更新时间,#genre#"] + [version, about, daily_mtv, daily_mtv1, daily_mtv2, daily_mtv3, daily_mtv4] + read_txt_to_array(MANUAL_ABOUT) + ['\n'])

    # 其它源 (others.txt)
    all_lines_others = []
    all_lines_others.extend(["漏网之鱼,#genre#"] + others_lines + ['\n'])

    # 8. 保存四个版本文件
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

    # 9. 生成M3U文件
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

    # 10. 统计信息 - 使用北京时间
    timeend = datetime.now(beijing_tz)
    elapsed_time = timeend - timestart
    total_seconds = elapsed_time.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)

    print("\n📊 ======== 执行统计 =======")
    print(f"⏰ 开始时间: {timestart.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"⏰ 结束时间: {timeend.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"⏱️ 执行时间: {minutes}分{seconds}秒")
    print(f"📋 黑名单: {len(combined_blacklist)} 条")
    print(f"📋 白名单: {whitelist_count} 个高速源")

    # 主频道统计
    print(f"🌐 央视源: {len(yangshi_lines)} 个")
    print(f"📡 卫视源: {len(weishi_lines)} 个")

    # 其他统计
    print(f"🚀 AKTV: {len(aktv_lines)} 个")
    print(f"🏆 赛事源: {len(normalized_tiyusaishi_lines)} 个")
    print(f"📦 其它源: {len(others_lines)} 个")
    print(f"📄 全部源: {len(all_lines_full)} 行")
    print(f"📄 精简源: {len(all_lines_lite)} 行")
    print(f"📄 定制源: {len(all_lines_custom)} 行")
    print("======================\n")
    
    # 最终检查所有输出文件
    print("🔍 最终文件检查:")
    all_files_ok = True
    output_files = {
        'full': FULL_OUTPUT,
        'lite': LITE_OUTPUT,
        'custom': CUSTOM_OUTPUT,
        'others': OTHERS_OUTPUT
    }
    
    for file_type, file_path in output_files.items():
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            status = "✅" if file_size > 0 else "❌"
            print(f"  {status} {file_type}: {file_path} ({file_size} 字节)")
            if file_size == 0:
                all_files_ok = False
        else:
            print(f"  ❌ {file_type}: {file_path} (文件不存在)")
            all_files_ok = False

    # 检查M3U文件
    for file_type in ['full', 'lite', 'custom']:
        m3u_file = output_files[file_type].replace(".txt", ".m3u")
        if os.path.exists(m3u_file):
            file_size = os.path.getsize(m3u_file)
            status = "✅" if file_size > 0 else "❌"
            print(f"  {status} {file_type}.m3u: {m3u_file} ({file_size} 字节)")
        else:
            print(f"  ❌ {file_type}.m3u: {m3u_file} (文件不存在)")
            all_files_ok = False

    if all_files_ok:
        print("🎉 所有文件生成成功！")
    else:
        print("⚠️ 部分文件生成有问题，请检查！")

if __name__ == "__main__":
    main()