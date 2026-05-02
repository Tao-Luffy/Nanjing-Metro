#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, timedelta

import pandas as pd


def generate_html_report():
    """Generate HTML report"""

    # Initialize variables
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

    # Try to read data from multiple locations
    possible_files = [
        'docs/data/recent_passenger_data.csv',
        'recent_passenger_data.csv',
        'docs/data/latest_data.json'
    ]

    # First try to read CSV data
    for file_path in possible_files:
        if os.path.exists(file_path):
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path, encoding='utf-8')
                    if not df.empty:
                        # Ensure 'total' column is numeric, coercing errors to NaN and then fill with 0
                        if 'total' in df.columns:
                            df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0)
                        else:
                            print(f"Warning: 'total' column not found in {file_path}")
                            continue

                        # Extract latest date and total passengers
                        if 'date' in df.columns and 'total' in df.columns:
                            latest_date = df['date'].iloc[0]
                            latest_total = df['total'].iloc[0]
                            print(f"Data loaded from {file_path}")
                            break
                elif file_path.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    latest_date = json_data.get('latest_date', 'N/A')
                    latest_total = json_data.get('latest_total', 'N/A')
                    print(f"JSON data loaded from {file_path}")
                    break
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue

    # Calculate statistics if data exists
    if not df.empty and 'total' in df.columns:
        avg_total = df['total'].mean()
        max_total = df['total'].max()
        min_total = df['total'].min()

        # Calculate day-over-day change
        if len(df) > 1:
            day_change_amount = df['total'].iloc[0] - df['total'].iloc[1]
            day_change_pct = (day_change_amount / df['total'].iloc[1] * 100) if df['total'].iloc[1] != 0 else 0

        # Calculate week-over-week change (assuming consecutive data)
        if len(df) > 7:
            week_change_amount = df['total'].iloc[0] - df['total'].iloc[7]
            week_change_pct = (week_change_amount / df['total'].iloc[7] * 100) if df['total'].iloc[7] != 0 else 0

        # Rename columns to English
        df = df.rename(columns={
            'date': 'Date',
            'total': 'Total Passengers (10k)'
        })
    else:
        # If no CSV data, try to extract from log file
        log_file = 'metro_analysis.log'
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Find latest data
                    for line in reversed(lines[-20:]):  # Check last 20 lines
                        if 'Total passengers:' in line:
                            parts = line.split('Total passengers:')
                            if len(parts) > 1:
                                total_str = parts[1].strip().split(' ')[0].replace('ten thousand', '')
                                try:
                                    latest_total = float(total_str)
                                    print(f"Total passengers extracted from log: {latest_total}")
                                except:
                                    pass
                        if 'Latest data:' in line:
                            parts = line.split('Latest data:')
                            if len(parts) > 1:
                                latest_date = parts[1].strip()
            except Exception as e:
                print(f"Error reading log file: {e}")

    # Read config.json data
    with open("config.json", 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        lines = config_data["lines"]
        quantity = len(lines)

        # Calculate total number of stations
        total_stations = sum(line.get("stations", 0) for line in lines)

    # Calculate station passenger intensity safely
    station_intensity = 0
    if latest_total != "N/A" and total_stations > 0:
        try:
            # Ensure latest_total is a valid number
            latest_total_num = float(latest_total)
            station_intensity = (latest_total_num * 10000) / total_stations
            if pd.isna(station_intensity):
                station_intensity = 0
            else:
                station_intensity = int(station_intensity)
        except (ValueError, TypeError):
            station_intensity = 0

    # Determine color for day-over-day and week-over-week changes
    def get_change_color(value):
        if value > 0:
            return "red"  # Increase - red
        elif value < 0:
            return "green"  # Decrease - green
        else:
            return "black"  # No change - black

    day_color = get_change_color(day_change_pct)
    week_color = get_change_color(week_change_pct)

    # Format percentage display with +/- sign
    def format_change_pct(value):
        if value > 0:
            return f"+{value:.3f}%"
        elif value < 0:
            return f"{value:.3f}%"
        else:
            return f"{value:.3f}%"

    # Format change amount with +/- sign and unit
    def format_change_amount(value):
        if value > 0:
            return f"+{abs(value):.1f} ten thousand"
        elif value < 0:
            return f"-{abs(value):.1f} ten thousand"
        else:
            return f"{abs(value):.1f} ten thousand"

    # Combine percentage and amount with line break
    def format_change_with_amount(pct_value, amount_value):
        return f"{format_change_pct(pct_value)}<br>{format_change_amount(amount_value)}"

    # Format line information display with line break
    def format_line_info(line_count, station_count):
        return f"{line_count} lines<br>{station_count} stations"

    # HTML template
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nanjing Metro Passenger Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
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

        /* Allow line breaks for change and line cards */
        .change-card .stat-value,
        .line-card .stat-value {{
            white-space: normal;
            line-height: 1.3;
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

        /* Single column layout for images */
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
            width: 100%;
        }}

        .image-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }}

        .image-card img {{
            width: 100%;
            height: auto;
            display: block;
            object-fit: contain;
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

        /* Mobile responsive adjustments */
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

            .change-card .stat-value,
            .line-card .stat-value {{
                font-size: 1.8em;
            }}
        }}

        /* Keep single column in landscape as well */
        @media (orientation: landscape) {{
            .images-grid {{
                flex-direction: column;
            }}
        }}
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Nanjing Metro Daily Passenger Analysis</h1>
            <p class="update-time">Update Time (Beijing Time): {(datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p class="update-time">Latest Data Date: {latest_date}</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Latest Daily Passengers</div>
                <div class="stat-value">{latest_total if latest_total != 'N/A' else 'N/A'}{'' if latest_total == 'N/A' else ' ten thousand'}</div>
                <div class="stat-label">passengers</div>
            </div>

            <div class="stat-card green-purple">
                <div class="stat-label">Yesterday Station Intensity</div>
                <div class="stat-value">{station_intensity if station_intensity > 0 else 'N/A'}{'' if station_intensity == 0 else ' pax/station'}</div>
                <div class="stat-label">Station Intensity = Total Passengers / Total Stations</div>
            </div>

            <div class="stat-card orange">
                <div class="stat-label">7-Day Average</div>
                <div class="stat-value">{avg_total:.2f} ten thousand</div>
                <div class="stat-label">passengers</div>
            </div>

            <div class="stat-card {day_color} change-card">
                <div class="stat-label">Day-over-Day</div>
                <div class="stat-value">{format_change_with_amount(day_change_pct, day_change_amount)}</div>
                <div class="stat-label">Compared to yesterday</div>
            </div>

            <div class="stat-card {week_color} change-card">
                <div class="stat-label">Week-over-Week</div>
                <div class="stat-value">{format_change_with_amount(week_change_pct, week_change_amount)}</div>
                <div class="stat-label">Compared to same day last week</div>
            </div>

            <div class="stat-card dark-blue line-card">
                <div class="stat-label">Operating Lines</div>
                <div class="stat-value">{format_line_info(quantity, total_stations)}</div>
                <div class="stat-label">Urban + Suburban lines</div>
            </div>
        </div>

        <h2>Visualization Charts</h2>
        <div class="images-grid">
            <div class="image-card">
                <img src="images/yesterday_passenger_line_proportion.png" alt="Yesterday Line Proportion Chart" style="width:100%; height:auto;">
                <div class="caption">
                    <h3>Yesterday Line Passenger Proportion</h3>
                </div>
            </div>

            <div class="image-card">
                <img src="images/last_60_days_total_passenger_trend.png" alt="Total Passenger Trend Chart" style="width:100%; height:auto;">
                <div class="caption">
                    <h3>Total Passenger Trend</h3>
                </div>
            </div>

            <div class="image-card">
                <img src="images/last_30_days_station_intensity_trend.png" alt="Station Intensity Trend Chart" style="width:100%; height:auto;">
                <div class="caption">
                    <h3>Station Intensity Trend</h3>
                </div>
            </div>

            <div class="image-card">
                <img src="images/last_30_days_line_proportion_trend.png" alt="Line Proportion Trend Chart" style="width:100%; height:auto;">
                <div class="caption">
                    <h3>Line Passenger Proportion Trend</h3>
                </div>
            </div>
        </div>

        <h2>Last 30 Days Data</h2>
        <div class="table-container">
            {df.to_html(index=False, classes='data-table') if len(df) > 0 else '<p>No data available</p>'}
        </div>

        <div class="footer">
            <p>Copyright &copy; 2025-{datetime.now().year} Nanjing Metro Passenger Analysis System | Auto-generated</p>
            <p>Data for reference only. Please refer to official announcements for accuracy.</p>
        </div>
    </div>
</body>
</html>
"""

    # Save HTML file
    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)

    print("HTML report generated")


if __name__ == "__main__":
    generate_html_report()
