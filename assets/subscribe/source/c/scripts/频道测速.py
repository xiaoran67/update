#!/data/data/com.termux/files/usr/bin/python3
import urllib.request
import socket
import time
import os
import threading
from queue import Queue
import sys

class StreamTester:
    def __init__(self, max_workers=200):
        self.max_workers = max_workers
        self.queue = Queue(maxsize=10000)
        self.lock = threading.Lock()
        self.valid_count = 0
        self.invalid_count = 0
        self.total_processed = 0
        
    def check_url(self, url):
        """快速检查URL"""
        try:
            # 设置超时
            socket.setdefaulttimeout(2)
            
            # 如果是HTTP/HTTPS
            if url.startswith('http'):
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0'},
                    method='HEAD'
                )
                
                try:
                    response = urllib.request.urlopen(req, timeout=2)
                    return response.getcode() < 400
                except:
                    # 尝试GET
                    try:
                        req.method = 'GET'
                        response = urllib.request.urlopen(req, timeout=2)
                        response.read(1)  # 只读1字节确认连接
                        return True
                    except:
                        return False
        except:
            return False
        
        return False
    
    def worker(self):
        """工作线程"""
        while True:
            try:
                item = self.queue.get(timeout=1)
                if item is None:
                    break
                    
                name, url = item
                is_valid = self.check_url(url)
                
                with self.lock:
                    self.total_processed += 1
                    if is_valid:
                        self.valid_count += 1
                        self.valid_file.write(f"{name},{url}\n")
                    else:
                        self.invalid_count += 1
                        self.invalid_file.write(f"{name},{url}\n")
                    
                    # 每1000个显示一次进度
                    if self.total_processed % 1000 == 0:
                        elapsed = time.time() - self.start_time
                        speed = self.total_processed / elapsed
                        remaining = (self.total_items - self.total_processed) / speed if speed > 0 else 0
                        
                        print(f"进度: {self.total_processed}/{self.total_items} "
                              f"({self.total_processed/self.total_items*100:.1f}%) | "
                              f"有效: {self.valid_count} | "
                              f"速度: {speed:.0f}个/秒 | "
                              f"剩余时间: {remaining/60:.1f}分钟")
                
                self.queue.task_done()
            except:
                break
    
    def test_file(self, input_file, batch_size=5000):
        """测试文件"""
        self.start_time = time.time()
        
        # 打开输出文件
        valid_path = "/storage/emulated/0/1314/output/valid.txt"
        invalid_path = "/storage/emulated/0/1314/output/invalid.txt"
        
        self.valid_file = open(valid_path, 'w', encoding='utf-8')
        self.invalid_file = open(invalid_path, 'w', encoding='utf-8')
        
        self.valid_file.write("# 有效直播源\n")
        self.valid_file.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.valid_file.write("🌐央视频道,#genre#\n")
        
        self.invalid_file.write("# 无效直播源\n")
        self.invalid_file.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.invalid_file.write("🌐无效频道,#genre#\n")
        
        # 启动工作线程
        threads = []
        for _ in range(self.max_workers):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 分批读取文件
        print("开始读取文件...")
        batch = []
        total_items = 0
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ',' in line and not line.startswith('#') and '🌐' not in line:
                    name, url = line.split(',', 1)
                    batch.append((name.strip(), url.strip()))
                    
                    if len(batch) >= batch_size:
                        # 放入队列
                        for item in batch:
                            self.queue.put(item)
                        total_items += len(batch)
                        batch = []
            
            # 处理最后一批
            if batch:
                for item in batch:
                    self.queue.put(item)
                total_items += len(batch)
        
        self.total_items = total_items
        print(f"总共需要测试: {total_items} 个源")
        
        # 等待队列完成
        self.queue.join()
        
        # 停止工作线程
        for _ in range(self.max_workers):
            self.queue.put(None)
        
        for t in threads:
            t.join()
        
        # 关闭文件
        self.valid_file.close()
        self.invalid_file.close()
        
        # 打印统计
        elapsed = time.time() - self.start_time
        print(f"\n测试完成!")
        print(f"总耗时: {elapsed:.1f}秒")
        print(f"总测试数: {total_items}")
        print(f"有效源: {self.valid_count}")
        print(f"无效源: {self.invalid_count}")
        if total_items > 0:
            print(f"有效率: {self.valid_count/total_items*100:.1f}%")
            print(f"平均速度: {total_items/elapsed:.1f}个/秒")

if __name__ == "__main__":
    input_file = "/storage/emulated/0/1314/output/full.txt"
    
    if not os.path.exists(input_file):
        print(f"文件不存在: {input_file}")
        sys.exit(1)
    
    tester = StreamTester(max_workers=200)
    tester.test_file(input_file, batch_size=10000)