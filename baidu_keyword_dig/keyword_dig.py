# coding=utf-8
# File       : keyword_dig.py
# Time       ：2025/9/11 10:42
# Author     ：yun.code@outlook.com
# Soft       : PyCharm
# version    ：3.12

'''
Description：执行关键词挖掘任务，下拉框、相关搜索、推广后台API
'''

import requests
import json
import os
import configparser
from lxml import etree
import requests.exceptions


class KeywordDig:
    def __init__(self, config_path=None):
        # 初始化配置解析器
        # 禁用插值功能，避免解析 % 字符
        self.config = configparser.ConfigParser(interpolation=None)

        # 配置文件路径（默认同目录下的config.ini）
        self.config_file = config_path or os.path.join(os.path.dirname(__file__), "config.ini")

        # 读取配置文件
        self._load_config()

        # 加载配置项到实例变量
        self._init_config()

    def _load_config(self):
        """加载并验证配置文件"""
        # 检查配置文件是否存在
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")

        # 读取配置文件
        read_ok = self.config.read(self.config_file, encoding="utf-8")
        if not read_ok:
            raise IOError(f"无法读取配置文件: {self.config_file}")

        # 验证必要的配置段是否存在
        required_sections = ["DEFAULT", "USER_CONFIG"]
        for section in required_sections:
            if section not in self.config.sections() and section not in self.config:
                raise ValueError(f"配置文件缺少必要段: [{section}]")

    def _init_config(self):
        """初始化配置项到实例变量"""
        # 请求头配置
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'user-agent': self.config.get("USER_CONFIG", "user-agent"),
            'cookie': self.config.get("USER_CONFIG", "cookie")
        }

        self.api_headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://fengchao.baidu.com',
            'referer': 'https://fengchao.baidu.com/fc/toolscenter/orientation/kr/user/20161608?from=qingge&globalProduct=1&userId=20161608&in=iframe&host_app=qingge',
            'user-agent': self.config.get("USER_CONFIG", "user-agent"),
            'cookie': self.config.get("USER_CONFIG", "cookie"),
        }

        # API地址配置（从DEFAULT段获取）
        self.sug_url = self.config.get("DEFAULT", "baidu_sug_url")
        self.search_url = self.config.get("DEFAULT", "baidu_search_url")
        self.fengchao_api_url = self.config.get("DEFAULT", "fengchao_api_url")

        # 用户认证信息（从USER_CONFIG段获取）
        self.userid = self.config.get("USER_CONFIG", "userid")
        self.token = self.config.get("USER_CONFIG", "token")
        self.reqid = self.config.get("USER_CONFIG", "reqid")

    def sug_word(self, key):
        """获取搜索下拉框推荐词"""
        try:
            payload = {
                'prod': 'pc',
                'wd': key
            }

            response = requests.get(
                url=self.sug_url,
                params=payload,
                headers=self.headers
            )
            response.raise_for_status()

            dict_data = json.loads(response.text)
            if "g" not in dict_data:
                return []

            keyword_data_list = dict_data["g"]
            return [item['q'] for item in keyword_data_list]

        except requests.exceptions.RequestException as e:
            print(f"获取下拉框推荐词网络错误 ({key}): {str(e)}")
        except Exception as e:
            print(f"获取下拉框推荐词处理错误 ({key}): {str(e)}")
        return []

    def other_search_word(self, key):
        """获取页面里的相关搜索词"""
        try:
            payload = {
                'wd': key
            }

            response = requests.get(
                url=self.search_url,
                params=payload,
                headers=self.headers
            )
            response.raise_for_status()

            html = etree.HTML(response.text)

            # 可能需要根据实际页面结构调整XPath
            dajia_word_list = html.xpath('//div[@class="list_1V4Yg"]//a//span[2]/text()')
            xiangguan_word_list = html.xpath(
                '//a[@class="rs-link_2DE3Q c-line-clamp1 c-color-link cos-font-medium"]/@title')

            # 去重并返回
            return list(set(dajia_word_list + xiangguan_word_list))

        except requests.exceptions.RequestException as e:
            print(f"获取相关搜索词网络错误 ({key}): {str(e)}")
        except Exception as e:
            print(f"获取相关搜索词处理错误 ({key}): {str(e)}")
        return []

    def fc_api_word(self, key):
        """通过API获取相关关键词及数据"""
        try:
            params = {
                "keyWordRecommendFilter": {
                    "device": '0',
                    "positiveWords": [],
                    "negativeWords": [],
                    "regionExtend": True,
                    "removeDuplicate": True,
                    "keywordRecommendReasons": [],
                    "searchRegions": "9999999"
                },
                "source": "web",
                "queryBy": '0',
                "querys": [key],
                "querySessions": [key],
                "entryMessage": "kr_station"
            }

            payload = {
                'reqid': self.reqid,
                'userid': self.userid,
                'token': self.token,
                'path': 'lightning/GET/KeywordSuggestService/getKeywordRecommendPassive',
                'source': 'aix',
                'params': json.dumps(params)
            }

            response = requests.post(
                url=self.fengchao_api_url,
                data=payload,
                headers=self.api_headers
            )
            response.raise_for_status()

            api_data = json.loads(response.text)

            if 'data' not in api_data or 'keywordRecommendItems' not in api_data['data']:
                return []

            keywords_dict_list = api_data['data']['keywordRecommendItems']

            result = []
            for word_dict in keywords_dict_list:
                item = {
                    'keyword': word_dict.get('keyword', ''),
                    'averageMonthPv': word_dict.get('averageMonthPv', '-'),
                    'averageMonthPvPc': word_dict.get('averageMonthPvPc', '-'),
                    'averageMonthPvMobile': word_dict.get('averageMonthPvMobile', '-'),
                    'averageDayPv': word_dict.get('averageDayPv', '-'),
                    'averageDayPvPc': word_dict.get('averageDayPvPc', '-'),
                    'averageDayPvMobile': word_dict.get('averageDayPvMobile', '-'),
                    'source': 'api'
                }
                result.append(item)

            return result

        except requests.exceptions.RequestException as e:
            print(f"API拓词网络错误 ({key}): {str(e)}")
        except Exception as e:
            print(f"API拓词处理错误 ({key}): {str(e)}")
        return []
