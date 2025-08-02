import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
import os
from urllib.parse import urlparse
import socket
import subprocess
import random
import json
import shutil

# ====== 全局配置 ======
LOG_LEVEL = "INFO"  # DEBUG/INFO/WARN/ERROR
MAX_WORKERS = 30
CHECK_TIMEOUT = 6
FFPROBE_TIMEOUT = 8
BLACK_HOSTS = ["127.0.0.1:8080", "live3.lalifeier.eu.org", "newcntv.qcloudcdn.com"]
# =====================

def log(level, msg):
    levels = ["DEBUG", "INFO", "WARN", "ERROR"]
    if levels.index(level) >= levels.index(LOG_LEVEL):
        print(f"[{level}] {msg}")

# 随机User-Agent
def get_random_user_agent():
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    ]
    return random.choice(USER_AGENTS)

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

def check_url(url, timeout=CHECK_TIMEOUT):
    start_time = time.time()
    success = False
    width, height = 0, 0
    encoded_url = urllib.parse.quote(url, safe=':/?&=')
    
    try:
        # 检查黑名单主机
        host = get_host_from_url(url)
        if any(black_host in host for black_host in BLACK_HOSTS):
            log("INFO", f"跳过黑名单主机: {host}")
            return False, None, None, None
            
        if url.startswith("http"):
            headers = {'User-Agent': get_random_user_agent()}
            req = urllib.request.Request(encoded_url, headers=headers)
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
        record_host(host)
        
    return success, elapsed_time, width, height

# 协议检测函数保持不变...

def process_line(line):
    if "#genre#" in line or "://" not in line:
        return None, None, None, None, None
        
    parts = line.split(',', 1)
    if len(parts) < 2:
        return None, None, None, None, None
        
    name, url = parts
    url = url.strip()
    success, elapsed, width, height = check_url(url)
    return name.strip(), url, success, elapsed, f"{width}x{height}" if width and height else "N/A"

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

def write_list(file_path, data_list):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        for item in data_list:
            file.write(item + '\n')

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

def process_remote_url(url):
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

def get_host_from_url(url):
    try:
        parsed_url = urlparse(url)
        return parsed_url.netloc
    except Exception as e:
        log("ERROR", f"解析主机失败: {e}")
        return "unknown"

# 使用字典统计blackhost
blacklist_dict = {}
def record_host(host):
    if host:
        blacklist_dict[host] = blacklist_dict.get(host, 0) + 1
        log("INFO", f"记录黑名单主机: {host} (总数: {blacklist_dict[host]})")

def save_blackhost_report(current_dir):
    blackhost_dir = os.path.join(current_dir, "blackhost")
    os.makedirs(blackhost_dir, exist_ok=True)
    
    filename = os.path.join(
        blackhost_dir,
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_blackhost_count.txt"
    )
    
    with open(filename, "w") as file:
        for host, count in sorted(blacklist_dict.items(), key=lambda x: x[1], reverse=True):
            file.write(f"{host}: {count}\n")
    
    log("INFO", f"黑名单统计保存到: {filename}")
    return filename

def create_tv_list(successlist):
    tv_list = []
    for item in successlist:
        if "#genre#" not in item and "," in item and "://" in item:
            parts = item.split(",", 1)
            if len(parts) > 1:
                tv_list.append(parts[1])
    return tv_list

if __name__ == "__main__":
    try:
        timestart = datetime.now()
        log("INFO", "Blacklist1检测开始")
        
        # 订阅URL列表
        urls = [
            "https://gitlab.com/p2v5/wangtv/-/raw/main/lunbo.txt",
            'https://gitlab.com/p2v5/wangtv/-/raw/main/wang-tvlive.txt'
        ]
        
        # 处理所有订阅URL
        all_lines = []
        url_stats = []
        for url in urls:
            lines = process_remote_url(url)
            url_stats.append(f"{len(lines)},{url}")
            all_lines.extend(lines)
        
        log("INFO", f"初始源数量: {len(all_lines)}")
        
        # 添加本地文件源
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        parent2_dir = os.path.dirname(parent_dir)
        
        def read_local_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return [line.strip() for line in file 
                           if "#genre#" not in line and "://" in line and line.strip()]
            except Exception as e:
                log("ERROR", f"读取本地文件失败: {file_path} - {e}")
                return []
        
        xiaoran_file = os.path.join(parent2_dir, 'xiaoran.txt')
        blacklist_file = os.path.join(current_dir, 'blacklist_auto.txt')
        
        all_lines.extend(read_local_file(xiaoran_file))
        all_lines.extend(read_local_file(blacklist_file))
        log("INFO", f"添加本地文件后总数: {len(all_lines)}")
        
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
        version = datetime.now().strftime("%Y%m%d-%H%M%S")
        successlist = []
        blacklist = []
        
        for res in results:
            name, url, success, elapsed, resolution = res
            if success and elapsed:
                successlist.append(f"{elapsed:.1f}ms,{name},{url}")
            else:
                blacklist.append(f"{name},{url}")
        
        # 排序
        successlist = sorted(successlist, key=lambda x: float(x.split("ms")[0]))
        blacklist = sorted(blacklist)
        
        # 添加标题和版本信息
        success_header = ["更新时间,#genre#", version, "", "响应时间,频道名称,URL地址,#genre#"] + successlist
        tv_header = ["更新时间,#genre#", version, "", "频道名称,URL地址,#genre#"] + create_tv_list(successlist)
        black_header = ["更新时间,#genre#", version, "", "频道名称,URL地址,#genre#"] + blacklist
        
        # 写入结果文件
        write_list(os.path.join(current_dir, 'whitelist_auto.txt'), success_header)
        write_list(os.path.join(current_dir, 'whitelist_auto_tv.txt'), tv_header)
        write_list(os.path.join(current_dir, 'blacklist_auto.txt'), black_header)
        
        # 保存历史记录
        history_dir = os.path.join(current_dir, "history", "blacklist")
        os.makedirs(history_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        write_list(os.path.join(history_dir, f"{timestamp}_whitelist_auto.txt"), success_header)
        write_list(os.path.join(history_dir, f"{timestamp}_blacklist_auto.txt"), black_header)
        
        # 保存黑名单统计
        save_blackhost_report(current_dir)
        
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
        for file in ['whitelist_auto.txt', 'whitelist_auto_tv.txt', 'blacklist_auto.txt']:
            with open(os.path.join(current_dir, file), 'w') as f:
                f.write(f"CheckTime：{datetime.now().strftime('%Y%m%d %H:%M:%S')}\n")
                f.write(f"ERROR：{str(e)}\n")