import urllib.request
from urllib.parse import urlparse
import re #正则
import os
from datetime import datetime, timedelta, timezone
import random
import opencc #简繁转换

import socket
import time

#创建输出目录（如果不存在）
os.makedirs('output/livesource', exist_ok=True)

#简繁转换
def traditional_to_simplified(text: str) -> str:
    # 初始化转换器，"t2s" 表示从繁体转为简体
    converter = opencc.OpenCC('t2s')
    simplified_text = converter.convert(text)
    return simplified_text

# 执行开始时间
timestart = datetime.now()

#读取文本方法
def read_txt_to_array(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            lines = [line.strip() for line in lines if line.strip()]  # 跳过空行
            return lines
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

#read BlackList 2025-07-20 13:14
def read_blacklist_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    BlackList = [line.split(',')[1].strip() for line in lines if ',' in line]
    return BlackList

blacklist_auto=read_blacklist_from_txt('scripts/livesource/blacklist/blacklist_auto.txt') 
blacklist_manual=read_blacklist_from_txt('scripts/livesource/blacklist/blacklist_manual.txt') 
combined_blacklist = set(blacklist_auto + blacklist_manual)

# 定义多个对象用于存储不同内容的行文本
yangshi_lines = [] #CCTV
weishi_lines = [] #卫视频道

# 地方台
beijing_lines = [] #北京频道
shanghai_lines = [] #上海频道
tianjin_lines = [] #天津频道
chongqing_lines = [] #重庆频道
guangdong_lines = [] #广东频道
jiangsu_lines = [] #江苏频道
zhejiang_lines = [] #浙江频道
shandong_lines = [] #山东频道
henan_lines = [] #河南频道
sichuan_lines = [] #四川频道
hebei_lines = [] #河北频道
hunan_lines = [] #湖南频道
hubei_lines = [] #湖北频道
anhui_lines = [] #安徽频道
fujian_lines = [] #福建频道
shanxi1_lines = [] #陕西频道
liaoning_lines = [] #辽宁频道
jiangxi_lines = [] #江西频道
heilongjiang_lines = [] #黑龙江频道
jilin_lines = [] #吉林频道
shanxi2_lines = [] #山西频道
guangxi_lines = [] #广西频道
yunnan_lines = [] #云南频道
guizhou_lines = [] #贵州频道
gansu_lines = [] #甘肃频道
neimenggu_lines = [] #内蒙频道
xinjiang_lines = [] #新疆频道
hainan_lines = [] #海南频道
ningxia_lines = [] #宁夏频道
qinghai_lines = [] #青海频道
xizang_lines = [] #西藏频道

# 定制频道
news_lines = [] #新闻频道
shuzi_lines = [] #数字频道
dianying_lines = [] #电影频道
jieshuo_lines = [] #解说频道
zongyi_lines = [] #综艺频道
huya_lines = [] #虎牙直播
douyu_lines = [] #斗鱼直播
xianggang_lines = [] #香港频道
aomen_lines = [] #澳门频道
china_lines = [] #中国频道
guoji_lines = [] #国际频道
gangaotai_lines = [] #港澳台
dianshiju_lines = [] #电视剧
radio_lines = [] #收音机
donghuapian_lines = [] #动画片
jilupian_lines = [] #记录片
tiyu_lines = [] #体育频道
tiyusaishi_lines = [] #体育赛事
youxi_lines = [] #游戏频道
xiqu_lines = [] #戏曲频道
yinyue_lines = [] #音乐频道
chunwan_lines = [] #春晚频道
zhibozhongguo_lines = [] #直播中国

other_lines = []
other_lines_url = [] # 为降低other文件大小，剔除重复url添加

# 新增：全局URL跟踪集合，用于跨分类去重
global_url_tracker = set()

def process_name_string(input_str):
    parts = input_str.split(',')
    processed_parts = []
    for part in parts:
        processed_part = process_part(part)
        processed_parts.append(processed_part)
    result_str = ','.join(processed_parts)
    return result_str

def process_part(part_str):
    # 处理逻辑
    if "CCTV" in part_str  and "://" not in part_str:
        part_str=part_str.replace("IPV6", "")  #先剔除IPV6字样
        part_str=part_str.replace("PLUS", "+")  #替换PLUS
        part_str=part_str.replace("1080", "")  #替换1080
        filtered_str = ''.join(char for char in part_str if char.isdigit() or char == 'K' or char == '+')
        if not filtered_str.strip(): #处理特殊情况，如果发现没有找到频道数字返回原名称
            filtered_str=part_str.replace("CCTV", "")

        if len(filtered_str) > 2 and re.search(r'4K|8K', filtered_str):   # 特殊处理CCTV中部分4K和8K名称
            # 使用正则表达式替换，删除4K或8K后面的字符，并且保留4K或8K
            filtered_str = re.sub(r'(4K|8K).*', r'\1', filtered_str)
            if len(filtered_str) > 2: 
                # 给4K或8K添加括号
                filtered_str = re.sub(r'(4K|8K)', r'(\1)', filtered_str)

        return "CCTV"+filtered_str 
        
    elif "卫视" in part_str:
        # 定义正则表达式模式，匹配"卫视"后面的内容
        pattern = r'卫视「.*」'
        # 使用sub函数替换匹配的内容为空字符串
        result_str = re.sub(pattern, '卫视', part_str)
        return result_str
    
    return part_str

# 准备支持m3u格式
def get_url_file_extension(url):
    # 解析URL
    parsed_url = urlparse(url)
    # 获取路径部分
    path = parsed_url.path
    # 提取文件扩展名
    extension = os.path.splitext(path)[1]
    return extension

def convert_m3u_to_txt(m3u_content):
    # 分行处理
    lines = m3u_content.split('\n')
    
    # 用于存储结果的列表
    txt_lines = []
    
    # 临时变量用于存储频道名称
    channel_name = ""
    
    for line in lines:
        # 过滤掉 #EXTM3U 开头的行
        if line.startswith("#EXTM3U"):
            continue
        # 处理 #EXTINF 开头的行
        if line.startswith("#EXTINF"):
            # 获取频道名称（假设频道名称在引号后）
            channel_name = line.split(',')[-1].strip()
        # 处理 URL 行
        elif line.startswith("http") or line.startswith("rtmp") or line.startswith("p3p") :
            txt_lines.append(f"{channel_name},{line.strip()}")
        
        # 处理后缀名为m3u，但是内容为txt的文件
        if "#genre#" not in line and "," in line and "://" in line:
            # 定义正则表达式，匹配频道名称,URL 的格式，并确保 URL 包含 "://"
            # xxxx,http://xxxxx.xx.xx
            pattern = r'^[^,]+,[^\s]+://[^\s]+$'
            if bool(re.match(pattern, line)):
                txt_lines.append(line)
    
    # 将结果合并成一个字符串，以换行符分隔
    return '\n'.join(txt_lines)

# 在list是否已经存在url 2025-07-20 13:14
def check_url_existence(data_list, url):
    """
    Check if a given URL exists in a list of data.

    :param data_list: List of strings containing the data
    :param url: The URL to check for existence
    :return: True if the URL exists in the list, otherwise False
    """
    # Extract URLs from the data list
    urls = [item.split(',')[1] for item in data_list]
    return url not in urls #如果不存在则返回true，需要

# 处理带$的URL，把$之后的内容都去掉（包括$也去掉） 【2025-07-20 13:14】
def clean_url(url):
    last_dollar_index = url.rfind('$')  # 安全起见找最后一个$处理
    if last_dollar_index != -1:
        return url[:last_dollar_index]
    return url

# 添加channel_name前剔除部分特定字符
removal_list = ["_电信", "电信", "高清", "频道", "（HD）", "-HD","英陆","_ITV","(北美)","(HK)","AKtv","「IPV4」","「IPV6」",
                "频陆","备陆","壹陆","贰陆","叁陆","肆陆","伍陆","陆陆","柒陆", "频晴","频粤","[超清]","高清","超清","标清","斯特",
                "粤陆", "国陆","肆柒","频英","频特","频国","频壹","频贰","肆贰","频测","咪咕","闽特","高特","频高","频标","汝阳","[HD]", "[BD]", "[SD]", "[VGA]"]
def clean_channel_name(channel_name, removal_list):
    for item in removal_list:
        channel_name = channel_name.replace(item, "")

    # 检查并移除末尾的 'HD'
    if channel_name.endswith("HD"):
        channel_name = channel_name[:-2]  # 去掉最后两个字符 "HD"
    
    if channel_name.endswith("台") and len(channel_name) > 3:
        channel_name = channel_name[:-1]  # 去掉最后两个字符 "台"

    return channel_name

# 新增：频道名称标准化函数
def normalize_channel_name(channel_name):
    """
    标准化频道名称，去除多余的空格和特殊字符，便于去重比较
    """
    # 去除前后空格
    channel_name = channel_name.strip()
    
    # 将多个连续空格替换为单个空格
    channel_name = re.sub(r'\s+', ' ', channel_name)
    
    # 移除特定模式的后缀
    patterns_to_remove = [
        r'\(\d+\)$',  # 末尾的(数字)
        r'\[\d+\]$',  # 末尾的[数字]
        r'-\d+$',     # 末尾的-数字
        r'_\d+$',     # 末尾的_数字
    ]
    
    for pattern in patterns_to_remove:
        channel_name = re.sub(pattern, '', channel_name)
    
    return channel_name.strip()

# 分发直播源，归类，把这部分从process_url剥离出来，为以后加入whitelist源清单做准备。
def process_channel_line(line):
    if  "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
        channel_name=line.split(',')[0].strip()
        channel_name= clean_channel_name(channel_name, removal_list)  #分发前清理channel_name中特定字符
        channel_name = traditional_to_simplified(channel_name)  #繁转简
        normalized_name = normalize_channel_name(channel_name)  # 标准化频道名称用于去重

        channel_address=clean_url(line.split(',')[1].strip())  #把URL中$之后的内容都去掉
        line=channel_name+","+channel_address #重新组织line
        
        # 创建唯一标识符用于全局去重
        channel_identifier = f"{normalized_name}|{channel_address}"

        if channel_address not in combined_blacklist and channel_identifier not in global_url_tracker: # 判断当前源是否在blacklist中且未被全局记录
            global_url_tracker.add(channel_identifier)  # 添加到全局跟踪器
            
            # 根据行内容判断存入哪个对象，开始分发
            # 主频道
            if "CCTV" in channel_name and check_url_existence(yangshi_lines, channel_address):
                yangshi_lines.append(process_name_string(line.strip()))
            elif channel_name in weishi_dictionary and check_url_existence(weishi_lines, channel_address):
                weishi_lines.append(process_name_string(line.strip()))
            
            # 地方台
            elif channel_name in beijing_dictionary and check_url_existence(beijing_lines, channel_address):
                beijing_lines.append(process_name_string(line.strip()))
            elif channel_name in shanghai_dictionary and check_url_existence(shanghai_lines, channel_address):
                shanghai_lines.append(process_name_string(line.strip()))
            elif channel_name in tianjin_dictionary and check_url_existence(tianjin_lines, channel_address):
                tianjin_lines.append(process_name_string(line.strip()))
            elif channel_name in chongqing_dictionary and check_url_existence(chongqing_lines, channel_address):
                chongqing_lines.append(process_name_string(line.strip()))
            elif channel_name in guangdong_dictionary and check_url_existence(guangdong_lines, channel_address):
                guangdong_lines.append(process_name_string(line.strip()))
            elif channel_name in jiangsu_dictionary and check_url_existence(jiangsu_lines, channel_address):
                jiangsu_lines.append(process_name_string(line.strip()))
            elif channel_name in zhejiang_dictionary and check_url_existence(zhejiang_lines, channel_address):
                zhejiang_lines.append(process_name_string(line.strip()))
            elif channel_name in shandong_dictionary and check_url_existence(shandong_lines, channel_address):
                shandong_lines.append(process_name_string(line.strip()))
            elif channel_name in henan_dictionary and check_url_existence(henan_lines, channel_address):
                henan_lines.append(process_name_string(line.strip()))
            elif channel_name in sichuan_dictionary and check_url_existence(sichuan_lines, channel_address):
                sichuan_lines.append(process_name_string(line.strip()))
            elif channel_name in hebei_dictionary and check_url_existence(hebei_lines, channel_address):
                hebei_lines.append(process_name_string(line.strip()))
            elif channel_name in hunan_dictionary and check_url_existence(hunan_lines, channel_address):
                hunan_lines.append(process_name_string(line.strip()))
            elif channel_name in hubei_dictionary and check_url_existence(hubei_lines, channel_address):
                hubei_lines.append(process_name_string(line.strip()))
            elif channel_name in anhui_dictionary and check_url_existence(anhui_lines, channel_address):
                anhui_lines.append(process_name_string(line.strip()))
            elif channel_name in fujian_dictionary and check_url_existence(fujian_lines, channel_address):
                fujian_lines.append(process_name_string(line.strip()))
            elif channel_name in shanxi1_dictionary and check_url_existence(shanxi1_lines, channel_address):
                shanxi1_lines.append(process_name_string(line.strip()))
            elif channel_name in liaoning_dictionary and check_url_existence(liaoning_lines, channel_address):
                liaoning_lines.append(process_name_string(line.strip()))
            elif channel_name in jiangxi_dictionary and check_url_existence(jiangxi_lines, channel_address):
                jiangxi_lines.append(process_name_string(line.strip()))
            elif channel_name in heilongjiang_dictionary and check_url_existence(heilongjiang_lines, channel_address):
                heilongjiang_lines.append(process_name_string(line.strip()))
            elif channel_name in jilin_dictionary and check_url_existence(jilin_lines, channel_address):
                jilin_lines.append(process_name_string(line.strip()))
            elif channel_name in shanxi2_dictionary and check_url_existence(shanxi2_lines, channel_address):
                shanxi2_lines.append(process_name_string(line.strip()))
            elif channel_name in guangxi_dictionary and check_url_existence(guangxi_lines, channel_address):
                guangxi_lines.append(process_name_string(line.strip()))
            elif channel_name in yunnan_dictionary and check_url_existence(yunnan_lines, channel_address):
                yunnan_lines.append(process_name_string(line.strip()))
            elif channel_name in guizhou_dictionary and check_url_existence(guizhou_lines, channel_address):
                guizhou_lines.append(process_name_string(line.strip()))
            elif channel_name in gansu_dictionary and check_url_existence(gansu_lines, channel_address):
                gansu_lines.append(process_name_string(line.strip()))
            elif channel_name in neimenggu_dictionary and check_url_existence(neimenggu_lines, channel_address):
                neimenggu_lines.append(process_name_string(line.strip()))
            elif channel_name in xinjiang_dictionary and check_url_existence(xinjiang_lines, channel_address):
                xinjiang_lines.append(process_name_string(line.strip()))
            elif channel_name in hainan_dictionary and check_url_existence(hainan_lines, channel_address):
                hainan_lines.append(process_name_string(line.strip()))
            elif channel_name in ningxia_dictionary and check_url_existence(ningxia_lines, channel_address):
                ningxia_lines.append(process_name_string(line.strip()))
            elif channel_name in qinghai_dictionary and check_url_existence(qinghai_lines, channel_address):
                qinghai_lines.append(process_name_string(line.strip()))
            elif channel_name in xizang_dictionary and check_url_existence(xizang_lines, channel_address):
                xizang_lines.append(process_name_string(line.strip()))
            
            # 定制频道
            elif channel_name in news_dictionary and check_url_existence(news_lines, channel_address):
                news_lines.append(process_name_string(line.strip()))
            elif channel_name in shuzi_dictionary and check_url_existence(shuzi_lines, channel_address):
                shuzi_lines.append(process_name_string(line.strip()))
            elif channel_name in dianying_dictionary and check_url_existence(dianying_lines, channel_address):
                dianying_lines.append(process_name_string(line.strip()))
            elif channel_name in jieshuo_dictionary and check_url_existence(jieshuo_lines, channel_address):
                jieshuo_lines.append(process_name_string(line.strip()))
            elif channel_name in zongyi_dictionary and check_url_existence(zongyi_lines, channel_address):
                zongyi_lines.append(process_name_string(line.strip()))
            elif channel_name in huya_dictionary and check_url_existence(huya_lines, channel_address):
                huya_lines.append(process_name_string(line.strip()))
            elif channel_name in douyu_dictionary and check_url_existence(douyu_lines, channel_address):
                douyu_lines.append(process_name_string(line.strip()))
            elif channel_name in xianggang_dictionary and check_url_existence(xianggang_lines, channel_address):
                xianggang_lines.append(process_name_string(line.strip()))
            elif channel_name in aomen_dictionary and check_url_existence(aomen_lines, channel_address):
                aomen_lines.append(process_name_string(line.strip()))
            elif channel_name in china_dictionary and check_url_existence(china_lines, channel_address):
                china_lines.append(process_name_string(line.strip()))
            elif channel_name in guoji_dictionary and check_url_existence(guoji_lines, channel_address):
                guoji_lines.append(process_name_string(line.strip()))
            elif channel_name in gangaotai_dictionary and check_url_existence(gangaotai_lines, channel_address):
                gangaotai_lines.append(process_name_string(line.strip()))
            elif channel_name in dianshiju_dictionary and check_url_existence(dianshiju_lines, channel_address):
                dianshiju_lines.append(process_name_string(line.strip()))
            elif channel_name in radio_dictionary and check_url_existence(radio_lines, channel_address):
                radio_lines.append(process_name_string(line.strip()))
            elif channel_name in donghuapian_dictionary and check_url_existence(donghuapian_lines, channel_address):
                donghuapian_lines.append(process_name_string(line.strip()))
            elif channel_name in jilupian_dictionary and check_url_existence(jilupian_lines, channel_address):
                jilupian_lines.append(process_name_string(line.strip()))
            elif channel_name in tiyu_dictionary and check_url_existence(tiyu_lines, channel_address):
                tiyu_lines.append(process_name_string(line.strip()))
            elif any(tiyusaishi_dictionary in channel_name for tiyusaishi_dictionary in tiyusaishi_dictionary) and check_url_existence(tiyusaishi_lines, channel_address):
                tiyusaishi_lines.append(process_name_string(line.strip()))
            elif channel_name in youxi_dictionary and check_url_existence(youxi_lines, channel_address):
                youxi_lines.append(process_name_string(line.strip()))
            elif channel_name in xiqu_dictionary and check_url_existence(xiqu_lines, channel_address):
                xiqu_lines.append(process_name_string(line.strip()))
            elif channel_name in yinyue_dictionary and check_url_existence(yinyue_lines, channel_address):
                yinyue_lines.append(process_name_string(line.strip()))
            elif channel_name in chunwan_dictionary and check_url_existence(chunwan_lines, channel_address):
                chunwan_lines.append(process_name_string(line.strip()))
            elif channel_name in zhibozhongguo_dictionary and check_url_existence(zhibozhongguo_lines, channel_address):
                zhibozhongguo_lines.append(process_name_string(line.strip()))
            else:
                if channel_address not in other_lines_url:
                    other_lines_url.append(channel_address)   #记录已加url
                    other_lines.append(line.strip())

# 随机获取User-Agent,备用 
def get_random_user_agent():
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
    ]
    return random.choice(USER_AGENTS)

