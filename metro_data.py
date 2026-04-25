import requests
import re
import json
import os
from typing import Dict, List, Optional
import pandas as pd


class NanjingSubwayDataCollector:
    """Nanjing Metro Data Collector"""

    def __init__(self, config_file: str = "config.json", cookie_file: str = "weibo_cookies.txt"):
        self.cookie_file = cookie_file
        self.cookie = None
        self.driver = None
        self.passenger_records = []
        self.line_data = {}
        self.config = self.load_config(config_file)
        self.all_lines = [line["name"] for line in self.config["lines"]]
        self.line_info = {line["name"]: line for line in self.config["lines"]}
        # Initialize Cookie
        self._init_cookie()

    def _init_cookie(self):
        """Initialize Cookie"""
        print("\n" + "=" * 60)
        print("   Cookie Management")
        print("=" * 60 + "\n")

        # Attempt to load local Cookie
        self.cookie = self._load_cookie_from_file()
        # return cookie

    def _load_cookie_from_file(self) -> Optional[str]:
        """Load Cookie from file"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"Failed to read Cookie file: {e}")
        return None

    def load_config(self, config_file: str) -> Dict:
        """Load configuration file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Configuration file {config_file} not found")
        except json.JSONDecodeError as e:
            print(f"Configuration file parsing error: {e}")

    def search_weibo(self, page: int) -> dict:
        """
        Search Weibo data

        Args:
            page: Page number

        Returns:
            dict: Returned JSON data
        """
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": self.cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://weibo.com/u/2638276292"
        }

        params = {
            "uid": self.config["data_source"]["weibo_user_id"],
            "page": page,
            "q": self.config["data_source"]["search_keyword"]
        }

        url = "https://weibo.com/ajax/statuses/searchProfile?"

        return requests.get(url, headers=headers, params=params).json()

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

    def collect_data(self) -> List[Dict]:
        """
        Collect Nanjing Metro passenger data

        Returns:
            List[Dict]: List of dictionaries containing date and passenger data
        """
        passenger_records = []
        max_pages = self.config["data_source"].get("max_pages", 10)
        error_notified = False

        for page in range(1, max_pages):
            try:
                response = self.search_weibo(page)

                if 'data' in response and 'list' in response['data']:
                    for item in response['data']['list']:
                        text = item.get('text_raw', '')

                        # Skip non-passenger-flow related content
                        if 'passenger' not in text or 'Nanjing Metro' not in text:
                            continue

                        # Extract date
                        date_str = self.extract_date(text)

                        # Extract passenger data
                        passenger_data = self.extract_passenger_data(text)

                        if date_str and passenger_data:
                            record = {
                                "date": date_str,
                                "passenger_data": passenger_data,
                                "raw_text": text[:100]
                            }
                            passenger_records.append(record)

                print(f"Processed page {page}")

            except Exception as e:
                print(f"Error processing page {page}: {e}")
                print(f"Error: {e}")
                if not error_notified:
                    error_notified = True
                    # try:
                    #     get_cookie.main()
                    # except:
                    #     print('Cookie auto-update failed')
                continue


        self.passenger_records = passenger_records
        self._organize_by_line()
        return passenger_records

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
