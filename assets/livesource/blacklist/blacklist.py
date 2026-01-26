import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
import os
from urllib.parse import urlparse
import socket
import subprocess
import traceback

timestart = datetime.now()
BlackHost = ["127.0.0.1:8080", "live3.lalifeier.eu.org", "newcntv.qcloudcdn.com"]

# 新增：全局列表收集所有运行时统计信息
runtime_stats = []

def read_txt_file(file_path):
    skip_strings = ['#genre#']
    required_strings = ['://']
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = [
            line for line in file
            if not any(skip_str in line for skip_str in skip_strings) and all(req_str in line for req_str in required_strings)
        ]
    return lines

def check_url(url, timeout=6):
    start_time = time.time()
    elapsed_time = None
    success = False
    encoded_url = urllib.parse.quote(url, safe=':/?&=')
    try:
        if url.startswith("http"):
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
            req = urllib.request.Request(encoded_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    success = True
        elif url.startswith("p3p"):
            success = check_p3p_url(url, timeout)
        elif url.startswith("p2p"):
            success = check_p2p_url(url, timeout)        
        elif url.startswith("rtmp") or url.startswith("rtsp"):
            success = check_rtmp_url(url, timeout)
        elif url.startswith("rtp"):
            success = check_rtp_url(url, timeout)
        elapsed_time = (time.time() - start_time) * 1000
    except Exception as e:
        print(f"Error checking {url}: {e}")
        record_host(get_host_from_url(url))
        elapsed_time = None
    return elapsed_time, success

def check_rtmp_url(url, timeout):
    try:
        result = subprocess.run(['ffprobe', url], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Error checking {url}: {e}")
    return False

def check_rtp_url(url, timeout):
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
    except (socket.timeout, socket.error):
        return False

def check_p3p_url(url, timeout):
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or (80 if parsed_url.scheme == "http" else 443)
        path = parsed_url.path or "/"
        if not host or not port or not path:
            raise ValueError("Invalid p3p URL")
        with socket.create_connection((host, port), timeout=timeout) as s:
            request = (
                f"GET {path} P3P/1.0\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: CustomClient/1.0\r\n"
                f"Connection: close\r\n\r\n"
            )
            s.sendall(request.encode())
            response = s.recv(1024)
            return b"P3P" in response
    except Exception as e:
        print(f"Error checking {url}: {e}")
    return False

def check_p2p_url(url, timeout):
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port
        path = parsed_url.path
        if not host or not port or not path:
            raise ValueError("Invalid P2P URL")
        with socket.create_connection((host, port), timeout=timeout) as s:
            request = f"YOUR_CUSTOM_REQUEST {path}\r\nHost: {host}\r\n\r\n"
            s.sendall(request.encode())
            response = s.recv(1024)
            return b"SOME_EXPECTED_RESPONSE" in response
    except Exception as e:
        print(f"Error checking {url}: {e}")
    return False

def process_line(line):
    if "#genre#" in line or "://" not in line:
        return None, None
    parts = line.split(',')
    if len(parts) == 2:
        name, url = parts
        elapsed_time, is_valid = check_url(url.strip())
        if is_valid:
            return elapsed_time, line.strip()
        else:
            return None, line.strip()
    return None, None

def process_urls_multithreaded(lines, max_workers=30):
    blacklist = [] 
    successlist = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_line, line): line for line in lines}
        for future in as_completed(futures):
            elapsed_time, result = future.result()
            if result:
                if elapsed_time is not None:
                    successlist.append(f"{elapsed_time:.2f}ms,{result}")
                else:
                    blacklist.append(result)
    return successlist, blacklist

def write_list(file_path, data_list):
    with open(file_path, 'w', encoding='utf-8') as file:
        for item in data_list:
            file.write(item + '\n')

