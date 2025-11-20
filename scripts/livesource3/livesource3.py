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
    
    # 其他配置
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
# 使用北京时间
beijing_tz = timezone(timedelta(hours=8))
timestart = datetime.now(beijing_tz)

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

# ==================== 频道管理器类 ====================
class ChannelManager:
    def __init__(self, config):
        self.config = config
        self.channel_sources = {}  # 频道名 -> 直播源列表
        self.all_channels = set()  # 所有频道名称
        self.category_channels = {}  # 分类 -> 频道列表
        
    def load_channel_names(self, directory, category_type):
        """加载频道名称（主频道和地方台）"""
        channel_names = {}
        if not os.path.exists(directory):
            print(f"⚠️ 目录不存在: {directory}")
            return channel_names
            
        for filename in os.listdir(directory):
            if filename.endswith('.txt'):
                category = filename[:-4]  # 去掉.txt后缀
                file_path = os.path.join(directory, filename)
                channels = read_txt_to_array(file_path)
                channel_names[category] = channels
                
                # 添加到全局频道集合
                self.all_channels.update(channels)
                
                # 记录分类信息
                for channel in channels:
                    if channel not in self.category_channels:
                        self.category_channels[channel] = []
                    self.category_channels[channel].append(f"{category_type}:{category}")
                
                print(f"✅ 加载 {category_type}-{category}: {len(channels)} 个频道")
                
        return channel_names
    
    def load_manual_sources(self):
        """加载手工区的直播源"""
        manual_dir = self.config['manual_dir']
        if not os.path.exists(manual_dir):
            print(f"⚠️ 手工区目录不存在: {manual_dir}")
            return
            
        manual_count = 0
        for filename in os.listdir(manual_dir):
            if filename.endswith('.txt'):
                file_path = os.path.join(manual_dir, filename)
                lines = read_txt_to_array(file_path)
                
                for line in lines:
                    if ',' in line and "#genre#" not in line:
                        try:
                            channel_name, source = line.strip().split(',', 1)
                            source = clean_url(source)
                            
                            # 跳过黑名单
                            if source in combined_blacklist or should_skip_url(source):
                                continue
                                
                            # 添加到频道源映射
                            if channel_name not in self.channel_sources:
                                self.channel_sources[channel_name] = []
                            
                            # URL去重
                            url_hash = get_url_hash(source)
                            existing_hashes = [get_url_hash(s) for s in self.channel_sources[channel_name]]
                            
                            if url_hash not in existing_hashes:
                                self.channel_sources[channel_name].append(source)
                                manual_count += 1
                                
                        except Exception as e:
                            print(f"⚠️ 解析手工区行错误: {e}, 行: {line}")
        
        print(f"✅ 手工区加载完成: {manual_count} 个直播源，{len(self.channel_sources)} 个频道")
    
    def process_url_source(self, url):
        """处理URL源并添加到频道管理器"""
        try:
            response_text = get_http_response(url)
            if not response_text:
                return 0

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
                        channel_name = clean_channel_name(channel_name, CONFIG['removal_list'])
                        channel_name = traditional_to_simplified(channel_name)
                        channel_address = clean_url(channel_address.strip())
                        
                        # 跳过黑名单
                        if channel_address in combined_blacklist:
                            continue
                        
                        # 添加到频道管理器
                        if channel_name not in self.channel_sources:
                            self.channel_sources[channel_name] = []
                        
                        # URL去重
                        url_hash = get_url_hash(channel_address)
                        existing_hashes = [get_url_hash(s) for s in self.channel_sources[channel_name]]
                        
                        if url_hash not in existing_hashes:
                            self.channel_sources[channel_name].append(channel_address)
                            valid_lines += 1
                            
                    except Exception as e:
                        print(f"⚠️ 处理行错误: {e}, 行: {line}")

            return valid_lines

        except Exception as e:
            print(f"❌ 处理URL时发生错误 {url}: {e}")
            return 0
    
    def generate_playlist(self, main_channels, local_channels, output_type='full'):
        """生成播放列表"""
        output_lines = []
        
        # 1. 主频道分类
        output_lines.append("🎬主频道,#genre#")
        for category, channels in main_channels.items():
            output_lines.append(f"📺{category},#genre#")
            
            # 按字典排序
            sorted_channels = sorted(channels)
            channel_count = 0
            for channel in sorted_channels:
                sources = self.channel_sources.get(channel, [])
                if sources:
                    for source in sources:
                        output_lines.append(f"{channel},{source}")
                        channel_count += 1
                        
            output_lines.append(f"# {category}共{channel_count}个频道")
            output_lines.append('')
        
        # 2. 地方台分类  
        output_lines.append("🏠地方台,#genre#")
        for category, channels in local_channels.items():
            output_lines.append(f"📍{category},#genre#")
            
            sorted_channels = sorted(channels)
            channel_count = 0
            for channel in sorted_channels:
                sources = self.channel_sources.get(channel, [])
                if sources:
                    for source in sources:
                        output_lines.append(f"{channel},{source}")
                        channel_count += 1
                        
            output_lines.append(f"# {category}共{channel_count}个频道")
            output_lines.append('')
        
        # 3. 手工区和其他特殊分类
        if output_type in ['full', 'custom']:
            # 添加手工区中不在主频道和地方台的频道
            manual_only_channels = []
            for channel in self.channel_sources:
                if (channel not in self.all_channels and 
                    any(keyword in channel for keyword in ['香港', '澳门', '台湾', '凤凰', 'TVB'])):
                    manual_only_channels.append(channel)
            
            if manual_only_channels:
                output_lines.append("🌟手工区,#genre#")
                for channel in sorted(manual_only_channels):
                    sources = self.channel_sources.get(channel, [])
                    for source in sources:
                        output_lines.append(f"{channel},{source}")
                output_lines.append('')
        
        # 4. 添加其他信息
        beijing_time = datetime.now(beijing_tz)
        formatted_time = beijing_time.strftime("%Y%m%d %H:%M:%S")
        
        output_lines.extend([
            "🕒更新时间,#genre#",
            f"更新时间,{formatted_time}",
            f"总频道数,{len([c for c in self.all_channels if c in self.channel_sources])}",
            f"直播源数,{sum(len(sources) for sources in self.channel_sources.values())}",
            ""
        ])
        
        return output_lines

