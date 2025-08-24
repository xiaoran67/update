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
import traceback
from collections import defaultdict

# 全局变量声明：解决作用域错误
runtime_stats = []  # 新增全局初始化

# 路径配置：定义所有输出文件和目录的位置
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # 脚本所在目录
RESULT_PATH = os.path.join(CURRENT_DIR, "result.txt")  # 检测总览结果文件
WHITELIST_PATH = os.path.join(CURRENT_DIR, "whitelist_auto.txt")  # 可用源列表
BLACKLIST_PATH = os.path.join(CURRENT_DIR, "blacklist_auto.txt")  # 不可用源列表
TV_LIST_PATH = os.path.join(CURRENT_DIR, "whitelist_auto_tv.txt")  # 电视专用可用列表
HISTORY_DIR = os.path.join(CURRENT_DIR, "history/blacklist")  # 历史记录存档目录
BLACKHOST_DIR = os.path.join(CURRENT_DIR, "blackhost")  # 故障主机统计目录

# 基础配置参数：控制脚本运行的核心参数
DEFAULT_MAX_WORKERS = 30  # 并发检测线程数量
DEFAULT_CHECK_TIMEOUT = 6  # 检测超时时间（秒）
DEFAULT_FFPROBE_TIMEOUT = 8  # 视频分辨率检测超时时间（秒）
DEFAULT_RETRY_COUNT = 2  # 远程订阅下载重试次数
DEFAULT_LOG_LEVEL = "INFO"  # 默认日志等级
DEFAULT_KEEP_PER_NAME = 1  # 同名频道保留数量
DEFAULT_KEEP_LINES = 100  # 结果最大行数限制
DEFAULT_SAVE_FAILED = False  # 是否保存失败源

# 示例黑名单主机（仅展示，不用于过滤）
BLACK_HOSTS = ["127.0.0.1:8080", "live3.lalifeier.eu.org", "newcntv.qcloudcdn.com"]

# 浏览器请求头列表：模拟正常访问
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
]


# 日志输出函数：按等级输出运行日志（同时收集统计）
def log(level, msg, log_level=DEFAULT_LOG_LEVEL):
    levels = ["DEBUG", "INFO", "WARN", "ERROR"]
    if levels.index(level) >= levels.index(log_level):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {msg}"
        print(log_msg)
        # 收集INFO及以上等级的日志到统计列表
        if levels.index(level) >= levels.index("INFO"):
            runtime_stats.append(log_msg)


# 获取随机浏览器请求头
def get_random_user_agent():
    return random.choice(USER_AGENTS)


# 获取视频分辨率：通过ffprobe工具解析视频信息
def get_video_resolution(video_path):
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height', '-of', 'json', video_path
    ]
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=DEFAULT_FFPROBE_TIMEOUT
        )
        if not result.stdout:
            log("WARN", f"ffprobe无输出: {video_path}", "WARN")
            return None, None
        video_info = json.loads(result.stdout)
        if not video_info.get('streams'):
            log("WARN", f"无视频流: {video_path}", "WARN")
            return None, None
        return video_info['streams'][0]['width'], video_info['streams'][0]['height']
    except Exception as e:
        log("WARN", f"获取分辨率失败: {e}", "WARN")
        return None, None


# 协议检测函数：检测不同类型的流媒体协议是否可用
def check_rtmp_url(url):
    # 检测RTMP/RTSP协议流
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=DEFAULT_CHECK_TIMEOUT
        )
        return result.returncode == 0  # 0表示检测成功
    except Exception as e:
        log("WARN", f"RTMP检测失败: {e}", "WARN")
        return False


def check_rtp_url(url):
    # 检测RTP协议流
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port
        if not host or not port:
            log("WARN", f"RTP URL格式无效: {url}", "WARN")
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(DEFAULT_CHECK_TIMEOUT)
            s.connect((host, port))
            s.sendto(b'ping', (host, port))
            s.recv(1024)
        return True
    except Exception as e:
        log("WARN", f"RTP检测失败: {e}", "WARN")
        return False


