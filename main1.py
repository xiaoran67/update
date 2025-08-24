import urllib.request
from urllib.parse import urlparse
import re
import os
from datetime import datetime, timedelta, timezone
import random
import opencc

import socket
import time

# 创建输出目录（如果不存在）
os.makedirs('output/custom1/', exist_ok=True)

# 简繁转换
def traditional_to_simplified(text: str) -> str:
    converter = opencc.OpenCC('t2s')  # t2s：繁体转简体
    return converter.convert(text)

# 执行开始时间
timestart = datetime.now()

# 读取文本方法（通用）
def read_txt_to_array(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            # 跳过空行并去除首尾空格
            return [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []
    except Exception as e:
        print(f"Read file error: {e}")
        return []

# 读取黑名单（修复：避免split索引越界）
def read_blacklist_from_txt(file_path):
    blacklist = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file.readlines():
            line = line.strip()
            if ',' in line and len(line.split(',')) >= 2:  # 确保有2个以上元素
                blacklist.append(line.split(',')[1].strip())
    return blacklist

# 加载黑名单（改用集合提升检索速度）
blacklist_auto = read_blacklist_from_txt('assets/blacklist1/blacklist_auto.txt') 
blacklist_manual = read_blacklist_from_txt('assets/blacklist1/blacklist_manual.txt') 
combined_blacklist = set(blacklist_auto + blacklist_manual)  # 集合检索效率高于列表

# 定义频道分类存储列表
ys_lines = []  # CCTV
ws_lines = []  # 卫视频道
sh_lines = []  # 地方台-上海
zj_lines = []  # 地方台-浙江
jsu_lines = []  # 地方台-江苏
gd_lines = []  # 地方台-广东
hn_lines = []  # 地方台-湖南
ah_lines = []  # 地方台-安徽
hain_lines = []  # 地方台-海南
nm_lines = []  # 地方台-内蒙
hb_lines = []  # 地方台-湖北
ln_lines = []  # 地方台-辽宁
sx_lines = []  # 地方台-陕西
shanxi_lines = []  # 地方台-山西
shandong_lines = []  # 地方台-山东
yunnan_lines = []  # 地方台-云南
bj_lines = []  # 地方台-北京
cq_lines = []  # 地方台-重庆
fj_lines = []  # 地方台-福建
gs_lines = []  # 地方台-甘肃
gx_lines = []  # 地方台-广西
gz_lines = []  # 地方台-贵州
heb_lines = []  # 地方台-河北
hen_lines = []  # 地方台-河南
hlj_lines = []  # 地方台-黑龙江
jl_lines = []  # 地方台-吉林
jx_lines = []  # 地方台-江西
nx_lines = []  # 地方台-宁夏
qh_lines = []  # 地方台-青海
sc_lines = []  # 地方台-四川
tj_lines = []  # 地方台-天津
xj_lines = []  # 地方台-新疆

ty_lines = []  # 体育频道
tyss_lines = []  # 体育赛事
sz_lines = []  # 数字频道
yy_lines = []  # 音乐频道
gj_lines = []  # 国际频道
js_lines = []  # 解说
cw_lines = []  # 春晚
dy_lines = []  # 电影
dsj_lines = []  # 电视剧
gat_lines = []  # 港澳台
xg_lines = []  # 香港
aomen_lines = []  # 澳门
tw_lines = []  # 台湾
dhp_lines = []  # 动画片
douyu_lines = []  # 斗鱼直播
huya_lines = []  # 虎牙直播
radio_lines = []  # 收音机
zb_lines = []  # 直播中国
zy_lines = []  # 综艺频道
game_lines = []  # 游戏频道
xq_lines = []  # 戏曲频道
jlp_lines = []  # 记录片

other_lines = []
other_lines_url = []  # 去重用：存储已加入other的URL

# 频道名称格式化（CCTV/卫视特殊处理）
def process_name_string(input_str):
    return ','.join([process_part(part) for part in input_str.split(',')])

def process_part(part_str):
    # 处理CCTV频道（清理冗余字符+标准化格式）
    if "CCTV" in part_str and "://" not in part_str:
        part_str = part_str.replace("IPV6", "").replace("PLUS", "+").replace("1080", "")
        # 提取数字、K、+字符
        filtered_str = ''.join([c for c in part_str if c.isdigit() or c in ('K', '+')])
        # 无有效字符时保留原始名称（去除CCTV）
        if not filtered_str.strip():
            filtered_str = part_str.replace("CCTV", "")
        # 4K/8K格式标准化（如CCTV4K→CCTV(4K)）
        if len(filtered_str) > 2 and re.search(r'4K|8K', filtered_str):
            filtered_str = re.sub(r'(4K|8K).*', r'\1', filtered_str)
            if len(filtered_str) > 2:
                filtered_str = re.sub(r'(4K|8K)', r'(\1)', filtered_str)
        return f"CCTV{filtered_str}"
    
    # 处理卫视频道（清理“卫视「xxx」”格式）
    elif "卫视" in part_str:
        return re.sub(r'卫视「.*」', '卫视', part_str)
    
    return part_str

# M3U格式处理（转换为“频道名,URL”文本格式）
def get_url_file_extension(url):
    return os.path.splitext(urlparse(url).path)[1]

def convert_m3u_to_txt(m3u_content):
    txt_lines = []
    channel_name = ""
    for line in m3u_content.split('\n'):
        line = line.strip()
        if line.startswith("#EXTM3U"):
            continue
        # 提取频道名（EXTINF行）
        elif line.startswith("#EXTINF"):
            channel_name = line.split(',')[-1].strip()
        # 提取URL（http/rtmp/p3p开头）
        elif line.startswith(("http", "rtmp", "p3p")):
            txt_lines.append(f"{channel_name},{line}")
        # 兼容“频道名,URL”格式的M3U文件
        elif "#genre#" not in line and "," in line and "://" in line:
            if re.match(r'^[^,]+,[^\s]+://[^\s]+$', line):
                txt_lines.append(line)
    return '\n'.join(txt_lines)

# URL去重检查（判断URL是否已存在于列表）
def check_url_existence(data_list, url):
    return url not in [item.split(',')[1] for item in data_list]

# URL清理（去除$及其后面的参数）
def clean_url(url):
    last_dollar_idx = url.rfind('$')
    return url[:last_dollar_idx] if last_dollar_idx != -1 else url

# 频道名清理（去除冗余关键词）
removal_list = [
    "_电信", "电信", "高清", "频道", "（HD）", "-HD", "英陆", "_ITV", "(北美)", "(HK)", "AKtv",
    "「IPV4」", "「IPV6」", "频陆", "备陆", "壹陆", "贰陆", "叁陆", "肆陆", "伍陆", "陆陆", "柒陆",
    "频晴", "频粤", "[超清]", "超清", "标清", "斯特", "粤陆", "国陆", "肆柒", "频英", "频特",
    "频国", "频壹", "频贰", "肆贰", "频测", "咪咕", "闽特", "高特", "频高", "频标", "汝阳"
]
def clean_channel_name(channel_name):
    for item in removal_list:
        channel_name = channel_name.replace(item, "")
    # 去除末尾HD/台（满足长度条件时）
    if channel_name.endswith("HD"):
        channel_name = channel_name[:-2]
    if channel_name.endswith("台") and len(channel_name) > 3:
        channel_name = channel_name[:-1]
    return channel_name

# 频道分类分发（核心逻辑：按名称匹配字典分类）
def process_channel_line(line):
    if "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
        # 基础清理：频道名去冗余+简繁转换，URL清理$参数
        channel_name = clean_channel_name(line.split(',')[0].strip())
        channel_name = traditional_to_simplified(channel_name)
        channel_address = clean_url(line.split(',')[1].strip())
        line = f"{channel_name},{channel_address}"
        
        # 黑名单过滤+URL去重后分类存储
        if channel_address not in combined_blacklist:
            # CCTV频道
            if "CCTV" in channel_name and check_url_existence(ys_lines, channel_address):
                ys_lines.append(process_name_string(line.strip()))
            # 卫视频道
            elif channel_name in ws_dictionary and check_url_existence(ws_lines, channel_address):
                ws_lines.append(process_name_string(line.strip()))
            # 浙江频道
            elif channel_name in zj_dictionary and check_url_existence(zj_lines, channel_address):
                zj_lines.append(process_name_string(line.strip()))
            # 江苏频道
            elif channel_name in jsu_dictionary and check_url_existence(jsu_lines, channel_address):
                jsu_lines.append(process_name_string(line.strip()))
            # 广东频道
            elif channel_name in gd_dictionary and check_url_existence(gd_lines, channel_address):
                gd_lines.append(process_name_string(line.strip()))
            # 湖南频道
            elif channel_name in hn_dictionary and check_url_existence(hn_lines, channel_address):
                hn_lines.append(process_name_string(line.strip()))
            # 湖北频道
            elif channel_name in hb_dictionary and check_url_existence(hb_lines, channel_address):
                hb_lines.append(process_name_string(line.strip()))
            # 安徽频道
            elif channel_name in ah_dictionary and check_url_existence(ah_lines, channel_address):
                ah_lines.append(process_name_string(line.strip()))
            # 海南频道
            elif channel_name in hain_dictionary and check_url_existence(hain_lines, channel_address):
                hain_lines.append(process_name_string(line.strip()))
            # 内蒙频道
            elif channel_name in nm_dictionary and check_url_existence(nm_lines, channel_address):
                nm_lines.append(process_name_string(line.strip()))
            # 辽宁频道
            elif channel_name in ln_dictionary and check_url_existence(ln_lines, channel_address):
                ln_lines.append(process_name_string(line.strip()))
            # 陕西频道
            elif channel_name in sx_dictionary and check_url_existence(sx_lines, channel_address):
                sx_lines.append(process_name_string(line.strip()))
            # 山西频道
            elif channel_name in shanxi_dictionary and check_url_existence(shanxi_lines, channel_address):
                shanxi_lines.append(process_name_string(line.strip()))
            # 山东频道
            elif channel_name in shandong_dictionary and check_url_existence(shandong_lines, channel_address):
                shandong_lines.append(process_name_string(line.strip()))
            # 云南频道
            elif channel_name in yunnan_dictionary and check_url_existence(yunnan_lines, channel_address):
                yunnan_lines.append(process_name_string(line.strip()))
            # 北京频道
            elif channel_name in bj_dictionary and check_url_existence(bj_lines, channel_address):
                bj_lines.append(process_name_string(line.strip()))
            # 重庆频道
            elif channel_name in cq_dictionary and check_url_existence(cq_lines, channel_address):
                cq_lines.append(process_name_string(line.strip()))
            # 福建频道（修复：缩进与其他频道一致）
            elif channel_name in fj_dictionary and check_url_existence(fj_lines, channel_address):
                fj_lines.append(process_name_string(line.strip()))
            # 甘肃频道
            elif channel_name in gs_dictionary and check_url_existence(gs_lines, channel_address):
                gs_lines.append(process_name_string(line.strip()))
            # 广西频道
            elif channel_name in gx_dictionary and check_url_existence(gx_lines, channel_address):
                gx_lines.append(process_name_string(line.strip()))
            # 贵州频道
            elif channel_name in gz_dictionary and check_url_existence(gz_lines, channel_address):
                gz_lines.append(process_name_string(line.strip()))
            # 河北频道
            elif channel_name in heb_dictionary and check_url_existence(heb_lines, channel_address):
                heb_lines.append(process_name_string(line.strip()))
            # 河南频道
            elif channel_name in hen_dictionary and check_url_existence(hen_lines, channel_address):
                hen_lines.append(process_name_string(line.strip()))
            # 黑龙江频道
            elif channel_name in hlj_dictionary and check_url_existence(hlj_lines, channel_address):
                hlj_lines.append(process_name_string(line.strip()))
            # 吉林频道
            elif channel_name in jl_dictionary and check_url_existence(jl_lines, channel_address):
                jl_lines.append(process_name_string(line.strip()))
            # 宁夏频道
            elif channel_name in nx_dictionary and check_url_existence(nx_lines, channel_address):
                nx_lines.append(process_name_string(line.strip()))
            # 江西频道
            elif channel_name in jx_dictionary and check_url_existence(jx_lines, channel_address):
                jx_lines.append(process_name_string(line.strip()))
            # 青海频道
            elif channel_name in qh_dictionary and check_url_existence(qh_lines, channel_address):
                qh_lines.append(process_name_string(line.strip()))
            # 四川频道
            elif channel_name in sc_dictionary and check_url_existence(sc_lines, channel_address):
                sc_lines.append(process_name_string(line.strip()))
            # 上海频道
            elif channel_name in sh_dictionary and check_url_existence(sh_lines, channel_address):
                sh_lines.append(process_name_string(line.strip()))
            # 天津频道
            elif channel_name in tj_dictionary and check_url_existence(tj_lines, channel_address):
                tj_lines.append(process_name_string(line.strip()))
            # 新疆频道
            elif channel_name in xj_dictionary and check_url_existence(xj_lines, channel_address):
                xj_lines.append(process_name_string(line.strip()))
            # 数字频道
            elif channel_name in sz_dictionary and check_url_existence(sz_lines, channel_address):
                sz_lines.append(process_name_string(line.strip()))
            # 国际频道
            elif channel_name in gj_dictionary and check_url_existence(gj_lines, channel_address):
                gj_lines.append(process_name_string(line.strip()))
            # 体育频道
            elif channel_name in ty_dictionary and check_url_existence(ty_lines, channel_address):
                ty_lines.append(process_name_string(line.strip()))
            # 体育赛事（修复：循环变量与列表名重名问题）
            elif any(tyss_key in channel_name for tyss_key in tyss_dictionary) and check_url_existence(tyss_lines, channel_address):
                tyss_lines.append(process_name_string(line.strip()))
            # 电影频道
            elif channel_name in dy_dictionary and check_url_existence(dy_lines, channel_address):
                dy_lines.append(process_name_string(line.strip()))
            # 电视剧频道
            elif channel_name in dsj_dictionary and check_url_existence(dsj_lines, channel_address):
                dsj_lines.append(process_name_string(line.strip()))
            # 港澳台频道
            elif channel_name in gat_dictionary and check_url_existence(gat_lines, channel_address):
                gat_lines.append(process_name_string(line.strip()))
            # 香港频道
            elif channel_name in xg_dictionary and check_url_existence(xg_lines, channel_address):
                xg_lines.append(process_name_string(line.strip()))
            # 澳门频道
            elif channel_name in aomen_dictionary and check_url_existence(aomen_lines, channel_address):
                aomen_lines.append(process_name_string(line.strip()))
            # 台湾频道
            elif channel_name in tw_dictionary and check_url_existence(tw_lines, channel_address):
                tw_lines.append(process_name_string(line.strip()))
            # 纪录片频道
            elif channel_name in jlp_dictionary and check_url_existence(jlp_lines, channel_address):
                jlp_lines.append(process_name_string(line.strip()))
            # 动画片频道
            elif channel_name in dhp_dictionary and check_url_existence(dhp_lines, channel_address):
                dhp_lines.append(process_name_string(line.strip()))
            # 戏曲频道
            elif channel_name in xq_dictionary and check_url_existence(xq_lines, channel_address):
                xq_lines.append(process_name_string(line.strip()))
            # 解说频道
            elif channel_name in js_dictionary and check_url_existence(js_lines, channel_address):
                js_lines.append(process_name_string(line.strip()))
            # 春晚频道
            elif channel_name in cw_dictionary and check_url_existence(cw_lines, channel_address):
                cw_lines.append(process_name_string(line.strip()))
            # 斗鱼直播
            elif channel_name in douyu_dictionary and check_url_existence(douyu_lines, channel_address):
                douyu_lines.append(process_name_string(line.strip()))
            # 虎牙直播
            elif channel_name in huya_dictionary and check_url_existence(huya_lines, channel_address):
                huya_lines.append(process_name_string(line.strip()))
            # 综艺频道
            elif channel_name in zy_dictionary and check_url_existence(zy_lines, channel_address):
                zy_lines.append(process_name_string(line.strip()))
            # 音乐频道
            elif channel_name in yy_dictionary and check_url_existence(yy_lines, channel_address):
                yy_lines.append(process_name_string(line.strip()))
            # 游戏频道
            elif channel_name in game_dictionary and check_url_existence(game_lines, channel_address):
                game_lines.append(process_name_string(line.strip()))
            # 收音机频道
            elif channel_name in radio_dictionary and check_url_existence(radio_lines, channel_address):
                radio_lines.append(process_name_string(line.strip()))
            # 直播中国
            elif channel_name in zb_dictionary and check_url_existence(zb_lines, channel_address):
                zb_lines.append(process_name_string(line.strip()))
            # 其他频道（去重）
            else:
                if channel_address not in other_lines_url:
                    other_lines_url.append(channel_address)
                    other_lines.append(line.strip())

# 随机User-Agent（备用）
def get_random_user_agent():
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
    ]
    return random.choice(USER_AGENTS)

# URL内容爬取与解析
def process_url(url):
    try:
        other_lines.append(f"◆◆◆　{url}")  # 记录处理过的URL（用于调试）
        
        # 构建请求（固定User-Agent，避免被拦截）
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
        
        # 读取URL内容
        with urllib.request.urlopen(req) as response:
            text = response.read().decode('utf-8').strip()
            
            # 判定M3U格式（扩展名或内容开头）
            is_m3u = text.startswith(("#EXTM3U", "#EXTINF"))
            if get_url_file_extension(url) in (".m3u", ".m3u8") or is_m3u:
                text = convert_m3u_to_txt(text)
            
            # 逐行解析（过滤无效格式，处理带#的多URL）
            for line in text.split('\n'):
                line = line.strip()
                if "#genre#" not in line and "," in line and "://" in line and "tvbus://" not in line and "/udp/" not in line:
                    channel_name, channel_address = line.split(',', 1)
                    # 处理带#的多URL（如URL#备用1#备用2）
                    if "#" in channel_address:
                        for sub_url in channel_address.split('#'):
                            process_channel_line(f"{channel_name},{sub_url}")
                    else:
                        process_channel_line(line)
        
        other_lines.append('\n')  # 分隔不同URL的记录
    
    except Exception as e:
        print(f"Process URL error: {url} -> {e}")

# 加载频道分类字典（从本地TXT读取）
# 主频道字典
ys_dictionary = read_txt_to_array('主频道/CCTV.txt')
ws_dictionary = read_txt_to_array('主频道/卫视频道.txt')
cw_dictionary = read_txt_to_array('主频道/春晚.txt')
dy_dictionary = read_txt_to_array('主频道/电影.txt')
dsj_dictionary = read_txt_to_array('主频道/电视剧.txt')
gat_dictionary = read_txt_to_array('主频道/港澳台.txt')
xg_dictionary = read_txt_to_array('主频道/香港.txt')
aomen_dictionary = read_txt_to_array('主频道/澳门.txt')
tw_dictionary = read_txt_to_array('主频道/台湾.txt')
dhp_dictionary = read_txt_to_array('主频道/动画片.txt')
radio_dictionary = read_txt_to_array('主频道/收音机.txt')
sz_dictionary = read_txt_to_array('主频道/数字频道.txt')
gj_dictionary = read_txt_to_array('主频道/国际频道.txt')
ty_dictionary = read_txt_to_array('主频道/体育频道.txt')
tyss_dictionary = read_txt_to_array('主频道/体育赛事.txt')
yy_dictionary = read_txt_to_array('主频道/音乐频道.txt')
js_dictionary = read_txt_to_array('主频道/解说频道.txt')
douyu_dictionary = read_txt_to_array('主频道/斗鱼直播.txt')
huya_dictionary = read_txt_to_array('主频道/虎牙直播.txt')
zb_dictionary = read_txt_to_array('主频道/直播中国.txt')
jlp_dictionary = read_txt_to_array('主频道/纪录片.txt')
zy_dictionary = read_txt_to_array('主频道/综艺频道.txt')
game_dictionary = read_txt_to_array('主频道/游戏频道.txt')
xq_dictionary = read_txt_to_array('主频道/戏曲频道.txt')

# 地方台字典
zj_dictionary = read_txt_to_array('地方台/浙江频道.txt')
jsu_dictionary = read_txt_to_array('地方台/江苏频道.txt')
gd_dictionary = read_txt_to_array('地方台/广东频道.txt')
gx_dictionary = read_txt_to_array('地方台/广西频道.txt')
jx_dictionary = read_txt_to_array('地方台/江西频道.txt')
hb_dictionary = read_txt_to_array('地方台/湖北频道.txt')
hn_dictionary = read_txt_to_array('地方台/湖南频道.txt')
ah_dictionary = read_txt_to_array('地方台/安徽频道.txt')
hain_dictionary = read_txt_to_array('地方台/海南频道.txt')
nm_dictionary = read_txt_to_array('地方台/内蒙频道.txt')
ln_dictionary = read_txt_to_array('地方台/辽宁频道.txt')
sx_dictionary = read_txt_to_array('地方台/陕西频道.txt')
shandong_dictionary = read_txt_to_array('地方台/山东频道.txt')
shanxi_dictionary = read_txt_to_array('地方台/山西频道.txt')
hen_dictionary = read_txt_to_array('地方台/河南频道.txt')
heb_dictionary = read_txt_to_array('地方台/河北频道.txt')
yunnan_dictionary = read_txt_to_array('地方台/云南频道.txt')
gz_dictionary = read_txt_to_array('地方台/贵州频道.txt')
sc_dictionary = read_txt_to_array('地方台/四川频道.txt')
fj_dictionary = read_txt_to_array('地方台/福建频道.txt')
gs_dictionary = read_txt_to_array('地方台/甘肃频道.txt')
hlj_dictionary = read_txt_to_array('地方台/黑龙江频道.txt')
jl_dictionary = read_txt_to_array('地方台/吉林频道.txt')
nx_dictionary = read_txt_to_array('地方台/宁夏频道.txt')
qh_dictionary = read_txt_to_array('地方台/青海频道.txt')
xj_dictionary = read_txt_to_array('地方台/新疆频道.txt')
bj_dictionary = read_txt_to_array('地方台/北京频道.txt')
sh_dictionary = read_txt_to_array('地方台/上海频道.txt')
tj_dictionary = read_txt_to_array('地方台/天津频道.txt')
cq_dictionary = read_txt_to_array('地方台/重庆频道.txt')

# 频道名纠错（从TXT加载“错误名→正确名”映射）
def load_corrections_name(filename):
    corrections = {}
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or ',' not in line:
                continue
            parts = line.split(',')
            correct_name = parts[0]
            for wrong_name in parts[1:]:
                corrections[wrong_name] = correct_name
    return corrections

corrections_name = load_corrections_name('assets/corrections_name.txt')

# 执行频道名纠错
def correct_name_data(corrections, data):
    corrected = []
    for line in data:
        line = line.strip()
        if ',' not in line:
            continue
        name, url = line.split(',', 1)
        # 替换错误名称
        if name in corrections:
            name = corrections[name]
        corrected.append(f"{name},{url}")
    return corrected

# 按字典顺序排序频道
def sort_data(order_dict, data):
    order_map = {name: idx for idx, name in enumerate(order_dict)}
    # 未在字典中的频道排在最后
    def sort_key(line):
        return order_map.get(line.split(',')[0], len(order_map))
    return sorted(data, key=sort_key)

# 处理动态URL（替换{MMdd}和{MMdd-1}为当前/昨日日期）
urls = read_txt_to_array('assets/urls-daily.txt')
for url in urls:
    if url.startswith("http"):
        # 替换当前日期（MMdd格式）
        if "{MMdd}" in url:
            url = url.replace("{MMdd}", datetime.now().strftime("%m%d"))
        # 替换昨日日期（MMdd格式）
        if "{MMdd-1}" in url:
            yesterday = datetime.now() - timedelta(days=1)
            url = url.replace("{MMdd-1}", yesterday.strftime("%m%d"))
        
        print(f"Processing URL: {url}")
        process_url(url)

# 加载高响应白名单（响应时间<2000ms的源）
print("Adding whitelist_auto.txt (response < 2000ms)")
whitelist_auto_lines = read_txt_to_array('assets/blacklist1/whitelist_auto.txt')
for line in whitelist_auto_lines:
    if "#genre#" not in line and "," in line and "://" in line:
        parts = line.split(",")
        try:
            response_time = float(parts[0].replace("ms", ""))
        except ValueError:
            response_time = 60000  # 转换失败默认60秒（不加入）
        # 仅保留2秒内的高响应源
        if response_time < 2000:
            process_channel_line(",".join(parts[1:]))

# 带重试的HTTP请求（优化爬取稳定性）
def get_http_response(url, timeout=8, retries=2, backoff_factor=1.0):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    for attempt in range(retries):
        try:
            # 修复：传入headers（原代码未传入导致User-Agent无效）
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            print(f"HTTPError [{e.code}]: {url} (no retry)")
            break  # HTTP错误无需重试
        except (urllib.error.URLError, socket.timeout) as e:
            print(f"Retry [{attempt+1}/{retries}]: {url} -> {e}")
        except Exception as e:
            print(f"Exception [{attempt+1}/{retries}]: {url} -> {type(e).__name__}")
        
        # 指数退避重试（避免频繁请求）
        if attempt < retries - 1:
            time.sleep(backoff_factor * (2 ** attempt))
    return None

# 体育赛事日期标准化（统一为MM-DD格式）
def normalize_date_to_md(text):
    text = text.strip()
    # 替换函数：确保日期后加空格分隔
    def format_md(match):
        month = int(match.group(1))
        day = int(match.group(2))
        suffix = match.group(3) or ''
        if not suffix.startswith(' '):
            suffix = f' {suffix}'
        return f"{month}-{day}{suffix}"
    
    # 处理MM/DD、YYYY-MM-DD、中文日期（X月X日）
    text = re.sub(r'^0?(\d{1,2})/0?(\d{1,2})(.*)', format_md, text)
    text = re.sub(r'^\d{4}-0?(\d{1,2})-0?(\d{1,2})(.*)', format_md, text)
    text = re.sub(r'^0?(\d{1,2})月0?(\d{1,2})日(.*)', format_md, text)
    return text

normalized_tyss_lines = [normalize_date_to_md(line) for line in tyss_lines]

# 处理AKTV源（优先在线获取，失败则读本地）
aktv_lines = []
aktv_url = "https://aktv.space/live.m3u"
aktv_text = get_http_response(aktv_url)
if aktv_text:
    print("AKTV: Loaded from online")
    aktv_text = convert_m3u_to_txt(aktv_text)
    aktv_lines = aktv_text.strip().split('\n')
else:
    print("AKTV: Loaded from local (online failed)")
    aktv_lines = read_txt_to_array('手工区/AKTV.txt')

# 生成体育赛事HTML列表（带复制功能）
def generate_playlist_html(data_list, output_file='output/custom1/sports.html'):
    html_head = '''
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6061710286208572" crossorigin="anonymous"></script>
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
        .item { margin-bottom: 20px; padding: 12px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.06); }
        .title { font-weight: bold; font-size: 1.1em; color: #333; margin-bottom: 5px; }
        .url-wrapper { display: flex; align-items: center; gap: 10px; }
        .url { max-width: 80%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 0.9em; color: #555; background: #f0f0f0; padding: 6px; border-radius: 4px; flex-grow: 1; }
        .copy-btn { background-color: #007BFF; border: none; color: white; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8em; }
        .copy-btn:hover { background-color: #0056b3; }
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
            const text = document.getElementById(id).textContent;
            navigator.clipboard.writeText(text).then(() => alert("已复制链接！")).catch(err => alert("复制失败: " + err));
        }
    </script>
</body>
</html>
    '''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_head + html_body + html_tail)
    print(f"✅ Sports HTML generated: {output_file}")

