# coding=utf-8
# File       : file_reader.py
# Time       ：2025/9/12 16:00
# Author     ：yun.code@outlook.com
# Soft       : PyCharm
# version    ：3.12

'''
Description：文件读取工具，负责读取input_data文件夹中的关键词文件
'''

import os


class FileReader:
    @staticmethod
    def _ensure_input_dir():
        """确保input_data文件夹存在"""
        input_dir = os.path.join(os.path.dirname(__file__), "input_data")
        os.makedirs(input_dir, exist_ok=True)
        return input_dir

    @staticmethod
    def read_keywords(file_path, skip_comment=True):
        """
        读取关键词文件
        :param file_path: 文件路径
        :param skip_comment: 是否跳过注释行（#开头）
        :return: 关键词列表
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                keywords = []
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # 跳过注释行
                    if skip_comment and line.startswith('#'):
                        continue
                    keywords.append(line)

                if not keywords:
                    raise ValueError(f"文件中没有有效的关键词: {file_path}")

                return keywords

        except Exception as e:
            raise Exception(f"读取文件出错: {str(e)}")

    @staticmethod
    def get_default_seed_file():
        """获取默认种子关键词文件路径（位于input_data文件夹）"""
        input_dir = FileReader._ensure_input_dir()
        seed_file = os.path.join(input_dir, "keyword.txt")
        # 如果文件不存在则创建
        if not os.path.exists(seed_file):
            with open(seed_file, 'w', encoding='utf-8') as f:
                f.write("# 请在此处输入种子关键词，每行一个\n")
                f.write("# 以#开头的行将被视为注释\n")
        return seed_file

    @staticmethod
    def get_default_pv_file():
        """获取默认待查询流量关键词文件路径（位于input_data文件夹）"""
        input_dir = FileReader._ensure_input_dir()
        pv_file = os.path.join(input_dir, "pv_keywords.txt")
        # 如果文件不存在则创建
        if not os.path.exists(pv_file):
            with open(pv_file, 'w', encoding='utf-8') as f:
                f.write("# 请在此处输入待查询流量的关键词，每行一个\n")
                f.write("# 以#开头的行将被视为注释\n")
        return pv_file
