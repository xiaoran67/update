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

# ==================== 配置区域 ====================
# 在这里修改输入输出路径即可
SOURCE_BASE = "scripts/livesource3"
OUTPUT_BASE = "output/livesource3"

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
        'simple': f'{OUTPUT_BASE}/simple.txt', 
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

# ==================== 初始化设置 ====================
os.makedirs(CONFIG['output_dir'], exist_ok=True)
timestart = datetime.now()

print(f"🚀 开始处理直播源 - 输入: {CONFIG['source_base']}, 输出: {CONFIG['output_base']}")

# ==================== 核心工具函数 ====================
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

# ==================== 黑名单处理 ====================
print("🔧 加载黑名单...")
blacklist_auto = read_blacklist_from_txt(f"{CONFIG['blacklist_dir']}/blacklist_auto.txt") 
blacklist_manual = read_blacklist_from_txt(f"{CONFIG['blacklist_dir']}/blacklist_manual.txt") 
combined_blacklist = set(blacklist_auto + blacklist_manual)
print(f"✅ 黑名单加载完成: {len(combined_blacklist)} 条记录")

# ==================== 数据存储容器 ====================
# 主频道
ys_lines, ws_lines = [], []  # CCTV, 卫视频道
tyss_lines, ty_lines = [], []  # 体育赛事, 体育频道

# 地方台
hb_lines, gd_lines = [], []  # 湖北频道, 广东频道

# 其他分类
aktv_lines = []  # AKTV
others_lines = []  # 其他频道
others_lines_url_set = set()  # 使用集合进行URL去重

# ==================== 频道名称处理函数 ====================
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

# ==================== URL处理函数 ====================
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

# ==================== 网络请求函数 ====================
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

# ==================== 核心分发逻辑 ====================
def process_channel_line(line):
    """处理单行频道数据并分类"""
    try:
        if "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
            channel_name = line.split(',')[0].strip()
            channel_name = clean_channel_name(channel_name, CONFIG['removal_list'])
            channel_name = traditional_to_simplified(channel_name)
            channel_address = clean_url(line.split(',')[1].strip())
            processed_line = channel_name + "," + channel_address

            # 跳过黑名单和特定协议
            if channel_address in combined_blacklist or should_skip_url(channel_address):
                return

            url_hash = get_url_hash(channel_address)
            
            # 主频道分发
            if "CCTV" in channel_name and check_url_existence(ys_lines, channel_address):
                ys_lines.append(process_name_string(processed_line))
            elif channel_name in ws_dictionary and check_url_existence(ws_lines, channel_address):
                ws_lines.append(process_name_string(processed_line))
            # 体育赛事分发
            elif any(tyss_item in channel_name for tyss_item in tyss_dictionary) and check_url_existence(tyss_lines, channel_address):
                tyss_lines.append(process_name_string(processed_line))
            # 地方台分发
            elif channel_name in hb_dictionary and check_url_existence(hb_lines, channel_address):
                hb_lines.append(process_name_string(processed_line))
            elif channel_name in gd_dictionary and check_url_existence(gd_lines, channel_address):
                gd_lines.append(process_name_string(processed_line))
            # AKTV分发
            elif "AKTV" in channel_name or "aktv" in channel_name.lower():
                aktv_lines.append(process_name_string(processed_line))
            # 其他频道分发
            else:
                if url_hash not in others_lines_url_set:
                    others_lines_url_set.add(url_hash)
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

# ==================== 数据排序和纠错 ====================
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

# ==================== 加载字典数据 ====================
print("📚 加载字典数据...")
# 主频道字典
ys_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/CCTV.txt")
ws_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/卫视频道.txt")
tyss_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/体育赛事.txt")

# 地方台字典
hb_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/湖北频道.txt")
gd_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/广东频道.txt")

# 加载纠错数据
corrections_name = load_corrections_name(f"{CONFIG['assets_dir']}/corrections_name.txt")