# 生成体育赛事HTML（去重后排序）
generate_playlist_html(sorted(set(normalized_tyss_lines)))

# 随机获取URL（用于“今日推台”）
def get_random_url(file_path):
    urls = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if ',' in line:
                urls.append(line.strip().split(',')[-1])
    return random.choice(urls) if urls else None

# 生成版本信息（北京时间）
beijing_time = datetime.now(timezone.utc) + timedelta(hours=8)
formatted_time = beijing_time.strftime("%Y%m%d %H:%M:%S")

# 版本与推荐台配置
version = f"{formatted_time},{get_random_url('assets/今日推台.txt')}"
about = f"xiaoranmuze,{get_random_url('assets/今日推台.txt')}"
daily_mtv = f"今日推荐,{get_random_url('assets/今日推荐.txt')}"
daily_mtv1 = f"🔥低调,{get_random_url('assets/今日推荐.txt')}"
daily_mtv2 = f"🔥使用,{get_random_url('assets/今日推荐.txt')}"
daily_mtv3 = f"🔥禁止,{get_random_url('assets/今日推荐.txt')}"
daily_mtv4 = f"🔥贩卖,{get_random_url('assets/今日推荐.txt')}"

# 补充手工区频道（本地TXT）
print("Processing manual channels...")
zj_lines += read_txt_to_array('手工区/浙江频道.txt')
hb_lines += read_txt_to_array('手工区/湖北频道.txt')
gd_lines += read_txt_to_array('手工区/广东频道.txt')
sh_lines += read_txt_to_array('手工区/上海频道.txt')
jsu_lines += read_txt_to_array('手工区/江苏频道.txt')