def get_url_file_extension(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    return os.path.splitext(path)[1]

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

def process_url(url):
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
            text = data.decode('utf-8')
            if get_url_file_extension(url) in [".m3u", ".m3u8"]:
                m3u_lines = convert_m3u_to_txt(text)
                stats = f"{len(m3u_lines)},{url.strip()}"
                url_statistics.append(stats)
                runtime_stats.append(f"远程订阅统计: {stats}")  # 收集统计
                urls_all_lines.extend(m3u_lines)
            elif get_url_file_extension(url) == ".txt":
                lines = text.split('\n')
                valid_lines = [line.strip() for line in lines if "#genre#" not in line and "," in line and "://" in line]
                stats = f"{len(valid_lines)},{url.strip()}"
                url_statistics.append(stats)
                runtime_stats.append(f"远程订阅统计: {stats}")  # 收集统计
                urls_all_lines.extend(valid_lines)
    except Exception as e:
        err_msg = f"处理URL[{url}]失败: {e}"
        print(err_msg)
        runtime_stats.append(err_msg)  # 收集错误统计

def remove_duplicates_url(lines):
    urls = []
    newlines = []
    for line in lines:
        if "," in line and "://" in line:
            channel_url = line.split(',')[1].strip()
            if channel_url not in urls:
                urls.append(channel_url)
                newlines.append(line)
    return newlines

def clean_url(lines):
    newlines = []
    for line in lines:
        if "," in line and "://" in line:
            last_dollar_index = line.rfind('$')
            if last_dollar_index != -1:
                line = line[:last_dollar_index]
            newlines.append(line)
    return newlines

def split_url(lines):
    newlines = []
    for line in lines:
        if "," in line:
            channel_name, channel_address = line.split(',', 1)
            if "#" not in channel_address:
                newlines.append(line)
            elif "#" in channel_address and "://" in channel_address:
                url_list = channel_address.split('#')
                for url in url_list:
                    if "://" in url:
                        newlines.append(line)
    return newlines

def get_host_from_url(url: str) -> str:
    try:
        parsed_url = urlparse(url)
        return parsed_url.netloc
    except Exception as e:
        return f"Error: {str(e)}"

blacklist_dict = {}
def record_host(host):
    if host in blacklist_dict:
        blacklist_dict[host] += 1
    else:
        blacklist_dict[host] = 1

if __name__ == "__main__":
    urls_all_lines = []
    url_statistics = []
    runtime_stats.append(f"===== 检测开始: {timestart.strftime('%Y%m%d %H:%M:%S')} =====")  # 初始统计

    try:
        # 远程订阅URL处理
        urls = [
            "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/full.txt",
            "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/result.txt"
        ]
        for url in urls:
            msg = f"处理远程URL: {url}"
            print(msg)
            runtime_stats.append(msg)  # 收集远程处理统计
            process_url(url)

        # 获取当前脚本目录
        current_dir = os.path.dirname(os.path.abspath(__file__))  
        runtime_stats.append(f"脚本目录: {current_dir}")  # 收集目录统计

        # 本地文件处理
        input_black_file = os.path.join(current_dir, 'blacklist_auto.txt')
        lines_black = read_txt_file(input_black_file) if os.path.exists(input_black_file) else []
        msg = f"本地black文件行数: {len(lines_black)}"
        print(msg)
        runtime_stats.append(msg)  # 收集本地文件统计

        # 合并输入源
        lines = urls_all_lines + lines_black
        urls_hj_before = len(lines)
        msg = f"初始总行数（远程+本地）: {urls_hj_before}"
        print(msg)
        runtime_stats.append(msg)  # 收集初始行数统计

        # 数据清洗流程
        lines = split_url(lines)
        urls_hj_before2 = len(lines)
        msg = f"分解#后行数: {urls_hj_before2}"
        print(msg)
        runtime_stats.append(msg)  # 收集分解后统计

        lines = clean_url(lines)
        urls_hj_before3 = len(lines)
        msg = f"去$后行数: {urls_hj_before3}"
        print(msg)
        runtime_stats.append(msg)  # 收集去$后统计

        lines = remove_duplicates_url(lines)
        urls_hj = len(lines)
        msg = f"去重后行数: {urls_hj}"
        print(msg)
        runtime_stats.append(msg)  # 收集去重后统计

        # 多线程检测
        CONCURRENT_WORKERS = 30
        msg = f"并发线程数: {CONCURRENT_WORKERS}"
        print(msg)
        runtime_stats.append(msg)  # 收集线程数统计

        successlist, blacklist = process_urls_multithreaded(lines, max_workers=CONCURRENT_WORKERS)
        urls_ok = len(successlist)
        urls_ng = len(blacklist)
        msg = f"检测结果: 成功{urls_ok}条, 失败{urls_ng}条"
        print(msg)
        runtime_stats.append(msg)  # 收集检测结果统计

        # 结果整理与保存
        def remove_prefix_from_lines(lines):
            result = []
            for line in lines:
                if "#genre#" not in line and "," in line and "://" in line:
                    parts = line.split(",")
                    result.append(",".join(parts[1:]))
            return result

        version = datetime.now().strftime("%Y%m%d-%H-%M-%S") + ",url"
        successlist_tv = ["更新时间,#genre#"] + [version] + ['\n'] + ["whitelist,#genre#"] + remove_prefix_from_lines(successlist)
        successlist = ["更新时间,#genre#"] + [version] + ['\n'] + ["RespoTime,whitelist,#genre#"] + successlist
        blacklist = ["更新时间,#genre#"] + [version] + ['\n'] + ["blacklist,#genre#"] + blacklist

        success_file = os.path.join(current_dir, 'whitelist_auto.txt')
        success_file_tv = os.path.join(current_dir, 'whitelist_auto_tv.txt')
        blacklist_file = os.path.join(current_dir, 'blacklist_auto.txt')
        write_list(success_file, successlist)
        write_list(success_file_tv, successlist_tv)
        write_list(blacklist_file, blacklist)
        runtime_stats.append(f"结果文件保存: {success_file}, {success_file_tv}, {blacklist_file}")  # 收集文件保存统计

        # 历史记录保存
        timenow = datetime.now().strftime("%Y%m%d_%H_%M_%S")
        history_dir = os.path.join(current_dir, "history", "blacklist")
        os.makedirs(history_dir, exist_ok=True)
        history_success_file = os.path.join(history_dir, f"{timenow}_whitelist_auto.txt")
        history_blacklist_file = os.path.join(history_dir, f"{timenow}_blacklist_auto.txt")
        write_list(history_success_file, successlist)
        write_list(history_blacklist_file, blacklist)
        runtime_stats.append(f"历史记录保存: {history_success_file}, {history_blacklist_file}")  # 收集历史记录统计

        # 执行时间统计
        timeend = datetime.now()
        elapsed_time = timeend - timestart
        total_seconds = elapsed_time.total_seconds()
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        timestart_str = timestart.strftime("%Y%m%d_%H_%M_%S")
        timeend_str = timeend.strftime("%Y%m%d_%H_%M_%S")
        msg = f"执行时间: {minutes}分{seconds}秒 (开始: {timestart_str}, 结束: {timeend_str})"
        print(msg)
        runtime_stats.append(msg)  # 收集时间统计

        # 故障主机统计
        blackhost_dir = os.path.join(current_dir, "blackhost")
        os.makedirs(blackhost_dir, exist_ok=True)
        blackhost_filename = os.path.join(blackhost_dir, f"{timenow}_blackhost_count.txt")
        def save_blackhost_to_txt(filename=blackhost_filename):
            with open(filename, "w") as file:
                for host, count in blacklist_dict.items():
                    file.write(f"{host}: {count}\n")
            return filename
        saved_host_file = save_blackhost_to_txt()
        runtime_stats.append(f"故障主机统计保存: {saved_host_file}")  # 收集故障主机统计

        # 🌟 写入所有统计到日志文件
        stats_file = os.path.join(current_dir, 'url_statistics.log')
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write(f"# 完整检测统计日志\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y%m%d %H:%M:%S')}\n")
            f.write("\n".join(runtime_stats))  # 写入所有收集的统计
        msg = f"✅ 所有统计已写入日志: {stats_file}"
        print(msg)

    except Exception as e:
        error_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
        err_msg = f"❌ 主程序异常: {str(e)}"
        print(err_msg)
        runtime_stats.append(f"\n# 检测异常 (时间: {error_time})")
        runtime_stats.append(f"# 错误原因: {str(e)}")
        runtime_stats.append(f"# 堆栈信息: {traceback.format_exc()}")

        # 异常时写入统计日志
        stats_file = os.path.join(current_dir, 'url_statistics.log')
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write(f"# 异常检测统计日志\n")
            f.write(f"# 异常时间: {error_time}\n")
            f.write("\n".join(runtime_stats))  # 写入异常前收集的统计+错误信息
        msg = f"⚠️ 异常统计已写入日志: {stats_file}"
        print(msg)

        # 覆盖核心结果文件为错误信息
        error_lines = [f"CheckTime：{error_time}", f"ERROR：{str(e)}"]
        for path in [
            os.path.join(current_dir, 'whitelist_auto.txt'),
            os.path.join(current_dir, 'whitelist_auto_tv.txt'),
            os.path.join(current_dir, 'blacklist_auto.txt')
        ]:
            write_list(path, error_lines)
