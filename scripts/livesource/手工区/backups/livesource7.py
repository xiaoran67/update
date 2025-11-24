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
SOURCE_BASE = "scripts/livesource1"
OUTPUT_BASE = "output/livesource1"

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
ys_lines = [] #CCTV
ws_lines = [] #卫视频道

# 地方台
sh_lines = [] #地方台-上海频道
zj_lines = [] #地方台-浙江频道
jsu_lines = [] #地方台-江苏频道
gd_lines = [] #地方台-广东频道
hn_lines = [] #地方台-湖南频道
ah_lines = [] #地方台-安徽频道
hain_lines = [] #地方台-海南频道
nm_lines = [] #地方台-内蒙频道
hb_lines = [] #地方台-湖北频道
ln_lines = [] #地方台-辽宁频道
sx_lines = [] #地方台-陕西频道
shanxi_lines = [] #地方台-山西频道
shandong_lines = [] #地方台-山东频道
yunnan_lines = [] #地方台-云南频道
bj_lines = [] #地方台-北京频道
cq_lines = [] #地方台-重庆频道
fj_lines = [] #地方台-福建频道
gs_lines = [] #地方台-甘肃频道
gx_lines = [] #地方台-广西频道
gz_lines = [] #地方台-贵州频道
heb_lines = [] #地方台-河北频道
hen_lines = [] #地方台-河南频道
hlj_lines = [] #地方台-黑龙江频道
jl_lines = [] #地方台-吉林频道
jx_lines = [] #地方台-江西频道
nx_lines = [] #地方台-宁夏频道
qh_lines = [] #地方台-青海频道
sc_lines = [] #地方台-四川频道
tj_lines = [] #地方台-天津频道
xj_lines = [] #地方台-新疆频道