# ------------------------------
# 生成3类输出文件：全集版、瘦身版、定制版
# ------------------------------
# 1. 全集版（含所有分类）
all_lines = ["🌐央视频道,#genre#"] + sort_data(ys_dictionary, correct_name_data(corrections_name, ys_lines)) + ['\n'] + \
    ["📡卫视频道,#genre#"] + sort_data(ws_dictionary, correct_name_data(corrections_name, ws_lines)) + ['\n'] + \
    ["☘️湖北频道,#genre#"] + sort_data(hb_dictionary, set(correct_name_data(corrections_name, hb_lines))) + ['\n'] + \
    ["☘️湖南频道,#genre#"] + sort_data(hn_dictionary, set(correct_name_data(corrections_name, hn_lines))) + ['\n'] + \
    ["☘️浙江频道,#genre#"] + sort_data(zj_dictionary, set(correct_name_data(corrections_name, zj_lines))) + ['\n'] + \
    ["☘️广东频道,#genre#"] + sort_data(gd_dictionary, set(correct_name_data(corrections_name, gd_lines))) + ['\n'] + \
    ["☘️江苏频道,#genre#"] + sort_data(jsu_dictionary, set(correct_name_data(corrections_name, jsu_lines))) + ['\n'] + \
    ["☘️江西频道,#genre#"] + sort_data(jx_dictionary, set(correct_name_data(corrections_name, jx_lines))) + ['\n'] + \
    ["☘️北京频道,#genre#"] + sort_data(bj_dictionary, set(correct_name_data(corrections_name, bj_lines))) + ['\n'] + \
    ["☘️上海频道,#genre#"] + sort_data(sh_dictionary, set(correct_name_data(corrections_name, sh_lines))) + ['\n'] + \
    ["☘️天津频道,#genre#"] + sort_data(tj_dictionary, set(correct_name_data(corrections_name, tj_lines))) + ['\n'] + \
    ["☘️重庆频道,#genre#"] + sort_data(cq_dictionary, set(correct_name_data(corrections_name, cq_lines))) + ['\n'] + \
    ["☘️安徽频道,#genre#"] + sort_data(ah_dictionary, set(correct_name_data(corrections_name, ah_lines))) + ['\n'] + \
    ["☘️海南频道,#genre#"] + sort_data(hain_dictionary, set(correct_name_data(corrections_name, hain_lines))) + ['\n'] + \
    ["☘️内蒙频道,#genre#"] + sort_data(nm_dictionary, set(correct_name_data(corrections_name, nm_lines))) + ['\n'] + \
    ["☘️辽宁频道,#genre#"] + sort_data(ln_dictionary, set(correct_name_data(corrections_name, ln_lines))) + ['\n'] + \
    ["☘️陕西频道,#genre#"] + sort_data(sx_dictionary, set(correct_name_data(corrections_name, sx_lines))) + ['\n'] + \
    ["☘️山东频道,#genre#"] + sort_data(shandong_dictionary, set(correct_name_data(corrections_name, shandong_lines))) + ['\n'] + \
    ["☘️山西频道,#genre#"] + sort_data(shanxi_dictionary, set(correct_name_data(corrections_name, shanxi_lines))) + ['\n'] + \
    ["☘️云南频道,#genre#"] + sort_data(yunnan_dictionary, set(correct_name_data(corrections_name, yunnan_lines))) + ['\n'] + \
    ["☘️福建频道,#genre#"] + sort_data(fj_dictionary, set(correct_name_data(corrections_name, fj_lines))) + ['\n'] + \
    ["☘️甘肃频道,#genre#"] + sort_data(gs_dictionary, set(correct_name_data(corrections_name, gs_lines))) + ['\n'] + \
    ["☘️广西频道,#genre#"] + sort_data(gx_dictionary, set(correct_name_data(corrections_name, gx_lines))) + ['\n'] + \
    ["☘️贵州频道,#genre#"] + sort_data(gz_dictionary, set(correct_name_data(corrections_name, gz_lines))) + ['\n'] + \
    ["☘️河北频道,#genre#"] + sort_data(heb_dictionary, set(correct_name_data(corrections_name, heb_lines))) + ['\n'] + \
    ["☘️河南频道,#genre#"] + sort_data(hen_dictionary, set(correct_name_data(corrections_name, hen_lines))) + ['\n'] + \
    ["☘️吉林频道,#genre#"] + sort_data(jl_dictionary, set(correct_name_data(corrections_name, jl_lines))) + ['\n'] + \
    ["☘️宁夏频道,#genre#"] + sort_data(nx_dictionary, set(correct_name_data(corrections_name, nx_lines))) + ['\n'] + \
    ["☘️青海频道,#genre#"] + sort_data(qh_dictionary, set(correct_name_data(corrections_name, qh_lines))) + ['\n'] + \
    ["☘️四川频道,#genre#"] + sort_data(sc_dictionary, set(correct_name_data(corrections_name, sc_lines))) + ['\n'] + \
    ["☘️新疆频道,#genre#"] + sort_data(xj_dictionary, set(correct_name_data(corrections_name, xj_lines))) + ['\n'] + \
    ["☘️黑龙江台,#genre#"] + sorted(set(correct_name_data(corrections_name, hlj_lines))) + ['\n'] + \
    ["🎞️数字频道,#genre#"] + sort_data(sz_dictionary, set(correct_name_data(corrections_name, sz_lines))) + ['\n'] + \
    ["🌎国际频道,#genre#"] + sort_data(gj_dictionary, set(correct_name_data(corrections_name, gj_lines))) + ['\n'] + \
    ["⚽体育频道,#genre#"] + sort_data(ty_dictionary, set(correct_name_data(corrections_name, ty_lines))) + ['\n'] + \
    ["🏆体育赛事,#genre#"] + normalized_tyss_lines + ['\n'] + \
    ["🐬斗鱼直播,#genre#"] + sort_data(douyu_dictionary, set(correct_name_data(corrections_name, douyu_lines))) + ['\n'] + \
    ["🐯虎牙直播,#genre#"] + sort_data(huya_dictionary, set(correct_name_data(corrections_name, huya_lines))) + ['\n'] + \
    ["🎙️解说频道,#genre#"] + sort_data(js_dictionary, set(correct_name_data(corrections_name, js_lines))) + ['\n'] + \
    ["🎬电影频道,#genre#"] + sort_data(dy_dictionary, set(correct_name_data(corrections_name, dy_lines))) + ['\n'] + \
    ["📺电·视·剧,#genre#"] + sort_data(dsj_dictionary, set(correct_name_data(corrections_name, dsj_lines))) + ['\n'] + \
    ["📽️记·录·片,#genre#"] + sort_data(jlp_dictionary,set(correct_name_data(corrections_name,jlp_lines)))+ ['\n'] + \
    ["🏕动·画·片,#genre#"] + sort_data(dhp_dictionary, set(correct_name_data(corrections_name, dhp_lines))) + ['\n'] + \
    ["📻收·音·机,#genre#"] + sort_data(radio_dictionary, set(correct_name_data(corrections_name, radio_lines))) + ['\n'] + \
    ["🇨🇳港·澳·台,#genre#"] +read_txt_to_array('手工区/♪港澳台.txt') + sort_data(gat_dictionary, set(correct_name_data(corrections_name, gat_lines))) + aktv_lines + ['\n'] + \
    ["🇭🇰香港频道,#genre#"] + sort_data(xg_dictionary, set(correct_name_data(corrections_name, xg_lines))) + ['\n'] + \
    ["🇲🇴澳门频道,#genre#"] + sort_data(aomen_dictionary, set(correct_name_data(corrections_name, aomen_lines))) + aktv_lines + ['\n'] + \
    ["🇹🇼台湾频道,#genre#"] + sort_data(tw_dictionary, set(correct_name_data(corrections_name, tw_lines)))  + ['\n'] + \
    ["🎭戏曲频道,#genre#"] + sort_data(xq_dictionary,set(correct_name_data(corrections_name,xq_lines))) + ['\n'] + \
    ["🎵音乐频道,#genre#"] + sort_data(yy_dictionary, set(correct_name_data(corrections_name, yy_lines))) + ['\n'] + \
    ["🎤综艺频道,#genre#"] + sorted(set(correct_name_data(corrections_name,zy_lines))) + ['\n'] + \
    ["🎮游戏频道,#genre#"] + sorted(set(correct_name_data(corrections_name,game_lines))) + ['\n'] + \
    ["✨优质央视,#genre#"] + read_txt_to_array('手工区/♪优质央视.txt') + ['\n'] + \
    ["🛰️优质卫视,#genre#"] + read_txt_to_array('手工区/♪优质卫视.txt') + ['\n'] + \
    ["📹直播中国,#genre#"] + sort_data(zb_dictionary, set(correct_name_data(corrections_name, zb_lines))) + ['\n'] + \
    ["🧨历届春晚,#genre#"] + sort_data(cw_dictionary, set(correct_name_data(corrections_name, cw_lines))) + ['\n'] + \
    ["🕒更新时间,#genre#"] + [version] + [about] + [daily_mtv] + [daily_mtv1] + [daily_mtv2] + [daily_mtv3] + [daily_mtv4] + read_txt_to_array('手工区/about.txt') + ['\n']

