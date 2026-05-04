import re
from datetime import datetime
from bs4 import BeautifulSoup


def extract_passenger_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    records = []

    cards = soup.find_all('div', class_='card9 weibo-member')
    if not cards:
        cards = soup.select('.card.m-panel.card9.weibo-member')

    for card in cards:
        og_text_div = card.select_one('.weibo-og .weibo-text')
        if not og_text_div:
            continue
        text = og_text_div.get_text(separator=' ', strip=True)

        # 筛选包含客流数据的微博
        if '#昨日客流#' not in text and '客运量' not in text:
            continue

        # 获取当前时间（用于动态年份）
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        year = None
        month = None
        day = None

        # 1. 尝试匹配完整 "2026年5月3日" 格式
        full_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
        if full_match:
            year = int(full_match.group(1))
            month = int(full_match.group(2))
            day = int(full_match.group(3))
        else:
            # 2. 匹配 "5月3日" 格式
            md_match = re.search(r'(\d{1,2})月(\d{1,2})日', text)
            if md_match:
                month = int(md_match.group(1))
                day = int(md_match.group(2))
                year = current_year
                # 如果解析出的月份比当前月份大1以上（例如当前1月，数据为12月），则认为是去年
                if month > current_month + 1:
                    year -= 1
            else:
                # 3. 匹配单独的 "3日" 格式（极少见，作为后备）
                d_match = re.search(r'(\d{1,2})日', text)
                if d_match:
                    day = int(d_match.group(1))
                    # 默认取当前月份的上一个月
                    month = current_month - 1 if current_month > 1 else 12
                    year = current_year
                    if month == 12:
                        year -= 1
                else:
                    print(f"警告：无法解析日期 -> {text[:60]}")
                    continue

        if year is None or month is None or day is None:
            continue

        date_str = f"{year}-{month:02d}-{day:02d}"

        # 解析各线路客流
        passenger_data = {}
        pattern = r'(\d+|S\d+)号线\s*(\d+\.?\d*)'
        matches = re.findall(pattern, text)
        for line_num, val_str in matches:
            line_name = line_num + '号线'
            passenger_data[line_name] = float(val_str)

        if not passenger_data:
            print(f"警告：未提取到线路客流数据 -> {text[:80]}")
            continue

        # 提取或计算总客流量
        total = 0.0
        total_match = re.search(r'(?:总?客运量)\s*(\d+\.?\d*)', text)
        if total_match:
            total = float(total_match.group(1))
        else:
            total = sum(passenger_data.values())

        passenger_data['total_passengers'] = round(total, 1)

        print(f"解析成功: {date_str} 总客流量 {total:.1f} 万，线路数 {len(passenger_data)-1}")

        records.append({
            "date": date_str,
            "passenger_data": passenger_data,
            "raw_text": text[:100]
        })

    return records


# 本地测试（可选）
if __name__ == "__main__":
    # 请根据实际 HTML 文件路径调整
    with open('docs/data/page.html', 'r', encoding='utf-8') as f:
        html = f.read()
    data = extract_passenger_data(html)