def check_p3p_url(url):
    # 检测P3P协议流
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or 80
        path = parsed_url.path or "/"
        if not host:
            log("WARN", f"P3P URL格式无效: {url}", "WARN")
            return False
        with socket.create_connection((host, port), DEFAULT_CHECK_TIMEOUT) as s:
            request = (
                f"GET {path} P3P/1.0\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: {get_random_user_agent()}\r\n"
                f"Connection: close\r\n\r\n"
            )
            s.sendall(request.encode())
            response = s.recv(1024)
            return b"P3P" in response
    except Exception as e:
        log("WARN", f"P3P检测失败: {e}", "WARN")
        return False


def check_p2p_url(url):
    # 检测P2P协议流
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or 443
        path = parsed_url.path or "/"
        if not host:
            log("WARN", f"P2P URL格式无效: {url}", "WARN")
            return False
        with socket.create_connection((host, port), DEFAULT_CHECK_TIMEOUT) as s:
            request = f"P2P_PROBE {path}\r\nHost: {host}\r\n\r\n"
            s.sendall(request.encode())
            response = s.recv(1024)
            return len(response) > 0  # 有响应则有效
    except Exception as e:
        log("WARN", f"P2P检测失败: {e}", "WARN")
        return False


# 从URL中提取主机地址
def get_host_from_url(url):
    try:
        return urlparse(url).netloc
    except Exception as e:
        log("ERROR", f"解析主机失败: {e}", "ERROR")
        return "unknown"


# 故障主机统计：记录所有检测失败的主机及次数
blacklist_dict = defaultdict(int)  # 存储主机:失败次数

def record_host(host):
    # 记录失败主机（所有失败主机均统计）
    blacklist_dict[host] += 1
    log("INFO", f"黑名单主机统计: {host} (累计: {blacklist_dict[host]})", "INFO")


# 统一URL检测入口：根据协议类型调用对应检测函数
def check_url(url, log_level):
    start_time = time.time()
    success = False
    width, height = None, None
    host = get_host_from_url(url)

    try:
        # 根据URL协议选择检测方式
        if url.startswith(("http://", "https://")):
            headers = {'User-Agent': get_random_user_agent()}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=DEFAULT_CHECK_TIMEOUT) as response:
                success = 200 <= response.status < 300  # HTTP 2xx状态码视为成功
        elif url.startswith(("rtmp://", "rtsp://")):
            success = check_rtmp_url(url)
        elif url.startswith("rtp://"):
            success = check_rtp_url(url)
        elif url.startswith("p3p://"):
            success = check_p3p_url(url)
        elif url.startswith("p2p://"):
            success = check_p2p_url(url)
        else:
            log("WARN", f"不支持的协议: {url.split(':')[0]}", log_level)
            return False, None, None, None

        # 计算耗时并尝试获取分辨率
        elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
        if success:
            width, height = get_video_resolution(url)
        log("DEBUG", f"检测 {url[:50]}: 成功={success}, 耗时={elapsed_time:.1f}ms, 分辨率={width}x{height}", log_level)
        return success, elapsed_time, width, height

    except Exception as e:
        log("WARN", f"检测异常 {url[:50]}: {e}", log_level)
        elapsed_time = None
        record_host(host)  # 检测失败时记录主机
        return False, elapsed_time, None, None


# 处理单条直播源：解析格式并调用检测函数
def process_line(line, allowed_protocols, log_level):
    if "#genre#" in line or "://" not in line:
        return None  # 跳过无效行

    # 拆分频道名和URL（兼容名称含逗号的情况）
    parts = line.split(',', 1)
    if len(parts) < 2:
        log("DEBUG", f"无效格式行: {line[:50]}", log_level)
        return None
    name, url = parts
    name = name.strip()
    url = url.strip().split('#')[0]  # 清理URL中的#参数

    # 协议过滤（如果指定了允许的协议）
    if allowed_protocols:
        proto = url.split(':')[0]
        if proto not in allowed_protocols:
            log("DEBUG", f"跳过协议不允许的URL: {url}", log_level)
            return None

    # 执行检测并返回结果
    success, elapsed_time, width, height = check_url(url, log_level)
    return name, url, success, elapsed_time, width, height