# 2. 瘦身版（仅核心频道）
all_lines_simple = ["央视频道,#genre#"] + sort_data(ys_dictionary, correct_name_data(corrections_name, ys_lines)) + ['\n'] + \
    ["卫视频道,#genre#"] + sort_data(ws_dictionary, correct_name_data(corrections_name, ws_lines)) + ['\n'] + \
    ["地方频道,#genre#"] + \
    sort_data(hb_dictionary, set(correct_name_data(corrections_name, hb_lines))) + \
    sort_data(hn_dictionary, set(correct_name_data(corrections_name, hn_lines))) + \
    sort_data(zj_dictionary, set(correct_name_data(corrections_name, zj_lines))) + \
    sort_data(gd_dictionary, set(correct_name_data(corrections_name, gd_lines))) + \
    sort_data(shandong_dictionary, set(correct_name_data(corrections_name, shandong_lines))) + \
    sorted(set(correct_name_data(corrections_name, jsu_lines))) + \
    sorted(set(correct_name_data(corrections_name, ah_lines))) + \
    sorted(set(correct_name_data(corrections_name, hain_lines))) + \
    sorted(set(correct_name_data(corrections_name, nm_lines))) + \
    sorted(set(correct_name_data(corrections_name, ln_lines))) + \
    sorted(set(correct_name_data(corrections_name, sx_lines))) + \
    sorted(set(correct_name_data(corrections_name, shanxi_lines))) + \
    sorted(set(correct_name_data(corrections_name, yunnan_lines))) + \
    sorted(set(correct_name_data(corrections_name, bj_lines))) + \
    sorted(set(correct_name_data(corrections_name, cq_lines))) + \
    sorted(set(correct_name_data(corrections_name, fj_lines))) + \
    sorted(set(correct_name_data(corrections_name, gs_lines))) + \
    sorted(set(correct_name_data(corrections_name, gx_lines))) + \
    sorted(set(correct_name_data(corrections_name, gz_lines))) + \
    sorted(set(correct_name_data(corrections_name, heb_lines))) + \
    sorted(set(correct_name_data(corrections_name, hen_lines))) + \
    sorted(set(correct_name_data(corrections_name, jl_lines))) + \
    sorted(set(correct_name_data(corrections_name, jx_lines))) + \
    sorted(set(correct_name_data(corrections_name, nx_lines))) + \
    sorted(set(correct_name_data(corrections_name, qh_lines))) + \
    sorted(set(correct_name_data(corrections_name, sc_lines))) + \
    sorted(set(correct_name_data(corrections_name, tj_lines))) + \
    sorted(set(correct_name_data(corrections_name, xj_lines))) + \
    sorted(set(correct_name_data(corrections_name, hlj_lines))) + \
    ['\n'] + \
    ["数字频道,#genre#"] + sort_data(sz_dictionary, set(correct_name_data(corrections_name, sz_lines))) + ['\n'] + \
    ["更新时间,#genre#"] + [version] + ['\n']

