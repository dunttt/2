# coding=utf-8
# File       : data_save.py
# Time       ：2025/9/12 19:30
# Author     ：yun.code@outlook.com
# Soft       : PyCharm
# version    ：3.12

'''
Description：处理并保存关键词挖掘结果和流量查询结果，修复字段不匹配问题
'''

import csv
import os
import time
from typing import List, Dict, Tuple


class DataSaver:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "output_data")
        os.makedirs(self.output_dir, exist_ok=True)

        # 挖掘结果表头
        self.dig_headers = [
            '种子词',
            '挖词类型',
            '关键词',
            '月均搜索量',
            '月均PC搜索量',
            '月均M搜索量',
            '日均搜索量',
            '日均PC搜索量',
            '日均M搜索量',
            '挖掘时间'
        ]

        # 流量查询结果表头（明确字段对应关系）
        self.pv_headers = [
            '关键词',
            '过滤状态',
            '过滤原因',
            '月均搜索量',
            '月均PC搜索量',
            '月均M搜索量',
            '日均搜索量',
            '日均PC搜索量',
            '日均M搜索量',
            '数据来源',
            '查询时间'
        ]

    def create_dig_file_path(self) -> str:
        """创建挖词结果文件路径（含唯一时间戳）"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        return os.path.join(self.output_dir, f"keyword_dig_results_{timestamp}.csv")

    def init_dig_file(self, file_path: str) -> None:
        """初始化挖词 CSV 文件（仅写入表头）"""
        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.dig_headers)
            writer.writeheader()

    def save_dig_api_batch(self, seed_keyword: str, api_items: List[Dict], file_path: str, dig_time: str) -> int:
        """将单个种子词的 API 拓词结果立即追加写入挖词 CSV，返回写入条数"""
        if not api_items:
            return 0
        with open(file_path, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.dig_headers)
            count = 0
            for item in api_items:
                writer.writerow({
                    '种子词': seed_keyword,
                    '挖词类型': 'API拓词',
                    '关键词': item.get('keyword', ''),
                    '月均搜索量': item.get('averageMonthPv', '-'),
                    '月均PC搜索量': item.get('averageMonthPvPc', '-'),
                    '月均M搜索量': item.get('averageMonthPvMobile', '-'),
                    '日均搜索量': item.get('averageDayPv', '-'),
                    '日均PC搜索量': item.get('averageDayPvPc', '-'),
                    '日均M搜索量': item.get('averageDayPvMobile', '-'),
                    '挖掘时间': dig_time
                })
                count += 1
        return count

    def append_non_api_pv_rows(self, file_path: str, word_meta_map: Dict[str, Dict], pv_results: List[Dict]) -> int:
        """
        将下拉/相关搜索去重后的词的 PV 结果追加写入挖词 CSV。
        word_meta_map: {keyword: {seed_keyword, source_type, dig_time}}
        pv_results: 来自 KeywordSearchPV 的结果列表（包含 averageMonthPv 等字段）
        返回写入条数
        """
        if not pv_results:
            return 0
        with open(file_path, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.dig_headers)
            count = 0
            for item in pv_results:
                key = item.get('keyword', '')
                meta = word_meta_map.get(key, {})
                writer.writerow({
                    '种子词': meta.get('seed_keyword', ''),
                    '挖词类型': meta.get('source_type', '下拉/相关搜索'),
                    '关键词': key,
                    '月均搜索量': item.get('averageMonthPv', '-'),
                    '月均PC搜索量': item.get('averageMonthPvPc', '-'),
                    '月均M搜索量': item.get('averageMonthPvMobile', '-'),
                    '日均搜索量': item.get('averageDayPv', '-'),
                    '日均PC搜索量': item.get('averageDayPvPc', '-'),
                    '日均M搜索量': item.get('averageDayPvMobile', '-'),
                    '挖掘时间': meta.get('dig_time', time.strftime('%Y-%m-%d %H:%M:%S'))
                })
                count += 1
        return count

    def save_dig_results(self, all_results: List[Dict]) -> Tuple[str, Dict]:
        """处理并保存关键词挖掘结果"""
        # 实现保持不变...
        unique_api_words = {}
        for result in all_results:
            for item in result['api_words']:
                keyword = item['keyword']
                if keyword not in unique_api_words:
                    unique_api_words[keyword] = {
                        'seed_keyword': result['seed_keyword'],
                        'item': item,
                        'dig_time': result['dig_time']
                    }

        dedup_stats = {
            'sug_words': 0,
            'related_words': 0,
            'api_words': len(unique_api_words),
            'total': 0
        }

        api_keywords_set = set(unique_api_words.keys())
        all_stored_keywords = set(unique_api_words.keys())

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        csv_file = os.path.join(self.output_dir, f"keyword_dig_results_{timestamp}.csv")

        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.dig_headers)
            writer.writeheader()

            for keyword, data in unique_api_words.items():
                item = data['item']
                writer.writerow({
                    '种子词': data['seed_keyword'],
                    '挖词类型': 'API拓词',
                    '关键词': keyword,
                    '月均搜索量': item['averageMonthPv'],
                    '月均PC搜索量': item['averageMonthPvPc'],
                    '月均M搜索量': item['averageMonthPvMobile'],
                    '日均搜索量': item['averageDayPv'],
                    '日均PC搜索量': item['averageDayPvPc'],
                    '日均M搜索量': item['averageDayPvMobile'],
                    '挖掘时间': data['dig_time']
                })

            for result in all_results:
                seed_keyword = result['seed_keyword']
                dig_time = result['dig_time']

                for word in result['sug_words']:
                    if word not in all_stored_keywords:
                        writer.writerow({
                            '种子词': seed_keyword,
                            '挖词类型': '下拉框',
                            '关键词': word,
                            '月均搜索量': '-',
                            '月均PC搜索量': '-',
                            '月均M搜索量': '-',
                            '日均搜索量': '-',
                            '日均PC搜索量': '-',
                            '日均M搜索量': '-',
                            '挖掘时间': dig_time
                        })
                        all_stored_keywords.add(word)
                        dedup_stats['sug_words'] += 1

                for word in result['related_search_words']:
                    if word not in all_stored_keywords:
                        writer.writerow({
                            '种子词': seed_keyword,
                            '挖词类型': '相关搜索',
                            '关键词': word,
                            '月均搜索量': '-',
                            '月均PC搜索量': '-',
                            '月均M搜索量': '-',
                            '日均搜索量': '-',
                            '日均PC搜索量': '-',
                            '日均M搜索量': '-',
                            '挖掘时间': dig_time
                        })
                        all_stored_keywords.add(word)
                        dedup_stats['related_words'] += 1

        dedup_stats['total'] = dedup_stats['sug_words'] + dedup_stats['related_words'] + dedup_stats['api_words']
        return csv_file, dedup_stats

    def save_pv_batch(self, pv_results: List[Dict], file_path: str, is_first_batch: bool = False) -> None:
        """
        批量保存关键词流量查询结果
        :param pv_results: 单批查询结果
        :param file_path: 保存文件路径
        :param is_first_batch: 是否为第一批数据（决定是否写入表头）
        """
        # 打开文件模式：第一批用写入模式，后续用追加模式
        mode = 'w' if is_first_batch else 'a'

        with open(file_path, mode, encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.pv_headers)

            # 只有第一批数据才写入表头
            if is_first_batch:
                writer.writeheader()

            # 处理每条结果，确保字段映射正确
            for item in pv_results:
                # 严格按照表头字段进行映射，修复字段不匹配问题
                writer.writerow({
                    '关键词': item['keyword'],
                    '过滤状态': item['status'],
                    '过滤原因': item['reason'],
                    '月均搜索量': item['averageMonthPv'],
                    '月均PC搜索量': item['averageMonthPvPc'],
                    '月均M搜索量': item['averageMonthPvMobile'],
                    '日均搜索量': item['averageDayPv'],
                    '日均PC搜索量': item['averageDayPvPc'],
                    '日均M搜索量': item['averageDayPvMobile'],
                    '数据来源': item['source'],
                    '查询时间': item.get('query_time', time.strftime('%Y-%m-%d %H:%M:%S'))
                })

        print(f"已保存 {len(pv_results)} 条数据到: {file_path}")

    def create_pv_file_path(self) -> str:
        """创建流量查询结果文件路径（含唯一时间戳）"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        return os.path.join(self.output_dir, f"keyword_pv_results_{timestamp}.csv")
