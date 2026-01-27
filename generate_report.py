#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime, timedelta
import pandas as pd

def generate_html_report():
    """生成HTML报告"""
    
    # 初始化变量
    df = pd.DataFrame()
    latest_date = "N/A"
    latest_total = "N/A"
    avg_total = 0
    max_total = 0
    min_total = 0
    day_change_pct = 0
    day_change_amount = 0
    week_change_pct = 0
    week_change_amount = 0
    
    # 尝试从多个位置读取数据
    possible_files = [
        'docs/data/最近客流数据.csv',
        '最近客流数据.csv',
        'docs/data/latest_data.json'
    ]
    
    # 首先尝试读取CSV数据
    for file_path in possible_files:
        if os.path.exists(file_path):
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path, encoding='utf-8')
                    if not df.empty:
                        # 提取最新日期和总客流量
                        if 'date' in df.columns and 'total' in df.columns:
                            latest_date = df['date'].iloc[0]
                            latest_total = df['total'].iloc[0]
                            print(f"✅ 从 {file_path} 读取到数据")
                            break
                elif file_path.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    latest_date = json_data.get('latest_date', 'N/A')
                    latest_total = json_data.get('latest_total', 'N/A')
                    print(f"✅ 从 {file_path} 读取到JSON数据")
                    break
            except Exception as e:
                print(f"⚠️ 读取 {file_path} 时出错: {e}")
                continue
    
    # 计算统计信息（如果有数据）
    if not df.empty and 'total' in df.columns:
        avg_total = df['total'].mean()
        max_total = df['total'].max()
        min_total = df['total'].min()
        
        # 计算日环比（与昨日相比）
        if len(df) > 1:
            day_change_amount = df['total'].iloc[0] - df['total'].iloc[1]
            day_change_pct = (day_change_amount / df['total'].iloc[1] * 100) if df['total'].iloc[1] != 0 else 0
        
        # 计算周同比（与上周同一天相比，假设数据是连续的）
        if len(df) > 7:
            week_change_amount = df['total'].iloc[0] - df['total'].iloc[7]
            week_change_pct = (week_change_amount / df['total'].iloc[7] * 100) if df['total'].iloc[7] != 0 else 0
        
        # 重命名列名为中文
        df = df.rename(columns={
            'date': '日期',
            'total': '总客流量(万)'
        })
    else:
        # 如果没有CSV数据，尝试从日志文件中提取
        log_file = 'metro_analysis.log'
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # 查找最新数据
                    for line in reversed(lines[-20:]):  # 检查最后20行
                        if '总客流量:' in line:
                            parts = line.split('总客流量:')
                            if len(parts) > 1:
                                total_str = parts[1].strip().split(' ')[0].replace('万', '')
                                try:
                                    latest_total = float(total_str)
                                    print(f"✅ 从日志文件提取到总客流量: {latest_total}")
                                except:
                                    pass
                        if '最新数据日期:' in line:
                            parts = line.split('最新数据日期:')
                            if len(parts) > 1:
                                latest_date = parts[1].strip()
            except Exception as e:
                print(f"⚠️ 读取日志文件时出错: {e}")
    
    # 读取config.json数据
    with open("config.json", 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        lines = config_data["lines"]
        quantity = len(lines)
        
        # 计算总站点数
        total_stations = sum(line.get("stations", 0) for line in lines)
    
    # 计算站点客流强度
    station_intensity = 0
    if latest_total != "N/A" and total_stations > 0:
        # 将万转换为实际人数，然后除以站点数
        station_intensity = (latest_total * 10000) / total_stations
        # 格式化为整数
        station_intensity = int(station_intensity)
    
    # 确定日环比和周同比的颜色
    def get_change_color(value):
        if value > 0:
            return "red"  # 上涨用红色
        elif value < 0:
            return "green"  # 下降用绿色
        else:
            return "black"  # 持平用黑色
    
    day_color = get_change_color(day_change_pct)
    week_color = get_change_color(week_change_pct)
    
    # 格式化百分比显示，添加+/-符号
    def format_change_pct(value):
        if value > 0:
            return f"+{value:.3f}%"
        elif value < 0:
            return f"{value:.3f}%"
        else:
            return f"{value:.3f}%"
    
    # 格式化增减量显示，添加+/-符号和单位
    def format_change_amount(value):
        if value > 0:
            return f"(+{abs(value):.1f}万)"
        elif value < 0:
            return f"(-{abs(value):.1f}万)"
        else:
            return f"({abs(value):.1f}万)"
    
    # 组合百分比和增减量
    def format_change_with_amount(pct_value, amount_value):
        return f"{format_change_pct(pct_value)} {format_change_amount(amount_value)}"
    
    # HTML模板
    html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>南京地铁客流分析 - {datetime.now().strftime('%Y年%m月%d日')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eaeaea;
        }}
        
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        
        .update-time {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            min-width: 340px;
        }}
        
        .stat-card.green {{
            background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%);
        }}
        
        .stat-card.orange {{
            background: linear-gradient(135deg, #fde68a 0%, #f97316 100%);
        }}

        .stat-card.dark-blue {{
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
        }}
        
        .stat-card.green-purple {{
            background: linear-gradient(135deg, #10b981 0%, #8b5cf6 100%);
        }}
        
        .stat-card.purple {{
            background: linear-gradient(135deg, #d8b4fe 0%, #a855f7 100%);
        }}
        
        .stat-card.red {{
            background: linear-gradient(135deg, #fdba74 0%, #ef4444 100%);
        }}
        
        .stat-card.black {{
            background: linear-gradient(135deg, #d1d5db 0%, #6b7280 100%);
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .change-detail {{
            font-size: 0.8em;
            opacity: 0.9;
            margin-top: 5px;
        }}
        
        /* 修改图片网格为单列布局 */
        .images-grid {{
            display: flex;
            flex-direction: column;
            gap: 30px;
            margin-bottom: 40px;
        }}
        
        .image-card {{
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            transition: transform 0.3s ease;
            width: 100%; /* 确保卡片宽度为100% */
        }}
        
        .image-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }}
        
        .image-card img {{
            width: 100%; /* 图片宽度100%填充卡片 */
            height: auto; /* 高度自适应，保持图片原始比例 */
            display: block; /* 防止图片下方有空白 */
            object-fit: contain; /* 保持图片完整显示，不裁剪 */
        }}
        
        .image-card .caption {{
            padding: 15px;
            text-align: center;
            background: #f8f9fa;
        }}
        
        .table-container {{
            overflow-x: auto;
            margin-bottom: 30px;
            height: 320px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        
        tr:hover {{
            background-color: #f5f5f5;
        }}
        
        .line-legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .line-item {{
            display: flex;
            align-items: center;
            margin-right: 15px;
        }}
        
        .line-color {{
            width: 20px;
            height: 20px;
            margin-right: 8px;
            border-radius: 4px;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eaeaea;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        /* 移动端适配 - 调整列数显示 */
        @media (max-width: 1400px) {{
            .stats-grid {{
                grid-template-columns: repeat(3, 1fr);
            }}
        }}
        
        @media (max-width: 1100px) {{
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            .stat-card {{
                min-width: auto;
            }}
            
            .container {{
                padding: 15px;
            }}
            
            h1 {{
                font-size: 2em;
            }}
            
            .stat-value {{
                font-size: 2em;
            }}
        }}
        
        /* 强制横屏时也保持单列 */
        @media (orientation: landscape) {{
            .images-grid {{
                flex-direction: column; /* 确保横屏时也是单列 */
            }}
        }}
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>🚇 南京地铁客流每日分析</h1>
            <p class="update-time">更新时间（北京时间）: {(datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p class="update-time">最新数据日期: {latest_date}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label"><i class="fas fa-users"></i> 最新日客流</div>
                <div class="stat-value">{latest_total if latest_total != 'N/A' else 'N/A'}{'' if latest_total == 'N/A' else '万'}</div>
                <div class="stat-label">万人次</div>
            </div>
            
            <div class="stat-card green-purple">
                <div class="stat-label"><i class="fas fa-chart-area"></i> 昨日站点客流强度</div>
                <div class="stat-value">{station_intensity if station_intensity > 0 else 'N/A'}{'' if station_intensity == 0 else '人/站'}</div>
                <div class="stat-label">站点客流强度=总客流量÷总站点数</div>
            </div>
            
            <div class="stat-card orange">
                <div class="stat-label"><i class="fas fa-chart-line"></i> 7日平均</div>
                <div class="stat-value">{avg_total:.2f}万</div>
                <div class="stat-label">万人次</div>
            </div>
            
            <div class="stat-card {day_color}">
                <div class="stat-label"><i class="fas fa-exchange-alt"></i> 日环比</div>
                <div class="stat-value">{format_change_with_amount(day_change_pct, day_change_amount)}</div>
                <div class="stat-label">与昨日相比</div>
            </div>
            
            <div class="stat-card {week_color}">
                <div class="stat-label"><i class="fas fa-calendar-week"></i> 周同比</div>
                <div class="stat-value">{format_change_with_amount(week_change_pct, week_change_amount)}</div>
                <div class="stat-label">与上周同期相比</div>
            </div>
            
            <div class="stat-card dark-blue">
                <div class="stat-label"><i class="fas fa-subway"></i> 运营线路</div>
                <div class="stat-value">{quantity}条 ({total_stations}站)</div>
                <div class="stat-label">市区线+郊区线</div>
            </div>
        </div>
        
        <h2><i class="fas fa-chart-bar"></i> 可视化图表</h2>
        <div class="images-grid">
            <div class="image-card">
                <img src="images/昨日客流线路占比图.png" alt="昨日客流线路占比图" style="width:100%; height:auto;">
                <div class="caption">
                    <h3>昨日客流线路占比</h3>
                </div>
            </div>
            
            <div class="image-card">
                <img src="images/最近60天总客流量变化趋势图.png" alt="总客流量变化趋势图" style="width:100%; height:auto;">
                <div class="caption">
                    <h3>总客流量变化趋势</h3>
                </div>
            </div>
            
            <div class="image-card">
                <img src="images/最近30天站点客流强度变化趋势图.png" alt="站点客流强度变化趋势图" style="width:100%; height:auto;">
                <div class="caption">
                    <h3>站点客流强度变化趋势</h3>
                </div>
            </div>
            
            <div class="image-card">
                <img src="images/最近30天线路客流量占比变化趋势图.png" alt="线路客流量占比变化趋势图" style="width:100%; height:auto;">
                <div class="caption">
                    <h3>线路客流量占比变化趋势</h3>
                </div>
            </div>
        </div>
        
        <h2><i class="fas fa-table"></i> 最近30天数据</h2>
        <div class="table-container">
            {df.to_html(index=False, classes='data-table') if len(df) > 0 else '<p>暂无数据</p>'}
        </div>
        
        <div class="footer">
            <p>Copyright © 2025-{datetime.now().year} 南京地铁客流分析系统 | 自动生成</p>
            <p>数据仅供参考，具体以官方发布为准。</p>
        </div>
    </div>
</body>
</html>
"""
    
    # 保存HTML文件
    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("HTML报告已生成")

if __name__ == "__main__":
    generate_html_report()
