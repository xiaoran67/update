import os
import time
from datetime import datetime

def modify_files_date(root_dir, target_date_str="2025-11-10 23:59:59"):
    """
    将指定目录及其子目录下所有文件的修改时间设置为目标时间
    
    Args:
        root_dir: 根目录路径
        target_date_str: 目标时间字符串，格式为"YYYY-MM-DD HH:MM:SS"
    """
    try:
        # 解析目标时间
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d %H:%M:%S")
        # 转换为时间戳
        target_timestamp = time.mktime(target_date.timetuple())
        
        # 遍历目录和子目录
        file_count = 0
        dir_count = 0
        
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dir_count += 1
            
            # 修改目录本身的日期
            try:
                os.utime(dirpath, (target_timestamp, target_timestamp))
            except Exception as e:
                print(f"无法修改目录 {dirpath} 的日期: {e}")
            
            # 修改文件日期
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    # 修改文件的访问和修改时间
                    os.utime(file_path, (target_timestamp, target_timestamp))
                    file_count += 1
                    print(f"已修改: {file_path}")
                    
                    # 每处理100个文件打印一次进度
                    if file_count % 100 == 0:
                        print(f"已处理 {file_count} 个文件...")
                        
                except PermissionError:
                    print(f"权限不足，跳过: {file_path}")
                except FileNotFoundError:
                    print(f"文件不存在，跳过: {file_path}")
                except Exception as e:
                    print(f"处理文件 {file_path} 时出错: {e}")
        
        print(f"\n完成！")
        print(f"处理了 {dir_count} 个目录")
        print(f"修改了 {file_count} 个文件")
        print(f"所有文件的日期已设置为: {target_date_str}")
        
    except ValueError:
        print(f"日期格式错误！请使用 'YYYY-MM-DD HH:MM:SS' 格式")
    except FileNotFoundError:
        print(f"目录不存在: {root_dir}")
    except Exception as e:
        print(f"发生错误: {e}")

def main():
    # 设置要处理的目录
    target_dir = "/storage/emulated/0/1314"
    
    # 检查目录是否存在
    if not os.path.exists(target_dir):
        print(f"错误: 目录不存在 - {target_dir}")
        return
    
    # 确认操作
    print("=" * 60)
    print(f"警告: 这将修改目录及其子目录下所有文件的日期")
    print(f"目标目录: {target_dir}")
    print(f"新日期: 2025-11-10 23:59:59")
    print("=" * 60)
    
    response = input("确认要执行此操作吗？(输入 'yes' 继续): ")
    
    if response.lower() == 'yes':
        print("开始处理...")
        modify_files_date(target_dir, "2025-11-10 23:59:59")
    else:
        print("操作已取消")

if __name__ == "__main__":
    main()