# 专业频道
ty_lines = [] #体育频道
tyss_lines = [] #体育赛事
sz_lines = [] #数字频道
yy_lines = [] #音乐频道
gj_lines = [] #国际频道
js_lines = [] #解说
cw_lines = [] #春晚
dy_lines = [] #电影
dsj_lines = [] #电视剧
gat_lines = [] #港澳台
xg_lines = [] #香港
aomen_lines = [] #澳门
tw_lines = [] #台湾
dhp_lines = [] #动画片
douyu_lines = [] #斗鱼直播
huya_lines = [] #虎牙直播
radio_lines = [] #收音机
zb_lines = [] #直播中国
zy_lines = [] #综艺频道
game_lines = [] #游戏频道
xq_lines = [] #戏曲
jlp_lines = [] #记录片

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
            
            if "CCTV" in channel_name and check_url_existence(ys_lines, channel_address):
                ys_lines.append(process_name_string(processed_line))
                channel_added = True
            
            if channel_name in ws_dictionary and check_url_existence(ws_lines, channel_address):
                ws_lines.append(process_name_string(processed_line))
                channel_added = True
            
            # 地方台分发 - 支持同频道多分类
            if channel_name in sh_dictionary and check_url_existence(sh_lines, channel_address):
                sh_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in zj_dictionary and check_url_existence(zj_lines, channel_address):
                zj_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jsu_dictionary and check_url_existence(jsu_lines, channel_address):
                jsu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gd_dictionary and check_url_existence(gd_lines, channel_address):
                gd_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hn_dictionary and check_url_existence(hn_lines, channel_address):
                hn_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in ah_dictionary and check_url_existence(ah_lines, channel_address):
                ah_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hain_dictionary and check_url_existence(hain_lines, channel_address):
                hain_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in nm_dictionary and check_url_existence(nm_lines, channel_address):
                nm_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hb_dictionary and check_url_existence(hb_lines, channel_address):
                hb_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in ln_dictionary and check_url_existence(ln_lines, channel_address):
                ln_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in sx_dictionary and check_url_existence(sx_lines, channel_address):
                sx_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shanxi_dictionary and check_url_existence(shanxi_lines, channel_address):
                shanxi_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in shandong_dictionary and check_url_existence(shandong_lines, channel_address):
                shandong_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in yunnan_dictionary and check_url_existence(yunnan_lines, channel_address):
                yunnan_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in bj_dictionary and check_url_existence(bj_lines, channel_address):
                bj_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in cq_dictionary and check_url_existence(cq_lines, channel_address):
                cq_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in fj_dictionary and check_url_existence(fj_lines, channel_address):
                fj_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gs_dictionary and check_url_existence(gs_lines, channel_address):
                gs_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gx_dictionary and check_url_existence(gx_lines, channel_address):
                gx_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gz_dictionary and check_url_existence(gz_lines, channel_address):
                gz_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in heb_dictionary and check_url_existence(heb_lines, channel_address):
                heb_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hen_dictionary and check_url_existence(hen_lines, channel_address):
                hen_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in hlj_dictionary and check_url_existence(hlj_lines, channel_address):
                hlj_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jl_dictionary and check_url_existence(jl_lines, channel_address):
                jl_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jx_dictionary and check_url_existence(jx_lines, channel_address):
                jx_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in nx_dictionary and check_url_existence(nx_lines, channel_address):
                nx_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in qh_dictionary and check_url_existence(qh_lines, channel_address):
                qh_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in sc_dictionary and check_url_existence(sc_lines, channel_address):
                sc_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in tj_dictionary and check_url_existence(tj_lines, channel_address):
                tj_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xj_dictionary and check_url_existence(xj_lines, channel_address):
                xj_lines.append(process_name_string(processed_line))
                channel_added = True
            
            # 专业频道分发
            if channel_name in ty_dictionary and check_url_existence(ty_lines, channel_address):
                ty_lines.append(process_name_string(processed_line))
                channel_added = True
            
            if any(tyss_item in channel_name for tyss_item in tyss_dictionary) and check_url_existence(tyss_lines, channel_address):
                tyss_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in sz_dictionary and check_url_existence(sz_lines, channel_address):
                sz_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in yy_dictionary and check_url_existence(yy_lines, channel_address):
                yy_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gj_dictionary and check_url_existence(gj_lines, channel_address):
                gj_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in js_dictionary and check_url_existence(js_lines, channel_address):
                js_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in cw_dictionary and check_url_existence(cw_lines, channel_address):
                cw_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dy_dictionary and check_url_existence(dy_lines, channel_address):
                dy_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dsj_dictionary and check_url_existence(dsj_lines, channel_address):
                dsj_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in gat_dictionary and check_url_existence(gat_lines, channel_address):
                gat_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xg_dictionary and check_url_existence(xg_lines, channel_address):
                xg_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in aomen_dictionary and check_url_existence(aomen_lines, channel_address):
                aomen_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in tw_dictionary and check_url_existence(tw_lines, channel_address):
                tw_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in dhp_dictionary and check_url_existence(dhp_lines, channel_address):
                dhp_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in douyu_dictionary and check_url_existence(douyu_lines, channel_address):
                douyu_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in huya_dictionary and check_url_existence(huya_lines, channel_address):
                huya_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in radio_dictionary and check_url_existence(radio_lines, channel_address):
                radio_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in zb_dictionary and check_url_existence(zb_lines, channel_address):
                zb_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in zy_dictionary and check_url_existence(zy_lines, channel_address):
                zy_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in game_dictionary and check_url_existence(game_lines, channel_address):
                game_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in xq_dictionary and check_url_existence(xq_lines, channel_address):
                xq_lines.append(process_name_string(processed_line))
                channel_added = True
                
            if channel_name in jlp_dictionary and check_url_existence(jlp_lines, channel_address):
                jlp_lines.append(process_name_string(processed_line))
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
ys_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/CCTV.txt")
ws_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/卫视频道.txt")

# 地方台字典
sh_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/上海频道.txt")
zj_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/浙江频道.txt")
jsu_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/江苏频道.txt")
gd_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/广东频道.txt")
hn_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/湖南频道.txt")
ah_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/安徽频道.txt")
hain_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/海南频道.txt")
nm_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/内蒙频道.txt")
hb_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/湖北频道.txt")
ln_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/辽宁频道.txt")
sx_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/陕西频道.txt")
shanxi_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/山西频道.txt")
shandong_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/山东频道.txt")
yunnan_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/云南频道.txt")
bj_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/北京频道.txt")
cq_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/重庆频道.txt")
fj_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/福建频道.txt")
gs_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/甘肃频道.txt")
gx_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/广西频道.txt")
gz_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/贵州频道.txt")
heb_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/河北频道.txt")
hen_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/河南频道.txt")
hlj_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/黑龙江频道.txt")
jl_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/吉林频道.txt")
jx_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/江西频道.txt")
nx_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/宁夏频道.txt")
qh_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/青海频道.txt")
sc_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/四川频道.txt")
tj_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/天津频道.txt")
xj_dictionary = read_txt_to_array(f"{CONFIG['local_channels_dir']}/新疆频道.txt")

