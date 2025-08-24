#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
import argparse
import sys

# ========== 默认配置 ==========
DEFAULT_MAX_WORKERS = 20
DEFAULT_CHECK_TIMEOUT = 6
DEFAULT_FFPROBE_TIMEOUT = 8
DEFAULT_KEEP_LINES = 100
DEFAULT_RETRY_COUNT = 2
DEFAULT_KEEP_PER_NAME = 1
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_SAVE_FAILED = False
DEFAULT_PROTOCOLS = []  # 空代表全部协议

# 默认订阅源URL
DEFAULT_REMOTE_URLS = [
    "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/custom.txt",
    "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/result.txt",
    "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/special/live_special.txt"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
]

# ================================================

def log(level, msg, log_level):
    levels = ["DEBUG", "INFO", "WARN", "ERROR"]
    if levels.index(level) >= levels.index(log_level):
        print(f"[{level}] {msg}")

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def get_video_resolution(video_path, timeout=DEFAULT_FFPROBE_TIMEOUT):
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height', '-of', 'json', video_path
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        video_info = json.loads(result.stdout)
        width = video_info['streams'][0]['width']
        height = video_info['streams'][0]['height']
        return width, height
    except Exception as e:
        log("WARN", f"获取分辨率失败: {e}", "WARN")
        return None, None
def check_rtmp_url(url, timeout=DEFAULT_CHECK_TIMEOUT):
    try:
        result = subprocess.run(['ffprobe', url], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return result.returncode == 0
    except Exception as e:
        log("WARN", f"RTMP检查失败: {e}", "WARN")
        return False

def check_rtp_url(url, timeout=DEFAULT_CHECK_TIMEOUT):
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            s.sendto(b'', (host, port))
            s.recv(1)
        return True
    except Exception as e:
        log("WARN", f"RTP检查失败: {e}", "WARN")
        return False

def check_p3p_url(url, timeout=DEFAULT_CHECK_TIMEOUT):
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port
        path = parsed_url.path
        if not host or not port or not path:
            return False
        with socket.create_connection((host, port), timeout=timeout) as s:
            request = f"GET {path} P3P/1.0\r\nHost: {host}\r\n\r\n"
            s.sendall(request.encode())
            response = s.recv(1024)
            return b"P3P" in response
    except Exception as e:
        log("WARN", f"P3P检查失败: {e}", "WARN")
        return False

def check_p2p_url(url, timeout=DEFAULT_CHECK_TIMEOUT):
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port
        path = parsed_url.path
        if not host or not port or not path:
            return False
        with socket.create_connection((host, port), timeout=timeout) as s:
            request = f"YOUR_CUSTOM_REQUEST {path}\r\nHost: {host}\r\n\r\n"
            s.sendall(request.encode())
            response = s.recv(1024)
            return b"SOME_EXPECTED_RESPONSE" in response
    except Exception as e:
        log("WARN", f"P2P检查失败: {e}", "WARN")
        return False

def check_url(url, timeout=DEFAULT_CHECK_TIMEOUT, log_level="INFO"):
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
            log("WARN", f"不支持的协议: {url}", log_level)

        elapsed_time = (time.time() - start_time) * 1000  # ms
        if success:
            width, height = get_video_resolution(url)
        log("DEBUG", f"Checked {url}: success={success}, time={elapsed_time:.1f}ms, resolution={width}x{height}", log_level)
    except Exception as e:
        log("WARN", f"Exception checking URL {url}: {e}", log_level)
        elapsed_time = None
    return success, elapsed_time, width, height

def process_line(line, timeout, allowed_protocols, log_level):
    if "#genre#" in line or "://" not in line:
        return None
    parts = line.split(',')
    if len(parts) != 2:
        return None
    name, url = parts
    url = url.strip()
    if allowed_protocols:
        proto = url.split(':')[0]
        if proto not in allowed_protocols:
            log("DEBUG", f"跳过协议不允许的URL：{url}", log_level)
            return None
    is_valid, elapsed_time, width, height = check_url(url, timeout, log_level)
    return name.strip(), url, is_valid, elapsed_time, width, height
def write_list(file_path, data_list):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data_list:
            f.write(item + '\n')

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

def process_url(url, urls_all_lines, url_statistics, log_level):
    try:
        log("INFO", f"下载并处理订阅链接: {url}", log_level)
        with urllib.request.urlopen(url) as response:
            data = response.read().decode('utf-8')
            ext = get_url_file_extension(url)
            if ext in ['.m3u', '.m3u8']:
                m3u_lines = convert_m3u_to_txt(data)
                url_statistics.append(f"{len(m3u_lines)},{url}")
                urls_all_lines.extend(m3u_lines)
            elif ext == '.txt':
                lines = data.split('\n')
                url_statistics.append(f"{len(lines)},{url}")
                for line in lines:
                    if "#genre#" not in line and "," in line and "://" in line:
                        urls_all_lines.append(line.strip())
            else:
                lines = data.split('\n')
                url_statistics.append(f"{len(lines)},{url}")
                for line in lines:
                    if "#genre#" not in line and "," in line and "://" in line:
                        urls_all_lines.append(line.strip())
    except Exception as e:
        log("ERROR", f"处理URL时发生错误：{e}", log_level)

def remove_duplicates(lines):
    seen = set()
    new_lines = []
    for line in lines:
        if "," in line and "://" in line:
            url = line.split(',', 1)[1].strip()
            if url not in seen:
                seen.add(url)
                new_lines.append(line)
    return new_lines

def clean_url(lines):
    new_lines = []
    for line in lines:
        if "," in line and "://" in line:
            last_dollar = line.rfind('$')
            if last_dollar != -1:
                line = line[:last_dollar]
            new_lines.append(line)
    return new_lines

def split_url(lines):
    new_lines = []
    for line in lines:
        if "," not in line:
            continue
        channel_name, channel_address = line.split(',', 1)
        if "#" not in channel_address:
            new_lines.append(line)
        else:
            url_list = channel_address.split('#')
            for url in url_list:
                if "://" in url:
                    new_lines.append(f"{channel_name},{url}")
    return new_lines

def process_urls_multithreaded(lines, threads, timeout, allowed_protocols, log_level):
    results = []
    if not lines:
        return results
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(process_line, line, timeout, allowed_protocols, log_level): line for line in lines}
        for future in as_completed(futures):
            try:
                res = future.result()
                if res:
                    results.append(res)
            except Exception as e:
                log("WARN", f"线程执行异常: {e}", log_level)
    return results