def process_url(url):
    try:
        other_lines.append("◆◆◆　"+url)  # 存入other_lines便于check 2025-07-20 13:14
        
        # 创建一个请求对象并添加自定义header
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')

        # 打开URL并读取内容
        with urllib.request.urlopen(req) as response:
            # 以二进制方式读取数据
            data = response.read()
            # 将二进制数据解码为字符串
            text = data.decode('utf-8')
            text = text.strip()

            #处理m3u和m3u8，提取channel_name和channel_address
            #增加扩展名非m3u和m3u8为扩展名的m3u格式            
            is_m3u = text.startswith("#EXTM3U") or text.startswith("#EXTINF")
            if get_url_file_extension(url)==".m3u" or get_url_file_extension(url)==".m3u8" or is_m3u:
                text=convert_m3u_to_txt(text)

            # 逐行处理内容
            lines = text.split('\n')
            print(f"行数: {len(lines)}")
            for line in lines:
                if  "#genre#" not in line and "," in line and "://" in line and "tvbus://" not in line and "/udp/" not in line:
                    # tvbus://剔除tvbus
                    # /udp/剔除组播
                    # 拆分成频道名和URL部分
                    channel_name, channel_address = line.split(',', 1)
                    #需要加处理带#号源=予加速源
                    if "#" not in channel_address:
                        process_channel_line(line) # 如果没有井号，则照常按照每行规则进行分发
                    else: 
                        # 如果有"#"号，则根据"#"号分隔
                        url_list = channel_address.split('#')
                        for channel_url in url_list:
                            newline=f'{channel_name},{channel_url}'
                            process_channel_line(newline)

            other_lines.append('\n') #每个url处理完成后，在other_lines加个回车 2025-07-20 13:14

    except Exception as e:
        print(f"处理URL时发生错误：{e}")

