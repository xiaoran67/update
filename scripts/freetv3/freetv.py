#!/usr/bin/env python3
"""
FreeTV 主程序 - 基于成功代码重构
"""
import urllib.request
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

class FreeTVProcessor:
    def __init__(self):
        # 设置路径
        self.script_dir = Path(__file__).parent
        self.output_dir = Path(__file__).parent.parent.parent / "output" / "freetv"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置和数据
        self.config = self.load_config()
        self.rename_dic = self.load_modify_name()
        self.freetv_dictionary = self.read_txt_to_array('channel_list.txt')
        self.freetv_dictionary_cctv = self.read_txt_to_array('cctv_list.txt')
        self.freetv_dictionary_ws = self.read_txt_to_array('ws_list.txt')
        
        # 存储数据
        self.freetv_lines = []
        self.freetv_cctv_lines = []
        self.freetv_ws_lines = []
        self.freetv_other_lines = []

    def load_config(self):
        """加载配置文件"""
        import yaml
        config_path = self.script_dir / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load_modify_name(self):
        """读取频道名称修正规则"""
        corrections = {}
        rename_file = self.script_dir / self.config['sources']['data_files']['rename_rules']
        try:
            with open(rename_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 2:
                        correct_name = parts[0]
                        for name in parts[1:]:
                            corrections[name] = correct_name
            return corrections
        except Exception as e:
            print(f"读取修正文件错误: {e}")
            return {}

    def read_txt_to_array(self, filename):
        """读取文本文件到数组"""
        try:
            file_path = self.script_dir / self.config['sources']['data_files'][filename.replace('.txt', '')]
            with open(file_path, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file if line.strip()]
        except Exception as e:
            print(f"读取文件错误 {filename}: {e}")
            return []

    def rename_channel(self, data):
        """修正频道名称"""
        corrected_data = []
        for line in data:
            if ',' in line:
                name, url = line.split(',', 1)
                if name in self.rename_dic and name != self.rename_dic[name]:
                    name = self.rename_dic[name]
                corrected_data.append(f"{name},{url}")
        return corrected_data

    def process_channel_line(self, line):
        """处理单个频道行"""
        if "#genre#" not in line and "," in line and "://" in line:
            channel_name, channel_address = line.split(',', 1)
            channel_address = channel_address + "$" + channel_name.strip().replace(' ', '_')
            processed_line = channel_name + "," + channel_address
            self.freetv_lines.append(processed_line.strip())

    def process_url(self, url):
        """处理URL"""
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            with urllib.request.urlopen(req) as response:
                data = response.read()
                text = data.decode('utf-8')
                lines = text.split('\n')
                print(f"处理URL: {url}, 行数: {len(lines)}")
                
                for line in lines:
                    if "#genre#" not in line and "," in line and "://" in line:
                        channel_name, channel_address = line.split(',', 1)
                        if channel_name in self.freetv_dictionary:
                            self.process_channel_line(line)
        except Exception as e:
            print(f"处理URL时发生错误：{e}")

    def clean_url(self, url):
        """清理URL中的$后缀"""
        last_dollar_index = url.rfind('$')
        if last_dollar_index != -1:
            return url[:last_dollar_index]
        return url

    def categorize_channels(self):
        """分类频道"""
        freetv_lines_renamed = self.rename_channel(self.freetv_lines)
        
        for line in freetv_lines_renamed:
            if "#genre#" not in line and "," in line and "://" in line:
                channel_name = line.split(',')[0].strip()
                channel_address = self.clean_url(line.split(',')[1].strip())
                clean_line = channel_name + "," + channel_address

                if channel_name in self.freetv_dictionary_cctv:
                    self.freetv_cctv_lines.append(clean_line.strip())
                elif channel_name in self.freetv_dictionary_ws:
                    self.freetv_ws_lines.append(clean_line.strip())
                else:
                    self.freetv_other_lines.append(clean_line.strip())

    def get_beijing_time(self):
        """获取北京时间"""
        utc_time = datetime.now(timezone.utc)
        beijing_time = utc_time + timedelta(hours=8)
        return beijing_time.strftime("%Y%m%d %H:%M:%S")

    def generate_output_files(self):
        """生成输出文件"""
        version = self.get_beijing_time() + ",url"
        
        # 生成完整列表
        freetv_lines_renamed = self.rename_channel(self.freetv_lines)
        output_lines = ["更新时间,#genre#", version, ''] + ["freetv,#genre#"] + sorted(set(freetv_lines_renamed))
        self.save_file("complete.txt", output_lines)
        self.generate_m3u("complete.m3u", freetv_lines_renamed)
        
        # 生成分类列表
        self.save_categorized_files(version)

    def save_categorized_files(self, version):
        """保存分类文件"""
        # CCTV频道
        if self.freetv_cctv_lines:
            output_lines_cctv = ["更新时间,#genre#", version, ''] + ["freetv_cctv,#genre#"] + sorted(set(self.freetv_cctv_lines))
            self.save_file("cctv_only.txt", output_lines_cctv)
            self.generate_m3u("cctv_only.m3u", self.freetv_cctv_lines)
        
        # 卫视频道
        if self.freetv_ws_lines:
            output_lines_ws = ["更新时间,#genre#", version, ''] + ["freetv_ws,#genre#"] + sorted(set(self.freetv_ws_lines))
            self.save_file("satellite.txt", output_lines_ws)
            self.generate_m3u("satellite.m3u", self.freetv_ws_lines)
        
        # 其他频道
        if self.freetv_other_lines:
            output_lines_other = ["更新时间,#genre#", version, ''] + ["freetv_other,#genre#"] + sorted(set(self.freetv_other_lines))
            self.save_file("others.txt", output_lines_other)
            self.generate_m3u("others.m3u", self.freetv_other_lines)

    def save_file(self, filename, content):
        """保存文本文件"""
        file_path = self.output_dir / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for line in content:
                    f.write(line + '\n')
            print(f"✅ 已保存: {filename}")
        except Exception as e:
            print(f"❌ 保存文件错误 {filename}: {e}")

    def generate_m3u(self, filename, channels):
        """生成M3U文件"""
        file_path = self.output_dir / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for line in channels:
                    if ',' in line:
                        name, url = line.split(',', 1)
                        clean_url = self.clean_url(url)
                        f.write(f"#EXTINF:-1,{name}\n")
                        f.write(f"{clean_url}\n")
            print(f"✅ 已保存: {filename}")
        except Exception as e:
            print(f"❌ 生成M3U文件错误 {filename}: {e}")

    def run(self):
        """主运行逻辑"""
        print("🚀 开始处理FreeTV频道...")
        
        # 处理URL
        for url in self.config['sources']['urls']:
            self.process_url(url)
        
        print(f"📡 获取到 {len(self.freetv_lines)} 个原始频道")
        
        if not self.freetv_lines:
            print("❌ 没有获取到任何频道数据")
            return
        
        # 分类频道
        self.categorize_channels()
        print(f"📊 分类结果 - CCTV: {len(self.freetv_cctv_lines)}, 卫视: {len(self.freetv_ws_lines)}, 其他: {len(self.freetv_other_lines)}")
        
        # 生成输出文件
        self.generate_output_files()
        print("🎉 FreeTV处理完成！")

def main():
    processor = FreeTVProcessor()
    processor.run()

if __name__ == "__main__":
    main()