def filter_keep_per_name(results, keep_per_name):
    kept = []
    name_count = {}
    for r in results:
        name = r[0]
        if name not in name_count:
            name_count[name] = 0
        if name_count[name] < keep_per_name:
            kept.append(r)
            name_count[name] += 1
    return kept
def parse_args():
    parser = argparse.ArgumentParser(description="IPTV直播源检测脚本，支持远程订阅和本地文件")
    parser.add_argument('--file', type=str, default="output/full.txt", help="本地输入直播源文件路径")
    parser.add_argument('--urls', type=str, default="", help="远程订阅URL列表，逗号分隔，优先级高于--file")
    parser.add_argument('--output', type=str, default="result.txt", help="检测结果输出文件路径（默认与脚本同目录）")
    parser.add_argument('--threads', type=int, default=DEFAULT_MAX_WORKERS, help="检测线程数")
    parser.add_argument('--timeout', type=int, default=DEFAULT_CHECK_TIMEOUT, help="请求超时时间（秒）")
    parser.add_argument('--retry', type=int, default=DEFAULT_RETRY_COUNT, help="最大重试次数")
    parser.add_argument('--protocol', type=str, default="", help="允许协议列表，逗号分隔，空代表全部")
    parser.add_argument('--save_failed', type=str, default=str(DEFAULT_SAVE_FAILED), help="是否保存失败源，true/false")
    parser.add_argument('--keep_per_name', type=int, default=DEFAULT_KEEP_PER_NAME, help="同名称直播源保留条数")
    parser.add_argument('--log_level', type=str, default=DEFAULT_LOG_LEVEL, help="日志等级 DEBUG/INFO/WARN/ERROR")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # 获取脚本所在目录（确保输出路径正确）
    script_dir = os.path.dirname(os.path.abspath(__file__))  # 脚本所在目录
    output_file = os.path.join(script_dir, args.output)      # 输出文件路径

    input_file = args.file
    max_workers = args.threads
    timeout = args.timeout
    max_retry = args.retry
    allowed_protocols = [p.strip() for p in args.protocol.split(',')] if args.protocol.strip() else []
    save_failed = args.save_failed.lower() == "true"
    keep_per_name = args.keep_per_name
    log_level = args.log_level.upper()
    
    # 处理订阅URL
    if args.urls.strip():
        remote_urls = [u.strip() for u in args.urls.split(',')]
    else:
        remote_urls = DEFAULT_REMOTE_URLS

    log("INFO", f"参数：输入文件={input_file}, 远程订阅={remote_urls}, 输出文件={output_file}", log_level)
    log("INFO", f"线程数={max_workers}, 超时={timeout}s, 重试={max_retry}, 协议过滤={allowed_protocols if allowed_protocols else '全部'}, 保存失败源={save_failed}, 同名保留={keep_per_name}, 日志等级={log_level}", log_level)

    urls_all_lines = []
    url_statistics = []

    # 远程订阅处理（失败不终止）
    if remote_urls:
        for url in remote_urls:
            for _ in range(max_retry):
                process_url(url, urls_all_lines, url_statistics, log_level)
                if urls_all_lines:
                    break
                log("WARN", f"重试下载远程订阅: {url}", log_level)

    # 本地文件处理（不存在则跳过）
    if not remote_urls or not urls_all_lines:
        if os.path.exists(input_file):
            try:
                with open(input_file, encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                    urls_all_lines.extend(lines)
                log("INFO", f"读取本地文件: {input_file}", log_level)
            except Exception as e:
                log("ERROR", f"读取本地文件失败: {e}", log_level)
        else:
            log("WARN", f"本地文件不存在: {input_file}，跳过", log_level)

    # ========== 记录各阶段行数 ==========
    urls_hj_before = len(urls_all_lines)  # 初始总行数（远程+本地合并后）
    
    urls_all_lines = split_url(urls_all_lines)
    urls_hj_before2 = len(urls_all_lines)  # 拆分#后行数
    
    urls_all_lines = clean_url(urls_all_lines)
    urls_hj_before3 = len(urls_all_lines)  # 去$后行数
    
    urls_all_lines = remove_duplicates(urls_all_lines)
    urls_hj = len(urls_all_lines)  # 去重后最终行数

    # ========== 检测准备汇总日志 ==========
    print("\n================ 检测准备汇总 ================")
    print(f"  初始总行数（远程+本地文件）: {urls_hj_before}")
    print(f"  拆分#后行数: {urls_hj_before2}")
    print(f"  去$后行数: {urls_hj_before3}")
    print(f"  去重后行数（最终待检测URL数）: {urls_hj}")
    print(f"  并发线程数: {max_workers}")
    print("==============================================\n")

    # 多线程检测
    results = process_urls_multithreaded(urls_all_lines, max_workers, timeout, allowed_protocols, log_level)
    log("INFO", f"检测完成: {len(results)} 条", log_level)

    if not save_failed:
        results = [r for r in results if r[2] is True]
        log("INFO", f"保留成功源: {len(results)}", log_level)

    results = filter_keep_per_name(results, keep_per_name)
    log("INFO", f"同名保留后: {len(results)}", log_level)

    if len(results) > DEFAULT_KEEP_LINES:
        results = results[:DEFAULT_KEEP_LINES]

    # 生成输出内容
    formatted_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
    output_lines = [f"CheckTime：{formatted_time}"]
    for name, url, valid, elapsed, w, h in results:
        elapsed_str = f"{elapsed:.1f}" if elapsed else "N/A"
        resolution = f"{w}x{h}" if w and h else "N/A"
        output_lines.append(f"{name},{url}${valid}${elapsed_str}ms${resolution}")

    # 写入输出文件（确保目录存在）
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in output_lines:
            f.write(line + '\n')
    log("INFO", f"结果写入: {os.path.abspath(output_file)}", log_level)  # 打印绝对路径确认位置

    for stat in url_statistics:
        log("INFO", f"订阅统计: {stat}", log_level)


if __name__ == "__main__":
    main()