# 新增：最终去重函数
def final_deduplicate_lines(lines):
    """
    最终去重函数，确保同一分类内没有重复的频道
    """
    seen_channels = set()
    deduplicated = []
    
    for line in lines:
        if "#genre#" in line or line == '\n':
            # 分类标题和空行直接保留
            deduplicated.append(line)
            continue
            
        if "," in line and "://" in line:
            parts = line.split(',', 1)
            if len(parts) == 2:
                channel_name, url = parts
                # 使用标准化名称和URL作为唯一标识
                normalized_name = normalize_channel_name(channel_name)
                channel_id = f"{normalized_name}|{url}"
                
                if channel_id not in seen_channels:
                    seen_channels.add(channel_id)
                    deduplicated.append(line)
    
    return deduplicated

current_directory = os.getcwd()  #准备读取txt

# 读取字典文本
# 主频道字典
yangshi_dictionary = read_txt_to_array('scripts/livesource/主频道/CCTV.txt')
weishi_dictionary = read_txt_to_array('scripts/livesource/主频道/卫视频道.txt')

# 地方台字典
beijing_dictionary = read_txt_to_array('scripts/livesource/地方台/北京频道.txt')
shanghai_dictionary = read_txt_to_array('scripts/livesource/地方台/上海频道.txt')
tianjin_dictionary = read_txt_to_array('scripts/livesource/地方台/天津频道.txt')
chongqing_dictionary = read_txt_to_array('scripts/livesource/地方台/重庆频道.txt')
guangdong_dictionary = read_txt_to_array('scripts/livesource/地方台/广东频道.txt')
jiangsu_dictionary = read_txt_to_array('scripts/livesource/地方台/江苏频道.txt')
zhejiang_dictionary = read_txt_to_array('scripts/livesource/地方台/浙江频道.txt')
shandong_dictionary = read_txt_to_array('scripts/livesource/地方台/山东频道.txt')
henan_dictionary = read_txt_to_array('scripts/livesource/地方台/河南频道.txt')
sichuan_dictionary = read_txt_to_array('scripts/livesource/地方台/四川频道.txt')
hebei_dictionary = read_txt_to_array('scripts/livesource/地方台/河北频道.txt')
hunan_dictionary = read_txt_to_array('scripts/livesource/地方台/湖南频道.txt')
hubei_dictionary = read_txt_to_array('scripts/livesource/地方台/湖北频道.txt')
anhui_dictionary = read_txt_to_array('scripts/livesource/地方台/安徽频道.txt')
fujian_dictionary = read_txt_to_array('scripts/livesource/地方台/福建频道.txt')
shanxi1_dictionary = read_txt_to_array('scripts/livesource/地方台/陕西频道.txt')
liaoning_dictionary = read_txt_to_array('scripts/livesource/地方台/辽宁频道.txt')
jiangxi_dictionary = read_txt_to_array('scripts/livesource/地方台/江西频道.txt')
heilongjiang_dictionary = read_txt_to_array('scripts/livesource/地方台/黑龙江频道.txt')
jilin_dictionary = read_txt_to_array('scripts/livesource/地方台/吉林频道.txt')
shanxi2_dictionary = read_txt_to_array('scripts/livesource/地方台/山西频道.txt')
guangxi_dictionary = read_txt_to_array('scripts/livesource/地方台/广西频道.txt')
yunnan_dictionary = read_txt_to_array('scripts/livesource/地方台/云南频道.txt')
guizhou_dictionary = read_txt_to_array('scripts/livesource/地方台/贵州频道.txt')
gansu_dictionary = read_txt_to_array('scripts/livesource/地方台/甘肃频道.txt')
neimenggu_dictionary = read_txt_to_array('scripts/livesource/地方台/内蒙频道.txt')
xinjiang_dictionary = read_txt_to_array('scripts/livesource/地方台/新疆频道.txt')
hainan_dictionary = read_txt_to_array('scripts/livesource/地方台/海南频道.txt')
ningxia_dictionary = read_txt_to_array('scripts/livesource/地方台/宁夏频道.txt')
qinghai_dictionary = read_txt_to_array('scripts/livesource/地方台/青海频道.txt')
xizang_dictionary = read_txt_to_array('scripts/livesource/地方台/西藏频道.txt')

