import re
from datetime import datetime
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

        # 筛选条件：包含 #昨日客流# 或 “客运量”
        if '#昨日客流#' not in text and '客运量' not in text:
            continue

        # ========== 1. 解析日期（支持动态年份） ==========
        current_year = datetime.now().year  # 例如 2026
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
                # 如果解析出来的月份比当前月份大很多，则可能是去年数据（例如当前1月，数据是12月）
                if month > current_month + 1:
                    year -= 1
            else:
                # 匹配单独的 "3日" 格式（月份采用预估值，但实际很少出现）
                d_match = re.search(r'(\d{1,2})日', text)
                if d_match:
                    day = int(d_match.group(1))
                    # 从已有记录中推断月份（最差情况默认4月，但最好有记录留存）
                    month = 4
                    year = current_year

        if year is None or month is None or day is None:
            print(f"警告：无法从文本中解析日期 -> {text[:60]}")
            continue

        date_str = f"{year}-{month:02d}-{day:02d}"

        # ========== 2. 解析各线路客流 ==========
        passenger_data = {}
        # 匹配：“1号线95.31”、“S1号线11.61” 等
        pattern = r'(\d+|S\d+)号线\s*(\d+\.?\d*)'
        matches = re.findall(pattern, text)
        for line_num, val_str in matches:
            line_name = line_num + '号线'  # 例如 “1号线”、“S1号线”
            passenger_data[line_name] = float(val_str)

        if not passenger_data:
            print(f"警告：未提取到任何线路客流数据，文本: {text[:80]}")
            continue

        # ========== 3. 解析或计算总客流量 ==========
        total = 0.0
        # 尝试提取 “客运量451.84” 或 “总客运量451.84”
        total_match = re.search(r'(?:总?客运量)\s*(\d+\.?\d*)', text)
        if total_match:
            total = float(total_match.group(1))
        else:
            # 没有明确总客流字段，则用线路客流之和
            total = sum(passenger_data.values())

        passenger_data['total_passengers'] = round(total, 1)

        print(f"解析成功: {date_str} 总客流量 {total:.1f} 万，线路数 {len(passenger_data)-1}")

        records.append({
            "date": date_str,
            "passenger_data": passenger_data,
            "raw_text": text[:100]
        })

    return records


# 使用示例（保留原调用方式）
if __name__ == "__main__":
    with open('docs/data/page.html', 'r', encoding='utf-8') as f:
        html = f.read()
    data = extract_passenger_data(html)