# 多线程检测直播源：提高检测效率
def process_urls_multithreaded(lines, max_workers, allowed_protocols, log_level):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有检测任务
        futures = {executor.submit(process_line, line, allowed_protocols, log_level): line for line in lines}
        # 获取检测结果
        for future in as_completed(futures):
            try:
                res = future.result()
                if res:
                    results.append(res)
            except Exception as e:
                log("ERROR", f"线程执行异常: {traceback.format_exc().splitlines()[-1]}", log_level)
    return results


# 数据清洗函数：处理直播源格式，确保检测准确性
def split_url(lines):
    # 拆分#分隔的多个URL
    new_lines = []
    for line in lines:
        if "," not in line:
            continue
        name_part, url_part = line.split(',', 1)
        name = name_part.strip()
        for url in url_part.split('#'):
            url = url.strip()
            if "://" in url:
                new_lines.append(f"{name},{url}")
    log("INFO", f"拆分#完成: 原{len(lines)}条 → 新{len(new_lines)}条", "INFO")
    return new_lines


def clean_url(lines):
    # 清理URL中$后的冗余参数
    new_lines = []
    for line in lines:
        if "," in line and "://" in line:
            last_dollar = line.rfind('$')
            if last_dollar != -1:
                line = line[:last_dollar]
            new_lines.append(line)
    log("INFO", f"清理$完成: 原{len(lines)}条 → 新{len(new_lines)}条", "INFO")
    return new_lines


def remove_duplicates(lines):
    # 去重URL，保留唯一直播源
    seen = set()
    new_lines = []
    for line in lines:
        if "," in line and "://" in line:
            url = line.split(',', 1)[1].strip().split('#')[0]  # 标准化URL
            if url not in seen:
                seen.add(url)
                new_lines.append(line)
    log("INFO", f"去重完成: 原{len(lines)}条 → 新{len(new_lines)}条", "INFO")
    return new_lines


# 输入处理函数：加载并解析直播源（远程订阅+本地文件）
def convert_m3u_to_txt(m3u_content):
    # 将M3U格式转换为"频道名,URL"格式
    lines = m3u_content.split('\n')
    txt_lines = []
    channel_name = "未知频道"  # 默认频道名
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTM3U"):
            continue  # 跳过M3U头
        if line.startswith("#EXTINF"):
            # 提取EXTINF中的频道名
            channel_name = line.split(',')[-1].strip() or channel_name
        elif line.startswith(("http", "rtmp", "rtsp", "p2p", "p3p")):
            # 添加频道名和URL
            txt_lines.append(f"{channel_name},{line}")
    return txt_lines


def get_url_file_extension(url):
    # 获取URL的文件扩展名（用于判断是否为M3U格式）
    parsed_url = urlparse(url)
    return os.path.splitext(parsed_url.path)[1].lower()


def process_remote_url(url, retry_count, log_level):
    # 下载远程订阅并解析为直播源列表（支持重试）
    for retry in range(retry_count + 1):
        try:
            log("INFO", f"下载订阅 (重试{retry}/{retry_count}): {url}", log_level)
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read().decode('utf-8', errors='replace')  # 容错编码
                ext = get_url_file_extension(url)
                if ext in ['.m3u', '.m3u8']:
                    # M3U格式转换为TXT
                    return convert_m3u_to_txt(data)
                else:
                    # 直接提取含URL的行
                    return [
                        line.strip() for line in data.split('\n')
                        if "#genre#" not in line and "," in line and "://" in line
                    ]
        except Exception as e:
            log("WARN", f"订阅下载失败 (重试{retry}/{retry_count}): {e}", log_level)
            if retry == retry_count:
                return []  # 重试次数用尽返回空
            time.sleep(1)  # 重试间隔
    return []


def read_local_files(files, log_level):
    # 读取本地文件中的直播源
    lines = []
    for file in files:
        file_path = os.path.join(CURRENT_DIR, file.strip())
        if not os.path.exists(file_path):
            log("WARN", f"本地文件不存在: {file_path}", log_level)
            continue
        with open(file_path, 'r', encoding='utf-8') as f:
            # 过滤有效行（不含#genre#、含://、非空）
            lines.extend([
                line.strip() for line in f
                if "#genre#" not in line and "://" in line and line.strip()
            ])
    log("INFO", f"本地文件加载完成: {len(lines)}条", log_level)
    return lines


