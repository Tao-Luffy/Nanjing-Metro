import requests
import re
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd


class NanjingSubwayDataCollector:
    """南京地铁数据收集器"""
    
    def __init__(self, config_file: str = "config.json",  cookie_file: str = "weibo_cookies.txt"):
        self.cookie_file = cookie_file
        self.cookie = None
        self.driver = None
        self.passenger_records = []
        self.line_data = {}
        self.config = self.load_config(config_file)
        self.all_lines = [line["name"] for line in self.config["lines"]]
        self.line_info = {line["name"]: line for line in self.config["lines"]}
        # 初始化 Cookie
        self._init_cookie()

    def _init_cookie(self):
        """初始化 Cookie"""
        print("\n" + "=" * 60)
        print("   Cookie 管理")
        print("=" * 60 + "\n")

        # 尝试加载本地 Cookie
        self.cookie = self._load_cookie_from_file()
        # return cookie

    def _load_cookie_from_file(self) -> Optional[str]:
        """从文件加载 Cookie"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"读取 Cookie 文件失败: {e}")
        return None


    def search_weibo(self, page: int) -> dict:
        """
        搜索微博数据
        
        Args:
            page: 页码
            
        Returns:
            dict: 返回的JSON数据
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
        从文本中提取客流数据
        
        Args:
            text: 包含客流数据的文本
            
        Returns:
            Optional[Dict[str, float]]: 线路到客流量的字典，如果提取失败返回None
        """
        # 动态生成线路正则表达式模式
        line_patterns = {}
        for line in self.all_lines:
            # 处理线路名称中的数字和字母
            line_name_clean = line.replace("号线", "")
            pattern = rf'{line.replace("号线", "号线")}\s*(\d+(?:\.\d+)?)'
            line_patterns[line] = pattern
        
        passenger_data = {}
        
        for line_name, pattern in line_patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    passenger_data[line_name] = float(match.group(1))
                except ValueError:
                    # 如果转换失败，尝试查找"停运"关键字
                    if "停运" in text or f"{line_name}停运" in text:
                        passenger_data[line_name] = 0.0
                    else:
                        passenger_data[line_name] = None
            else:
                # 检查是否有停运的情况
                if f"{line_name}停运" in text:
                    passenger_data[line_name] = 0.0
                else:
                    passenger_data[line_name] = None
        
        # 提取总客流量（如果有）
        total_pattern = r'客运量\s*(\d+(?:\.\d+)?)'
        total_match = re.search(total_pattern, text)
        if total_match:
            try:
                passenger_data["总客流量"] = float(total_match.group(1))
            except ValueError:
                passenger_data["总客流量"] = None
        
        return passenger_data if passenger_data else None
    
    def extract_date(self, text: str) -> Optional[str]:
        """
        从文本中提取日期
        
        Args:
            text: 包含日期的文本
            
        Returns:
            Optional[str]: 格式为"MM-DD"的日期字符串，如果提取失败返回None
        """
        # 匹配"X月X日"的格式
        date_pattern = r'(\d{1,2})月(\d{1,2})日'
        match = re.search(date_pattern, text)
        
        if match:
            month = match.group(1).zfill(2)
            day = match.group(2).zfill(2)
            return f"{month}-{day}"
        
        return None
    
    def collect_data(self) -> List[Dict]:
        """
        收集南京地铁客流数据
        
        Returns:
            List[Dict]: 包含日期和客流数据的字典列表
        """
        passenger_records = []
        max_pages = self.config["data_source"].get("max_pages", 10)
        
        for page in range(1, max_pages):
            try:
                response = self.search_weibo(page)
                
                if 'data' in response and 'list' in response['data']:
                    for item in response['data']['list']:
                        text = item.get('text_raw', '')
                        
                        # 跳过非客流相关的内容
                        if '客流' not in text or '南京地铁' not in text:
                            continue
                        
                        # 提取日期
                        date_str = self.extract_date(text)
                        
                        # 提取客流数据
                        passenger_data = self.extract_passenger_data(text)
                        
                        if date_str and passenger_data:
                            record = {
                                "date": date_str,
                                "passenger_data": passenger_data,
                                "raw_text": text[:100]
                            }
                            passenger_records.append(record)
                            
                print(f"已处理第 {page} 页数据")
                
            except Exception as e:
                print(f"处理第 {page} 页数据时出错: {e}")
                continue
        
        self.passenger_records = passenger_records
        self._organize_by_line()
        return passenger_records
    
    def _organize_by_line(self):
        """按线路整理数据"""
        for line in self.all_lines:
            self.line_data[line] = []
            for record in self.passenger_records:
                value = record['passenger_data'].get(line)
                self.line_data[line].append({
                    "date": record['date'],
                    "passenger_count": value,
                    "total": record['passenger_data'].get('总客流量')
                })
    
    def get_line_colors(self) -> Dict[str, str]:
        """获取所有线路的颜色配置"""
        colors = {}
        for line in self.line_info.values():
            colors[line["name"]] = line.get("color", "#CCCCCC")
        return colors
    
    def get_line_info(self, line_name: str) -> Dict:
        """获取指定线路的详细信息"""
        return self.line_info.get(line_name, {})
    
    def get_latest_date(self) -> str:
        """获取最新日期"""
        if not self.passenger_records:
            return ""
        return self.passenger_records[0]['date']
    
    def get_latest_data(self) -> Dict:
        """获取最新一天的数据"""
        if not self.passenger_records:
            return {}
        return self.passenger_records[0]
    
    def get_last_n_days(self, n: int = None) -> List[Dict]:
        """获取最近n天的数据"""
        if not self.passenger_records:
            return []
        if n is None:
            n = self.config["visualization"].get("default_days", 7)
        return self.passenger_records[:min(n, len(self.passenger_records))]
    
    def get_line_last_n_days(self, line_name: str, n: int = None) -> List[Dict]:
        """获取指定线路最近n天的数据"""
        if line_name not in self.line_data:
            return []
        if n is None:
            n = self.config["visualization"].get("default_days", 7)
        return self.line_data[line_name][:min(n, len(self.line_data[line_name]))]
    
    def get_latest_line_proportions(self) -> Dict[str, float]:
        """获取最新一天各线路占比"""
        latest_data = self.get_latest_data()
        if not latest_data:
            return {}
        
        passenger_data = latest_data['passenger_data']
        total = passenger_data.get('总客流量')
        if not total:
            return {}
        
        proportions = {}
        for line in self.all_lines:
            count = passenger_data.get(line)
            if count is not None:
                proportions[line] = (count / total) * 100
        
        return proportions
    
    def get_last_n_days_line_data(self, n: int = None) -> pd.DataFrame:
        """获取最近n天各线路数据（DataFrame格式）"""
        if n is None:
            n = 30
        last_n_days = self.get_last_n_days(n)
        
        data = []
        for record in last_n_days:
            row = {'date': record['date'], 'total': record['passenger_data'].get('总客流量')}
            for line in self.all_lines:
                row[line] = record['passenger_data'].get(line)
            data.append(row)
        
        df = pd.DataFrame(data)
        return df
    
    def get_last_n_days_proportions(self, n: int = None) -> pd.DataFrame:
        """获取最近n天各线路占比（DataFrame格式）"""
        if n is None:
            n = self.config["visualization"].get("default_days", 7)
        df = self.get_last_n_days_line_data(n)
        
        # 计算每条线路的占比
        for line in self.all_lines:
            if line in df.columns:
                df[f'{line}_占比'] = df[line] / df['total'] * 100
        
        return df
