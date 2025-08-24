import os
import requests
from datetime import datetime, timedelta
import traceback  # 新增：详细错误追踪

# 读取文本方法（增强容错）
def read_txt_to_array(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:  # 忽略编码错误
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"❌ 错误：文件未找到 → {file_path}")
        return []
    except Exception as e:
        print(f"❌ 错误：读取文件失败 → {file_path} → {str(e)}")
        return []

# 下载逻辑（增强错误重试）
def download_file(url, folder_name):
    max_retries = 3  # 新增：重试 3 次
    for retry in range(max_retries):
        try:
            response = requests.get(url, timeout=15)  # 延长超时到 15 秒
            response.raise_for_status()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            file_name = url.split('/')[-1].split('?')[0]
            file_path = os.path.join(folder_name, f"{timestamp}_{file_name}")
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ 下载成功 → {file_path}（大小：{len(response.content)} 字节）")
            return file_path
        except requests.exceptions.Timeout:
            print(f"⚠️ 下载超时（重试 {retry+1}/{max_retries}）→ {url}")
        except requests.exceptions.HTTPError as e:
            print(f"⚠️ HTTP 错误（重试 {retry+1}/{max_retries}）→ {url} → {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 网络错误（重试 {retry+1}/{max_retries}）→ {url} → {str(e)}")
        except Exception as e:
            print(f"⚠️ 未知错误（重试 {retry+1}/{max_retries}）→ {url} → {str(e)}")
            traceback.print_exc()  # 新增：打印详细错误栈
    print(f"❌ 下载失败（重试 {max_retries} 次）→ {url}")
    return None

# 主逻辑
if __name__ == "__main__":
    # 自动适配 GitHub Actions 环境
    root_dir = os.environ.get('GITHUB_WORKSPACE', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 拼接 URLs 文件路径
    urls1_path = os.path.join(root_dir, 'assets', 'snapshot', 'urls.txt')
    urls2_path = os.path.join(root_dir, 'assets', 'urls-daily.txt')
    
    # 读取并去重 URLs
    urls = set(read_txt_to_array(urls1_path) + read_txt_to_array(urls2_path))
    print(f"✅ 已读取 {len(urls)} 个 URL（去重后）")
    
    # 创建当日文件夹
    current_date = datetime.now().strftime('%Y-%m-%d')
    folder_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), current_date)
    
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"✅ 创建文件夹 → {folder_name}")
    
    # 存储已下载的文件路径
    downloaded_files = []
    
    # 处理每个 URL
    for idx, url in enumerate(urls, start=1):
        print(f"\n===== 开始处理 URL {idx}/{len(urls)} =====\n原始 URL: {url}")
        
        # 替换动态参数（如 {MMdd}）
        if "{MMdd}" in url:
            url = url.replace("{MMdd}", datetime.now().strftime("%m%d"))
            print(f"替换 {{{{MMdd}}}} → {url}")
        if "{MMdd-1}" in url:
            url = url.replace("{MMdd-1}", (datetime.now() - timedelta(days=1)).strftime("%m%d"))
            print(f"替换 {{{{MMdd-1}}}} → {url}")
        
        # 跳过无效 URL
        if not url.startswith(('http://', 'https://')):
            print(f"跳过无效 URL → {url}（需以 http/https 开头）")
            continue
        
        # 下载文件（带重试）
        file_path = download_file(url, folder_name)
        if file_path:
            downloaded_files.append(file_path)
    
    # 打印最终结果
    print(f"\n===== 处理完成 =====\n共处理 {len(urls)} 个 URL，{len(downloaded_files)} 个文件已下载")
    if downloaded_files:
        print("下载的文件：")
        for f in downloaded_files:
            print(f"  - {f}")
    else:
        print("没有文件下载")
