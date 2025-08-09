import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
import os
from urllib.parse import urlparse
import socket
import subprocess
import json
import random

# ====== 全局配置 ======
LOG_LEVEL = "INFO"  # DEBUG/INFO/WARN/ERROR
MAX_WORKERS = 20
CHECK_TIMEOUT = 6
FFPROBE_TIMEOUT = 8
# =====================

def log(level, msg):
    levels = ["DEBUG", "INFO", "WARN", "ERROR"]
    if levels.index(level) >= levels.index(LOG_LEVEL):
        print(f"[{level}] {msg}")

def get_video_resolution(video_path, timeout=FFPROBE_TIMEOUT):
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height', '-of', 'json', video_path
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                               text=True, timeout=timeout)
        video_info = json.loads(result.stdout)
        width = video_info['streams'][0]['width']
        height = video_info['streams'][0]['height']
        return width, height
    except Exception as e:
        log("WARN", f"获取分辨率失败: {e}")
        return None, None

# 随机User-Agent
def get_random_user_agent():
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    ]
    return random.choice(USER_AGENTS)

def check_url(url, timeout=CHECK_TIMEOUT):
    start_time = time.time()
    success = False
    width, height = 0, 0
    
    try:
        if url.startswith("http"):
            headers = {'User-Agent': get_random_user_agent()}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                success = (response.status == 200)
        elif url.startswith("p3p"):
            success = check_p3p_url(url, timeout)
        elif url.startswith("p2p"):
            success = check_p2p_url(url, timeout)        
        elif url.startswith("rtmp") or url.startswith("rtsp"):
            success = check_rtmp_url(url, timeout)
        elif url.startswith("rtp"):
            success = check_rtp_url(url, timeout)
        else:
            log("WARN", f"不支持的协议: {url}")

        elapsed_time = (time.time() - start_time) * 1000
        if success:
            width, height = get_video_resolution(url)
        log("DEBUG", f"检测 {url}: 成功={success}, 时间={elapsed_time:.1f}ms, 分辨率={width}x{height}")
    except Exception as e:
        log("WARN", f"检测URL异常 {url}: {e}")
        elapsed_time = None
        
    return success, elapsed_time, width, height

# 协议检测函数保持不变...

def process_line(line):
    if "#genre#" in line or "://" not in line:
        return None, None, None, None
        
    parts = line.split(',', 1)
    if len(parts) < 2:
        return None, None, None, None
        
    name, url = parts
    url = url.strip()
    return name.strip(), url, *check_url(url)

# 高效多线程处理
def process_urls_multithreaded(lines, max_workers=MAX_WORKERS):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_line, line): line for line in lines}
        for future in as_completed(futures):
            try:
                res = future.result()
                if res[0] is not None:  # 有效结果
                    results.append(res)
            except Exception as e:
                log("ERROR", f"线程执行异常: {e}")
    return results

# 写入文件
def write_list(file_path, data_list):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        for item in data_list:
            file.write(item + '\n')

# 转换M3U格式
def convert_m3u_to_txt(m3u_content):
    lines = m3u_content.split('\n')
    txt_lines = []
    channel_name = ""
    
    for line in lines:
        if line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            channel_name = line.split(',')[-1].strip()
        elif line.startswith("http"):
            txt_lines.append(f"{channel_name},{line.strip()}")
    return txt_lines

def get_url_file_extension(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    return os.path.splitext(path)[1]

# 处理URL订阅
def process_url(url):
    try:
        log("INFO", f"处理订阅URL: {url}")
        with urllib.request.urlopen(url) as response:
            data = response.read().decode('utf-8')
            ext = get_url_file_extension(url)
            if ext in ['.m3u', '.m3u8']:
                return convert_m3u_to_txt(data)
            else:
                return [line.strip() for line in data.split('\n') 
                       if "#genre#" not in line and "," in line and "://" in line]
    except Exception as e:
        log("ERROR", f"处理URL异常: {e}")
        return []

# 高效去重
def remove_duplicates_url(lines):
    seen = set()
    newlines = []
    for line in lines:
        if "," not in line or "://" not in line:
            continue
            
        url = line.split(',', 1)[1].strip()
        if url not in seen:
            seen.add(url)
            newlines.append(line)
    return newlines

# 清理URL
def clean_url(lines):
    newlines = []
    for line in lines:
        if "," not in line or "://" not in line:
            continue
            
        last_dollar = line.rfind('$')
        if last_dollar != -1:
            line = line[:last_dollar]
        newlines.append(line)
    return newlines

# 修正URL拆分
def split_url(lines):
    newlines = []
    for line in lines:
        if "," not in line:
            continue
            
        parts = line.split(',', 1)
        name = parts[0].strip()
        address = parts[1].strip()
        
        if "#" not in address:
            newlines.append(line)
        else:
            urls = address.split('#')
            for url in urls:
                if "://" in url:
                    newlines.append(f"{name},{url.strip()}")
    return newlines

if __name__ == "__main__":
    try:
        timestart = datetime.now()
        log("INFO", "Blacklist2检测开始")
        
        # 订阅URL列表
        urls = [
            'https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/refs/heads/main/%E4%B8%93%E5%8C%BA/%E2%99%AA%E4%BC%98%E8%B4%A8%E5%8D%AB%E8%A7%86.txt'
        ]
        
        # 处理所有订阅URL
        all_lines = []
        url_stats = []
        for url in urls:
            lines = process_url(url)
            url_stats.append(f"{len(lines)},{url}")
            all_lines.extend(lines)
        
        log("INFO", f"初始源数量: {len(all_lines)}")
        
        # 处理流程
        all_lines = split_url(all_lines)
        log("INFO", f"拆分后数量: {len(all_lines)}")
        
        all_lines = clean_url(all_lines)
        log("INFO", f"清理后数量: {len(all_lines)}")
        
        all_lines = remove_duplicates_url(all_lines)
        log("INFO", f"去重后数量: {len(all_lines)}")
        
        # 多线程检测
        results = process_urls_multithreaded(all_lines)
        log("INFO", f"检测完成，有效源: {len(results)}")
        
        # 生成结果
        formatted_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
        output_lines = [f"CheckTime：{formatted_time}"]
        
        for res in results:
            name, url, valid, elapsed, width, height = res
            elapsed_str = f"{elapsed:.1f}ms" if elapsed else "N/A"
            resolution = f"{width}x{height}" if width and height else "N/A"
            output_lines.append(f"{name},{url},{valid},{elapsed_str},{resolution}")
        
        # 写入结果
        current_dir = os.path.dirname(os.path.abspath(__file__))
        result_file = os.path.join(current_dir, 'result.txt')
        write_list(result_file, output_lines)
        log("INFO", f"结果写入: {result_file}")
        
        # 性能统计
        timeend = datetime.now()
        elapsed = timeend - timestart
        log("INFO", f"执行时间: {elapsed.total_seconds():.1f}秒")
        
        for stat in url_stats:
            log("INFO", f"订阅统计: {stat}")
            
    except Exception as e:
        log("ERROR", f"主程序异常: {e}")
        # 确保结果文件存在
        current_dir = os.path.dirname(os.path.abspath(__file__))
        result_file = os.path.join(current_dir, 'result.txt')
        with open(result_file, 'w') as f:
            f.write(f"CheckTime：{datetime.now().strftime('%Y%m%d %H:%M:%S')}\n")
            f.write(f"ERROR：{str(e)}\n")