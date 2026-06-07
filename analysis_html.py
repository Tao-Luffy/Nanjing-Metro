#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from datetime import datetime
from bs4 import BeautifulSoup


def extract_passenger_data(html_content):
    """
    从微博页面 HTML 中提取南京地铁每日客流数据。

    参数:
        html_content (str): 微博页面的 HTML 文本

    返回:
        list: 包含字典的列表，每个字典格式：
              {
                  "date": "2026-05-03",
                  "passenger_data": {
                      "1号线": 95.31,
                      "2号线": 84.55,
                      ...
                      "total_passengers": 451.84
                  },
                  "raw_text": "微博原文前100字"
              }
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    records = []

    # 查找所有微博卡片（适配新旧版结构）
    cards = soup.find_all('div', class_='card9 weibo-member')
    if not cards:
        cards = soup.select('.card.m-panel.card9.weibo-member')

    for card in cards:
        # 提取原创微博文本（非转发）
        og_text_div = card.select_one('.weibo-og .weibo-text')
        if not og_text_div:
            continue
        text = og_text_div.get_text(separator=' ', strip=True)

        # 只处理包含客流数据的微博（#昨日客流# 或 “客运量”）
        if '#昨日客流#' not in text and '客运量' not in text:
            continue

        # ==================== 1. 解析日期（支持动态年份） ====================
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_day = now.day

        year = None
        month = None
        day = None

        # 优先匹配完整 "2026年5月3日" 格式
        full_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
        if full_match:
            year = int(full_match.group(1))
            month = int(full_match.group(2))
            day = int(full_match.group(3))
        else:
            # 匹配 "5月3日" 格式
            md_match = re.search(r'(\d{1,2})月(\d{1,2})日', text)
            if md_match:
                month = int(md_match.group(1))
                day = int(md_match.group(2))
                year = current_year
                # 如果解析出的月份大于当前月份+1，则认为是去年（如当前1月遇上12月数据）
                if month > current_month + 1:
                    year -= 1
            else:
                # 匹配单独的 "3日" 格式（极少情况，作为后备）
                d_match = re.search(r'(\d{1,2})日', text)
                if d_match:
                    day = int(d_match.group(1))
                    if day > current_day + 1:
                        month = current_month - 1
                    else:
                        month = current_month
                    year = current_year
                    if month == 0:
                        month = 12
                        year -= 1
                else:
                    print(f"警告：无法从文本中解析日期 -> {text[:60]}")
                    continue

        if year is None or month is None or day is None:
            continue

        date_str = f"{year}-{month:02d}-{day:02d}"

        # ==================== 2. 解析各线路客流（保留两位小数） ====================
        passenger_data = {}
        # 支持 "1号线"、"S1号线" 等格式
        pattern = r'(\d+|S\d+)号线\s*(\d+\.?\d*)'
        matches = re.findall(pattern, text)
        for line_num, val_str in matches:
            line_name = line_num + '号线'
            passenger_data[line_name] = round(float(val_str), 2)

        if not passenger_data:
            print(f"警告：未提取到任何线路客流数据 -> {text[:80]}")
            continue

        # ==================== 3. 总客流量解析（优先文本提取，否则求和） ====================
        total_passengers = 0.0

        # 优先匹配 "客运量" 后面的数字（不依赖“总”字）
        total_match = re.search(r'客运量\s*(\d+\.?\d*)', text)
        if total_match:
            total_passengers = round(float(total_match.group(1)), 2)
            print(f"从文本提取总客流量: {total_passengers:.2f}")
        else:
            # 若没有明确的总客流量字段，则对各线路客流求和并保留两位小数
            total_passengers = round(sum(passenger_data.values()), 2)
            print(f"未找到'客运量'字段，使用求和: {total_passengers:.2f}")

        passenger_data['total_passengers'] = total_passengers

        print(f"解析成功: {date_str} 总客流量 {total_passengers:.2f} 万")

        records.append({
            "date": date_str,
            "passenger_data": passenger_data,
            "raw_text": text[:100]   # 保存原文前100个字符，便于调试
        })

    return records


# 本地测试入口（可选）
if __name__ == "__main__":
    # 请根据实际情况修改 HTML 文件路径
    html_file = 'docs/data/page.html'
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    data = extract_passenger_data(html)
