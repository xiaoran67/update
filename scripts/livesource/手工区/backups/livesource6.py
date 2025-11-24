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

# ======= 配置区域 ========
# 在这里修改输入输出路径即可
SOURCE_BASE = "scripts/livesource6"
OUTPUT_BASE = "output/livesource6"

CONFIG = {
    # 输入路径配置
    'source_base': SOURCE_BASE,
    'assets_dir': f"{SOURCE_BASE}",
    'blacklist_dir': f"{SOURCE_BASE}/blacklist",
    'main_channels_dir': f"{SOURCE_BASE}/主频道", 
    'local_channels_dir': f"{SOURCE_BASE}/地方台",
    'manual_dir': f"{SOURCE_BASE}/手工区",
    
    # 输出路径配置
    'output_base': OUTPUT_BASE,
    'output_dir': OUTPUT_BASE,
    'output_files': {
        'full': f'{OUTPUT_BASE}/full.txt',
        'lite': f'{OUTPUT_BASE}/lite.txt', 
        'custom': f'{OUTPUT_BASE}/custom.txt',
        'others': f'{OUTPUT_BASE}/others.txt'
    },
    
    # 其他配置（通常不需要修改）
    'request_timeout': 10,
    'request_retries': 3,
    'request_backoff_factor': 1.5,
    
    'removal_list': [
        "_电信", "电信", "高清", "频道", "（HD）", "-HD", "英陆", "_ITV", "(北美)", "(HK)", 
        "AKtv", "「IPV4」", "「IPV6」", "频陆", "备陆", "壹陆", "贰陆", "叁陆", "肆陆", 
        "伍陆", "陆陆", "柒陆", "频晴", "频粤", "[超清]", "高清", "超清", "标清", "斯特",
        "粤陆", "国陆", "肆柒", "频英", "频特", "频国", "频壹", "频贰", "肆贰", "频测",
        "咪咕", "闽特", "高特", "频高", "频标", "汝阳"
    ],
    
    'critical_files': ['full.txt', 'custom.txt'],
    'url_patterns_to_skip': ['tvbus://', '/udp/', 'rtsp://', 'rtp://']
}

# ====== 初始化设置 ======
os.makedirs(CONFIG['output_dir'], exist_ok=True)
# 使用北京时间
beijing_tz = timezone(timedelta(hours=8))
timestart = datetime.now(beijing_tz)

print(f"🚀 开始处理直播源 - 输入: {CONFIG['source_base']}, 输出: {CONFIG['output_base']}")

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
    return any(pattern in url for pattern in CONFIG['url_patterns_to_skip'])

# ====== 黑名单处理 ======
print("🔧 加载黑名单...")
blacklist_auto = read_blacklist_from_txt(f"{CONFIG['blacklist_dir']}/blacklist_auto.txt") 
blacklist_manual = read_blacklist_from_txt(f"{CONFIG['blacklist_dir']}/blacklist_manual.txt") 
combined_blacklist = set(blacklist_auto + blacklist_manual)
print(f"✅ 黑名单加载完成: {len(combined_blacklist)} 条记录")

# ====== 数据存储容器 ======
# 主频道
yangshi_lines = [] #CCTV
weishi_lines = [] #卫视频道

# 地方台
beijing_lines = [] #地方台-北京频道
shanghai_lines = [] #地方台-上海频道
tianjin_lines = [] #地方台-天津频道
chongqing_lines = [] #地方台-重庆频道
guangdong_lines = [] #地方台-广东频道
jiangsu_lines = [] #地方台-江苏频道
zhejiang_lines = [] #地方台-浙江频道
shandong_lines = [] #地方台-山东频道
henan_lines = [] #地方台-河南频道
sichuan_lines = [] #地方台-四川频道
hebei_lines = [] #地方台-河北频道
hunan_lines = [] #地方台-湖南频道
hubei_lines = [] #地方台-湖北频道
anhui_lines = [] #地方台-安徽频道
fujian_lines = [] #地方台-福建频道
shanxi1_lines = [] #地方台-陕西频道
liaoning_lines = [] #地方台-辽宁频道
jiangxi_lines = [] #地方台-江西频道
heilongjiang_lines = [] #地方台-黑龙江频道
jilin_lines = [] #地方台-吉林频道
shanxi2_lines = [] #地方台-山西频道
guangxi_lines = [] #地方台-广西频道
yunnan_lines = [] #地方台-云南频道
guizhou_lines = [] #地方台-贵州频道
gansu_lines = [] #地方台-甘肃频道
neimenggu_lines = [] #地方台-内蒙频道
xinjiang_lines = [] #地方台-新疆频道
hainan_lines = [] #地方台-海南频道
ningxia_lines = [] #地方台-宁夏频道
qinghai_lines = [] #地方台-青海频道
xizang_lines = [] #地方台-西藏频道

