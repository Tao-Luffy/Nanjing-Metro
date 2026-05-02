#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import io

# 修复 Windows 控制台编码问题，支持中文输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Then import other libraries
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ========== 设置中文字体（避免图表中文显示方框）==========
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'WenQuanYi Zen Hei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示为方块的问题
# =====================================================

import numpy as np
from metro_data import NanjingSubwayDataCollector
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('metro_analysis.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Set chart style
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

    def plot_compact_pie_chart(self):
        """客流量占比饼图"""
        try:
            proportions = self.data_collector.get_latest_line_proportions()
            latest_date = self.data_collector.get_latest_date()

            latest_data = self.data_collector.get_latest_data()
            total_passenger = latest_data['passenger_data'].get('total_passengers', 0)

            if not proportions or total_passenger == 0:
                logger.warning("未找到最新数据或总客流量为零")
                return None

            sorted_items = sorted(proportions.items(), key=lambda x: x[1], reverse=True)

            lines = [item[0] for item in sorted_items]
            values = [item[1] for item in sorted_items]

            actual_passengers = []
            for value in values:
                actual = total_passenger * value / 100
                actual_passengers.append(actual)

            colors = [self.line_colors.get(line, '#CCCCCC') for line in lines]
            fig, ax = plt.subplots(figsize=(9, 12))

            wedges, texts = ax.pie(
                values,
                colors=colors,
                startangle=90,
                wedgeprops=dict(width=0.4, edgecolor='white'),
                labels=None
            )

            # 图例文本：线路名、占比、实际客流量（万）
            legend_labels = []
            for line, value, actual in zip(lines, values, actual_passengers):
                legend_labels.append(f"{line}: {value:.1f}% ({actual:.1f} 万)")

            # 图例放在图表下方，两列显示
            ax.legend(wedges, legend_labels,
                      loc='upper center',
                      bbox_to_anchor=(0, -0.2, 1, 0.2),
                      ncol=2,
                      fontsize=20)

            # 中心文字：日期、总客流量（万）
            center_text = f"{latest_date}\n总客流量\n{total_passenger:.1f} 万"
            ax.text(0, 0, center_text,
                    ha='center', va='center',
                    fontsize=28, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            ax.axis('equal')

            plt.tight_layout()

            os.makedirs('docs/images', exist_ok=True)
            fig.savefig('docs/images/yesterday_passenger_line_proportion.png', dpi=300, bbox_inches='tight')
            plt.close(fig)

            logger.info("客流量占比饼图已生成")
            return fig

        except Exception as e:
            logger.error(f"生成占比饼图时出错: {e}", exc_info=True)
            return None

    def plot_total_passenger_trend(self, n_days=60):
        """总客流量趋势图"""
        try:
            df = self.data_collector.get_last_n_days_line_data(n_days)

            if df.empty:
                logger.warning(f"未找到最近 {n_days} 天的数据")
                return None

            # 删除缺失值
            df = df.dropna(subset=['date', 'total'])
            if df.empty:
                logger.warning("删除缺失值后无有效数据")
                return None

            # 反转数据以按时间正序
            df = df.iloc[::-1].reset_index(drop=True)

            fig, ax = plt.subplots(figsize=(14, 8))

            if 'total' in df.columns:
                # 先绘制填充区域（蓝色渐变阴影）
                ax.fill_between(df['date'], df['total'],
                                alpha=0.3,
                                color='#1f77b4',
                                edgecolor='none',
                                interpolate=True)

                # 再绘制折线
                ax.plot(df['date'], df['total'],
                        color='#1f77b4',
                        marker='o',
                        linewidth=2.5,
                        markersize=8)

            ax.set_xlabel('日期', fontsize=30, fontweight='bold')
            ax.set_ylabel('总客流量（万）', fontsize=30, fontweight='bold')  # 修改单位：万人次 -> 万

            ax.legend(['总客流量'], loc='lower right', fontsize=30, title=None)
            ax.grid(True, alpha=0.3, linestyle='--')

            plt.xticks(rotation=45, ha='right', fontsize=12)
            plt.yticks(fontsize=12)

            ax.set_ylim(bottom=0)

            plt.tight_layout()

            os.makedirs('docs/images', exist_ok=True)
            fig.savefig(f'docs/images/last_{n_days}_days_total_passenger_trend.png',
                        dpi=300, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"最近 {n_days} 天总客流量趋势图已生成")
            return fig

        except Exception as e:
            logger.error(f"生成总客流量趋势图时出错: {e}", exc_info=True)
            return None

    def plot_last_n_days_line_trend(self, n_days=30):
        """各线路站点客流强度趋势图（原站均客流量）"""
        try:
            df = self.data_collector.get_last_n_days_line_data(n_days)

            if df.empty:
                logger.warning(f"未找到最近 {n_days} 天的数据")
                return None

            # 反转数据以按时间正序
            df = df.iloc[::-1].reset_index(drop=True)

            line_info = self.data_collector.line_info

            # 增加图表高度，为底部图例预留空间
            fig, ax = plt.subplots(figsize=(14, 21))

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

                    legend_handles.append(line_plot[0])
                    legend_labels.append(f'{line} ({stations}站)')

            ax.set_xlabel('日期', fontsize=30, fontweight='bold')
            ax.set_ylabel('站点客流强度（万/站）', fontsize=30, fontweight='bold')  # 修改标签和单位

            ax.grid(True, alpha=0.3, linestyle='--')

            plt.xticks(rotation=45, ha='right', fontsize=12)
            plt.yticks(fontsize=12)

            ax.set_ylim(bottom=0)

            # 图例放在图表下方，三列显示
            ax.legend(legend_handles, legend_labels,
                      loc='upper center',
                      bbox_to_anchor=(0, -0.45, 1, 0.2),
                      ncol=3,
                      mode="expand",
                      borderaxespad=0,
                      fontsize=30,
                      frameon=True,
                      fancybox=True)

            plt.tight_layout(rect=[0, 0.25, 1, 0.95])

            os.makedirs('docs/images', exist_ok=True)
            fig.savefig(f'docs/images/last_{n_days}_days_station_intensity_trend.png',
                        dpi=300, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"最近 {n_days} 天站点客流强度趋势图已生成")  # 修改日志描述
            return fig

        except Exception as e:
            logger.error(f"生成站点客流强度趋势图时出错: {e}", exc_info=True)
            return None

    def plot_line_proportion_trend(self, n_days=30):
        """各线路客流量占比趋势图"""
        try:
            df = self.data_collector.get_last_n_days_line_data(n_days)

            if df.empty:
                logger.warning(f"未找到最近 {n_days} 天的数据")
                return None

            # 反转数据以按时间正序
            df = df.iloc[::-1].reset_index(drop=True)

            # 获取所有线路列（排除 'total' 和 'date'）
            line_columns = [col for col in df.columns if col not in ['total', 'date']]
            valid_line_columns = [col for col in line_columns if col in self.data_collector.all_lines]

            if not valid_line_columns:
                logger.warning("未找到有效的线路数据")
                return None

            # 计算每日总客流量（所有线路之和）
            total_passengers = df[valid_line_columns].sum(axis=1).values
            total_passengers = np.where(total_passengers == 0, 1, total_passengers)  # 避免除零

            fig, ax = plt.subplots(figsize=(14, 19))

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

                    legend_handles.append(line_plot[0])
                    legend_labels.append(line)

            ax.set_xlabel('日期', fontsize=30, fontweight='bold')
            ax.set_ylabel('线路占比（%）', fontsize=30, fontweight='bold')

            ax.grid(True, alpha=0.3, linestyle='--')

            plt.xticks(rotation=45, ha='right', fontsize=12)
            plt.yticks(fontsize=12)

            ax.set_ylim(bottom=0)

            # 图例放在图表下方，最多4列
            ax.legend(legend_handles, legend_labels,
                      loc='upper center',
                      bbox_to_anchor=(0, -0.45, 1, 0.2),
                      ncol=min(4, len(legend_labels)),
                      mode="expand",
                      borderaxespad=0,
                      fontsize=30,
                      frameon=True,
                      fancybox=True)

            plt.tight_layout(rect=[0, 0.25, 1, 0.95])

            os.makedirs('docs/images', exist_ok=True)
            fig.savefig(f'docs/images/last_{n_days}_days_line_proportion_trend.png',
                        dpi=300, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"最近 {n_days} 天线路占比趋势图已生成")
            return fig

        except Exception as e:
            logger.error(f"生成线路占比趋势图时出错: {e}", exc_info=True)
            return None


def main():
    """主函数"""
    logger.info("开始收集南京地铁客流数据...")

    try:
        collector = NanjingSubwayDataCollector("config.json")
        passenger_records = collector.collect_data()

        logger.info(f"已收集 {len(passenger_records)} 条客流记录")

        if passenger_records:
            latest_date = collector.get_latest_date()
            latest_data = collector.get_latest_data()
            total = latest_data['passenger_data'].get('total_passengers', 0)

            logger.info(f"最新数据日期: {latest_date}")
            logger.info(f"总客流量: {total:.1f} 万")  # 修改单位：万人次 -> 万

            logger.info("=== 线路配置信息 ===")
            for line in collector.all_lines:
                info = collector.get_line_info(line)
                stations = info.get('stations', 'N/A')
                logger.info(f"{line}: {stations} 站 - {info.get('description', '')}")

            visualizer = NanjingSubwayVisualizer(collector)

            logger.info("1. 生成线路占比饼图...")
            fig1 = visualizer.plot_compact_pie_chart()
            if fig1:
                logger.info("   线路占比饼图已保存")

            logger.info("2. 生成总客流量趋势图...")
            fig2 = visualizer.plot_total_passenger_trend()
            if fig2:
                logger.info("   总客流量趋势图已保存")

            logger.info("3. 生成站点客流强度趋势图...")  # 修改描述
            fig3 = visualizer.plot_last_n_days_line_trend()
            if fig3:
                logger.info("   站点客流强度趋势图已保存")  # 修改描述

            logger.info("4. 生成线路占比趋势图...")
            fig4 = visualizer.plot_line_proportion_trend()
            if fig4:
                logger.info("   线路占比趋势图已保存")

            os.makedirs('docs/data', exist_ok=True)
            df = collector.get_last_n_days_line_data()
            if not df.empty:
                # 保存 CSV 时，将 date 列转换回字符串
                df_csv = df.copy()
                df_csv['date'] = df_csv['date'].dt.strftime('%Y-%m-%d')
                df_csv.to_csv('docs/data/recent_passenger_data.csv', index=False, encoding='utf-8-sig')

                # 生成 JSON 数据前，将 DataFrame 中的 Timestamp 转换为字符串
                records = df.to_dict('records')
                for record in records:
                    if 'date' in record and hasattr(record['date'], 'strftime'):
                        record['date'] = record['date'].strftime('%Y-%m-%d')
                    # 确保所有数值都是 Python 原生类型
                    for key, value in record.items():
                        if hasattr(value, 'item'):  # numpy 类型
                            record[key] = value.item()

                json_data = {
                    'latest_date': latest_date,
                    'latest_total': float(total),
                    'data': records,
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

                logger.info("数据已保存为 CSV 和 JSON 格式")

            logger.info("分析完成！")

            print("\n" + "=" * 60)
            print("南京地铁客流分析完成！")
            print("=" * 60)
            print(f"最新数据日期: {latest_date}")
            print(f"总客流量: {total:.1f} 万")  # 修改单位
            print(f"已生成图表: 4 张")
            print("图表类型: 线路占比饼图、总客流量趋势图、站点客流强度趋势图、线路占比趋势图")  # 修改名称
            print(f"数据文件: recent_passenger_data.csv")
            print(f"JSON 文件: latest_data.json")
            print("=" * 60)
            print(f"报告 URL: 部署后访问 https://Unqualified-Developers.github.io/Nanjing-Metro/")
            print("=" * 60)

        else:
            logger.warning("未收集到数据")
            print("未收集到数据，请检查数据源或网络连接。")

    except Exception as e:
        logger.error(f"执行过程中出错: {e}", exc_info=True)
        print(f"执行错误: {e}")
        raise


if __name__ == "__main__":
    main()
