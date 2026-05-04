import re

from bs4 import BeautifulSoup


def extract_passenger_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    records = []

    # 查找所有微博卡片
    cards = soup.find_all('div', class_='card9 weibo-member')
    if not cards:
        cards = soup.select('.card.m-panel.card9.weibo-member')

    for card in cards:
        # 提取主微博文本（原创部分）
        og_text_div = card.select_one('.weibo-og .weibo-text')
        if not og_text_div:
            continue
        text = og_text_div.get_text(separator=' ', strip=True)

        # 只处理“#昨日客流#”微博
        if '#昨日客流#' not in text:
            continue

        # 解析日期
        date_str = None
        month = 4  # 根据上下文，所有数据均在 4 月，缺省即为 4
        year = 2026

        # 尝试匹配“4月29日”这类完整月日
        m = re.search(r'(\d{1,2})月(\d{1,2})日', text)
        if m:
            month = int(m.group(1))
            day = int(m.group(2))
            date_str = f"{year}-{month:02d}-{day:02d}"
        else:
            # 尝试匹配单独的“30日”
            m = re.search(r'(\d{1,2})日', text)
            if m:
                day = int(m.group(1))
                date_str = f"{year}-{month:02d}-{day:02d}"

        if not date_str:
            continue  # 无法解析日期则跳过

        # 解析客流数据
        passenger_data = {}
        # 匹配线路和客流，如“1号线99.54”、“S1号线16.26”
        pattern = r'(\d+|S\d+)号线\s*(\d+\.?\d*)'
        for line, val in re.findall(pattern, text):
            passenger_data[line + '号线'] = float(val)

        if not passenger_data:
            continue

        records.append({
            "date": date_str,
            "passenger_data": passenger_data,
            "raw_text": text[:100]
        })

    return records


# 使用示例：
# 假设 html 文件已保存为 page.html
with open('docs/data/page.html', 'r', encoding='utf-8') as f:
    html = f.read()

data = extract_passenger_data(html)