# 专业频道
news_lines = [] #新闻频道
shuzi_lines = [] #数字频道
dianying_lines = [] #电影频道
jieshuo_lines = [] #解说频道
zongyi_lines = [] #综艺频道
huya_lines = [] #虎牙直播
douyu_lines = [] #斗鱼直播
xianggang_lines = [] #香港频道
aomen_lines = [] #澳门频道
china_lines = [] #中国频道
guoji_lines = [] #国际频道
gangaotai_lines = [] #港澳台
dianshiju_lines = [] #电视剧
radio_lines = [] #收音机
donghuapian_lines = [] #动画片
jilupian_lines = [] #记录片
tiyu_lines = [] #体育频道
tiyusaishi_lines = [] #体育赛事
youxi_lines = [] #游戏频道
xiqu_lines = [] #戏曲频道
yinyue_lines = [] #音乐频道
chunwan_lines = [] #春晚频道
zhibozhongguo_lines = [] #直播中国

# 其他分类
others_lines = []
others_lines_url = [] # 为降低others_文件大小，剔除重复url添加
aktv_lines = [] # AKTV频道

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
    timeout = timeout or CONFIG['request_timeout']
    retries = retries or CONFIG['request_retries']
    backoff_factor = backoff_factor or CONFIG['request_backoff_factor']
    
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

# ====== 核心分发逻辑 ======
def process_channel_line(line):
    """处理单行频道数据并分类 - 支持同频道多分类且去重"""
    try:
        if "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
            channel_name = line.split(',')[0].strip()
            original_name = channel_name  # 保存原始名称
            channel_name = clean_channel_name(channel_name, CONFIG['removal_list'])
            channel_name = traditional_to_simplified(channel_name)
            channel_address = clean_url(line.split(',')[1].strip())
            
            # 跳过黑名单和特定协议
            if channel_address in combined_blacklist or should_skip_url(channel_address):
                return

            url_hash = get_url_hash(channel_address)
            processed_line = channel_name + "," + channel_address

            # 主频道分发 - 支持同频道多分类
            channel_added = False
            
            if "CCTV" in channel_name and check_url_existence(yangshi_lines, channel_address):
                yangshi_lines.append(process_name_string(processed_line))
                channel_added = True
            
            if channel_name in weishi_dictionary and check_url_existence(weishi_lines, channel_address):
                weishi_lines.append(process_name_string(processed_line))
                channel_added = True
            
            # 地方台分发 - 支持同频道多分类
            if channel_name in beijing_dictionary and check_url_existence(beijing_lines, channel_address):
                beijing_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shanghai_dictionary and check_url_existence(shanghai_lines, channel_address):
                shanghai_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in tianjin_dictionary and check_url_existence(tianjin_lines, channel_address):
                tianjin_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in chongqing_dictionary and check_url_existence(chongqing_lines, channel_address):
                chongqing_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in guangdong_dictionary and check_url_existence(guangdong_lines, channel_address):
                guangdong_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jiangsu_dictionary and check_url_existence(jiangsu_lines, channel_address):
                jiangsu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in zhejiang_dictionary and check_url_existence(zhejiang_lines, channel_address):
                zhejiang_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shandong_dictionary and check_url_existence(shandong_lines, channel_address):
                shandong_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in henan_dictionary and check_url_existence(henan_lines, channel_address):
                henan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in sichuan_dictionary and check_url_existence(sichuan_lines, channel_address):
                sichuan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hebei_dictionary and check_url_existence(hebei_lines, channel_address):
                hebei_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hunan_dictionary and check_url_existence(hunan_lines, channel_address):
                hunan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hubei_dictionary and check_url_existence(hubei_lines, channel_address):
                hubei_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in anhui_dictionary and check_url_existence(anhui_lines, channel_address):
                anhui_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in fujian_dictionary and check_url_existence(fujian_lines, channel_address):
                fujian_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shanxi1_dictionary and check_url_existence(shanxi1_lines, channel_address):
                shanxi1_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in liaoning_dictionary and check_url_existence(liaoning_lines, channel_address):
                liaoning_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jiangxi_dictionary and check_url_existence(jiangxi_lines, channel_address):
                jiangxi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in heilongjiang_dictionary and check_url_existence(heilongjiang_lines, channel_address):
                heilongjiang_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jilin_dictionary and check_url_existence(jilin_lines, channel_address):
                jilin_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shanxi2_dictionary and check_url_existence(shanxi2_lines, channel_address):
                shanxi2_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in guangxi_dictionary and check_url_existence(guangxi_lines, channel_address):
                guangxi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in yunnan_dictionary and check_url_existence(yunnan_lines, channel_address):
                yunnan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in guizhou_dictionary and check_url_existence(guizhou_lines, channel_address):
                guizhou_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gansu_dictionary and check_url_existence(gansu_lines, channel_address):
                gansu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in neimenggu_dictionary and check_url_existence(neimenggu_lines, channel_address):
                neimenggu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xinjiang_dictionary and check_url_existence(xinjiang_lines, channel_address):
                xinjiang_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hainan_dictionary and check_url_existence(hainan_lines, channel_address):
                hainan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in ningxia_dictionary and check_url_existence(ningxia_lines, channel_address):
                ningxia_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in qinghai_dictionary and check_url_existence(qinghai_lines, channel_address):
                qinghai_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xizang_dictionary and check_url_existence(xizang_lines, channel_address):
                xizang_lines.append(process_name_string(processed_line))
                channel_added = True
            
            # 专业频道分发
            if channel_name in news_dictionary and check_url_existence(news_lines, channel_address):
                news_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shuzi_dictionary and check_url_existence(shuzi_lines, channel_address):
                shuzi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dianying_dictionary and check_url_existence(dianying_lines, channel_address):
                dianying_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jieshuo_dictionary and check_url_existence(jieshuo_lines, channel_address):
                jieshuo_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in zongyi_dictionary and check_url_existence(zongyi_lines, channel_address):
                zongyi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in huya_dictionary and check_url_existence(huya_lines, channel_address):
                huya_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in douyu_dictionary and check_url_existence(douyu_lines, channel_address):
                douyu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xianggang_dictionary and check_url_existence(xianggang_lines, channel_address):
                xianggang_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in aomen_dictionary and check_url_existence(aomen_lines, channel_address):
                aomen_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in china_dictionary and check_url_existence(china_lines, channel_address):
                china_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in guoji_dictionary and check_url_existence(guoji_lines, channel_address):
                guoji_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gangaotai_dictionary and check_url_existence(gangaotai_lines, channel_address):
                gangaotai_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dianshiju_dictionary and check_url_existence(dianshiju_lines, channel_address):
                dianshiju_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in radio_dictionary and check_url_existence(radio_lines, channel_address):
                radio_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in donghuapian_dictionary and check_url_existence(donghuapian_lines, channel_address):
                donghuapian_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jilupian_dictionary and check_url_existence(jilupian_lines, channel_address):
                jilupian_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in tiyu_dictionary and check_url_existence(tiyu_lines, channel_address):
                tiyu_lines.append(process_name_string(processed_line))
                channel_added = True
            
            if any(tiyusaishi_item in channel_name for tiyusaishi_item in tiyusaishi_dictionary) and check_url_existence(tiyusaishi_lines, channel_address):
                tiyusaishi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in youxi_dictionary and check_url_existence(youxi_lines, channel_address):
                youxi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xiqu_dictionary and check_url_existence(xiqu_lines, channel_address):
                xiqu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in yinyue_dictionary and check_url_existence(yinyue_lines, channel_address):
                yinyue_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in chunwan_dictionary and check_url_existence(chunwan_lines, channel_address):
                chunwan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in zhibozhongguo_dictionary and check_url_existence(zhibozhongguo_lines, channel_address):
                zhibozhongguo_lines.append(process_name_string(processed_line))
                channel_added = True
            
            # 其他频道分发 - 使用URL哈希去重
            if not channel_added and url_hash not in others_lines_url:
                others_lines_url.append(url_hash)
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
yangshi_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/CCTV.txt")
weishi_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/卫视频道.txt")

