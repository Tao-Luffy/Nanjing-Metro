import json
import re
from typing import Dict, List, Optional

import pandas as pd

from analysis_html import extract_passenger_data


class NanjingSubwayDataCollector:
    """Nanjing Metro Data Collector"""

    def __init__(self, config_file: str = "config.json"):
        self.passenger_records = []
        self.line_data = {}
        self.config = self.load_config(config_file)
        self.all_lines = [line["name"] for line in self.config["lines"]]
        self.line_info = {line["name"]: line for line in self.config["lines"]}

    def collect_data(self):
        with open('page.html', 'r', encoding='utf-8') as f:
            html = f.read()
        html_source = extract_passenger_data(html)
        passenger_records = html_source
        self.passenger_records = passenger_records
        return passenger_records

    def load_config(self, config_file: str) -> Dict:
        """Load configuration file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Configuration file {config_file} not found")
        except json.JSONDecodeError as e:
            print(f"Configuration file parsing error: {e}")

    def extract_passenger_data(self, text: str) -> Optional[Dict[str, float]]:
        """
        Extract passenger data from text

        Args:
            text: Text containing passenger flow data

        Returns:
            Optional[Dict[str, float]]: Dictionary mapping line to passenger volume, None if extraction fails
        """
        # Dynamically generate line regex patterns
        line_patterns = {}
        for line in self.all_lines:
            # Handle numbers and letters in line names
            line_name_clean = line.replace("Line", "")
            pattern = rf'{line.replace("Line", "Line")}\s*(\d+(?:\.\d+)?)'
            line_patterns[line] = pattern

        passenger_data = {}

        for line_name, pattern in line_patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    passenger_data[line_name] = float(match.group(1))
                except ValueError:
                    # If conversion fails, try to find "suspended" keyword
                    if "suspended" in text or f"{line_name} suspended" in text:
                        passenger_data[line_name] = 0.0
                    else:
                        passenger_data[line_name] = None
            else:
                # Check for suspended service case
                if f"{line_name} suspended" in text:
                    passenger_data[line_name] = 0.0
                else:
                    passenger_data[line_name] = None

        # Extract total passenger volume (if available)
        total_pattern = r'Passenger Volume\s*(\d+(?:\.\d+)?)'
        total_match = re.search(total_pattern, text)
        if total_match:
            try:
                passenger_data["total_passengers"] = float(total_match.group(1))
            except ValueError:
                passenger_data["total_passengers"] = None

        return passenger_data if passenger_data else None

    def extract_date(self, text: str) -> Optional[str]:
        """
        Extract date from text

        Args:
            text: Text containing date

        Returns:
            Optional[str]: Date string in "MM-DD" format, None if extraction fails
        """
        # Match "Month Day" format (Chinese or English)
        date_pattern = r'(\d{1,2})\s*[Month]\s*(\d{1,2})\s*[Day]'
        # Alternative pattern for numeric dates like MM/DD or MM-DD
        alt_pattern = r'(\d{1,2})[/-](\d{1,2})'
        match = re.search(date_pattern, text) or re.search(alt_pattern, text)

        if match:
            month = match.group(1).zfill(2)
            day = match.group(2).zfill(2)
            return f"{month}-{day}"

        return None

    def _organize_by_line(self):
        """Organize data by line"""
        for line in self.all_lines:
            self.line_data[line] = []
            for record in self.passenger_records:
                value = record['passenger_data'].get(line)
                self.line_data[line].append({
                    "date": record['date'],
                    "passenger_count": value,
                    "total": record['passenger_data'].get('total_passengers')
                })

    def get_line_colors(self) -> Dict[str, str]:
        """Get color configuration for all lines"""
        colors = {}
        for line in self.line_info.values():
            colors[line["name"]] = line.get("color", "#CCCCCC")
        return colors

    def get_line_info(self, line_name: str) -> Dict:
        """Get detailed information for a specific line"""
        return self.line_info.get(line_name, {})

    def get_latest_date(self) -> str:
        """Get the latest date"""
        if not self.passenger_records:
            return ""
        return self.passenger_records[0]['date']

    def get_latest_data(self) -> Dict:
        """Get data for the most recent day"""
        if not self.passenger_records:
            return {}
        return self.passenger_records[0]

    def get_last_n_days(self, n: int = None) -> List[Dict]:
        """Get data for the last n days"""
        if not self.passenger_records:
            return []
        if n is None:
            n = self.config["visualization"].get("default_days", 7)
        return self.passenger_records[:min(n, len(self.passenger_records))]

    def get_line_last_n_days(self, line_name: str, n: int = None) -> List[Dict]:
        """Get data for a specific line for the last n days"""
        if line_name not in self.line_data:
            return []
        if n is None:
            n = self.config["visualization"].get("default_days", 7)
        return self.line_data[line_name][:min(n, len(self.line_data[line_name]))]

    def get_latest_line_proportions(self) -> Dict[str, float]:
        """Get proportion of each line for the latest day"""
        latest_data = self.get_latest_data()
        if not latest_data:
            return {}

        passenger_data = latest_data['passenger_data']
        total = passenger_data.get('total_passengers')
        if not total:
            return {}

        proportions = {}
        for line in self.all_lines:
            count = passenger_data.get(line)
            if count is not None:
                proportions[line] = (count / total) * 100

        return proportions

    def get_last_n_days_line_data(self, n: int = None) -> pd.DataFrame:
        """Get line data for the last n days in DataFrame format"""
        if n is None:
            n = 30
        last_n_days = self.get_last_n_days(n)

        data = []
        for record in last_n_days:
            row = {'date': record['date'], 'total': record['passenger_data'].get('total_passengers')}
            for line in self.all_lines:
                row[line] = record['passenger_data'].get(line)
            data.append(row)

        df = pd.DataFrame(data)

        # 类型转换：确保 date 为 datetime，数值列为 float
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        numeric_cols = ['total'] + self.all_lines
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def get_last_n_days_proportions(self, n: int = None) -> pd.DataFrame:
        """Get proportion of each line for the last n days in DataFrame format"""
        if n is None:
            n = self.config["visualization"].get("default_days", 7)
        df = self.get_last_n_days_line_data(n)

        # Calculate proportion for each line
        for line in self.all_lines:
            if line in df.columns:
                df[f'{line}_proportion'] = df[line] / df['total'] * 100

        return df