print(f"✅ 字典数据加载完成: CCTV({len(ys_dictionary)}) 卫视({len(ws_dictionary)}) 湖北({len(hb_dictionary)}) 广东({len(gd_dictionary)})")

# ==================== 主处理流程 ====================
def main():
    print("🚀 开始处理直播源...")
    
    # 1. 处理URL源
    urls = read_txt_to_array(f"{CONFIG['assets_dir']}/urls-daily.txt")
    print(f"📡 发现 {len(urls)} 个URL源")
    
    for url in urls:
        if url.startswith("http"):
            # 处理日期变量
            if "{MMdd}" in url:
                current_date_str = datetime.now().strftime("%m%d")
                url = url.replace("{MMdd}", current_date_str)
            if "{MMdd-1}" in url:
                yesterday_date_str = (datetime.now() - timedelta(days=1)).strftime("%m%d")
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
    gd_manual = read_txt_to_array(f"{CONFIG['manual_dir']}/广东频道.txt")
    gd_lines.extend(gd_manual)
    print(f"✅ 手工区处理完成: 广东({len(gd_manual)})")

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

    normalized_tyss_lines = [normalize_date_to_md(s) for s in tyss_lines]

    # 6. 生成版本信息
    utc_time = datetime.now(timezone.utc)
    beijing_time = utc_time + timedelta(hours=8)
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

    version = formatted_time + "," + get_random_url(f"{CONFIG['assets_dir']}/今日推台.txt")
    about = "xiaoranmuze," + get_random_url(f"{CONFIG['assets_dir']}/今日推台.txt")
    daily_mtv = "今日推荐," + get_random_url(f"{CONFIG['assets_dir']}/今日推荐.txt")
    daily_mtv1 = "🔥低调," + get_random_url(f"{CONFIG['assets_dir']}/今日推荐.txt")
    daily_mtv2 = "🔥使用," + get_random_url(f"{CONFIG['assets_dir']}/今日推荐.txt")
    daily_mtv3 = "🔥禁止," + get_random_url(f"{CONFIG['assets_dir']}/今日推荐.txt")
    daily_mtv4 = "🔥贩卖," + get_random_url(f"{CONFIG['assets_dir']}/今日推荐.txt")

    # 7. 生成输出文件
    print("📄 生成输出文件...")
    
    # 全部源 (full.txt)
    all_lines_full = []
    all_lines_full.extend(["🌐央视频道,#genre#"] + sort_data(ys_dictionary, correct_name_data(corrections_name, ys_lines)) + ['\n'])
    all_lines_full.extend(["📡卫视频道,#genre#"] + sort_data(ws_dictionary, correct_name_data(corrections_name, ws_lines)) + ['\n'])
    all_lines_full.extend(["☘️湖北频道,#genre#"] + sort_data(hb_dictionary, set(correct_name_data(corrections_name, hb_lines))) + ['\n'])
    all_lines_full.extend(["☘️广东频道,#genre#"] + sort_data(gd_dictionary, set(correct_name_data(corrections_name, gd_lines))) + ['\n'])
    all_lines_full.extend(["🏆体育赛事,#genre#"] + normalized_tyss_lines + ['\n'])
    all_lines_full.extend(["🚀AKTV📶,#genre#"] + aktv_lines + ['\n'])
    all_lines_full.extend(["🕒更新时间,#genre#"] + [version, about, daily_mtv, daily_mtv1, daily_mtv2, daily_mtv3, daily_mtv4] + read_txt_to_array(f"{CONFIG['manual_dir']}/about.txt") + ['\n'])

    # 精简源 (simple.txt)
    all_lines_simple = []
    all_lines_simple.extend(["央视频道,#genre#"] + sort_data(ys_dictionary, correct_name_data(corrections_name, ys_lines)) + ['\n'])
    all_lines_simple.extend(["卫视频道,#genre#"] + sort_data(ws_dictionary, correct_name_data(corrections_name, ws_lines)) + ['\n'])
    all_lines_simple.extend(["地方频道,#genre#"] + sort_data(hb_dictionary, set(correct_name_data(corrections_name, hb_lines))) + sort_data(gd_dictionary, set(correct_name_data(corrections_name, gd_lines))) + ['\n'])
    all_lines_simple.extend(["体育赛事,#genre#"] + normalized_tyss_lines + ['\n'])
    all_lines_simple.extend(["AKTV,#genre#"] + aktv_lines + ['\n'])
    all_lines_simple.extend(["更新时间,#genre#"] + [version] + ['\n'])

    # 定制源 (custom.txt)
    all_lines_custom = []
    all_lines_custom.extend(["🌐央视频道,#genre#"] + sort_data(ys_dictionary, correct_name_data(corrections_name, ys_lines)) + ['\n'])
    all_lines_custom.extend(["📡卫视频道,#genre#"] + sort_data(ws_dictionary, correct_name_data(corrections_name, ws_lines)) + ['\n'])
    all_lines_custom.extend(["🏠地方频道,#genre#"] + sort_data(hb_dictionary, set(correct_name_data(corrections_name, hb_lines))) + sort_data(gd_dictionary, set(correct_name_data(corrections_name, gd_lines))) + ['\n'])
    all_lines_custom.extend(["🏆体育赛事,#genre#"] + normalized_tyss_lines + ['\n'])
    all_lines_custom.extend(["🚀AKTV📶,#genre#"] + aktv_lines + ['\n'])
    all_lines_custom.extend(["🕒更新时间,#genre#"] + [version, about, daily_mtv, daily_mtv1, daily_mtv2, daily_mtv3, daily_mtv4] + read_txt_to_array(f"{CONFIG['manual_dir']}/about.txt") + ['\n'])

    # 其它源 (others.txt)
    all_lines_others = []
    all_lines_others.extend(["其它源,#genre#"] + others_lines + ['\n'])

    # 保存四个版本文件
    output_data = {
        'full': all_lines_full,
        'simple': all_lines_simple,
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

    # 为full、simple、custom生成对应的M3U文件
    print("🎵 生成M3U文件...")
    make_m3u(CONFIG['output_files']['full'], CONFIG['output_files']['full'].replace(".txt", ".m3u"))
    make_m3u(CONFIG['output_files']['simple'], CONFIG['output_files']['simple'].replace(".txt", ".m3u"))
    make_m3u(CONFIG['output_files']['custom'], CONFIG['output_files']['custom'].replace(".txt", ".m3u"))

    # 9. 统计信息
    timeend = datetime.now()
    elapsed_time = timeend - timestart
    total_seconds = elapsed_time.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)

    print("\n📊 =============== 执行统计 ===============")
    print(f"⏰ 开始时间: {timestart.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏰ 结束时间: {timeend.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ 执行时间: {minutes}分{seconds}秒")
    print(f"📋 黑名单: {len(combined_blacklist)} 条")
    print(f"📋 白名单: {len(whitelist_auto_lines)} 条")
    print(f"📺 央视源: {len(ys_lines)} 个")
    print(f"📺 卫视源: {len(ws_lines)} 个") 
    print(f"📺 湖北源: {len(hb_lines)} 个")
    print(f"📺 广东源: {len(gd_lines)} 个")
    print(f"⚽ 体育赛事: {len(normalized_tyss_lines)} 个")
    print(f"🚀 AKTV: {len(aktv_lines)} 个")
    print(f"📦 其它源: {len(others_lines)} 个")
    print(f"📄 全部源: {len(all_lines_full)} 行")
    print(f"📄 精简源: {len(all_lines_simple)} 行")
    print(f"📄 定制源: {len(all_lines_custom)} 行")
    print("==========================================\n")

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
    for file_type in ['full', 'simple', 'custom']:
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

    print("🏁 处理完成！")

if __name__ == "__main__":
    main()