# 地方台字典
beijing_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/北京频道.txt")
shanghai_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/上海频道.txt")
tianjin_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/天津频道.txt")
chongqing_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/重庆频道.txt")
guangdong_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/广东频道.txt")
jiangsu_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/江苏频道.txt")
zhejiang_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/浙江频道.txt")
shandong_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/山东频道.txt")
henan_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/河南频道.txt")
sichuan_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/四川频道.txt")
hebei_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/河北频道.txt")
hunan_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/湖南频道.txt")
hubei_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/湖北频道.txt")
anhui_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/安徽频道.txt")
fujian_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/福建频道.txt")
shanxi1_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/陕西频道.txt")
liaoning_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/辽宁频道.txt")
jiangxi_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/江西频道.txt")
heilongjiang_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/黑龙江频道.txt")
jilin_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/吉林频道.txt")
shanxi2_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/山西频道.txt")
guangxi_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/广西频道.txt")
yunnan_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/云南频道.txt")
guizhou_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/贵州频道.txt")
gansu_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/甘肃频道.txt")
neimenggu_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/内蒙频道.txt")
xinjiang_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/新疆频道.txt")
hainan_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/海南频道.txt")
ningxia_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/宁夏频道.txt")
qinghai_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/青海频道.txt")
xizang_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/西藏频道.txt")

# 专业频道字典
news_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/新闻频道.txt")
shuzi_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/数字频道.txt")
dianying_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/电影频道.txt")
jieshuo_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/解说频道.txt")
zongyi_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/综艺频道.txt")
huya_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/虎牙直播.txt")
douyu_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/斗鱼直播.txt")
xianggang_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/香港频道.txt")
aomen_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/澳门频道.txt")
china_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/中国频道.txt")
guoji_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/国际频道.txt")
gangaotai_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/港澳台.txt")
dianshiju_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/电视剧.txt")
radio_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/收音机.txt")
donghuapian_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/动画片.txt")
jilupian_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/记录片.txt")
tiyu_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/体育频道.txt")
tiyusaishi_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/体育赛事.txt")
youxi_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/游戏频道.txt")
xiqu_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/戏曲频道.txt")
yinyue_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/音乐频道.txt")
chunwan_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/春晚频道.txt")
zhibozhongguo_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/直播中国.txt")