# ==================== 原有工具函数（保持不变） ====================
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

def get_random_url(file_path):
    """随机获取URL"""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if ',' in line:
                    url = line.strip().split(',')[-1]
                    if url.startswith('http'):
                        urls.append(url)    
    except Exception as e:
        print(f"⚠️ 读取文件 {file_path} 时发生错误：{e}")
    return random.choice(urls) if urls else ""

# ==================== 黑名单处理 ====================
print("🔧 加载黑名单...")
blacklist_auto = read_blacklist_from_txt(f"{CONFIG['blacklist_dir']}/blacklist_auto.txt") 
blacklist_manual = read_blacklist_from_txt(f"{CONFIG['blacklist_dir']}/blacklist_manual.txt") 
combined_blacklist = set(blacklist_auto + blacklist_manual)
print(f"✅ 黑名单加载完成: {len(combined_blacklist)} 条记录")

# ==================== 主处理流程 ====================
def main():
    print("🚀 开始处理直播源...")
    
    # 初始化频道管理器
    channel_manager = ChannelManager(CONFIG)
    
    # 1. 加载频道名称
    print("📚 加载主频道和地方台名称...")
    main_channels = channel_manager.load_channel_names(CONFIG['main_channels_dir'], "主频道")
    local_channels = channel_manager.load_channel_names(CONFIG['local_channels_dir'], "地方台")
    
    print(f"✅ 频道名称加载完成: 主频道({len(main_channels)}类) 地方台({len(local_channels)}类)")
    print(f"📊 总频道数: {len(channel_manager.all_channels)}")
    
    # 2. 处理URL源
    urls = read_txt_to_array(f"{CONFIG['assets_dir']}/urls-daily.txt")
    print(f"📡 发现 {len(urls)} 个URL源")
    
    total_url_sources = 0
    for url in urls:
        if url.startswith("http"):
            # 处理日期变量 - 使用北京时间
            current_date_str = datetime.now(beijing_tz).strftime("%m%d")
            yesterday_date_str = (datetime.now(beijing_tz) - timedelta(days=1)).strftime("%m%d")
            
            if "{MMdd}" in url:
                url = url.replace("{MMdd}", current_date_str)
            if "{MMdd-1}" in url:
                url = url.replace("{MMdd-1}", yesterday_date_str)
            
            print(f"🌐 处理URL: {url}")
            count = channel_manager.process_url_source(url)
            total_url_sources += count
            print(f"✅ 处理完成: {count} 个有效频道")
    
    print(f"📡 URL源处理完成: {total_url_sources} 个直播源")
    
    # 3. 加载手工区直播源
    print("🔧 加载手工区直播源...")
    channel_manager.load_manual_sources()
    
    # 4. 生成各种版本的播放列表
    print("📄 生成播放列表...")
    
    # 完整版
    full_lines = channel_manager.generate_playlist(main_channels, local_channels, 'full')
    with open(CONFIG['output_files']['full'], 'w', encoding='utf-8') as f:
        f.write('\n'.join(full_lines))
    print(f"✅ 完整版生成: {len(full_lines)} 行")
    
    # 精简版（只包含部分分类）
    simple_main = {k: v for k, v in main_channels.items() if 'CCTV' in k or '卫视' in k}
    simple_local = {k: v for k, v in local_channels.items() if any(prov in k for prov in ['北京', '上海', '广东', '湖北'])}
    simple_lines = channel_manager.generate_playlist(simple_main, simple_local, 'simple')
    with open(CONFIG['output_files']['simple'], 'w', encoding='utf-8') as f:
        f.write('\n'.join(simple_lines))
    print(f"✅ 精简版生成: {len(simple_lines)} 行")
    
    # 定制版（可以根据需要调整）
    custom_lines = channel_manager.generate_playlist(main_channels, local_channels, 'custom')
    with open(CONFIG['output_files']['custom'], 'w', encoding='utf-8') as f:
        f.write('\n'.join(custom_lines))
    print(f"✅ 定制版生成: {len(custom_lines)} 行")
    
    # 5. 生成M3U文件
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

    print("🎵 生成M3U文件...")
    make_m3u(CONFIG['output_files']['full'], CONFIG['output_files']['full'].replace(".txt", ".m3u"))
    make_m3u(CONFIG['output_files']['simple'], CONFIG['output_files']['simple'].replace(".txt", ".m3u"))
    make_m3u(CONFIG['output_files']['custom'], CONFIG['output_files']['custom'].replace(".txt", ".m3u"))
    
    # 6. 生成统计信息
    timeend = datetime.now(beijing_tz)
    elapsed_time = timeend - timestart
    total_seconds = elapsed_time.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    
    total_sources = sum(len(sources) for sources in channel_manager.channel_sources.values())
    channels_with_sources = len([c for c in channel_manager.all_channels if c in channel_manager.channel_sources])

    print("\n📊 =============== 执行统计 ===============")
    print(f"⏰ 开始时间: {timestart.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"⏰ 结束时间: {timeend.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"⏱️ 执行时间: {minutes}分{seconds}秒")
    print(f"📋 黑名单: {len(combined_blacklist)} 条")
    print(f"📺 总频道数: {len(channel_manager.all_channels)}")
    print(f"🔗 有直播源的频道: {channels_with_sources}")
    print(f"📡 总直播源数: {total_sources}")
    print(f"📁 主频道分类: {len(main_channels)}")
    print(f"🏠 地方台分类: {len(local_channels)}")
    print(f"📄 完整版行数: {len(full_lines)}")
    print(f"📄 精简版行数: {len(simple_lines)}")
    print(f"📄 定制版行数: {len(custom_lines)}")
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