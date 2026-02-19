# coding=utf-8
# File       : run.py
# Time       ：2025/9/12 18:40
# Author     ：yun.code@outlook.com
# Soft       : PyCharm
# version    ：3.12

'''
Description：主程序入口，协调执行不同任务
'''

import os
import time
from keyword_dig import KeywordDig
from keyword_searchpv import KeywordSearchPV
from data_save import DataSaver
from file_reader import FileReader


class KeywordRunner:
    def __init__(self):
        self.digger = KeywordDig()
        self.saver = DataSaver()
        self.reader = FileReader()
        # 初始化流量查询器，指定输出目录
        self.pv_searcher = KeywordSearchPV(
            output_dir=self.saver.output_dir
        )

    def run_dig_task(self, seed_file=None):
        """执行关键词挖掘任务"""
        try:
            seed_file = seed_file or self.reader.get_default_seed_file()
            print(f"从文件读取种子关键词: {seed_file}")
            keywords = self.reader.read_keywords(seed_file)
            print(f"成功读取 {len(keywords)} 个种子关键词")

            # 初始化挖词结果文件（先写表头，后续增量写入）
            dig_file = self.saver.create_dig_file_path()
            self.saver.init_dig_file(dig_file)

            # 全局去重容器
            api_keywords = set()  # 已通过API返回的关键词集合
            word_meta_map = {}    # 下拉/相关搜索词元信息：{关键词: {seed_keyword, source_type, dig_time}}
            api_written_count = 0
            for i, keyword in enumerate(keywords, 1):
                print(f"\n{'-' * 60}")
                print(f"处理关键词 {i}/{len(keywords)}: {keyword}")

                result = self._process_single_dig(keyword)

                # 1) API 拓词结果即时追加保存到挖词 CSV
                api_written_count += self.saver.save_dig_api_batch(
                    seed_keyword=keyword,
                    api_items=result.get('api_words', []),
                    file_path=dig_file,
                    dig_time=result['dig_time']
                )

                # 记录API关键词集合用于后续去重
                for item in result.get('api_words', []):
                    k = item.get('keyword', '')
                    if k:
                        api_keywords.add(k)

                # 2) 收集下拉/相关搜索词的元信息（全局去重按第一次来源记录）
                for w in result.get('sug_words', []):
                    if w and w not in word_meta_map:
                        word_meta_map[w] = {
                            'seed_keyword': keyword,
                            'source_type': '下拉框',
                            'dig_time': result['dig_time']
                        }
                for w in result.get('related_search_words', []):
                    if w and w not in word_meta_map:
                        word_meta_map[w] = {
                            'seed_keyword': keyword,
                            'source_type': '相关搜索',
                            'dig_time': result['dig_time']
                        }

                if i % 5 == 0 and i < len(keywords):
                    print("休息3秒，避免请求过于频繁...")
                    time.sleep(3)

            print(f"\n{'-' * 60}")
            print("开始处理非API关键词的流量查询并追加写入...")

            # 过滤出需要查询 PV 的下拉/相关搜索词（排除 API 已覆盖）
            non_api_keywords = [k for k in word_meta_map.keys() if k not in api_keywords]

            sug_saved = 0
            related_saved = 0

            if non_api_keywords:
                try:
                    pv_file, pv_results = self.pv_searcher.search_pv(non_api_keywords)
                    print(f"非API关键词的流量结果临时保存到: {pv_file}")

                    # 将PV数据映射回挖词CSV（保留原来源类型与种子词）
                    appended = self.saver.append_non_api_pv_rows(
                        file_path=dig_file,
                        word_meta_map=word_meta_map,
                        pv_results=pv_results
                    )

                    # 统计按来源类型的追加量
                    for item in pv_results:
                        src = word_meta_map.get(item.get('keyword', ''), {}).get('source_type')
                        if src == '下拉框':
                            sug_saved += 1
                        elif src == '相关搜索':
                            related_saved += 1

                    print(f"已将 {appended} 条非API关键词（含PV）追加写入挖词文件: {dig_file}")
                except Exception as e:
                    print(f"非API关键词自动流量查询或追加写入出错: {str(e)}")
            else:
                print("无需要查询PV的非API关键词。")

            # 打印统计信息
            dedup_stats = {
                'sug_words': sug_saved,
                'related_words': related_saved,
                'api_words': api_written_count,
                'total': sug_saved + related_saved + api_written_count
            }
            self._print_dig_statistics(dedup_stats, [
                # 构造最小统计所需结构
                {
                    'sug_words': [k for k, v in word_meta_map.items() if v['source_type'] == '下拉框'],
                    'related_search_words': [k for k, v in word_meta_map.items() if v['source_type'] == '相关搜索'],
                    'api_words': [{'keyword': k} for k in api_keywords]
                }
            ])

            print(f"挖掘结果主文件: {dig_file}")
            return dig_file

        except Exception as e:
            print(f"挖掘任务执行出错: {str(e)}")
            return None

    def run_pv_task(self, pv_file=None):
        """执行关键词流量查询任务（批量查询批量保存）"""
        try:
            # 1. 读取待查询关键词
            pv_file = pv_file or self.reader.get_default_pv_file()
            print(f"从文件读取待查询流量关键词: {pv_file}")
            keywords = self.reader.read_keywords(pv_file)
            print(f"成功读取 {len(keywords)} 个待查询关键词")

            # 2. 执行流量查询（每批查询完成后会自动保存）
            print("开始查询关键词流量，每批查询完成后将自动保存结果...")
            csv_file, all_results = self.pv_searcher.search_pv(keywords)
            print(f"流量查询全部完成，总记录数: {len(all_results)} 条（包含过滤结果）")
            print(f"最终结果文件: {csv_file}")

            return csv_file

        except Exception as e:
            print(f"流量查询任务执行出错: {str(e)}")
            return None

    def _process_single_dig(self, keyword):
        """处理单个关键词的挖掘"""
        result = {
            'seed_keyword': keyword,
            'sug_words': [],
            'related_search_words': [],
            'api_words': [],
            'dig_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            print("获取下拉框推荐词...", end=' ')
            result['sug_words'] = self.digger.sug_word(keyword)
            print(f"找到 {len(result['sug_words'])} 个")

            time.sleep(1)

            print("获取相关搜索词...", end=' ')
            result['related_search_words'] = self.digger.other_search_word(keyword)
            print(f"找到 {len(result['related_search_words'])} 个")

            time.sleep(1)

            print("通过API获取关键词...", end=' ')
            result['api_words'] = self.digger.fc_api_word(keyword)
            print(f"找到 {len(result['api_words'])} 个")

        except Exception as e:
            print(f"处理关键词 {keyword} 时出错: {str(e)}")

        return result

    def _print_dig_statistics(self, dedup_stats, all_results):
        """打印挖掘统计信息"""
        original_stats = {
            'sug_words': sum(len(r['sug_words']) for r in all_results),
            'related_words': sum(len(r['related_search_words']) for r in all_results),
            'api_words': sum(len(r['api_words']) for r in all_results)
        }

        total_original = original_stats['sug_words'] + original_stats['related_words'] + original_stats['api_words']
        total_duplicates = total_original - dedup_stats['total']

        print("\n" + "=" * 60)
        print("挖词结果统计信息")
        print("-" * 60)
        print(
            f"下拉框：挖掘 {original_stats['sug_words']:,} 个，去重 {original_stats['sug_words'] - dedup_stats['sug_words']:,} 个，保存 {dedup_stats['sug_words']:,} 个")
        print(
            f"相关搜索：挖掘 {original_stats['related_words']:,} 个，去重 {original_stats['related_words'] - dedup_stats['related_words']:,} 个，保存 {dedup_stats['related_words']:,} 个")
        print(
            f"API拓词：挖掘 {original_stats['api_words']:,} 个，去重 {original_stats['api_words'] - dedup_stats['api_words']:,} 个，保存 {dedup_stats['api_words']:,} 个")
        print("-" * 60)
        print(f"合计：挖掘 {total_original:,} 个，去重 {total_duplicates:,} 个，保存 {dedup_stats['total']:,} 个")
        print("=" * 60)


def main():
    print("=" * 60)
    print("关键词工具启动")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    runner = KeywordRunner()

    print("\n请选择要执行的任务:")
    print("1. 关键词挖掘（从种子词拓展新关键词）")
    print("2. 关键词流量查询（查询已有关键词的搜索量）")

    choice = input("请输入任务编号(1/2): ").strip()

    if choice == '1':
        print("\n可选：自定义种子词文件路径（留空使用默认 input_data/keyword.txt）")
        custom_seed = input("请输入种子词文件路径: ").strip()
        runner.run_dig_task(seed_file=custom_seed or None)
    elif choice == '2':
        print("\n可选：自定义待查PV关键词文件路径（留空使用默认 input_data/pv_keywords.txt）")
        custom_pv = input("请输入待查PV关键词文件路径: ").strip()
        runner.run_pv_task(pv_file=custom_pv or None)
    else:
        print("无效的选择")
        return

    print("\n任务完成")
    print(f"完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
