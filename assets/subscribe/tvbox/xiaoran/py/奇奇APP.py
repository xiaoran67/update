# coding=utf-8
# !/usr/bin/python

"""

作者 丢丢喵 内容均从互联网收集而来 仅供交流学习使用 严禁用于商业用途 请于24小时内删除
         ====================Diudiumiao====================

"""

from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from Crypto.Cipher import AES
from datetime import datetime
from bs4 import BeautifulSoup
from base64 import b64decode
from base64 import b64encode
import urllib.request
import urllib.parse
import datetime
import binascii
import requests
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "http://110.42.67.221:8006"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Host': '110.42.67.221:8006',
    'Connection': 'Keep-Alive',
    'User-Agent': 'okhttp/3.10.0',
    'Accept-Encoding': 'gzip, deflate'
          }

class Spider(Spider):

    def getName(self):
        return "丢丢喵"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def decrypt_aes_cbc(self,ciphertext_base64):
        key_hex = "31323334353637383961626364656667"
        iv_hex = "31323334353637383961626364656667"
        key = bytes.fromhex(key_hex)
        iv = bytes.fromhex(iv_hex)
        ciphertext = b64decode(ciphertext_base64)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(ciphertext)
        padding_length = decrypted_padded[-1]
        decrypted = decrypted_padded[:-padding_length]
        return decrypted.decode('utf-8')

    def encrypt_aes_cbc(self,plaintext):
        key_hex = "31323334353637383961626364656667"
        iv_hex = "31323334353637383961626364656667"
        key = bytes.fromhex(key_hex)
        iv = bytes.fromhex(iv_hex)
        plaintext_bytes = plaintext.encode('utf-8')
        padded_plaintext = pad(plaintext_bytes, AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(padded_plaintext)
        return b64encode(encrypted).decode('utf-8')

    def homeContent(self, filter):
        result = {"class": []}
        data = self.fetch_home_data()
        self.process_type_list(data, result)
        return result

    def fetch_home_data(self):
        url = f"{xurl}/api.php/qijiappapi.index/initV122"
        detail = requests.get(url=url, headers=headers)
        detail.encoding = "utf-8"
        data = detail.json()
        data = data['data']
        data = self.decrypt_aes_cbc(data)
        return json.loads(data)

    def process_type_list(self, data, result):
        for vod in data['type_list']:
            name = vod['type_name']
            if self.should_skip_type(name):
                continue
            id = vod['type_id']
            result["class"].append({"type_id": id, "type_name": name})

    def should_skip_type(self, name):
        skip_names = ["全部"]
        return name in skip_names

    def homeVideoContent(self):
        videos = []
        data = self.fetch_home_video_data()
        self.process_video_list(data, videos)
        return {'list': videos}

    def fetch_home_video_data(self):
        url = f"{xurl}/api.php/qijiappapi.index/initV122"
        detail = requests.get(url=url, headers=headers)
        detail.encoding = "utf-8"
        data = detail.json()
        data = data['data']
        data = self.decrypt_aes_cbc(data)
        return json.loads(data)

    def process_video_list(self, data, videos):
        for vods in data['type_list']:
            for vod in vods['recommend_list']:
                video = self.create_video_item(vod)
                videos.append(video)

    def create_video_item(self, vod):
        name = vod['vod_name']
        id = vod['vod_id']
        pic = vod['vod_pic']
        remark = vod.get('vod_remarks', '暂无备注')
        return {"vod_id": id,"vod_name": name,"vod_pic": pic,"vod_remarks": remark}

    def categoryContent(self, cid, pg, filter, ext):
        videos = []
        page = self.parse_page_number(pg)
        data = self.build_category_request_data(cid, page)
        response_data = self.fetch_category_data(data)
        self.process_category_videos(response_data, videos)
        return self.build_category_result(videos, pg)

    def parse_page_number(self, pg):
        return int(pg) if pg else 1

    def build_category_request_data(self, cid, page):
        return {'area': '全部','year': '全部','type_id': cid,'page': page,'sort': '最新','lang': '全部','class': '全部'}

    def fetch_category_data(self, data):
        url = f"{xurl}/api.php/qijiappapi.index/typeFilterVodList"
        response = requests.post(url=url, headers=headers, data=data)
        response_data = response.json()
        data = response_data['data']
        data = self.decrypt_aes_cbc(data)
        return json.loads(data)

    def process_category_videos(self, data, videos):
        for vod in data['recommend_list']:
            video = self.create_category_video_item(vod)
            videos.append(video)

    def create_category_video_item(self, vod):
        name = vod['vod_name']
        id = vod['vod_id']
        pic = vod['vod_pic']
        remark = vod.get('vod_remarks', '暂无备注')
        return {"vod_id": id,"vod_name": name,"vod_pic": pic,"vod_remarks": remark}

    def build_category_result(self, videos, pg):
        return {'list': videos,'page': pg,'pagecount': 9999,'limit': 90,'total': 999999}

    def detailContent(self, ids):
        did = ids[0]
        result = {}
        videos = []
        data = self.build_detail_request_data(did)
        response_data = self.fetch_detail_data(data)
        vod_data = self.parse_detail_response(response_data)
        content = self.extract_detail_content(vod_data)
        director = self.extract_detail_director(vod_data)
        actor = self.extract_detail_actor(vod_data)
        remarks = self.extract_detail_remarks(vod_data)
        year = self.extract_detail_year(vod_data)
        area = self.extract_detail_area(vod_data)
        xianlu = self.extract_detail_xianlu(vod_data)
        bofang = self.extract_detail_play_urls(vod_data)
        videos.append({
            "vod_id": did,
            "vod_director": director,
            "vod_actor": actor,
            "vod_remarks": remarks,
            "vod_year": year,
            "vod_area": area,
            "vod_content": content,
            "vod_play_from": xianlu,
            "vod_play_url": bofang
                      })
        result['list'] = videos
        return result

    def build_detail_request_data(self, did):
        return {
            'vod_id': did
               }

    def fetch_detail_data(self, data):
        url = f"{xurl}/api.php/qijiappapi.index/vodDetail3"
        response = requests.post(url=url, headers=headers, data=data)
        response_data = response.json()
        data = response_data['data']
        data = self.decrypt_aes_cbc(data)
        return json.loads(data)

    def parse_detail_response(self, response_data):
        return response_data

    def extract_detail_content(self, vod_data):
        vod_blurb = vod_data.get('vod', {}).get('vod_blurb', '').replace('\u3000', '')
        return '集多为您介绍剧情📢' + vod_blurb

    def extract_detail_director(self, vod_data):
        return vod_data.get('vod', {}).get('vod_director', '')

    def extract_detail_actor(self, vod_data):
        return vod_data.get('vod', {}).get('vod_actor', '')

    def extract_detail_remarks(self, vod_data):
        return vod_data.get('vod', {}).get('vod_remarks', '')

    def extract_detail_year(self, vod_data):
        return vod_data.get('vod', {}).get('vod_year', '')

    def extract_detail_area(self, vod_data):
        return vod_data.get('vod', {}).get('vod_area', '')

    def extract_detail_xianlu(self, vod_data):
        xianlu = ''
        for vod in vod_data['vod_play_list']:
            name = vod['player_info']['show']
            xianlu = xianlu + name + '$$$'
        return xianlu[:-3]

    def extract_detail_play_urls(self, vod_data):
        bofang = ''
        for vods in vod_data['vod_play_list']:
            for vod in vods['urls']:
                name = vod['name']
                id = vod['parse_api_url']
                bofang = bofang + name + '$' + id + '#'
            bofang = bofang[:-1] + '$$$'
        return bofang[:-3]

    def playerContent(self, flag, id, vipFlags):
        url_value = self.process_player_url(id)
        return self.build_player_result(url_value)

    def process_player_url(self, id):
        if 'YYNB-' in id:
            return self.handle_special_url(id, 'YYNB-')
        elif 'https://v.qq.com' in id:
            return self.handle_special_url(id, 'https://v.qq.com')
        elif 'https://vip.ffzy' in id:
            return self.handle_special_url(id, 'https://vip.ffzy')
        elif 'https://v.lzcdn' in id:
            return self.handle_special_url(id, 'https://v.lzcdn')
        elif 'https://cdn.yzzy' in id:
            return self.handle_special_url(id, 'https://cdn.yzzy')
        elif 'https://www.iqiyi.com' in id:
            return self.handle_special_url(id, 'https://www.iqiyi.com')
        elif 'https://www.mgtv.com' in id:
            return self.handle_special_url(id, 'https://www.mgtv.com')
        elif 'https://v.youku.com' in id:
            return self.handle_special_url(id, 'https://v.youku.com')
        elif 'https://www.bilibili.com' in id:
            return self.handle_special_url(id, 'https://www.bilibili.com')
        elif 'NBY-' in id or 'Ace_Net' in id or 'Ace_JP' in id:
            return self.handle_direct_url(id)
        return ''

    def handle_special_url(self, id, prefix):
        fenge = id.split(prefix)
        url2 = f"{prefix}{fenge[1]}"
        url2 = self.encrypt_aes_cbc(url2)
        params = {'parse_api': fenge[0],'url': url2,'player_parse_type': 1,'token': ''}
        url = f"{xurl}/api.php/qijiappapi.index/vodParse"
        response = requests.post(url, data=params, headers=headers)
        response_data = response.json()
        data_value = response_data['data']
        data = self.decrypt_aes_cbc(data_value)
        data = json.loads(data)
        inner_json = json.loads(data['json'])
        return inner_json['url']

    def handle_direct_url(self, id):
        detail = requests.get(url=id, headers=headers)
        detail.encoding = "utf-8"
        data = detail.json()
        return data['url']

    def build_player_result(self, url_value):
        return {"parse": 0,"playUrl": '',"url": url_value,"header": headerx}

    def searchContentPage(self, key, quick, pg):
        videos = []
        page = self.parse_search_page(pg)
        data = self.build_search_request_data(key, page)
        response_data = self.fetch_search_data(data)
        self.process_search_results(response_data, videos)
        return self.build_search_result(videos, pg)

    def parse_search_page(self, pg):
        return int(pg) if pg else 1

    def build_search_request_data(self, key, page):
        return {'keywords': key,'type_id': 0,'page': page}

    def fetch_search_data(self, data):
        url = "http://110.42.67.221:8006/api.php/qijiappapi.index/searchList7"
        response = requests.post(url=url, headers=headers, data=data)
        response_data = response.json()
        data = response_data['data']
        data = self.decrypt_aes_cbc(data)
        return json.loads(data)

    def process_search_results(self, data, videos):
        for vod in data['search_list']:
            video = self.create_search_video_item(vod)
            videos.append(video)

    def create_search_video_item(self, vod):
        name = vod['vod_name']
        id = vod['vod_id']
        pic = vod['vod_pic']
        remark = vod.get('vod_remarks', '暂无备注')
        return {"vod_id": id,"vod_name": name,"vod_pic": pic,"vod_remarks": remark}

    def build_search_result(self, videos, pg):
        return {'list': videos,'page': pg,'pagecount': 9999,'limit': 90,'total': 999999}

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, '1')

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None











