import os

def m3u_to_txt(m3u_file_path, txt_file_path=None):
    if not txt_file_path:
        m3u_dir = os.path.dirname(m3u_file_path)
        m3u_name = os.path.splitext(os.path.basename(m3u_file_path))[0]
        txt_file_path = os.path.join(m3u_dir, f"{m3u_name}.txt")
    
    channels = []
    
    try:
        with open(m3u_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
            if not lines or lines[0].strip() != '#EXTM3U':
                print("警告：非标准M3U文件，尝试解析...")
            
            for i in range(1, len(lines)):
                line = lines[i].strip()
                if line.startswith('#EXTINF:'):
                    name_start = line.rfind(',') + 1
                    channel_name = line[name_start:].strip() if name_start > 0 else f"未知频道_{i}"
                    
                    if i + 1 < len(lines):
                        channel_url = lines[i+1].strip()
                        if channel_url:
                            channels.append((channel_name, channel_url))
        
        with open(txt_file_path, 'w', encoding='utf-8') as f:
            for name, url in channels:
                f.write(f"{name}\n{url}\n\n")  # 无序号，仅名称+地址
        
        print(f"转换完成！{len(channels)}个频道，保存至：\n{txt_file_path}")
    
    except FileNotFoundError:
        print(f"错误：文件不存在 - {m3u_file_path}")
    except Exception as e:
        print(f"出错：{str(e)}")


if __name__ == "__main__":
    m3u_path = "/storage/emulated/0/.aaa/backups/fm.m3u"
    m3u_to_txt(m3u_path)