# 3. 定制版（全集基础上优化分类展示）
all_lines_custom = ["🌐央视频道,#genre#"] + sort_data(ys_dictionary, correct_name_data(corrections_name, ys_lines)) + ['\n'] + \
    ["📡卫视频道,#genre#"] + sort_data(ws_dictionary, correct_name_data(corrections_name, ws_lines)) + ['\n'] + \
    ["🏠地方频道,#genre#"] + \
    sort_data(hb_dictionary, set(correct_name_data(corrections_name, hb_lines))) + \
    sort_data(hn_dictionary, set(correct_name_data(corrections_name, hn_lines))) + \
    sort_data(zj_dictionary, set(correct_name_data(corrections_name, zj_lines))) + \
    sort_data(gd_dictionary, set(correct_name_data(corrections_name, gd_lines))) + \
    sort_data(shandong_dictionary, set(correct_name_data(corrections_name, shandong_lines))) + \
    sorted(set(correct_name_data(corrections_name, jsu_lines))) + \
    sorted(set(correct_name_data(corrections_name, ah_lines))) + \
    sorted(set(correct_name_data(corrections_name, hain_lines))) + \
    sorted(set(correct_name_data(corrections_name, nm_lines))) + \
    sorted(set(correct_name_data(corrections_name, ln_lines))) + \
    sorted(set(correct_name_data(corrections_name, sx_lines))) + \
    sorted(set(correct_name_data(corrections_name, shanxi_lines))) + \
    sorted(set(correct_name_data(corrections_name, yunnan_lines))) + \
    sorted(set(correct_name_data(corrections_name, bj_lines))) + \
    sorted(set(correct_name_data(corrections_name, cq_lines))) + \
    sorted(set(correct_name_data(corrections_name, fj_lines))) + \
    sorted(set(correct_name_data(corrections_name, gs_lines))) + \
    sorted(set(correct_name_data(corrections_name, gx_lines))) + \
    sorted(set(correct_name_data(corrections_name, gz_lines))) + \
    sorted(set(correct_name_data(corrections_name, heb_lines))) + \
    sorted(set(correct_name_data(corrections_name, hen_lines))) + \
    sorted(set(correct_name_data(corrections_name, jl_lines))) + \
    sorted(set(correct_name_data(corrections_name, jx_lines))) + \
    sorted(set(correct_name_data(corrections_name, nx_lines))) + \
    sorted(set(correct_name_data(corrections_name, qh_lines))) + \
    sorted(set(correct_name_data(corrections_name, sc_lines))) + \
    sorted(set(correct_name_data(corrections_name, tj_lines))) + \
    sorted(set(correct_name_data(corrections_name, xj_lines))) + \
    sorted(set(correct_name_data(corrections_name, hlj_lines))) + \
    ['\n'] + \
    ["🎞️数字频道,#genre#"] + sort_data(sz_dictionary, set(correct_name_data(corrections_name, sz_lines))) + ['\n'] + \
    ["🌎国际频道,#genre#"] + sort_data(gj_dictionary, set(correct_name_data(corrections_name, gj_lines))) + ['\n'] + \
    ["⚽体育频道,#genre#"] + sort_data(ty_dictionary, set(correct_name_data(corrections_name, ty_lines))) + ['\n'] + \
    ["🏆体育赛事,#genre#"] + normalized_tyss_lines + ['\n'] + \
    ["🐬斗鱼直播,#genre#"] + sort_data(douyu_dictionary, set(correct_name_data(corrections_name, douyu_lines))) + ['\n'] + \
    ["🐯虎牙直播,#genre#"] + sort_data(huya_dictionary, set(correct_name_data(corrections_name, huya_lines))) + ['\n'] + \
    ["🎙️解说频道,#genre#"] + sort_data(js_dictionary, set(correct_name_data(corrections_name, js_lines))) + ['\n'] + \
    ["🎬电影频道,#genre#"] + sort_data(dy_dictionary, set(correct_name_data(corrections_name, dy_lines))) + ['\n'] + \
    ["📺电·视·剧,#genre#"] + sort_data(dsj_dictionary, set(correct_name_data(corrections_name, dsj_lines))) + ['\n'] + \
    ["📽️记·录·片,#genre#"] + sort_data(jlp_dictionary,set(correct_name_data(corrections_name,jlp_lines)))+ ['\n'] + \
    ["🏕动·画·片,#genre#"] + sort_data(dhp_dictionary, set(correct_name_data(corrections_name, dhp_lines))) + ['\n'] + \
    ["📻收·音·机,#genre#"] + sort_data(radio_dictionary, set(correct_name_data(corrections_name, radio_lines))) + ['\n'] + \
    ["🇨🇳港·澳·台,#genre#"] +read_txt_to_array('手工区/♪港澳台.txt') + sort_data(gat_dictionary, set(correct_name_data(corrections_name, gat_lines))) + aktv_lines + ['\n'] + \
    ["🇭🇰香港频道,#genre#"] + sort_data(xg_dictionary, set(correct_name_data(corrections_name, xg_lines))) + ['\n'] + \
    ["🇲🇴澳门频道,#genre#"] + sort_data(aomen_dictionary, set(correct_name_data(corrections_name, aomen_lines))) + aktv_lines + ['\n'] + \
    ["🇹🇼台湾频道,#genre#"] + sort_data(tw_dictionary, set(correct_name_data(corrections_name, tw_lines)))  + ['\n'] + \
    ["🎭戏曲频道,#genre#"] + sort_data(xq_dictionary,set(correct_name_data(corrections_name,xq_lines))) + ['\n'] + \
    ["🎵音乐频道,#genre#"] + sort_data(yy_dictionary, set(correct_name_data(corrections_name, yy_lines))) + ['\n'] + \
    ["🎤综艺频道,#genre#"] + sorted(set(correct_name_data(corrections_name,zy_lines))) + ['\n'] + \
    ["🎮游戏频道,#genre#"] + sorted(set(correct_name_data(corrections_name,game_lines))) + ['\n'] + \
    ["✨优质央视,#genre#"] + read_txt_to_array('手工区/♪优质央视.txt') + ['\n'] + \
    ["🛰️优质卫视,#genre#"] + read_txt_to_array('手工区/♪优质卫视.txt') + ['\n'] + \
    ["📹直播中国,#genre#"] + sort_data(zb_dictionary, set(correct_name_data(corrections_name, zb_lines))) + ['\n'] + \
    ["🧨历届春晚,#genre#"] + sort_data(cw_dictionary, set(correct_name_data(corrections_name, cw_lines))) + ['\n'] + \
    ["🕒更新时间,#genre#"] + [version] + [about] + [daily_mtv] + [daily_mtv1] + [daily_mtv2] + [daily_mtv3] + [daily_mtv4] + read_txt_to_array('手工区/about.txt') + ['\n']