# 定制频道字典
news_dictionary = read_txt_to_array('scripts/livesource/主频道/新闻频道.txt')
shuzi_dictionary = read_txt_to_array('scripts/livesource/主频道/数字频道.txt')
dianying_dictionary = read_txt_to_array('scripts/livesource/主频道/电影频道.txt')
jieshuo_dictionary = read_txt_to_array('scripts/livesource/主频道/解说频道.txt')
zongyi_dictionary = read_txt_to_array('scripts/livesource/主频道/综艺频道.txt')
huya_dictionary = read_txt_to_array('scripts/livesource/主频道/虎牙直播.txt')
douyu_dictionary = read_txt_to_array('scripts/livesource/主频道/斗鱼直播.txt')
xianggang_dictionary = read_txt_to_array('scripts/livesource/主频道/香港频道.txt')
aomen_dictionary = read_txt_to_array('scripts/livesource/主频道/澳门频道.txt')
china_dictionary = read_txt_to_array('scripts/livesource/主频道/中国频道.txt')
guoji_dictionary = read_txt_to_array('scripts/livesource/主频道/国际频道.txt')
gangaotai_dictionary = read_txt_to_array('scripts/livesource/主频道/港澳台.txt')
dianshiju_dictionary = read_txt_to_array('scripts/livesource/主频道/电视剧.txt')
radio_dictionary = read_txt_to_array('scripts/livesource/主频道/收音机.txt')
donghuapian_dictionary = read_txt_to_array('scripts/livesource/主频道/动画片.txt')
jilupian_dictionary = read_txt_to_array('scripts/livesource/主频道/记录片.txt')
tiyu_dictionary = read_txt_to_array('scripts/livesource/主频道/体育频道.txt')
tiyusaishi_dictionary = read_txt_to_array('scripts/livesource/主频道/体育赛事.txt')
youxi_dictionary = read_txt_to_array('scripts/livesource/主频道/游戏频道.txt')
xiqu_dictionary = read_txt_to_array('scripts/livesource/主频道/戏曲频道.txt')
yinyue_dictionary = read_txt_to_array('scripts/livesource/主频道/音乐频道.txt')
chunwan_dictionary = read_txt_to_array('scripts/livesource/主频道/春晚频道.txt')
zhibozhongguo_dictionary = read_txt_to_array('scripts/livesource/主频道/直播中国.txt')

#读取纠错频道名称方法
def load_corrections_name(filename):
    corrections = {}
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): #跳过空行
                continue
            parts = line.strip().split(',')
            correct_name = parts[0]
            for name in parts[1:]:
                corrections[name] = correct_name
    return corrections

#读取纠错文件
corrections_name = load_corrections_name('scripts/livesource/corrections_name.txt')

#纠错频道名称
def correct_name_data(corrections, data):
    corrected_data = []
    for line in data:
        line = line.strip()
        if ',' not in line:
            # 行格式错误：跳过或记录
            continue

        name, url = line.split(',', 1)

        # 空 name 处理（可选）
        if name in corrections and name != corrections[name]:
            name = corrections[name]

        corrected_data.append(f"{name},{url}")
    return corrected_data

def sort_data(order, data):
    # 创建一个字典来存储每行数据的索引
    order_dict = {name: i for i, name in enumerate(order)}
    
    # 定义一个排序键函数，处理不在 order_dict 中的字符串
    def sort_key(line):
        name = line.split(',')[0]
        return order_dict.get(name, len(order))
    
    # 按照 order 中的顺序对数据进行排序
    sorted_data = sorted(data, key=sort_key)
    return sorted_data

# 定义
urls = read_txt_to_array('scripts/livesource/urls-daily.txt')
# 处理
for url in urls:
    if url.startswith("http"):
        if "{MMdd}" in url: #特别处理113
            current_date_str = datetime.now().strftime("%m%d")
            url=url.replace("{MMdd}", current_date_str)

        if "{MMdd-1}" in url: #特别处理113
            yesterday_date_str = (datetime.now() - timedelta(days=1)).strftime("%m%d")
            url=url.replace("{MMdd-1}", yesterday_date_str)
            
        print(f"处理URL: {url}")
        process_url(url)

# 定义一个函数，提取每行中逗号前面的数字部分作为排序的依据
def extract_number(s):
    num_str = s.split(',')[0].split('-')[1]  # 提取逗号前面的数字部分
    numbers = re.findall(r'\d+', num_str)   #因为有+和K
    return int(numbers[-1]) if numbers else 999

# 定义一个自定义排序函数
def custom_sort(s):
    if "CCTV-4K" in s:
        return 2  # 将包含 "4K" 的字符串排在后面
    elif "CCTV-8K" in s:
        return 3  # 将包含 "8K" 的字符串排在后面 
    elif "(4K)" in s:
        return 1  # 将包含 " (4K)" 的字符串排在后面
    else:
        return 0  # 其他字符串保持原顺序

#读取whitelist,把高响应源从白名单中抽出加入merged_output。
print(f"ADD whitelist_auto.txt")
whitelist_auto_lines=read_txt_to_array('scripts/livesource/blacklist/whitelist_auto.txt') #
for whitelist_line in whitelist_auto_lines:
    if  "#genre#" not in whitelist_line and "," in whitelist_line and "://" in whitelist_line:
        whitelist_parts = whitelist_line.split(",")
        try:
            response_time = float(whitelist_parts[0].replace("ms", ""))
        except ValueError:
            print(f"response_time转换失败: {whitelist_line}")
            response_time = 60000  # 单位毫秒，转换失败给个60秒
        if response_time < 2000:  #2s以内的高响应源
            process_channel_line(",".join(whitelist_parts[1:]))

def get_http_response(url, timeout=8, retries=2, backoff_factor=1.0):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
                return data.decode('utf-8')
        except urllib.error.HTTPError as e:
            print(f"[HTTPError] Code: {e.code}, URL: {url}")
            break  # 一般来说 HTTP 错误不会在重试中恢复
        except urllib.error.URLError as e:
            print(f"[URLError] Reason: {e.reason}, Attempt: {attempt + 1}")
        except socket.timeout:
            print(f"[Timeout] URL: {url}, Attempt: {attempt + 1}")
        except Exception as e:
            print(f"[Exception] {type(e).__name__}: {e}, Attempt: {attempt + 1}")
        
        # 等待一段时间后重试
        if attempt < retries - 1:
            time.sleep(backoff_factor * (2 ** attempt))
    
    return None  # 所有尝试失败后返回 None

# 将日期统一格式化为 MM-DD格式
def normalize_date_to_md(text):
    text = text.strip()

    # 定义替换函数：确保后面有一个空格
    def format_md(m):
        month = int(m.group(1))
        day = int(m.group(2))
        after = m.group(3) or ''
        # 如果 after 不是以空格开头，就加一个空格
        if not after.startswith(' '):
            after = ' ' + after
        return f"{month}-{day}{after}"

    # MM/DD
    text = re.sub(r'^0?(\d{1,2})/0?(\d{1,2})(.*)', format_md, text)

    # YYYY-MM-DD
    text = re.sub(r'^\d{4}-0?(\d{1,2})-0?(\d{1,2})(.*)', format_md, text)

    # 中文日期
    text = re.sub(r'^0?(\d{1,2})月0?(\d{1,2})日(.*)', format_md, text)

    return text

# 将日期统一格式化为 MM-DD格式
normalized_tiyusaishi_lines = [normalize_date_to_md(s) for s in tiyusaishi_lines]

#AKTV#
aktv_lines = [] #AKTV
aktv_url = "https://aktv.space/live.m3u" #AKTV

aktv_text = get_http_response(aktv_url)
if aktv_text:
    print("AKTV成功获取内容")
    aktv_text = convert_m3u_to_txt(aktv_text)
    aktv_lines = aktv_text.strip().split('\n')
else:
    print("AKTV请求失败，从本地获取！")
    aktv_lines = read_txt_to_array('scripts/livesource/手工区/AKTV.txt')

def generate_playlist_html(data_list, output_file='playlist.html'):
    html_head = '''
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">        
        <script async src="https://pagead2.googlesyndication.compagead/js/adsbygoogle.js?client=ca-pub-6061710286208572"
     crossorigin="anonymous"></script>
        <!-- Setup Google Analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-BS1Z4F5BDN"></script>
        <script> 
        window.dataLayer = window.dataLayer || []; 
        function gtag(){dataLayer.push(arguments);} 
        gtag('js', new Date()); 
        gtag('config', 'G-BS1Z4F5BDN'); 
        </script>
        <title>最新体育赛事</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background: #f9f9f9; }
            .item { margin-bottom: 20px; padding: 12px; background: #fff; border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.06); }
            .title { font-weight: bold; font-size: 1.1em; color: #333; margin-bottom: 5px; }
            .url-wrapper { display: flex; align-items: center; gap: 10px; }
            .url {
                max-width: 80%;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                font-size: 0.9em;
                color: #555;
                background: #f0f0f0;
                padding: 6px;
                border-radius: 4px;
                flex-grow: 1;
            }
            .copy-btn {
                background-color: #007BFF;
                border: none;
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.8em;
            }
            .copy-btn:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
    <h2>📋 最新体育赛事列表</h2>
    '''

    html_body = ''
    for idx, entry in enumerate(data_list):
        if ',' not in entry:
            continue
        info, url = entry.split(',', 1)
        url_id = f"url_{idx}"
        html_body += f'''
        <div class="item">
            <div class="title">🕒 {info}</div>
            <div class="url-wrapper">
                <div class="url" id="{url_id}">{url}</div>
                <button class="copy-btn" onclick="copyToClipboard('{url_id}')">复制</button>
            </div>
        </div>
        '''

    html_tail = '''
    <script>
        function copyToClipboard(id) {
            const el = document.getElementById(id);
            const text = el.textContent;
            navigator.clipboard.writeText(text).then(() => {
                alert("已复制链接！");
            }).catch(err => {
                alert("复制失败: " + err);
            });
        }
    </script>
    </body>
    </html>
    '''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_head + html_body + html_tail)
    print(f"✅ 网页已生成：{output_file}")