# 专业频道字典
ty_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/体育频道.txt")
tyss_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/体育赛事.txt")
sz_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/数字频道.txt")
yy_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/音乐频道.txt")
gj_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/国际频道.txt")
js_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/解说.txt")
cw_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/春晚.txt")
dy_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/电影.txt")
dsj_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/电视剧.txt")
gat_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/港澳台.txt")
xg_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/香港.txt")
aomen_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/澳门.txt")
tw_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/台湾.txt")
dhp_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/动画片.txt")
douyu_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/斗鱼直播.txt")
huya_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/虎牙直播.txt")
radio_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/收音机.txt")
zb_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/直播中国.txt")
zy_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/综艺频道.txt")
game_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/游戏频道.txt")
xq_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/戏曲.txt")
jlp_dictionary = read_txt_to_array(f"{CONFIG['main_channels_dir']}/记录片.txt")

# 加载纠错数据
corrections_name = load_corrections_name(f"{CONFIG['assets_dir']}/corrections_name.txt")

print(f"✅ 字典数据加载完成: CCTV({len(ys_dictionary)}) 卫视({len(ws_dictionary)}) 地方台(27个) 专业频道(22个)")

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
        '广东频道': gd_lines,
        '湖北频道': hb_lines, 
        '湖南频道': hn_lines,
        '浙江频道': zj_lines,
        '江苏频道': jsu_lines
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

    normalized_tyss_lines = [normalize_date_to_md(s) for s in tyss_lines]

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
    all_lines_full.extend(["🌐央视频道,#genre#"] + sort_data(ys_dictionary, correct_name_data(corrections_name, ys_lines)) + ['\n'])
    all_lines_full.extend(["📡卫视频道,#genre#"] + sort_data(ws_dictionary, correct_name_data(corrections_name, ws_lines)) + ['\n'])

    # 地方台分类
    all_lines_full.extend(["🏠湖北频道,#genre#"] + sort_data(hb_dictionary, correct_name_data(corrections_name, hb_lines)) + ['\n'])
    all_lines_full.extend(["🏠上海频道,#genre#"] + sort_data(sh_dictionary, correct_name_data(corrections_name, sh_lines)) + ['\n'])
    all_lines_full.extend(["🏠浙江频道,#genre#"] + sort_data(zj_dictionary, correct_name_data(corrections_name, zj_lines)) + ['\n'])
    all_lines_full.extend(["🏠江苏频道,#genre#"] + sort_data(jsu_dictionary, correct_name_data(corrections_name, jsu_lines)) + ['\n'])
    all_lines_full.extend(["🏠广东频道,#genre#"] + sort_data(gd_dictionary, correct_name_data(corrections_name, gd_lines)) + ['\n'])
    all_lines_full.extend(["🏠湖南频道,#genre#"] + sort_data(hn_dictionary, correct_name_data(corrections_name, hn_lines)) + ['\n'])
    all_lines_full.extend(["🏠安徽频道,#genre#"] + sort_data(ah_dictionary, correct_name_data(corrections_name, ah_lines)) + ['\n'])
    all_lines_full.extend(["🏠海南频道,#genre#"] + sort_data(hain_dictionary, correct_name_data(corrections_name, hain_lines)) + ['\n'])
    all_lines_full.extend(["🏠内蒙频道,#genre#"] + sort_data(nm_dictionary, correct_name_data(corrections_name, nm_lines)) + ['\n'])
    all_lines_full.extend(["🏠辽宁频道,#genre#"] + sort_data(ln_dictionary, correct_name_data(corrections_name, ln_lines)) + ['\n'])
    all_lines_full.extend(["🏠陕西频道,#genre#"] + sort_data(sx_dictionary, correct_name_data(corrections_name, sx_lines)) + ['\n'])
    all_lines_full.extend(["🏠山西频道,#genre#"] + sort_data(shanxi_dictionary, correct_name_data(corrections_name, shanxi_lines)) + ['\n'])
    all_lines_full.extend(["🏠山东频道,#genre#"] + sort_data(shandong_dictionary, correct_name_data(corrections_name, shandong_lines)) + ['\n'])
    all_lines_full.extend(["🏠云南频道,#genre#"] + sort_data(yunnan_dictionary, correct_name_data(corrections_name, yunnan_lines)) + ['\n'])
    all_lines_full.extend(["🏠北京频道,#genre#"] + sort_data(bj_dictionary, correct_name_data(corrections_name, bj_lines)) + ['\n'])
    all_lines_full.extend(["🏠重庆频道,#genre#"] + sort_data(cq_dictionary, correct_name_data(corrections_name, cq_lines)) + ['\n'])
    all_lines_full.extend(["🏠福建频道,#genre#"] + sort_data(fj_dictionary, correct_name_data(corrections_name, fj_lines)) + ['\n'])
    all_lines_full.extend(["🏠甘肃频道,#genre#"] + sort_data(gs_dictionary, correct_name_data(corrections_name, gs_lines)) + ['\n'])
    all_lines_full.extend(["🏠广西频道,#genre#"] + sort_data(gx_dictionary, correct_name_data(corrections_name, gx_lines)) + ['\n'])
    all_lines_full.extend(["🏠贵州频道,#genre#"] + sort_data(gz_dictionary, correct_name_data(corrections_name, gz_lines)) + ['\n'])
    all_lines_full.extend(["🏠河北频道,#genre#"] + sort_data(heb_dictionary, correct_name_data(corrections_name, heb_lines)) + ['\n'])
    all_lines_full.extend(["🏠河南频道,#genre#"] + sort_data(hen_dictionary, correct_name_data(corrections_name, hen_lines)) + ['\n'])
    all_lines_full.extend(["🏠黑龙江频道,#genre#"] + sort_data(hlj_dictionary, correct_name_data(corrections_name, hlj_lines)) + ['\n'])
    all_lines_full.extend(["🏠吉林频道,#genre#"] + sort_data(jl_dictionary, correct_name_data(corrections_name, jl_lines)) + ['\n'])
    all_lines_full.extend(["🏠江西频道,#genre#"] + sort_data(jx_dictionary, correct_name_data(corrections_name, jx_lines)) + ['\n'])
    all_lines_full.extend(["🏠宁夏频道,#genre#"] + sort_data(nx_dictionary, correct_name_data(corrections_name, nx_lines)) + ['\n'])
    all_lines_full.extend(["🏠青海频道,#genre#"] + sort_data(qh_dictionary, correct_name_data(corrections_name, qh_lines)) + ['\n'])
    all_lines_full.extend(["🏠四川频道,#genre#"] + sort_data(sc_dictionary, correct_name_data(corrections_name, sc_lines)) + ['\n'])
    all_lines_full.extend(["🏠天津频道,#genre#"] + sort_data(tj_dictionary, correct_name_data(corrections_name, tj_lines)) + ['\n'])
    all_lines_full.extend(["🏠新疆频道,#genre#"] + sort_data(xj_dictionary, correct_name_data(corrections_name, xj_lines)) + ['\n'])

    # 专业频道
    all_lines_full.extend(["⚽体育频道,#genre#"] + sort_data(ty_dictionary, correct_name_data(corrections_name, ty_lines)) + ['\n'])
    all_lines_full.extend(["🏆体育赛事,#genre#"] + normalized_tyss_lines + ['\n'])
    all_lines_full.extend(["🔢数字频道,#genre#"] + sort_data(sz_dictionary, correct_name_data(corrections_name, sz_lines)) + ['\n'])
    all_lines_full.extend(["🎵音乐频道,#genre#"] + sort_data(yy_dictionary, correct_name_data(corrections_name, yy_lines)) + ['\n'])
    all_lines_full.extend(["🌍国际频道,#genre#"] + sort_data(gj_dictionary, correct_name_data(corrections_name, gj_lines)) + ['\n'])
    all_lines_full.extend(["🎙️解说,#genre#"] + sort_data(js_dictionary, correct_name_data(corrections_name, js_lines)) + ['\n'])
    all_lines_full.extend(["🎉春晚,#genre#"] + sort_data(cw_dictionary, correct_name_data(corrections_name, cw_lines)) + ['\n'])
    all_lines_full.extend(["🎬电影,#genre#"] + sort_data(dy_dictionary, correct_name_data(corrections_name, dy_lines)) + ['\n'])
    all_lines_full.extend(["📺电视剧,#genre#"] + sort_data(dsj_dictionary, correct_name_data(corrections_name, dsj_lines)) + ['\n'])
    all_lines_full.extend(["🎭港澳台,#genre#"] + sort_data(gat_dictionary, correct_name_data(corrections_name, gat_lines)) + ['\n'])
    all_lines_full.extend(["🏙️香港,#genre#"] + sort_data(xg_dictionary, correct_name_data(corrections_name, xg_lines)) + ['\n'])
    all_lines_full.extend(["🎰澳门,#genre#"] + sort_data(aomen_dictionary, correct_name_data(corrections_name, aomen_lines)) + ['\n'])
    all_lines_full.extend(["📺动画片,#genre#"] + sort_data(dhp_dictionary, correct_name_data(corrections_name, dhp_lines)) + ['\n'])
    all_lines_full.extend(["🐟斗鱼直播,#genre#"] + sort_data(douyu_dictionary, correct_name_data(corrections_name, douyu_lines)) + ['\n'])
    all_lines_full.extend(["🐯虎牙直播,#genre#"] + sort_data(huya_dictionary, correct_name_data(corrections_name, huya_lines)) + ['\n'])
    all_lines_full.extend(["📻收音机,#genre#"] + sort_data(radio_dictionary, correct_name_data(corrections_name, radio_lines)) + ['\n'])
    all_lines_full.extend(["🇨🇳直播中国,#genre#"] + sort_data(zb_dictionary, correct_name_data(corrections_name, zb_lines)) + ['\n'])
    all_lines_full.extend(["🎪综艺频道,#genre#"] + sort_data(zy_dictionary, correct_name_data(corrections_name, zy_lines)) + ['\n'])
    all_lines_full.extend(["🎮游戏频道,#genre#"] + sort_data(game_dictionary, correct_name_data(corrections_name, game_lines)) + ['\n'])
    all_lines_full.extend(["🎭戏曲,#genre#"] + sort_data(xq_dictionary, correct_name_data(corrections_name, xq_lines)) + ['\n'])
    all_lines_full.extend(["🎬记录片,#genre#"] + sort_data(jlp_dictionary, correct_name_data(corrections_name, jlp_lines)) + ['\n'])

    # 完整版其他和更新信息
    all_lines_full.extend(["📦其它源,#genre#"] + others_lines + ['\n'])
    all_lines_full.extend(["🕒更新时间,#genre#"] + [version, about, daily_mtv, daily_mtv1, daily_mtv2, daily_mtv3, daily_mtv4] + read_txt_to_array(f"{CONFIG['manual_dir']}/about.txt") + ['\n'])

    # 精简源 (lite.txt)
    all_lines_lite = []
    all_lines_lite.extend(["央视频道,#genre#"] + sort_data(ys_dictionary, correct_name_data(corrections_name, ys_lines)) + ['\n'])
    all_lines_lite.extend(["卫视频道,#genre#"] + sort_data(ws_dictionary, correct_name_data(corrections_name, ws_lines)) + ['\n'])

    # 合并地方频道
    all_lines_lite.extend(["地方频道,#genre#"] + 
                           sort_data(sh_dictionary, correct_name_data(corrections_name, sh_lines)) +
                           sort_data(zj_dictionary, correct_name_data(corrections_name, zj_lines)) +
                           sort_data(jsu_dictionary, correct_name_data(corrections_name, jsu_lines)) +
                           sort_data(gd_dictionary, correct_name_data(corrections_name, gd_lines)) +
                           sort_data(hn_dictionary, correct_name_data(corrections_name, hn_lines)) +
                           sort_data(ah_dictionary, correct_name_data(corrections_name, ah_lines)) +
                           sort_data(hain_dictionary, correct_name_data(corrections_name, hain_lines)) +
                           sort_data(nm_dictionary, correct_name_data(corrections_name, nm_lines)) +
                           sort_data(hb_dictionary, correct_name_data(corrections_name, hb_lines)) +
                           sort_data(ln_dictionary, correct_name_data(corrections_name, ln_lines)) +
                           sort_data(sx_dictionary, correct_name_data(corrections_name, sx_lines)) +
                           sort_data(shanxi_dictionary, correct_name_data(corrections_name, shanxi_lines)) +
                           sort_data(shandong_dictionary, correct_name_data(corrections_name, shandong_lines)) +
                           sort_data(yunnan_dictionary, correct_name_data(corrections_name, yunnan_lines)) +
                           sort_data(bj_dictionary, correct_name_data(corrections_name, bj_lines)) +
                           sort_data(cq_dictionary, correct_name_data(corrections_name, cq_lines)) +
                           sort_data(fj_dictionary, correct_name_data(corrections_name, fj_lines)) +
                           sort_data(gs_dictionary, correct_name_data(corrections_name, gs_lines)) +
                           sort_data(gx_dictionary, correct_name_data(corrections_name, gx_lines)) +
                           sort_data(gz_dictionary, correct_name_data(corrections_name, gz_lines)) +
                           sort_data(heb_dictionary, correct_name_data(corrections_name, heb_lines)) +
                           sort_data(hen_dictionary, correct_name_data(corrections_name, hen_lines)) +
                           sort_data(hlj_dictionary, correct_name_data(corrections_name, hlj_lines)) +
                           sort_data(jl_dictionary, correct_name_data(corrections_name, jl_lines)) +
                           sort_data(jx_dictionary, correct_name_data(corrections_name, jx_lines)) +
                           sort_data(nx_dictionary, correct_name_data(corrections_name, nx_lines)) +
                           sort_data(qh_dictionary, correct_name_data(corrections_name, qh_lines)) +
                           sort_data(sc_dictionary, correct_name_data(corrections_name, sc_lines)) +
                           sort_data(tj_dictionary, correct_name_data(corrections_name, tj_lines)) +
                           sort_data(xj_dictionary, correct_name_data(corrections_name, xj_lines)) + ['\n'])

    # 精简源更新信息
    all_lines_lite.extend(["更新时间,#genre#"] + [version] + ['\n'])

    # 定制源 (custom.txt)
    all_lines_custom = []
    all_lines_custom.extend(["🌐央视频道,#genre#"] + sort_data(ys_dictionary, correct_name_data(corrections_name, ys_lines)) + ['\n'])
    all_lines_custom.extend(["📡卫视频道,#genre#"] + sort_data(ws_dictionary, correct_name_data(corrections_name, ws_lines)) + ['\n'])

    # 定制源的地方频道
    all_lines_custom.extend(["🏠地方频道,#genre#"] + 

                           sort_data(hb_dictionary, correct_name_data(corrections_name, hb_lines)) +
                           sort_data(sh_dictionary, correct_name_data(corrections_name, sh_lines)) +
                           sort_data(zj_dictionary, correct_name_data(corrections_name, zj_lines)) +
                           sort_data(jsu_dictionary, correct_name_data(corrections_name, jsu_lines)) +
                           sort_data(gd_dictionary, correct_name_data(corrections_name, gd_lines)) +
                           sort_data(hn_dictionary, correct_name_data(corrections_name, hn_lines)) +
                           sort_data(bj_dictionary, correct_name_data(corrections_name, bj_lines)) +
                           sort_data(shandong_dictionary, correct_name_data(corrections_name, shandong_lines)) + ['\n'])

    # 定制源的专业频道
    all_lines_custom.extend(["⚽体育频道,#genre#"] + sort_data(ty_dictionary, correct_name_data(corrections_name, ty_lines)) + ['\n'])
    all_lines_custom.extend(["🏆体育赛事,#genre#"] + normalized_tyss_lines + ['\n'])
    all_lines_custom.extend(["🎬影视娱乐,#genre#"] + 
                           sort_data(dy_dictionary, correct_name_data(corrections_name, dy_lines)) +
                           sort_data(dsj_dictionary, correct_name_data(corrections_name, dsj_lines)) +
                           sort_data(zy_dictionary, correct_name_data(corrections_name, zy_lines)) + ['\n'])
    all_lines_custom.extend(["🎭港澳台,#genre#"] + 
                           sort_data(gat_dictionary, correct_name_data(corrections_name, gat_lines)) +
                           sort_data(xg_dictionary, correct_name_data(corrections_name, xg_lines)) +
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
    print(f"🌐 央视源: {len(ys_lines)} 个")
    print(f"📡 卫视源: {len(ws_lines)} 个")

    # 地方台统计
    print(f"🏠 上海源: {len(sh_lines)} 个")
    print(f"🏠 浙江源: {len(zj_lines)} 个")
    print(f"🏠 江苏源: {len(jsu_lines)} 个")
    print(f"🏠 广东源: {len(gd_lines)} 个")
    print(f"🏠 湖南源: {len(hn_lines)} 个")
    print(f"🏠 安徽源: {len(ah_lines)} 个")
    print(f"🏠 海南源: {len(hain_lines)} 个")
    print(f"🏠 内蒙源: {len(nm_lines)} 个")
    print(f"🏠 湖北源: {len(hb_lines)} 个")
    print(f"🏠 辽宁源: {len(ln_lines)} 个")
    print(f"🏠 陕西源: {len(sx_lines)} 个")
    print(f"🏠 山西源: {len(shanxi_lines)} 个")
    print(f"🏠 山东源: {len(shandong_lines)} 个")
    print(f"🏠 云南源: {len(yunnan_lines)} 个")
    print(f"🏠 北京源: {len(bj_lines)} 个")
    print(f"🏠 重庆源: {len(cq_lines)} 个")
    print(f"🏠 福建源: {len(fj_lines)} 个")
    print(f"🏠 甘肃源: {len(gs_lines)} 个")
    print(f"🏠 广西源: {len(gx_lines)} 个")
    print(f"🏠 贵州源: {len(gz_lines)} 个")
    print(f"🏠 河北源: {len(heb_lines)} 个")
    print(f"🏠 河南源: {len(hen_lines)} 个")
    print(f"🏠 黑龙江源: {len(hlj_lines)} 个")
    print(f"🏠 吉林源: {len(jl_lines)} 个")
    print(f"🏠 江西源: {len(jx_lines)} 个")
    print(f"🏠 宁夏源: {len(nx_lines)} 个")
    print(f"🏠 青海源: {len(qh_lines)} 个")
    print(f"🏠 四川源: {len(sc_lines)} 个")
    print(f"🏠 天津源: {len(tj_lines)} 个")
    print(f"🏠 新疆源: {len(xj_lines)} 个")

    # 专业频道统计
    print(f"⚽ 体育频道: {len(ty_lines)} 个")
    print(f"🏆 体育赛事: {len(normalized_tyss_lines)} 个")
    print(f"🔢 数字频道: {len(sz_lines)} 个")
    print(f"🎵 音乐频道: {len(yy_lines)} 个")
    print(f"🌍 国际频道: {len(gj_lines)} 个")
    print(f"🎙️ 解说: {len(js_lines)} 个")
    print(f"🎉 春晚: {len(cw_lines)} 个")
    print(f"🎬 电影: {len(dy_lines)} 个")
    print(f"📺 电视剧: {len(dsj_lines)} 个")
    print(f"🎭 港澳台: {len(gat_lines)} 个")
    print(f"🏙️ 香港: {len(xg_lines)} 个")
    print(f"🎰 澳门: {len(aomen_lines)} 个")
    print(f"📺 动画片: {len(dhp_lines)} 个")
    print(f"🐟 斗鱼直播: {len(douyu_lines)} 个")
    print(f"🐯 虎牙直播: {len(huya_lines)} 个")
    print(f"📻 收音机: {len(radio_lines)} 个")
    print(f"🇨🇳 直播中国: {len(zb_lines)} 个")
    print(f"🎪 综艺频道: {len(zy_lines)} 个")
    print(f"🎮 游戏频道: {len(game_lines)} 个")
    print(f"🎭 戏曲: {len(xq_lines)} 个")
    print(f"🎬 记录片: {len(jlp_lines)} 个")

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
