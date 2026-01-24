#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 首先配置字体
try:
    from setup_fonts import setup_chinese_fonts
    if setup_chinese_fonts():
        print("✓ 字体配置完成")
    else:
        print("⚠ 字体配置可能有问题，继续运行...")
except Exception as e:
    print(f"⚠ 字体配置脚本出错: {e}")

# 然后导入其他库
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from metro_data import NanjingSubwayDataCollector
import pandas as pd
import logging
from datetime import datetime
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('metro_analysis.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 确保中文字体设置
def ensure_chinese_font():
    """确保中文字体设置正确"""
    try:
        current_fonts = plt.rcParams.get('font.sans-serif', [])
        
        if not current_fonts:
            font_candidates = [
                'WenQuanYi Zen Hei',
                'DejaVu Sans',
                'Liberation Sans',
                'Arial Unicode MS',
                'sans-serif'
            ]
            
            available_fonts = []
            all_fonts = [f.name for f in fm.fontManager.ttflist]
            for font in font_candidates:
                if font in all_fonts:
                    available_fonts.append(font)
            
            if available_fonts:
                plt.rcParams['font.sans-serif'] = available_fonts
                plt.rcParams['axes.unicode_minus'] = False
            else:
                plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
                
    except Exception as e:
        logger.error(f"确保字体设置时出错: {e}")

ensure_chinese_font()

# 设置图表样式
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['figure.figsize'] = (14, 8)

class NanjingSubwayVisualizer:
    """南京地铁数据可视化器"""
    
    def __init__(self, data_collector):
        self.data_collector = data_collector
        self.line_colors = self._get_line_colors()
        
    def _get_line_colors(self):
        """获取线路颜色"""
        colors = {}
        line_colors_config = self.data_collector.get_line_colors()
        
        if line_colors_config:
            return line_colors_config
        
        all_lines = self.data_collector.all_lines
        n_lines = len(all_lines)
        
        cmap = plt.cm.Set3
        for i, line in enumerate(all_lines):
            colors[line] = cmap(i / max(1, n_lines - 1))
        
        return colors
    
    def _ensure_font(self):
        """确保字体设置正确"""
        try:
            if not plt.rcParams['font.sans-serif']:
                plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'DejaVu Sans', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
        except:
            pass

    def plot_compact_pie_chart(self):
        """占比饼图"""
        try:
            self._ensure_font()
            
            proportions = self.data_collector.get_latest_line_proportions()
            latest_date = self.data_collector.get_latest_date()
            
            latest_data = self.data_collector.get_latest_data()
            total_passenger = latest_data['passenger_data'].get('总客流量', 0)
            
            if not proportions:
                logger.warning("没有找到最新数据")
                return None
            
            sorted_items = sorted(proportions.items(), key=lambda x: x[1], reverse=True)
            
            lines = [item[0] for item in sorted_items]
            values = [item[1] for item in sorted_items]
            
            actual_passengers = []
            for value in values:
                actual = total_passenger * value / 100
                actual_passengers.append(actual)
            
            colors = [self.line_colors.get(line, '#CCCCCC') for line in lines]
            fig, ax = plt.subplots(figsize=(12, 10))
            
            wedges, texts = ax.pie(
                values,
                colors=colors,
                startangle=90,
                wedgeprops=dict(width=0.4, edgecolor='white'),
                labels=None
            )
            
            legend_labels = []
            for line, value, actual in zip(lines, values, actual_passengers):
                if line.startswith("其他"):
                    legend_labels.append(f"{line}: {value:.1f}%\n({actual:.1f}万)")
                else:
                    legend_labels.append(f"{line}: {value:.1f}%\n({actual:.1f}万)")
            
            ax.legend(wedges, legend_labels,
                     loc="center left",
                     bbox_to_anchor=(1, 0, 0.5, 1),
                     fontsize=20)
            
            center_text = f"{latest_date}\n总客流\n{total_passenger:.1f}万"
            ax.text(0, 0, center_text,
                   ha='center', va='center',
                   fontsize=28, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            ax.axis('equal')
            
            plt.tight_layout()
            
            os.makedirs('docs/images', exist_ok=True)
            fig.savefig('docs/images/昨日客流线路占比图.png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            logger.info("占比饼图已生成")
            return fig
            
        except Exception as e:
            logger.error(f"生成占比饼图时出错: {e}", exc_info=True)
            return None
    
    def plot_total_passenger_trend(self, n_days=60):
        """绘制总客流量变化趋势图"""
        try:
            self._ensure_font()
            
            # 获取原始数据（微博是倒序的，最新的在前）
            df = self.data_collector.get_last_n_days_line_data(n_days)
            
            if df.empty:
                logger.warning(f"没有找到最近{n_days}天的数据")
                return None
            
            # 微博数据是倒序的，我们需要反转数据以得到正确的时间顺序
            df = df.iloc[::-1].reset_index(drop=True)
            
            fig, ax = plt.subplots(figsize=(14, 8))
            
            if 'total' in df.columns:
                ax.plot(df['date'], df['total'], 
                       color='#1f77b4',
                       marker='o',
                       linewidth=2.5,
                       markersize=8)
            
            ax.set_xlabel('日期', fontsize=20, fontweight='bold')
            ax.set_ylabel('总客流量（万）', fontsize=20, fontweight='bold')
            
            ax.legend(['总客流量'], loc='lower right', fontsize=20, title=None)
            ax.grid(True, alpha=0.3, linestyle='--')
            
            plt.xticks(rotation=45, ha='right', fontsize=12)
            plt.yticks(fontsize=12)
            
            ax.set_ylim(bottom=0)
            
            plt.tight_layout()
            
            os.makedirs('docs/images', exist_ok=True)
            fig.savefig(f'docs/images/最近{n_days}天总客流量变化趋势图.png', 
                       dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            logger.info(f"最近{n_days}天总客流量变化趋势图已生成")
            
            return fig
            
        except Exception as e:
            logger.error(f"生成总客流量变化趋势图时出错: {e}", exc_info=True)
            return None
    
    def plot_last_n_days_line_trend(self, n_days=30):
        """绘制站点客流强度变化趋势图"""
        try:
            self._ensure_font()
            
            # 获取原始数据（微博是倒序的，最新的在前）
            df = self.data_collector.get_last_n_days_line_data(n_days)
            
            if df.empty:
                logger.warning(f"没有找到最近{n_days}天的数据")
                return None
            
            # 微博数据是倒序的，我们需要反转数据以得到正确的时间顺序
            df = df.iloc[::-1].reset_index(drop=True)
            
            line_info = self.data_collector.line_info
            
            # 增大图表高度，为底部图例留出空间
            fig, ax = plt.subplots(figsize=(14, 9))
            
            # 存储图例信息
            legend_handles = []
            legend_labels = []
            
            for line in self.data_collector.all_lines:
                if line in df.columns and df[line].notna().any():
                    color = self.line_colors.get(line, '#CCCCCC')
                    
                    stations = line_info.get(line, {}).get('stations', 1)
                    if stations == 0:
                        stations = 1
                    
                    station_intensity = df[line] / stations
                    
                    line_plot = ax.plot(df['date'], station_intensity, 
                                       color=color,
                                       marker='o',
                                       linewidth=2.5,
                                       markersize=8)
                    
                    # 保存图例句柄和标签
                    legend_handles.append(line_plot[0])
                    legend_labels.append(f'{line} ({stations}站)')
            
            ax.set_xlabel('日期', fontsize=20, fontweight='bold')
            ax.set_ylabel('站点客流强度（万/站）', fontsize=20, fontweight='bold')
            
            ax.grid(True, alpha=0.3, linestyle='--')
            
            plt.xticks(rotation=45, ha='right', fontsize=12)
            plt.yticks(fontsize=12)
            
            ax.set_ylim(bottom=0)

            # 将图例放在图表下方，横向排列
            # 调整图例位置：bbox_to_anchor=(0, -0.25, 1, 0.2) 表示：
            # 左对齐(0)，在图表下方(-0.25)，宽度占满(1)，高度为0.2
            ax.legend(legend_handles, legend_labels,
                     loc='upper center',
                     bbox_to_anchor=(0, -0.5, 1, 0.2),
                     ncol=min(6, len(legend_labels)),  # 最多6列，根据线路数量调整
                     mode="expand",
                     borderaxespad=0,
                     fontsize=14,
                     frameon=True,
                     fancybox=True,
                     shadow=True)
            
            # 调整布局，为底部图例留出更多空间
            plt.tight_layout(rect=[0, 0.2, 1, 0.95])  # 底部留出10%的空间
            
            os.makedirs('docs/images', exist_ok=True)
            fig.savefig(f'docs/images/最近{n_days}天站点客流强度变化趋势图.png', 
                       dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            logger.info(f"最近{n_days}天站点客流强度变化趋势图已生成")
            
            return fig
            
        except Exception as e:
            logger.error(f"生成站点客流强度趋势图时出错: {e}", exc_info=True)
            return None
    
    def plot_line_proportion_trend(self, n_days=30):
        """绘制线路客流量占比变化趋势图"""
        try:
            self._ensure_font()
            
            # 获取原始数据（微博是倒序的，最新的在前）
            df = self.data_collector.get_last_n_days_line_data(n_days)
            
            if df.empty:
                logger.warning(f"没有找到最近{n_days}天的数据")
                return None
            
            # 微博数据是倒序的，我们需要反转数据以得到正确的时间顺序
            df = df.iloc[::-1].reset_index(drop=True)
            
            # 获取所有线路列（排除'total'和'date'）
            line_columns = [col for col in df.columns if col not in ['total', 'date']]
            
            # 使用已知的线路列表，确保只计算有数据的线路
            valid_line_columns = [col for col in line_columns if col in self.data_collector.all_lines]
            
            if not valid_line_columns:
                logger.warning("没有找到有效的线路数据")
                return None
            
            # 计算每日总客流量（所有线路之和）
            total_passengers = df[valid_line_columns].sum(axis=1).values
            
            # 确保没有零值，避免除以零
            total_passengers = np.where(total_passengers == 0, 1, total_passengers)
            
            # 增大图表高度，为底部图例留出空间
            fig, ax = plt.subplots(figsize=(14, 9))
            
            # 存储图例信息
            legend_handles = []
            legend_labels = []
            
            for line in self.data_collector.all_lines:
                if line in df.columns and df[line].notna().any():
                    color = self.line_colors.get(line, '#CCCCCC')
                    
                    # 计算每日占比
                    proportions = (df[line].values / total_passengers) * 100
                    
                    line_plot = ax.plot(df['date'], proportions, 
                                       color=color,
                                       marker='o',
                                       linewidth=2.5,
                                       markersize=8)
                    
                    # 保存图例句柄和标签
                    legend_handles.append(line_plot[0])
                    legend_labels.append(line)
            
            ax.set_xlabel('日期', fontsize=20, fontweight='bold')
            ax.set_ylabel('线路客流量占比（%）', fontsize=20, fontweight='bold')
            
            ax.grid(True, alpha=0.3, linestyle='--')
            
            plt.xticks(rotation=45, ha='right', fontsize=12)
            plt.yticks(fontsize=12)
            
            ax.set_ylim(bottom=0)
            
            # 将图例放在图表下方，横向排列
            # 调整图例位置：bbox_to_anchor=(0, -0.25, 1, 0.2) 表示：
            # 左对齐(0)，在图表下方(-0.25)，宽度占满(1)，高度为0.2
            ax.legend(legend_handles, legend_labels,
                     loc='upper center',
                     bbox_to_anchor=(0, -0.5, 1, 0.2),
                     ncol=min(6, len(legend_labels)),  # 最多6列，根据线路数量调整
                     mode="expand",
                     borderaxespad=0,
                     fontsize=14,
                     frameon=True,
                     fancybox=True,
                     shadow=True)
            
            # 调整布局，为底部图例留出更多空间
            plt.tight_layout(rect=[0, 0.2, 1, 0.95])  # 底部留出10%的空间
            
            os.makedirs('docs/images', exist_ok=True)
            fig.savefig(f'docs/images/最近{n_days}天线路客流量占比变化趋势图.png', 
                       dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            logger.info(f"最近{n_days}天线路客流量占比变化趋势图已生成")
            
            return fig
            
        except Exception as e:
            logger.error(f"生成线路客流量占比变化趋势图时出错: {e}", exc_info=True)
            return None

def main():
    """主函数"""
    logger.info("开始收集南京地铁客流数据...")
    
    try:
        collector = NanjingSubwayDataCollector("config.json")
        passenger_records = collector.collect_data()
        
        logger.info(f"共收集到 {len(passenger_records)} 条客流记录")
        
        if passenger_records:
            latest_date = collector.get_latest_date()
            latest_data = collector.get_latest_data()
            total = latest_data['passenger_data'].get('总客流量', 0)
            
            logger.info(f"最新数据: {latest_date}")
            logger.info(f"总客流量: {total:.1f}万")
            
            logger.info("=== 线路配置信息 ===")
            for line in collector.all_lines:
                info = collector.get_line_info(line)
                stations = info.get('stations', 'N/A')
                logger.info(f"{line}: {stations}站 - {info.get('description', '')}")
            
            visualizer = NanjingSubwayVisualizer(collector)
            
            logger.info("1. 正在绘制线路占比饼图...")
            fig1 = visualizer.plot_compact_pie_chart()
            if fig1:
                logger.info("  线路占比饼图已保存")
            
            logger.info("2. 正在绘制总客流量变化趋势图...")
            fig2 = visualizer.plot_total_passenger_trend()
            if fig2:
                logger.info("  总客流量变化趋势图已保存")
            
            logger.info("3. 正在绘制站点客流强度变化趋势图...")
            fig3 = visualizer.plot_last_n_days_line_trend()
            if fig3:
                logger.info("  站点客流强度变化趋势图已保存")
            
            logger.info("4. 正在绘制线路客流量占比变化趋势图...")
            fig4 = visualizer.plot_line_proportion_trend()
            if fig4:
                logger.info("  线路客流量占比变化趋势图已保存")
            
            os.makedirs('docs/data', exist_ok=True)
            df = collector.get_last_n_days_line_data()
            if not df.empty:
                df.to_csv('docs/data/最近客流数据.csv', index=False, encoding='utf-8-sig')
                
                json_data = {
                    'latest_date': latest_date,
                    'latest_total': float(total),
                    'data': df.to_dict('records'),
                    'update_time': datetime.now().isoformat(),
                    'line_info': {}
                }
                
                for line in collector.all_lines:
                    info = collector.get_line_info(line)
                    json_data['line_info'][line] = {
                        'stations': info.get('stations', 0),
                        'color': info.get('color', '#CCCCCC'),
                        'description': info.get('description', '')
                    }
                
                with open('docs/data/latest_data.json', 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                logger.info("数据已保存为CSV和JSON格式")
            
            logger.info("分析完成！")
            
            print("\n" + "="*60)
            print("✅ 南京地铁客流分析完成！")
            print("="*60)
            print(f"📅 最新数据日期: {latest_date}")
            print(f"👥 总客流量: {total:.1f}万")
            print(f"📊 生成图表数: 4张")
            print(f"📈 图表类型: 线路占比饼图、总客流量变化趋势图、站点客流强度变化趋势图、线路客流量占比变化趋势图")
            print(f"💾 数据文件: 最近7天客流数据.csv")
            print(f"💾 JSON文件: latest_data.json")
            print("="*60)
            print(f"🌐 报告地址: 部署后访问 https://Unqualified-Developers.github.io/Nanjing-Metro/")
            print("="*60)
            
        else:
            logger.warning("没有收集到数据")
            print("❌ 没有收集到数据，请检查数据源或网络连接")
            
    except Exception as e:
        logger.error(f"运行过程中发生错误: {e}", exc_info=True)
        print(f"❌ 运行出错: {e}")
        raise

if __name__ == "__main__":
    main()