generate_playlist_html(sorted(set(normalized_tiyusaishi_lines)), 'output/livesource/sports.html')

# 随机取得URL
def get_random_url(file_path):
    urls = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # 查找逗号后面的部分，即URL
            url = line.strip().split(',')[-1]
            urls.append(url)    
    # 随机返回一个URL
    return random.choice(urls) if urls else None

# 获取当前的 UTC 时间
utc_time = datetime.now(timezone.utc)
# 北京时间
beijing_time = utc_time + timedelta(hours=8)
# 格式化为所需的格式
formatted_time = beijing_time.strftime("%Y%m%d %H:%M:%S")

version=formatted_time+","+get_random_url('scripts/livesource/手工区/今日推台.txt')
about="xiaoranmuze,"+get_random_url('scripts/livesource/手工区/今日推台.txt')

daily_mtv="今日推荐,"+get_random_url('scripts/livesource/手工区/今日推荐.txt')
daily_mtv1="🔥低调,"+get_random_url('scripts/livesource/手工区/今日推荐.txt')
daily_mtv2="🔥使用,"+get_random_url('scripts/livesource/手工区/今日推荐.txt')
daily_mtv3="🔥禁止,"+get_random_url('scripts/livesource/手工区/今日推荐.txt')
daily_mtv4="🔥贩卖,"+get_random_url('scripts/livesource/手工区/今日推荐.txt')

# 增加手工区
print(f"处理手工区...")
# 按照手工区映射进行处理
hubei_lines = hubei_lines + read_txt_to_array('scripts/livesource/手工区/湖北频道.txt')
guoji_lines = guoji_lines + read_txt_to_array('scripts/livesource/手工区/国际频道.txt')
gangaotai_lines = gangaotai_lines + read_txt_to_array('scripts/livesource/手工区/港·澳·台.txt')
donghuapian_lines = donghuapian_lines + read_txt_to_array('scripts/livesource/手工区/动·画·片.txt')
radio_lines = radio_lines + read_txt_to_array('scripts/livesource/手工区/收·音·机.txt')
jilupian_lines = jilupian_lines + read_txt_to_array('scripts/livesource/手工区/记·录·片.txt')
xianggang_lines = xianggang_lines + read_txt_to_array('scripts/livesource/手工区/香港频道.txt')
aomen_lines = aomen_lines + read_txt_to_array('scripts/livesource/手工区/澳门频道.txt')
china_lines = china_lines + read_txt_to_array('scripts/livesource/手工区/中国频道.txt')

# 最终去重处理所有分类列表
print("正在进行最终去重处理...")
all_category_lists = [
    yangshi_lines, weishi_lines, beijing_lines, shanghai_lines, tianjin_lines, chongqing_lines,
    guangdong_lines, jiangsu_lines, zhejiang_lines, shandong_lines, henan_lines, sichuan_lines,
    hebei_lines, hunan_lines, hubei_lines, anhui_lines, fujian_lines, shanxi1_lines, liaoning_lines,
    jiangxi_lines, heilongjiang_lines, jilin_lines, shanxi2_lines, guangxi_lines, yunnan_lines,
    guizhou_lines, gansu_lines, neimenggu_lines, xinjiang_lines, hainan_lines, ningxia_lines,
    qinghai_lines, xizang_lines, news_lines, shuzi_lines, dianying_lines, jieshuo_lines, zongyi_lines,
    huya_lines, douyu_lines, xianggang_lines, aomen_lines, china_lines, guoji_lines, gangaotai_lines,
    dianshiju_lines, radio_lines, donghuapian_lines, jilupian_lines, tiyu_lines, tiyusaishi_lines,
    youxi_lines, xiqu_lines, yinyue_lines, chunwan_lines, zhibozhongguo_lines
]

# 对每个分类列表进行最终去重
for i, category_list in enumerate(all_category_lists):
    all_category_lists[i] = final_deduplicate_lines(category_list)

# 重新赋值去重后的列表
(yangshi_lines, weishi_lines, beijing_lines, shanghai_lines, tianjin_lines, chongqing_lines,
 guangdong_lines, jiangsu_lines, zhejiang_lines, shandong_lines, henan_lines, sichuan_lines,
 hebei_lines, hunan_lines, hubei_lines, anhui_lines, fujian_lines, shanxi1_lines, liaoning_lines,
 jiangxi_lines, heilongjiang_lines, jilin_lines, shanxi2_lines, guangxi_lines, yunnan_lines,
 guizhou_lines, gansu_lines, neimenggu_lines, xinjiang_lines, hainan_lines, ningxia_lines,
 qinghai_lines, xizang_lines, news_lines, shuzi_lines, dianying_lines, jieshuo_lines, zongyi_lines,
 huya_lines, douyu_lines, xianggang_lines, aomen_lines, china_lines, guoji_lines, gangaotai_lines,
 dianshiju_lines, radio_lines, donghuapian_lines, jilupian_lines, tiyu_lines, tiyusaishi_lines,
 youxi_lines, xiqu_lines, yinyue_lines, chunwan_lines, zhibozhongguo_lines) = all_category_lists