# 加载纠错数据
corrections_name = load_corrections_name(f"{CONFIG['assets_dir']}/corrections_name.txt")

print(f"✅ 字典数据加载完成: CCTV({len(yangshi_dictionary)}) 卫视({len(weishi_dictionary)}) 地方台(31个) 专业频道(23个)")

# ====== 主处理流程 ======
def main():
    print("🚀 开始处理直播源...")
    
    # 1. 处理URL源
    urls = read_txt_to_array(f"{CONFIG['assets_dir']}/urls-daily.txt")
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
    whitelist_auto_lines = read_txt_to_array(f"{CONFIG['blacklist_dir']}/whitelist_auto.txt")
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
        '广东频道': guangdong_lines,
        '湖北频道': hubei_lines, 
        '湖南频道': hunan_lines,
        '浙江频道': zhejiang_lines,
        '江苏频道': jiangsu_lines
    }

    for region, target_list in manual_files.items():
        manual_file = f"{CONFIG['manual_dir']}/{region}.txt"
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
        aktv_lines.extend(read_txt_to_array(f"{CONFIG['manual_dir']}/AKTV.txt"))
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

    version = formatted_time + "," + get_random_url(f"{CONFIG['manual_dir']}/今日推台.txt")
    about = "xiaoranmuze," + get_random_url(f"{CONFIG['manual_dir']}/今日推台.txt")
    daily_mtv = "今日推荐," + get_random_url(f"{CONFIG['manual_dir']}/今日推荐.txt")
    daily_mtv1 = "🔥低调," + get_random_url(f"{CONFIG['manual_dir']}/今日推荐.txt")
    daily_mtv2 = "🔥使用," + get_random_url(f"{CONFIG['manual_dir']}/今日推荐.txt")
    daily_mtv3 = "🔥禁止," + get_random_url(f"{CONFIG['manual_dir']}/今日推荐.txt")
    daily_mtv4 = "🔥贩卖," + get_random_url(f"{CONFIG['manual_dir']}/今日推荐.txt")

    # 7. 生成输出文件
    print("📄 生成输出文件...")

    # 全部源 (full.txt)
    all_lines_full = []
    all_lines_full.extend(["🌐央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name, yangshi_lines)) + ['\n'])
    all_lines_full.extend(["📡卫视频道,#genre#"] + sort_data(weishi_dictionary, correct_name_data(corrections_name, weishi_lines)) + ['\n'])

    # 地方台分类
    all_lines_full.extend(["☘️北京频道,#genre#"] + sort_data(beijing_dictionary, correct_name_data(corrections_name, beijing_lines)) + ['\n'])
    all_lines_full.extend(["☘️上海频道,#genre#"] + sort_data(shanghai_dictionary, correct_name_data(corrections_name, shanghai_lines)) + ['\n'])
    all_lines_full.extend(["☘️天津频道,#genre#"] + sort_data(tianjin_dictionary, correct_name_data(corrections_name, tianjin_lines)) + ['\n'])
    all_lines_full.extend(["☘️重庆频道,#genre#"] + sort_data(chongqing_dictionary, correct_name_data(corrections_name, chongqing_lines)) + ['\n'])
    all_lines_full.extend(["☘️广东频道,#genre#"] + sort_data(guangdong_dictionary, correct_name_data(corrections_name, guangdong_lines)) + ['\n'])
    all_lines_full.extend(["☘️江苏频道,#genre#"] + sort_data(jiangsu_dictionary, correct_name_data(corrections_name, jiangsu_lines)) + ['\n'])
    all_lines_full.extend(["☘️浙江频道,#genre#"] + sort_data(zhejiang_dictionary, correct_name_data(corrections_name, zhejiang_lines)) + ['\n'])
    all_lines_full.extend(["☘️山东频道,#genre#"] + sort_data(shandong_dictionary, correct_name_data(corrections_name, shandong_lines)) + ['\n'])
    all_lines_full.extend(["☘️河南频道,#genre#"] + sort_data(henan_dictionary, correct_name_data(corrections_name, henan_lines)) + ['\n'])
    all_lines_full.extend(["☘️四川频道,#genre#"] + sort_data(sichuan_dictionary, correct_name_data(corrections_name, sichuan_lines)) + ['\n'])
    all_lines_full.extend(["☘️河北频道,#genre#"] + sort_data(hebei_dictionary, correct_name_data(corrections_name, hebei_lines)) + ['\n'])
    all_lines_full.extend(["☘️湖南频道,#genre#"] + sort_data(hunan_dictionary, correct_name_data(corrections_name, hunan_lines)) + ['\n'])
    all_lines_full.extend(["☘️湖北频道,#genre#"] + sort_data(hubei_dictionary, correct_name_data(corrections_name, hubei_lines)) + ['\n'])
    all_lines_full.extend(["☘️安徽频道,#genre#"] + sort_data(anhui_dictionary, correct_name_data(corrections_name, anhui_lines)) + ['\n'])
    all_lines_full.extend(["☘️福建频道,#genre#"] + sort_data(fujian_dictionary, correct_name_data(corrections_name, fujian_lines)) + ['\n'])
    all_lines_full.extend(["☘️陕西频道,#genre#"] + sort_data(shanxi1_dictionary, correct_name_data(corrections_name, shanxi1_lines)) + ['\n'])
    all_lines_full.extend(["☘️辽宁频道,#genre#"] + sort_data(liaoning_dictionary, correct_name_data(corrections_name, liaoning_lines)) + ['\n'])
    all_lines_full.extend(["☘️江西频道,#genre#"] + sort_data(jiangxi_dictionary, correct_name_data(corrections_name, jiangxi_lines)) + ['\n'])
    all_lines_full.extend(["☘️黑龙江台,#genre#"] + sort_data(heilongjiang_dictionary, correct_name_data(corrections_name, heilongjiang_lines)) + ['\n'])
    all_lines_full.extend(["☘️吉林频道,#genre#"] + sort_data(jilin_dictionary, correct_name_data(corrections_name, jilin_lines)) + ['\n'])
    all_lines_full.extend(["☘️山西频道,#genre#"] + sort_data(shanxi2_dictionary, correct_name_data(corrections_name, shanxi2_lines)) + ['\n'])
    all_lines_full.extend(["☘️广西频道,#genre#"] + sort_data(guangxi_dictionary, correct_name_data(corrections_name, guangxi_lines)) + ['\n'])
    all_lines_full.extend(["☘️云南频道,#genre#"] + sort_data(yunnan_dictionary, correct_name_data(corrections_name, yunnan_lines)) + ['\n'])
    all_lines_full.extend(["☘️贵州频道,#genre#"] + sort_data(guizhou_dictionary, correct_name_data(corrections_name, guizhou_lines)) + ['\n'])
    all_lines_full.extend(["☘️甘肃频道,#genre#"] + sort_data(gansu_dictionary, correct_name_data(corrections_name, gansu_lines)) + ['\n'])
    all_lines_full.extend(["☘️内蒙频道,#genre#"] + sort_data(neimenggu_dictionary, correct_name_data(corrections_name, neimenggu_lines)) + ['\n'])
    all_lines_full.extend(["☘️新疆频道,#genre#"] + sort_data(xinjiang_dictionary, correct_name_data(corrections_name, xinjiang_lines)) + ['\n'])
    all_lines_full.extend(["☘️海南频道,#genre#"] + sort_data(hainan_dictionary, correct_name_data(corrections_name, hainan_lines)) + ['\n'])
    all_lines_full.extend(["☘️宁夏频道,#genre#"] + sort_data(ningxia_dictionary, correct_name_data(corrections_name, ningxia_lines)) + ['\n'])
    all_lines_full.extend(["☘️青海频道,#genre#"] + sort_data(qinghai_dictionary, correct_name_data(corrections_name, qinghai_lines)) + ['\n'])
    all_lines_full.extend(["☘️西藏频道,#genre#"] + sort_data(xizang_dictionary, correct_name_data(corrections_name, xizang_lines)) + ['\n'])

    # 专业频道
    all_lines_full.extend(["📰新闻频道,#genre#"] + sort_data(news_dictionary, correct_name_data(corrections_name, news_lines)) + ['\n'])
    all_lines_full.extend(["🎞️数字频道,#genre#"] + sort_data(shuzi_dictionary, correct_name_data(corrections_name, shuzi_lines)) + ['\n'])
    all_lines_full.extend(["🎬电影频道,#genre#"] + sort_data(dianying_dictionary, correct_name_data(corrections_name, dianying_lines)) + ['\n'])
    all_lines_full.extend(["🎙️解说频道,#genre#"] + sort_data(jieshuo_dictionary, correct_name_data(corrections_name, jieshuo_lines)) + ['\n'])
    all_lines_full.extend(["🎤综艺频道,#genre#"] + sort_data(zongyi_dictionary, correct_name_data(corrections_name, zongyi_lines)) + ['\n'])
    all_lines_full.extend(["🐯虎牙直播,#genre#"] + sort_data(huya_dictionary, correct_name_data(corrections_name, huya_lines)) + ['\n'])
    all_lines_full.extend(["🐬斗鱼直播,#genre#"] + sort_data(douyu_dictionary, correct_name_data(corrections_name, douyu_lines)) + ['\n'])
    all_lines_full.extend(["🇭🇰香港频道,#genre#"] + sort_data(xianggang_dictionary, correct_name_data(corrections_name, xianggang_lines)) + ['\n'])
    all_lines_full.extend(["🇲🇴澳门频道,#genre#"] + sort_data(aomen_dictionary, correct_name_data(corrections_name, aomen_lines)) + ['\n'])
    all_lines_full.extend(["🇨🇳中国频道,#genre#"] + sort_data(china_dictionary, correct_name_data(corrections_name, china_lines)) + ['\n'])
    all_lines_full.extend(["🌎国际频道,#genre#"] + sort_data(guoji_dictionary, correct_name_data(corrections_name, guoji_lines)) + ['\n'])
    all_lines_full.extend(["🇨🇳港澳台,#genre#"] + sort_data(gangaotai_dictionary, correct_name_data(corrections_name, gangaotai_lines)) + ['\n'])
    all_lines_full.extend(["📺电视剧,#genre#"] + sort_data(dianshiju_dictionary, correct_name_data(corrections_name, dianshiju_lines)) + ['\n'])
    all_lines_full.extend(["📻收音机,#genre#"] + sort_data(radio_dictionary, correct_name_data(corrections_name, radio_lines)) + ['\n'])
    all_lines_full.extend(["🏕动画片,#genre#"] + sort_data(donghuapian_dictionary, correct_name_data(corrections_name, donghuapian_lines)) + ['\n'])
    all_lines_full.extend(["📽️记录片,#genre#"] + sort_data(jilupian_dictionary, correct_name_data(corrections_name, jilupian_lines)) + ['\n'])
    all_lines_full.extend(["⚽体育频道,#genre#"] + sort_data(tiyu_dictionary, correct_name_data(corrections_name, tiyu_lines)) + ['\n'])
    all_lines_full.extend(["🏆体育赛事,#genre#"] + normalized_tiyusaishi_lines + ['\n'])
    all_lines_full.extend(["🎮游戏频道,#genre#"] + sort_data(youxi_dictionary, correct_name_data(corrections_name, youxi_lines)) + ['\n'])
    all_lines_full.extend(["🎭戏曲频道,#genre#"] + sort_data(xiqu_dictionary, correct_name_data(corrections_name, xiqu_lines)) + ['\n'])
    all_lines_full.extend(["🎵音乐频道,#genre#"] + sort_data(yinyue_dictionary, correct_name_data(corrections_name, yinyue_lines)) + ['\n'])
    all_lines_full.extend(["🎉春晚频道,#genre#"] + sort_data(chunwan_dictionary, correct_name_data(corrections_name, chunwan_lines)) + ['\n'])
    all_lines_full.extend(["📡直播中国,#genre#"] + sort_data(zhibozhongguo_dictionary, correct_name_data(corrections_name, zhibozhongguo_lines)) + ['\n'])

    # 完整版其他和更新信息
    all_lines_full.extend(["📦其它源,#genre#"] + others_lines + ['\n'])
    all_lines_full.extend(["🕒更新时间,#genre#"] + [version, about, daily_mtv, daily_mtv1, daily_mtv2, daily_mtv3, daily_mtv4] + read_txt_to_array(f"{CONFIG['manual_dir']}/about.txt") + ['\n'])

    # 精简源 (lite.txt)
    all_lines_lite = []
    all_lines_lite.extend(["央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name, yangshi_lines)) + ['\n'])
    all_lines_lite.extend(["卫视频道,#genre#"] + sort_data(weishi_dictionary, correct_name_data(corrections_name, weishi_lines)) + ['\n'])

    # 合并地方频道
    all_lines_lite.extend(["地方频道,#genre#"] + 
                           sort_data(beijing_dictionary, correct_name_data(corrections_name, beijing_lines)) +
                           sort_data(shanghai_dictionary, correct_name_data(corrections_name, shanghai_lines)) +
                           sort_data(tianjin_dictionary, correct_name_data(corrections_name, tianjin_lines)) +
                           sort_data(chongqing_dictionary, correct_name_data(corrections_name, chongqing_lines)) +
                           sort_data(guangdong_dictionary, correct_name_data(corrections_name, guangdong_lines)) +
                           sort_data(jiangsu_dictionary, correct_name_data(corrections_name, jiangsu_lines)) +
                           sort_data(zhejiang_dictionary, correct_name_data(corrections_name, zhejiang_lines)) +
                           sort_data(shandong_dictionary, correct_name_data(corrections_name, shandong_lines)) +
                           sort_data(henan_dictionary, correct_name_data(corrections_name, henan_lines)) +
                           sort_data(sichuan_dictionary, correct_name_data(corrections_name, sichuan_lines)) +
                           sort_data(hebei_dictionary, correct_name_data(corrections_name, hebei_lines)) +
                           sort_data(hunan_dictionary, correct_name_data(corrections_name, hunan_lines)) +
                           sort_data(hubei_dictionary, correct_name_data(corrections_name, hubei_lines)) +
                           sort_data(anhui_dictionary, correct_name_data(corrections_name, anhui_lines)) +
                           sort_data(fujian_dictionary, correct_name_data(corrections_name, fujian_lines)) +
                           sort_data(shanxi1_dictionary, correct_name_data(corrections_name, shanxi1_lines)) +
                           sort_data(liaoning_dictionary, correct_name_data(corrections_name, liaoning_lines)) +
                           sort_data(jiangxi_dictionary, correct_name_data(corrections_name, jiangxi_lines)) +
                           sort_data(heilongjiang_dictionary, correct_name_data(corrections_name, heilongjiang_lines)) +
                           sort_data(jilin_dictionary, correct_name_data(corrections_name, jilin_lines)) +
                           sort_data(shanxi2_dictionary, correct_name_data(corrections_name, shanxi2_lines)) +
                           sort_data(guangxi_dictionary, correct_name_data(corrections_name, guangxi_lines)) +
                           sort_data(yunnan_dictionary, correct_name_data(corrections_name, yunnan_lines)) +
                           sort_data(guizhou_dictionary, correct_name_data(corrections_name, guizhou_lines)) +
                           sort_data(gansu_dictionary, correct_name_data(corrections_name, gansu_lines)) +
                           sort_data(neimenggu_dictionary, correct_name_data(corrections_name, neimenggu_lines)) +
                           sort_data(xinjiang_dictionary, correct_name_data(corrections_name, xinjiang_lines)) +
                           sort_data(hainan_dictionary, correct_name_data(corrections_name, hainan_lines)) +
                           sort_data(ningxia_dictionary, correct_name_data(corrections_name, ningxia_lines)) +
                           sort_data(qinghai_dictionary, correct_name_data(corrections_name, qinghai_lines)) +
                           sort_data(xizang_dictionary, correct_name_data(corrections_name, xizang_lines)) + ['\n'])

    # 精简源更新信息
    all_lines_lite.extend(["更新时间,#genre#"] + [version] + ['\n'])

    # 定制源 (custom.txt)
    all_lines_custom = []
    all_lines_custom.extend(["🌐央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name, yangshi_lines)) + ['\n'])
    all_lines_custom.extend(["📡卫视频道,#genre#"] + sort_data(weishi_dictionary, correct_name_data(corrections_name, weishi_lines)) + ['\n'])

    # 定制源的地方频道
    all_lines_custom.extend(["🏠地方频道,#genre#"] + 
                           sort_data(hubei_dictionary, correct_name_data(corrections_name, hubei_lines)) +
                           sort_data(shanghai_dictionary, correct_name_data(corrections_name, shanghai_lines)) +
                           sort_data(zhejiang_dictionary, correct_name_data(corrections_name, zhejiang_lines)) +
                           sort_data(jiangsu_dictionary, correct_name_data(corrections_name, jiangsu_lines)) +
                           sort_data(guangdong_dictionary, correct_name_data(corrections_name, guangdong_lines)) +
                           sort_data(hunan_dictionary, correct_name_data(corrections_name, hunan_lines)) +
                           sort_data(beijing_dictionary, correct_name_data(corrections_name, beijing_lines)) +
                           sort_data(shandong_dictionary, correct_name_data(corrections_name, shandong_lines)) + ['\n'])

    # 定制源的专业频道
    all_lines_custom.extend(["⚽体育频道,#genre#"] + sort_data(tiyu_dictionary, correct_name_data(corrections_name, tiyu_lines)) + ['\n'])
    all_lines_custom.extend(["🏆体育赛事,#genre#"] + normalized_tiyusaishi_lines + ['\n'])
    all_lines_custom.extend(["🎬影视娱乐,#genre#"] + 
                           sort_data(dianying_dictionary, correct_name_data(corrections_name, dianying_lines)) +
                           sort_data(dianshiju_dictionary, correct_name_data(corrections_name, dianshiju_lines)) +
                           sort_data(zongyi_dictionary, correct_name_data(corrections_name, zongyi_lines)) + ['\n'])
    all_lines_custom.extend(["🎭港澳台,#genre#"] + 
                           sort_data(gangaotai_dictionary, correct_name_data(corrections_name, gangaotai_lines)) +
                           sort_data(xianggang_dictionary, correct_name_data(corrections_name, xianggang_lines)) +
                           sort_data(aomen_dictionary, correct_name_data(corrections_name, aomen_lines)) + ['\n'])
    all_lines_custom.extend(["📦其它源,#genre#"] + others_lines + ['\n'])
    all_lines_custom.extend(["🕒更新时间,#genre#"] + [version, about, daily_mtv, daily_mtv1, daily_mtv2, daily_mtv3, daily_mtv4] + read_txt_to_array(f"{CONFIG['manual_dir']}/about.txt") + ['\n'])

    # 其它源 (others.txt)
    all_lines_others = []
    all_lines_others.extend(["其它源,#genre#"] + others_lines + ['\n'])

    # 7. 保存四个版本文件
    output_data = {
        'full': all_lines_full,
        'lite': all_lines_lite,
        'custom': all_lines_custom,
        'others': all_lines_others
    }

    for file_type, lines in output_data.items():
        file_path = CONFIG['output_files'][file_type]
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

    # 8. 生成M3U文件
    def get_logo_by_channel_name(channel_name):
        """根据频道名称获取logo"""
        try:
            channels_logos = read_txt_to_array(f"{CONFIG['assets_dir']}/logo.txt")
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
    make_m3u(CONFIG['output_files']['full'], CONFIG['output_files']['full'].replace(".txt", ".m3u"))
    make_m3u(CONFIG['output_files']['lite'], CONFIG['output_files']['lite'].replace(".txt", ".m3u"))
    make_m3u(CONFIG['output_files']['custom'], CONFIG['output_files']['custom'].replace(".txt", ".m3u"))

    # 9. 统计信息 - 使用北京时间
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

    # 地方台统计
    print(f"🏠 北京源: {len(beijing_lines)} 个")
    print(f"🏠 上海源: {len(shanghai_lines)} 个")
    print(f"🏠 天津源: {len(tianjin_lines)} 个")
    print(f"🏠 重庆源: {len(chongqing_lines)} 个")
    print(f"🏠 广东源: {len(guangdong_lines)} 个")
    print(f"🏠 江苏源: {len(jiangsu_lines)} 个")
    print(f"🏠 浙江源: {len(zhejiang_lines)} 个")
    print(f"🏠 山东源: {len(shandong_lines)} 个")
    print(f"🏠 河南源: {len(henan_lines)} 个")
    print(f"🏠 四川源: {len(sichuan_lines)} 个")
    print(f"🏠 河北源: {len(hebei_lines)} 个")
    print(f"🏠 湖南源: {len(hunan_lines)} 个")
    print(f"🏠 湖北源: {len(hubei_lines)} 个")
    print(f"🏠 安徽源: {len(anhui_lines)} 个")
    print(f"🏠 福建源: {len(fujian_lines)} 个")
    print(f"🏠 陕西源: {len(shanxi1_lines)} 个")
    print(f"🏠 辽宁源: {len(liaoning_lines)} 个")
    print(f"🏠 江西源: {len(jiangxi_lines)} 个")
    print(f"🏠 黑龙江源: {len(heilongjiang_lines)} 个")
    print(f"🏠 吉林源: {len(jilin_lines)} 个")
    print(f"🏠 山西源: {len(shanxi2_lines)} 个")
    print(f"🏠 广西源: {len(guangxi_lines)} 个")
    print(f"🏠 云南源: {len(yunnan_lines)} 个")
    print(f"🏠 贵州源: {len(guizhou_lines)} 个")
    print(f"🏠 甘肃源: {len(gansu_lines)} 个")
    print(f"🏠 内蒙源: {len(neimenggu_lines)} 个")
    print(f"🏠 新疆源: {len(xinjiang_lines)} 个")
    print(f"🏠 海南源: {len(hainan_lines)} 个")
    print(f"🏠 宁夏源: {len(ningxia_lines)} 个")
    print(f"🏠 青海源: {len(qinghai_lines)} 个")
    print(f"🏠 西藏源: {len(xizang_lines)} 个")

    # 专业频道统计
    print(f"📰 新闻频道: {len(news_lines)} 个")
    print(f"🎞️ 数字频道: {len(shuzi_lines)} 个")
    print(f"🎬 电影频道: {len(dianying_lines)} 个")
    print(f"🎙️ 解说频道: {len(jieshuo_lines)} 个")
    print(f"🎤 综艺频道: {len(zongyi_lines)} 个")
    print(f"🐯 虎牙直播: {len(huya_lines)} 个")
    print(f"🐬 斗鱼直播: {len(douyu_lines)} 个")
    print(f"🇭🇰 香港频道: {len(xianggang_lines)} 个")
    print(f"🇲🇴 澳门频道: {len(aomen_lines)} 个")
    print(f"🇨🇳 中国频道: {len(china_lines)} 个")
    print(f"🌎 国际频道: {len(guoji_lines)} 个")
    print(f"🇨🇳 港澳台: {len(gangaotai_lines)} 个")
    print(f"📺 电视剧: {len(dianshiju_lines)} 个")
    print(f"📻 收音机: {len(radio_lines)} 个")
    print(f"🏕 动画片: {len(donghuapian_lines)} 个")
    print(f"📽️ 记录片: {len(jilupian_lines)} 个")
    print(f"⚽ 体育频道: {len(tiyu_lines)} 个")
    print(f"🏆 体育赛事: {len(normalized_tiyusaishi_lines)} 个")
    print(f"🎮 游戏频道: {len(youxi_lines)} 个")
    print(f"🎭 戏曲频道: {len(xiqu_lines)} 个")
    print(f"🎵 音乐频道: {len(yinyue_lines)} 个")
    print(f"🎉 春晚频道: {len(chunwan_lines)} 个")
    print(f"📡 直播中国: {len(zhibozhongguo_lines)} 个")

    # 其他统计
    print(f"🚀 AKTV: {len(aktv_lines)} 个")
    print(f"📦 其它源: {len(others_lines)} 个")
    print(f"📄 全部源: {len(all_lines_full)} 行")
    print(f"📄 精简源: {len(all_lines_lite)} 行")
    print(f"📄 定制源: {len(all_lines_custom)} 行")
    print("======================\n")

    # 最终检查所有输出文件
    print("🔍 最终文件检查:")
    all_files_ok = True
    for file_type, file_path in CONFIG['output_files'].items():
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
        m3u_file = CONFIG['output_files'][file_type].replace(".txt", ".m3u")
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