# 输出处理函数：保存检测结果到文件
def write_list(file_path, data_list):
    # 通用文件写入函数（确保目录存在）
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data_list:
            f.write(item + '\n')
    log("INFO", f"写入文件: {file_path} (共{len(data_list)}行)", "INFO")


def save_blackhost_report():
    # 保存故障主机统计（空数据时生成占位文件）
    os.makedirs(BLACKHOST_DIR, exist_ok=True)  # 确保目录存在
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(BLACKHOST_DIR, f"{timestamp}_blackhost_count.txt")
    
    with open(filename, "w", encoding='utf-8') as f:
        if blacklist_dict:
            # 有数据时写入主机和失败次数（按次数排序）
            for host, count in sorted(blacklist_dict.items(), key=lambda x: -x[1]):
                f.write(f"{host}: {count}\n")
        else:
            # 无数据时写入占位文本，避免目录为空
            f.write("# 本次检测无黑名单主机统计\n")
    log("INFO", f"黑名单统计保存至: {filename}", "INFO")


def create_tv_list(success_results):
    # 生成电视专用可用源列表（仅含频道名和URL）
    tv_list = []
    for res in success_results:
        name, url = res[0], res[1]
        tv_list.append(f"{name},{url}")
    return tv_list


def save_history(whitelist, blacklist):
    # 保存历史记录（白名单和黑名单）
    os.makedirs(HISTORY_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 保存历史白名单
    write_list(os.path.join(HISTORY_DIR, f"{timestamp}_whitelist_auto.txt"), whitelist)
    # 保存历史黑名单
    write_list(os.path.join(HISTORY_DIR, f"{timestamp}_blacklist_auto.txt"), blacklist)


def filter_keep_per_name(results, keep_per_name):
    # 同名频道保留指定数量（去重同名源）
    kept = []
    name_count = defaultdict(int)  # 记录每个频道名的保留数量
    for r in results:
        name = r[0]
        if name_count[name] < keep_per_name:
            kept.append(r)
            name_count[name] += 1
    return kept


# 命令行参数解析：支持自定义脚本运行参数
def parse_args():
    parser = argparse.ArgumentParser(description="直播源检测工具")
    parser.add_argument('--urls', type=str, default="", help="远程订阅URL（逗号分隔）")
    parser.add_argument('--local-files', type=str, default="blacklist_auto.txt", help="本地文件路径（逗号分隔）")
    parser.add_argument('--threads', type=int, default=DEFAULT_MAX_WORKERS, help="并发线程数")
    parser.add_argument('--timeout', type=int, default=DEFAULT_CHECK_TIMEOUT, help="检测超时时间（秒）")
    parser.add_argument('--retry', type=int, default=DEFAULT_RETRY_COUNT, help="订阅下载重试次数")
    parser.add_argument('--protocol', type=str, default="", help="允许的协议（逗号分隔，如http,rtmp）")
    parser.add_argument('--save-failed', type=bool, default=DEFAULT_SAVE_FAILED, help="是否保存失败源（true/false）")
    parser.add_argument('--keep-per-name', type=int, default=DEFAULT_KEEP_PER_NAME, help="同名频道保留数量")
    parser.add_argument('--keep-lines', type=int, default=DEFAULT_KEEP_LINES, help="结果最大行数限制")
    parser.add_argument('--log-level', type=str, default=DEFAULT_LOG_LEVEL, help="日志等级（DEBUG/INFO/WARN/ERROR）")
    return parser.parse_args()


# 主函数：串联整个检测流程
def main():
    global runtime_stats  # 明确全局引用（此处可省略，因为已全局初始化，但保留增强可读性）
    runtime_stats = [f"===== 检测开始: {datetime.now().strftime('%Y%m%d %H:%M:%S')} ====="]  # 初始化统计
    
    args = parse_args()  # 解析命令行参数
    log_level = args.log_level.upper()
    allowed_protocols = [p.strip() for p in args.protocol.split(',')] if args.protocol else []  # 允许的协议列表
    start_time = datetime.now()  # 记录开始时间

    # 1. 加载直播源（远程订阅+本地文件）
    all_lines = []  # 存储所有待检测的直播源
    url_stats = []  # 记录各订阅的直播源数量

    # 加载远程订阅（默认使用预设URL，支持通过参数自定义）
    remote_urls = [u.strip() for u in args.urls.split(',')] if args.urls.strip() else [
        "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/freetv/freetv_output.txt",
        "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/freetv/freetv_output_cctv.txt",
        "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/freetv/freetv_output_ws.txt",
        "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/freetv/freetv_output_other.txt",
        "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/full.txt",
        "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/result.txt"
    ]
    runtime_stats.append(f"远程订阅列表: {remote_urls}")  # 收集远程URL列表
    for url in remote_urls:
        lines = process_remote_url(url, args.retry, log_level)  # 下载并解析订阅
        url_stats.append(f"{len(lines)},{url}")  # 记录订阅统计
        all_lines.extend(lines)
    log("INFO", f"远程订阅加载完成: {len(all_lines)}条", log_level)

    # 加载本地文件（默认加载blacklist_auto.txt）
    if args.local_files:
        local_files = args.local_files.split(',')
        runtime_stats.append(f"本地文件列表: {local_files}")  # 收集本地文件列表
        all_lines.extend(read_local_files(local_files, log_level))
    log("INFO", f"总初始行数: {len(all_lines)}", log_level)

    # 2. 数据清洗（拆分#参数、清理$参数、去重）
    initial_count = len(all_lines)
    all_lines = split_url(all_lines)
    split_count = len(all_lines)
    all_lines = clean_url(all_lines)
    clean_count = len(all_lines)
    all_lines = remove_duplicates(all_lines)
    dedup_count = len(all_lines)
    # 收集清洗统计
    runtime_stats.extend([
        f"数据清洗统计: 初始={initial_count} → 拆分#后={split_count} → 清理$后={clean_count} → 去重后={dedup_count}",
        f"清洗后待检测行数: {dedup_count}"
    ])

    # 3. 多线程检测直播源
    runtime_stats.append(f"开始多线程检测: 线程数={args.threads}, 待检测行数={dedup_count}")
    results = process_urls_multithreaded(
        all_lines, args.threads, allowed_protocols, log_level
    )
    log("INFO", f"检测完成: 总结果{len(results)}条", log_level)

    # 4. 结果过滤（同名源保留、分离成功/失败源、行数限制）
    results = filter_keep_per_name(results, args.keep_per_name)  # 同名源保留
    kept_count = len(results)
    runtime_stats.append(f"同名源保留后行数: {kept_count}")
    
    success_results = [r for r in results if r[2]]  # 成功源
    failed_results = [r for r in results if not r[2]]  # 失败源
    runtime_stats.append(f"检测结果: 成功={len(success_results)}条, 失败={len(failed_results)}条")
    
    if not args.save_failed:
        results = success_results  # 不保存失败源时仅保留成功源
    
    # 限制结果最大行数
    if len(results) > args.keep_lines:
        results = results[:args.keep_lines]
        runtime_stats.append(f"结果行数超限({len(results)} > {args.keep_lines})，已截断")
    log("INFO", f"最终结果行数: {len(results)}", log_level)

    # 5. 保存所有检测结果
    version = datetime.now().strftime("%Y%m%d-%H%M%S")  # 版本时间戳
    formatted_time = datetime.now().strftime("%Y%m%d %H:%M:%S")  # 格式化时间
    runtime_stats.append(f"结果生成时间: {formatted_time}")  # 收集生成时间

    # 保存白名单、电视白名单、黑名单
    whitelist_lines = [
        "更新时间,#genre#", version, "", "响应时间,频道名称,URL地址,#genre#"
    ] + [f"{r[3]:.1f}ms,{r[0]},{r[1]}" for r in success_results if r[3]]
    tv_lines = [
        "更新时间,#genre#", version, "", "频道名称,URL地址,#genre#"
    ] + create_tv_list(success_results)
    blacklist_lines = [
        "更新时间,#genre#", version, "", "频道名称,URL地址,#genre#"
    ] + [f"{r[0]},{r[1]}" for r in failed_results]
    
    write_list(WHITELIST_PATH, whitelist_lines)
    write_list(TV_LIST_PATH, tv_lines)
    write_list(BLACKLIST_PATH, blacklist_lines)
    runtime_stats.extend([  # 收集结果文件路径
        f"白名单文件: {WHITELIST_PATH} (行数={len(whitelist_lines)})",
        f"电视白名单文件: {TV_LIST_PATH} (行数={len(tv_lines)})",
        f"黑名单文件: {BLACKLIST_PATH} (行数={len(blacklist_lines)})"
    ])

    # 保存检测总览结果
    result_lines = [f"CheckTime：{formatted_time}"] + [
        f"{r[0]},{r[1]},{r[2]},{f'{r[3]:.1f}ms' if r[3] else 'N/A'},{f'{r[4]}x{r[5]}' if r[4] and r[5] else 'N/A'}"
        for r in results
    ]
    write_list(RESULT_PATH, result_lines)
    runtime_stats.append(f"总览结果文件: {RESULT_PATH} (行数={len(result_lines)})")

    # 保存历史记录和故障主机统计
    save_history(whitelist_lines, blacklist_lines)
    save_blackhost_report()
    runtime_stats.append("历史记录和故障主机统计已保存")

    # 6. 输出统计信息
    elapsed_total = (datetime.now() - start_time).total_seconds()  # 总耗时
    minutes = int(elapsed_total // 60)
    seconds = int(elapsed_total % 60)
    runtime_stats.extend([  # 收集时间统计
        f"总执行时间: {minutes}分{seconds}秒",
        f"开始时间: {start_time.strftime('%Y%m%d %H:%M:%S')}",
        f"结束时间: {datetime.now().strftime('%Y%m%d %H:%M:%S')}"
    ])
    for stat in url_stats:
        log("INFO", f"订阅统计: {stat}", log_level)

    # 生成URL统计日志文件（包含所有运行时统计）
    stats_file = os.path.join(CURRENT_DIR, 'url_statistics.log')
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write(f"# 完整检测统计日志\n")
        f.write(f"# 生成时间: {datetime.now().strftime('%Y%m%d %H:%M:%S')}\n")
        f.write(f"# 总执行时间: {minutes}分{seconds}秒\n\n")
        f.write("\n".join(runtime_stats))  # 写入所有收集的统计
        f.write("\n\n# 远程订阅详细统计:\n")
        if url_stats:
            f.write("\n".join(url_stats))
        else:
            f.write("# 本次检测无远程订阅统计数据\n")
    log("INFO", f"URL统计日志已保存到: {stats_file}")


# 脚本入口：捕获异常并生成错误记录
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
        error_msg = f"主程序异常: {traceback.format_exc()}"
        log("ERROR", error_msg, "ERROR")
        
        # 收集异常统计
        runtime_stats.append(f"\n===== 检测异常: {error_time} =====")
        runtime_stats.append(f"错误原因: {str(e)}")
        runtime_stats.append(f"堆栈信息: {traceback.format_exc()}")
        
        # 异常时生成错误文件（覆盖关键输出）
        error_lines = [f"CheckTime：{error_time}", f"ERROR：{str(e)}"]
        for path in [WHITELIST_PATH, TV_LIST_PATH, BLACKLIST_PATH, RESULT_PATH]:
            write_list(path, error_lines)
        
        # 异常时生成URL统计日志（包含异常前统计）
        stats_file = os.path.join(CURRENT_DIR, 'url_statistics.log')
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write(f"# 异常检测统计日志\n")
            f.write(f"# 异常时间: {error_time}\n")
            f.write(f"# 错误原因: {str(e)}\n\n")
            f.write("\n".join(runtime_stats))  # 写入异常前收集的统计
        log("ERROR", f"异常时URL统计日志已保存到: {stats_file}")