# 完整版 合并所有对象中的行文本
all_lines_full = ["🌐央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name, yangshi_lines)) + ['\n'] + \
    ["📡卫视频道,#genre#"] + sort_data(weishi_dictionary, correct_name_data(corrections_name, weishi_lines)) + ['\n'] + \
    ["🏙️北京频道,#genre#"] + sort_data(beijing_dictionary, set(correct_name_data(corrections_name, beijing_lines))) + ['\n'] + \
    ["🏙️上海频道,#genre#"] + sort_data(shanghai_dictionary, set(correct_name_data(corrections_name, shanghai_lines))) + ['\n'] + \
    ["🏙️天津频道,#genre#"] + sort_data(tianjin_dictionary, set(correct_name_data(corrections_name, tianjin_lines))) + ['\n'] + \
    ["🏙️重庆频道,#genre#"] + sort_data(chongqing_dictionary, set(correct_name_data(corrections_name, chongqing_lines))) + ['\n'] + \
    ["🏙️广东频道,#genre#"] + sort_data(guangdong_dictionary, set(correct_name_data(corrections_name, guangdong_lines))) + ['\n'] + \
    ["🏙️江苏频道,#genre#"] + sort_data(jiangsu_dictionary, set(correct_name_data(corrections_name, jiangsu_lines))) + ['\n'] + \
    ["🏙️浙江频道,#genre#"] + sort_data(zhejiang_dictionary, set(correct_name_data(corrections_name, zhejiang_lines))) + ['\n'] + \
    ["🏙️山东频道,#genre#"] + sort_data(shandong_dictionary, set(correct_name_data(corrections_name, shandong_lines))) + ['\n'] + \
    ["🏙️河南频道,#genre#"] + sort_data(henan_dictionary, set(correct_name_data(corrections_name, henan_lines))) + ['\n'] + \
    ["🏙️四川频道,#genre#"] + sort_data(sichuan_dictionary, set(correct_name_data(corrections_name, sichuan_lines))) + ['\n'] + \
    ["🏙️河北频道,#genre#"] + sort_data(hebei_dictionary, set(correct_name_data(corrections_name, hebei_lines))) + ['\n'] + \
    ["🏙️湖南频道,#genre#"] + sort_data(hunan_dictionary, set(correct_name_data(corrections_name, hunan_lines))) + ['\n'] + \
    ["🏙️湖北频道,#genre#"] + sort_data(hubei_dictionary, set(correct_name_data(corrections_name, hubei_lines))) + ['\n'] + \
    ["🏙️安徽频道,#genre#"] + sort_data(anhui_dictionary, set(correct_name_data(corrections_name, anhui_lines))) + ['\n'] + \
    ["🏙️福建频道,#genre#"] + sort_data(fujian_dictionary, set(correct_name_data(corrections_name, fujian_lines))) + ['\n'] + \
    ["🏙️陕西频道,#genre#"] + sort_data(shanxi1_dictionary, set(correct_name_data(corrections_name, shanxi1_lines))) + ['\n'] + \
    ["🏙️辽宁频道,#genre#"] + sort_data(liaoning_dictionary, set(correct_name_data(corrections_name, liaoning_lines))) + ['\n'] + \
    ["🏙️江西频道,#genre#"] + sort_data(jiangxi_dictionary, set(correct_name_data(corrections_name, jiangxi_lines))) + ['\n'] + \
    ["🏙️黑龙江频道,#genre#"] + sort_data(heilongjiang_dictionary, set(correct_name_data(corrections_name, heilongjiang_lines))) + ['\n'] + \
    ["🏙️吉林频道,#genre#"] + sort_data(jilin_dictionary, set(correct_name_data(corrections_name, jilin_lines))) + ['\n'] + \
    ["🏙️山西频道,#genre#"] + sort_data(shanxi2_dictionary, set(correct_name_data(corrections_name, shanxi2_lines))) + ['\n'] + \
    ["🏙️广西频道,#genre#"] + sort_data(guangxi_dictionary, set(correct_name_data(corrections_name, guangxi_lines))) + ['\n'] + \
    ["🏙️云南频道,#genre#"] + sort_data(yunnan_dictionary, set(correct_name_data(corrections_name, yunnan_lines))) + ['\n'] + \
    ["🏙️贵州频道,#genre#"] + sort_data(guizhou_dictionary, set(correct_name_data(corrections_name, guizhou_lines))) + ['\n'] + \
    ["🏙️甘肃频道,#genre#"] + sort_data(gansu_dictionary, set(correct_name_data(corrections_name, gansu_lines))) + ['\n'] + \
    ["🏙️内蒙频道,#genre#"] + sort_data(neimenggu_dictionary, set(correct_name_data(corrections_name, neimenggu_lines))) + ['\n'] + \
    ["🏙️新疆频道,#genre#"] + sort_data(xinjiang_dictionary, set(correct_name_data(corrections_name, xinjiang_lines))) + ['\n'] + \
    ["🏙️海南频道,#genre#"] + sort_data(hainan_dictionary, set(correct_name_data(corrections_name, hainan_lines))) + ['\n'] + \
    ["🏙️宁夏频道,#genre#"] + sort_data(ningxia_dictionary, set(correct_name_data(corrections_name, ningxia_lines))) + ['\n'] + \
    ["🏙️青海频道,#genre#"] + sort_data(qinghai_dictionary, set(correct_name_data(corrections_name, qinghai_lines))) + ['\n'] + \
    ["🏙️西藏频道,#genre#"] + sort_data(xizang_dictionary, set(correct_name_data(corrections_name, xizang_lines))) + ['\n'] + \
    ["📰新闻频道,#genre#"] + sort_data(news_dictionary, set(correct_name_data(corrections_name, news_lines))) + ['\n'] + \
    ["🔢数字频道,#genre#"] + sort_data(shuzi_dictionary, set(correct_name_data(corrections_name, shuzi_lines))) + ['\n'] + \
    ["🎬电影频道,#genre#"] + sort_data(dianying_dictionary, set(correct_name_data(corrections_name, dianying_lines))) + ['\n'] + \
    ["🎙️解说频道,#genre#"] + sort_data(jieshuo_dictionary, set(correct_name_data(corrections_name, jieshuo_lines))) + ['\n'] + \
    ["🎭综艺频道,#genre#"] + sort_data(zongyi_dictionary, set(correct_name_data(corrections_name, zongyi_lines))) + ['\n'] + \
    ["🐯虎牙直播,#genre#"] + sort_data(huya_dictionary, set(correct_name_data(corrections_name, huya_lines))) + ['\n'] + \
    ["🐬斗鱼直播,#genre#"] + sort_data(douyu_dictionary, set(correct_name_data(corrections_name, douyu_lines))) + ['\n'] + \
    ["🇭🇰香港频道,#genre#"] + sort_data(xianggang_dictionary, set(correct_name_data(corrections_name, xianggang_lines))) + ['\n'] + \
    ["🇲🇴澳门频道,#genre#"] + sort_data(aomen_dictionary, set(correct_name_data(corrections_name, aomen_lines))) + ['\n'] + \
    ["🇨🇳中国频道,#genre#"] + sort_data(china_dictionary, set(correct_name_data(corrections_name, china_lines))) + ['\n'] + \
    ["🌍国际频道,#genre#"] + sort_data(guoji_dictionary, set(correct_name_data(corrections_name, guoji_lines))) + ['\n'] + \
    ["🇨🇳港澳台,#genre#"] + sort_data(gangaotai_dictionary, set(correct_name_data(corrections_name, gangaotai_lines))) + ['\n'] + \
    ["📺电视剧,#genre#"] + sort_data(dianshiju_dictionary, set(correct_name_data(corrections_name, dianshiju_lines))) + ['\n'] + \
    ["📻收音机,#genre#"] + sort_data(radio_dictionary, set(correct_name_data(corrections_name, radio_lines))) + ['\n'] + \
    ["🐶动画片,#genre#"] + sort_data(donghuapian_dictionary, set(correct_name_data(corrections_name, donghuapian_lines))) + ['\n'] + \
    ["🎞️记录片,#genre#"] + sort_data(jilupian_dictionary, set(correct_name_data(corrections_name, jilupian_lines))) + ['\n'] + \
    ["⚽体育频道,#genre#"] + sort_data(tiyu_dictionary, set(correct_name_data(corrections_name, tiyu_lines))) + ['\n'] + \
    ["🏆体育赛事,#genre#"] + normalized_tiyusaishi_lines + ['\n'] + \
    ["🎮游戏频道,#genre#"] + sort_data(youxi_dictionary, set(correct_name_data(corrections_name, youxi_lines))) + ['\n'] + \
    ["🎭戏曲频道,#genre#"] + sort_data(xiqu_dictionary, set(correct_name_data(corrections_name, xiqu_lines))) + ['\n'] + \
    ["🎵音乐频道,#genre#"] + sort_data(yinyue_dictionary, set(correct_name_data(corrections_name, yinyue_lines))) + ['\n'] + \
    ["🎉春晚频道,#genre#"] + sort_data(chunwan_dictionary, set(correct_name_data(corrections_name, chunwan_lines))) + ['\n'] + \
    ["📹直播中国,#genre#"] + sort_data(zhibozhongguo_dictionary, set(correct_name_data(corrections_name, zhibozhongguo_lines))) + ['\n'] + \
    ["🕒更新时间,#genre#"] + [version] + [about] + [daily_mtv] + [daily_mtv1] + [daily_mtv2] + [daily_mtv3] + [daily_mtv4] + read_txt_to_array('scripts/livesource/手工区/about.txt') + ['\n']

# 瘦身版
all_lines_lite = ["央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name, yangshi_lines)) + ['\n'] + \
    ["卫视频道,#genre#"] + sort_data(weishi_dictionary, correct_name_data(corrections_name, weishi_lines)) + ['\n'] + \
    ["地方频道,#genre#"] + \
    sort_data(hubei_dictionary, set(correct_name_data(corrections_name, hubei_lines))) + \
    sort_data(hunan_dictionary, set(correct_name_data(corrections_name, hunan_lines))) + \
    sort_data(zhejiang_dictionary, set(correct_name_data(corrections_name, zhejiang_lines))) + \
    sort_data(guangdong_dictionary, set(correct_name_data(corrections_name, guangdong_lines))) + \
    sort_data(shandong_dictionary, set(correct_name_data(corrections_name, shandong_lines))) + \
    sorted(set(correct_name_data(corrections_name, jiangsu_lines))) + \
    sorted(set(correct_name_data(corrections_name, anhui_lines))) + \
    sorted(set(correct_name_data(corrections_name, hainan_lines))) + \
    sorted(set(correct_name_data(corrections_name, neimenggu_lines))) + \
    sorted(set(correct_name_data(corrections_name, liaoning_lines))) + \
    sorted(set(correct_name_data(corrections_name, shanxi1_lines))) + \
    sorted(set(correct_name_data(corrections_name, shanxi2_lines))) + \
    sorted(set(correct_name_data(corrections_name, yunnan_lines))) + \
    sorted(set(correct_name_data(corrections_name, beijing_lines))) + \
    sorted(set(correct_name_data(corrections_name, chongqing_lines))) + \
    sorted(set(correct_name_data(corrections_name, fujian_lines))) + \
    sorted(set(correct_name_data(corrections_name, gansu_lines))) + \
    sorted(set(correct_name_data(corrections_name, guangxi_lines))) + \
    sorted(set(correct_name_data(corrections_name, guizhou_lines))) + \
    sorted(set(correct_name_data(corrections_name, hebei_lines))) + \
    sorted(set(correct_name_data(corrections_name, henan_lines))) + \
    sorted(set(correct_name_data(corrections_name, jilin_lines))) + \
    sorted(set(correct_name_data(corrections_name, jiangxi_lines))) + \
    sorted(set(correct_name_data(corrections_name, ningxia_lines))) + \
    sorted(set(correct_name_data(corrections_name, qinghai_lines))) + \
    sorted(set(correct_name_data(corrections_name, sichuan_lines))) + \
    sorted(set(correct_name_data(corrections_name, tianjin_lines))) + \
    sorted(set(correct_name_data(corrections_name, xinjiang_lines))) + \
    sorted(set(correct_name_data(corrections_name, heilongjiang_lines))) + \
    ['\n'] + \
    ["更新时间,#genre#"] + [version] + ['\n']

# custom定制
all_lines_custom = ["🌐央视频道,#genre#"] + sort_data(yangshi_dictionary, correct_name_data(corrections_name, yangshi_lines)) + ['\n'] + \
    ["📡卫视频道,#genre#"] + sort_data(weishi_dictionary, correct_name_data(corrections_name, weishi_lines)) + ['\n'] + \
    ["🏠地方频道,#genre#"] + \
    sort_data(hubei_dictionary, set(correct_name_data(corrections_name, hubei_lines))) + \
    sort_data(hunan_dictionary, set(correct_name_data(corrections_name, hunan_lines))) + \
    sort_data(zhejiang_dictionary, set(correct_name_data(corrections_name, zhejiang_lines))) + \
    sort_data(guangdong_dictionary, set(correct_name_data(corrections_name, guangdong_lines))) + \
    sort_data(shandong_dictionary, set(correct_name_data(corrections_name, shandong_lines))) + \
    sorted(set(correct_name_data(corrections_name, jiangsu_lines))) + \
    sorted(set(correct_name_data(corrections_name, anhui_lines))) + \
    sorted(set(correct_name_data(corrections_name, hainan_lines))) + \
    sorted(set(correct_name_data(corrections_name, neimenggu_lines))) + \
    sorted(set(correct_name_data(corrections_name, liaoning_lines))) + \
    sorted(set(correct_name_data(corrections_name, shanxi1_lines))) + \
    sorted(set(correct_name_data(corrections_name, shanxi2_lines))) + \
    sorted(set(correct_name_data(corrections_name, yunnan_lines))) + \
    sorted(set(correct_name_data(corrections_name, beijing_lines))) + \
    sorted(set(correct_name_data(corrections_name, chongqing_lines))) + \
    sorted(set(correct_name_data(corrections_name, fujian_lines))) + \
    sorted(set(correct_name_data(corrections_name, gansu_lines))) + \
    sorted(set(correct_name_data(corrections_name, guangxi_lines))) + \
    sorted(set(correct_name_data(corrections_name, guizhou_lines))) + \
    sorted(set(correct_name_data(corrections_name, hebei_lines))) + \
    sorted(set(correct_name_data(corrections_name, henan_lines))) + \
    sorted(set(correct_name_data(corrections_name, jilin_lines))) + \
    sorted(set(correct_name_data(corrections_name, jiangxi_lines))) + \
    sorted(set(correct_name_data(corrections_name, ningxia_lines))) + \
    sorted(set(correct_name_data(corrections_name, qinghai_lines))) + \
    sorted(set(correct_name_data(corrections_name, sichuan_lines))) + \
    sorted(set(correct_name_data(corrections_name, tianjin_lines))) + \
    sorted(set(correct_name_data(corrections_name, xinjiang_lines))) + \
    sorted(set(correct_name_data(corrections_name, heilongjiang_lines))) + \
    ['\n'] + \
    ["🔢数字频道,#genre#"] + sort_data(shuzi_dictionary, set(correct_name_data(corrections_name, shuzi_lines))) + ['\n'] + \
    ["🌍国际频道,#genre#"] + sort_data(guoji_dictionary, set(correct_name_data(corrections_name, guoji_lines))) + ['\n'] + \
    ["⚽体育频道,#genre#"] + sort_data(tiyu_dictionary, set(correct_name_data(corrections_name, tiyu_lines))) + ['\n'] + \
    ["🏆体育赛事,#genre#"] + normalized_tiyusaishi_lines + ['\n'] + \
    ["🐬斗鱼直播,#genre#"] + sort_data(douyu_dictionary, set(correct_name_data(corrections_name, douyu_lines))) + ['\n'] + \
    ["🐯虎牙直播,#genre#"] + sort_data(huya_dictionary, set(correct_name_data(corrections_name, huya_lines))) + ['\n'] + \
    ["🎙️解说频道,#genre#"] + sort_data(jieshuo_dictionary, set(correct_name_data(corrections_name, jieshuo_lines))) + ['\n'] + \
    ["🎬电影频道,#genre#"] + sort_data(dianying_dictionary, set(correct_name_data(corrections_name, dianying_lines))) + ['\n'] + \
    ["📺电视剧,#genre#"] + sort_data(dianshiju_dictionary, set(correct_name_data(corrections_name, dianshiju_lines))) + ['\n'] + \
    ["🎞️记录片,#genre#"] + sort_data(jilupian_dictionary, set(correct_name_data(corrections_name, jilupian_lines))) + ['\n'] + \
    ["🐶动画片,#genre#"] + sort_data(donghuapian_dictionary, set(correct_name_data(corrections_name, donghuapian_lines))) + ['\n'] + \
    ["📻收音机,#genre#"] + sort_data(radio_dictionary, set(correct_name_data(corrections_name, radio_lines))) + ['\n'] + \
    ["🇨🇳港澳台,#genre#"] + sort_data(gangaotai_dictionary, set(correct_name_data(corrections_name, gangaotai_lines))) + ['\n'] + \
    ["🇭🇰香港频道,#genre#"] + sort_data(xianggang_dictionary, set(correct_name_data(corrections_name, xianggang_lines))) + ['\n'] + \
    ["🇲🇴澳门频道,#genre#"] + sort_data(aomen_dictionary, set(correct_name_data(corrections_name, aomen_lines))) + ['\n'] + \
    ["🎭戏曲频道,#genre#"] + sort_data(xiqu_dictionary, set(correct_name_data(corrections_name, xiqu_lines))) + ['\n'] + \
    ["🎵音乐频道,#genre#"] + sort_data(yinyue_dictionary, set(correct_name_data(corrections_name, yinyue_lines))) + ['\n'] + \
    ["🎭综艺频道,#genre#"] + sorted(set(correct_name_data(corrections_name, zongyi_lines))) + ['\n'] + \
    ["🎮游戏频道,#genre#"] + sorted(set(correct_name_data(corrections_name, youxi_lines))) + ['\n'] + \
    ["📹直播中国,#genre#"] + sort_data(zhibozhongguo_dictionary, set(correct_name_data(corrections_name, zhibozhongguo_lines))) + ['\n'] + \
    ["🎉春晚频道,#genre#"] + sort_data(chunwan_dictionary, set(correct_name_data(corrections_name, chunwan_lines))) + ['\n'] + \
    ["🕒更新时间,#genre#"] + [version] + [about] + [daily_mtv] + [daily_mtv1] + [daily_mtv2] + [daily_mtv3] + [daily_mtv4] + read_txt_to_array('scripts/livesource/手工区/about.txt') + ['\n']

print("对最终输出进行去重...")
all_lines_full = final_deduplicate_lines(all_lines_full)
all_lines_lite = final_deduplicate_lines(all_lines_lite)
all_lines_custom = final_deduplicate_lines(all_lines_custom)
other_lines = final_deduplicate_lines(other_lines)

# 将合并后的文本写入文件
output_full = "output/livesource/full.txt"
output_lite = "output/livesource/lite.txt"
output_custom = "output/livesource/custom.txt"
output_other = "output/livesource/other.txt"

try:
    # 完整版
    with open(output_full, 'w', encoding='utf-8') as f:
        for line in all_lines_full:
            f.write(line + '\n')
    print(f"完整版已保存到文件: {output_full}")

    # 精简版
    with open(output_lite, 'w', encoding='utf-8') as f:
        for line in all_lines_lite:
            f.write(line + '\n')
    print(f"精简版已保存到文件: {output_lite}")

    # 定制版
    with open(output_custom, 'w', encoding='utf-8') as f:
        for line in all_lines_custom:
            f.write(line + '\n')
    print(f"定制版已保存到文件: {output_custom}")

    # 其它源
    with open(output_other, 'w', encoding='utf-8') as f:
        f.write("其它频道,#genre#\n")
        channel_count = 0
        for line in other_lines:
            if "," in line and "://" in line:  # 只统计真正的频道行
                f.write(line + '\n')
                channel_count += 1
            else:
                f.write(line + '\n')
        # 可选：在文件末尾添加统计信息
        f.write(f"\n# 其它频道总计: {channel_count} 个频道\n")
    print(f"其它源已保存到文件: {output_other}")

except Exception as e:
    print(f"保存文件时发生错误：{e}")

########## 添加生成m3u文件
channels_logos=read_txt_to_array('scripts/livesource/logo.txt') #读入logo库
def get_logo_by_channel_name(channel_name):
    
    # 遍历数组查找频道名称
    for line in channels_logos:
        # 去除首尾空白并检查是否为空行(没有这个判断logo中如果出现空行会出错)
        if not line.strip():
            continue
        name, url = line.split(',')
        if name == channel_name:
            return url
    return None

def make_m3u(txt_file, m3u_file):
    try:
        output_text = '#EXTM3U x-tvg-url="https://live.fanmingming.cn/e.xml"\n'

        with open(txt_file, "r", encoding='utf-8') as file:
            input_text = file.read()

        lines = input_text.strip().split("\n")
        group_name = ""
        for line in lines:
            parts = line.split(",")
            if len(parts) == 2 and "#genre#" in line:
                group_name = parts[0]
            elif len(parts) == 2:
                channel_name = parts[0]
                channel_url = parts[1]
                logo_url=get_logo_by_channel_name(channel_name)
                if logo_url is None:  #not found logo
                    output_text += f"#EXTINF:-1 group-title=\"{group_name}\",{channel_name}\n"
                    output_text += f"{channel_url}\n"
                else:
                    output_text += f"#EXTINF:-1  tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\"  group-title=\"{group_name}\",{channel_name}\n"
                    output_text += f"{channel_url}\n"

        with open(f"{m3u_file}", "w", encoding='utf-8') as file:
            file.write(output_text)

        print(f"M3U文件 '{m3u_file}' 生成成功。")
    except Exception as e:
        print(f"发生错误: {e}")

make_m3u(output_full, output_full.replace(".txt", ".m3u"))
make_m3u(output_lite, output_lite.replace(".txt", ".m3u"))
make_m3u(output_custom, output_custom.replace(".txt", ".m3u"))

# 执行结束时间
timeend = datetime.now()

# 计算时间差
elapsed_time = timeend - timestart
total_seconds = elapsed_time.total_seconds()

# 转换为分钟和秒
minutes = int(total_seconds // 60)
seconds = int(total_seconds % 60)
# 格式化开始和结束时间
timestart_str = timestart.strftime("%Y%m%d_%H_%M_%S")
timeend_str = timeend.strftime("%Y%m%d_%H_%M_%S")

print(f"开始时间: {timestart_str}")
print(f"结束时间: {timeend_str}")
print(f"执行时间: {minutes} 分 {seconds} 秒")

# 详细统计信息
print("\n" + "="*50)
print("📊 详细统计信息")
print("="*50)

# 计算实际频道数量（排除分类标题和空行）
def count_actual_channels(lines):
    count = 0
    for line in lines:
        if line and "#genre#" not in line and line != '\n' and "," in line and "://" in line:
            count += 1
    return count

# 主频道统计
yangshi_count = count_actual_channels(yangshi_lines)
weishi_count = count_actual_channels(weishi_lines)

# 地方台统计
local_counts = {
    "北京": count_actual_channels(beijing_lines),
    "上海": count_actual_channels(shanghai_lines),
    "天津": count_actual_channels(tianjin_lines),
    "重庆": count_actual_channels(chongqing_lines),
    "广东": count_actual_channels(guangdong_lines),
    "江苏": count_actual_channels(jiangsu_lines),
    "浙江": count_actual_channels(zhejiang_lines),
    "山东": count_actual_channels(shandong_lines),
    "河南": count_actual_channels(henan_lines),
    "四川": count_actual_channels(sichuan_lines),
    "河北": count_actual_channels(hebei_lines),
    "湖南": count_actual_channels(hunan_lines),
    "湖北": count_actual_channels(hubei_lines),
    "安徽": count_actual_channels(anhui_lines),
    "福建": count_actual_channels(fujian_lines),
    "陕西": count_actual_channels(shanxi1_lines),
    "辽宁": count_actual_channels(liaoning_lines),
    "江西": count_actual_channels(jiangxi_lines),
    "黑龙江": count_actual_channels(heilongjiang_lines),
    "吉林": count_actual_channels(jilin_lines),
    "山西": count_actual_channels(shanxi2_lines),
    "广西": count_actual_channels(guangxi_lines),
    "云南": count_actual_channels(yunnan_lines),
    "贵州": count_actual_channels(guizhou_lines),
    "甘肃": count_actual_channels(gansu_lines),
    "内蒙": count_actual_channels(neimenggu_lines),
    "新疆": count_actual_channels(xinjiang_lines),
    "海南": count_actual_channels(hainan_lines),
    "宁夏": count_actual_channels(ningxia_lines),
    "青海": count_actual_channels(qinghai_lines),
    "西藏": count_actual_channels(xizang_lines)
}

# 定制频道统计
custom_counts = {
    "新闻": count_actual_channels(news_lines),
    "数字": count_actual_channels(shuzi_lines),
    "电影": count_actual_channels(dianying_lines),
    "解说": count_actual_channels(jieshuo_lines),
    "综艺": count_actual_channels(zongyi_lines),
    "虎牙": count_actual_channels(huya_lines),
    "斗鱼": count_actual_channels(douyu_lines),
    "香港": count_actual_channels(xianggang_lines),
    "澳门": count_actual_channels(aomen_lines),
    "中国": count_actual_channels(china_lines),
    "国际": count_actual_channels(guoji_lines),
    "港澳台": count_actual_channels(gangaotai_lines),
    "电视剧": count_actual_channels(dianshiju_lines),
    "收音机": count_actual_channels(radio_lines),
    "动画片": count_actual_channels(donghuapian_lines),
    "记录片": count_actual_channels(jilupian_lines),
    "体育": count_actual_channels(tiyu_lines),
    "体育赛事": count_actual_channels(tiyusaishi_lines),
    "游戏": count_actual_channels(youxi_lines),
    "戏曲": count_actual_channels(xiqu_lines),
    "音乐": count_actual_channels(yinyue_lines),
    "春晚": count_actual_channels(chunwan_lines),
    "直播中国": count_actual_channels(zhibozhongguo_lines)
}

# 计算总数
total_local_channels = sum(local_counts.values())
total_custom_channels = sum(custom_counts.values())
total_channels = yangshi_count + weishi_count + total_local_channels + total_custom_channels
other_channels_count = count_actual_channels(other_lines)

# 版本统计
full_channels_count = count_actual_channels(all_lines_full)
lite_channels_count = count_actual_channels(all_lines_lite)
custom_channels_count = count_actual_channels(all_lines_custom)

print(f"🔧 黑名单数量: {len(combined_blacklist)}")
print(f"📺 总频道数量: {total_channels}")
print(f"📋 其它源数量: {other_channels_count}")
print()

print("📈 版本统计:")
print(f"  ✅ 完整版频道数: {full_channels_count}")
print(f"  🔸 精简版频道数: {lite_channels_count}")
print(f"  🎯 定制版频道数: {custom_channels_count}")
print()

print("🏠 主频道统计:")
print(f"  📡 央视频道: {yangshi_count}")
print(f"  🌟 卫视频道: {weishi_count}")
print()

print("📍 地方台统计 (前10):")
# 按数量排序并显示前10
sorted_local = sorted(local_counts.items(), key=lambda x: x[1], reverse=True)[:10]
for region, count in sorted_local:
    if count > 0:
        print(f"  {region}: {count}")
print(f"  ... 其它 {len(local_counts) - 10} 个地区")
print(f"  📊 地方台总数: {total_local_channels}")

print()
print("🎭 定制频道统计:")
# 按数量排序并显示前10
sorted_custom = sorted(custom_counts.items(), key=lambda x: x[1], reverse=True)[:10]
for category, count in sorted_custom:
    if count > 0:
        print(f"  {category}: {count}")
print(f"  ... 其它 {len(custom_counts) - 10} 个分类")
print(f"  📊 定制频道总数: {total_custom_channels}")

print("\n" + "="*50)
print("🎉 处理完成!")
print("="*50)