# ------------------------------
# 写入TXT文件
# ------------------------------
output_paths = {
    'full': 'output/custom1/full.txt',
    'simple': 'output/custom1/simple.txt',
    'custom': 'output/custom1/custom.txt',
    'others': 'output/custom1/others.txt'
}

try:
    # 写入全集版
    with open(output_paths['full'], 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_lines))
    print(f"✅ Full TXT saved: {output_paths['full']}")

    # 写入瘦身版
    with open(output_paths['simple'], 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_lines_simple))
    print(f"✅ Simple TXT saved: {output_paths['simple']}")

    # 写入定制版
    with open(output_paths['custom'], 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_lines_custom))
    print(f"✅ Custom TXT saved: {output_paths['custom']}")

    # 写入其他频道记录
    with open(output_paths['others'], 'w', encoding='utf-8') as f:
        f.write('\n'.join(other_lines))
    print(f"✅ Others TXT saved: {output_paths['others']}")

except Exception as e:
    print(f"Save TXT error: {e}")

# ------------------------------
# 生成M3U文件（带EPG和频道Logo）
# ------------------------------
def make_m3u(txt_file, m3u_file):
    try:
        # M3U头部（指定EPG源）
        m3u_header = '#EXTM3U x-tvg-url="https://live.fanmingming.cn/e.xml"\n'
        m3u_content = m3u_header
        
        # 读取TXT内容并转换为M3U格式
        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
        
        group_name = ""  # 当前分类组名
        channel_logos = {line.split(',')[0]: line.split(',')[1] for line in read_txt_to_array('assets/logo.txt') if ',' in line}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 更新分类组名（识别“#genre#”行）
            if "#genre#" in line and "," in line:
                group_name = line.split(',')[0]
            # 转换频道行为M3U格式
            elif "," in line and "://" in line:
                channel_name, channel_url = line.split(',', 1)
                # 获取频道Logo（无则Logo（无则省略）
                logo_url = channel_logos.get(channel_name)
                if logo_url:
                    m3u_content += f"#EXTINF:-1 tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\" group-title=\"{group_name}\",{channel_name}\n"
                else:
                    m3u_content += f"#EXTINF:-1 group-title=\"{group_name}\",{channel_name}\n"
                m3u_content += f"{channel_url}\n"
        
        # 写入M3U文件
        with open(m3u_file, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        print(f"✅ M3U generated: {m3u_file}")
    
    except Exception as e:
        print(f"Make M3U error: {e}")

# 为3类TXT生成对应M3U
make_m3u(output_paths['full'], output_paths['full'].replace('.txt', '.m3u'))
make_m3u(output_paths['simple'], output_paths['simple'].replace('.txt', '.m3u'))
make_m3u(output_paths['custom'], output_paths['custom'].replace('.txt', '.m3u'))

# ------------------------------
# 执行信息统计
# ------------------------------
timeend = datetime.now()
elapsed_time = timeend - timestart
total_seconds = elapsed_time.total_seconds()
minutes = int(total_seconds // 60)
seconds = int(total_seconds % 60)

# 输出执行信息
print(f"\n=== 执行统计 ===")
print(f"开始时间: {timestart.strftime('%Y%m%d_%H_%M_%S')}")
print(f"结束时间: {timeend.strftime('%Y%m%d_%H_%M_%S')}")
print(f"执行时间: {minutes} 分 {seconds} 秒")
print(f"黑名单数量: {len(combined_blacklist)}")
print(f"全集版行数: {len(all_lines)}")
print(f"定制版行数: {len(all_lines_custom)}")
print(f"其他记录行数: {len(other_lines)}")
