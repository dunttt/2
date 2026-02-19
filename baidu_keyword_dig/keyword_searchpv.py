# coding=utf-8
# File       : keyword_searchpv.py
# Time       ：2025/9/12 19:30
# Author     ：yun.code@outlook.com
# Soft       : PyCharm
# version    ：3.12

'''
Description：关键词流量查询任务，修复批量保存字段不匹配问题
'''

import requests
import json
import os
import configparser
import time
import requests.exceptions


class KeywordSearchPV:
    def __init__(self, config_path=None, output_dir=None):
        # 初始化配置解析器
        self.config = configparser.ConfigParser(interpolation=None)
        self.config_file = config_path or os.path.join(os.path.dirname(__file__), "config.ini")
        self._load_config()
        self._init_config()

        # 输出目录（从外部传入，确保与DataSaver一致）
        self.output_dir = output_dir
        self.max_allowed_length = 40

    def _load_config(self):
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
        read_ok = self.config.read(self.config_file, encoding="utf-8")
        if not read_ok:
            raise IOError(f"无法读取配置文件: {self.config_file}")
        required_sections = ["DEFAULT", "USER_CONFIG"]
        for section in required_sections:
            if section not in self.config.sections() and section not in self.config:
                raise ValueError(f"配置文件缺少必要段: [{section}]")

    def _init_config(self):
        self.headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://fengchao.baidu.com',
            'referer': 'https://fengchao.baidu.com/fc/toolscenter/orientation/kr/user/20161608?from=qingge&globalProduct=1&userId=20161608&in=iframe&host_app=qingge',
            'user-agent': self.config.get("USER_CONFIG", "user-agent"),
            'cookie': self.config.get("USER_CONFIG", "cookie"),
        }
        self.api_url = self.config.get("DEFAULT", "fengchao_api_url")
        self.userid = self.config.get("USER_CONFIG", "userid")
        self.token = self.config.get("USER_CONFIG", "token")
        self.reqid = self.config.get("USER_CONFIG", "reqid")
        self.batch_size = 1000

    def _calculate_length(self, keyword):
        length = 0
        for char in keyword:
            if '\u4e00' <= char <= '\u9fff' or \
                    '\u3000' <= char <= '\u303f' or \
                    '\uff00' <= char <= '\uffef':
                length += 2
            else:
                length += 1
        return length

    def _filter_long_keywords(self, keywords):
        filtered = []
        filter_info = []
        for keyword in keywords:
            length = self._calculate_length(keyword)
            if length > self.max_allowed_length:
                filter_info.append({
                    'keyword': keyword,
                    'status': '字符过滤',
                    'reason': f'长度为{length}，超过最大允许长度{self.max_allowed_length}',
                    'averageMonthPv': '-',
                    'averageMonthPvPc': '-',
                    'averageMonthPvMobile': '-',
                    'averageDayPv': '-',
                    'averageDayPvPc': '-',
                    'averageDayPvMobile': '-',
                    'source': 'local',
                    'query_time': time.strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                filtered.append(keyword)
        return filtered, filter_info

    def _query_batch(self, keywords):
        try:
            params = {
                "logid": -1,
                "bidWordSource": "wordList",
                "keywordList": [{"keywordName": key} for key in keywords]
            }

            payload = {
                'reqid': self.reqid,
                'userid': self.userid,
                'token': self.token,
                'path': 'puppet/GET/PvSearchFunction/getPvSearch',
                'source': 'aix',
                'params': json.dumps(params)
            }

            response = requests.post(
                url=self.api_url,
                data=payload,
                headers=self.headers
            )

            response.raise_for_status()
            data = json.loads(response.text)

            if 'data' not in data or 'data' not in data['data']:
                return [{
                    'keyword': keyword,
                    'status': '未知过滤',
                    'reason': 'API未返回数据',
                    'averageMonthPv': '-',
                    'averageMonthPvPc': '-',
                    'averageMonthPvMobile': '-',
                    'averageDayPv': '-',
                    'averageDayPvPc': '-',
                    'averageDayPvMobile': '-',
                    'source': 'search',
                    'query_time': time.strftime('%Y-%m-%d %H:%M:%S')
                } for keyword in keywords]

            keyword_data_list = data['data']['data']
            result = []
            returned_keywords = set()

            for keyword_data in keyword_data_list:
                item = {
                    'keyword': keyword_data.get('keywordName', ''),
                    'status': '正常',
                    'reason': '',
                    'averageMonthPv': keyword_data.get('averageMonthPv', '-'),
                    'averageMonthPvPc': keyword_data.get('averageMonthPvPc', '-'),
                    'averageMonthPvMobile': keyword_data.get('averageMonthPvMobile', '-'),
                    'averageDayPv': '-',
                    'averageDayPvPc': '-',
                    'averageDayPvMobile': '-',
                    'source': 'search',
                    'query_time': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                result.append(item)
                returned_keywords.add(item['keyword'])

            for keyword in keywords:
                if keyword not in returned_keywords:
                    result.append({
                        'keyword': keyword,
                        'status': '未知过滤',
                        'reason': 'API返回结果中不包含该关键词',
                        'averageMonthPv': '-',
                        'averageMonthPvPc': '-',
                        'averageMonthPvMobile': '-',
                        'averageDayPv': '-',
                        'averageDayPvPc': '-',
                        'averageDayPvMobile': '-',
                        'source': 'search',
                        'query_time': time.strftime('%Y-%m-%d %H:%M:%S')
                    })

            return result

        except Exception as e:
            print(f"批量查询搜索量出错: {str(e)}")
            return [{
                'keyword': keyword,
                'status': '未知过滤',
                'reason': str(e),
                'averageMonthPv': '-',
                'averageMonthPvPc': '-',
                'averageMonthPvMobile': '-',
                'averageDayPv': '-',
                'averageDayPvPc': '-',
                'averageDayPvMobile': '-',
                'source': 'search',
                'query_time': time.strftime('%Y-%m-%d %H:%M:%S')
            } for keyword in keywords]

    def search_pv(self, keywords):
        """查询多个关键词的搜索量数据，批量查询批量保存"""
        from data_save import DataSaver  # 避免循环导入

        # 初始化数据保存器
        saver = DataSaver(self.output_dir)
        # 创建唯一的结果文件路径
        result_file = saver.create_pv_file_path()

        # 所有结果的汇总列表
        all_results = []

        # 1. 先处理并保存被字符过滤的关键词
        filtered_keywords, filter_results = self._filter_long_keywords(keywords)
        if filter_results:
            all_results.extend(filter_results)
            # 保存过滤结果（作为第一批数据写入，包含表头）
            saver.save_pv_batch(filter_results, result_file, is_first_batch=True)
            first_batch_saved = True
        else:
            first_batch_saved = False

        # 2. 计算总批次
        total_batches = (len(filtered_keywords) + self.batch_size - 1) // self.batch_size

        # 3. 按批次处理过滤后的关键词
        for i in range(0, len(filtered_keywords), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch = filtered_keywords[i:i + self.batch_size]
            print(f"正在查询第 {batch_num}/{total_batches} 批，共 {len(batch)} 个关键词")

            # 执行查询
            batch_results = self._query_batch(batch)
            all_results.extend(batch_results)

            # 保存当前批次结果（第一批非过滤数据需要判断是否已写入表头）
            saver.save_pv_batch(
                batch_results,
                result_file,
                is_first_batch=not first_batch_saved and batch_num == 1
            )
            first_batch_saved = True  # 确保后续批次都是追加模式

            # 控制请求频率
            if i + self.batch_size < len(filtered_keywords):
                time.sleep(2)

        return result_file, all_results
