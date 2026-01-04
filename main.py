#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 首先配置字体
try:
    from setup_fonts import setup_chinese_fonts, test_chinese_font
    if setup_chinese_fonts():
        print("✓ 字体配置完成")
    else:
        print("⚠ 字体配置可能有问题，继续运行...")
except Exception as e:
    print(f"⚠ 字体配置脚本出错: {e}")

# 然后导入其他库
import matplotlib
matplotlib.use('Agg')  # 使用Agg后端，避免GUI问题
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
        # 检查当前字体设置
        current_fonts = plt.rcParams.get('font.sans-serif', [])
        print(f"当前字体设置: {current_fonts}")
        
        if not current_fonts:
            # 如果没有设置，尝试设置
            font_candidates = [
                'WenQuanYi Zen Hei',
                'DejaVu Sans',
                'Liberation Sans',
                'Arial Unicode MS',
                'sans-serif'
            ]
            
            # 检查哪些字体可用
            available_fonts = []
            all_fonts = [f.name for f in fm.fontManager.ttflist]
            for font in font_candidates:
                if font in all_fonts:
                    available_fonts.append(font)
            
            if available_fonts:
                plt.rcParams['font.sans-serif'] = available_fonts
                plt.rcParams['axes.unicode_minus'] = False
                print(f"已设置字体: {available_fonts}")
            else:
                # 紧急备用方案：使用默认字体
                plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
                print("使用默认字体设置")
                
    except Exception as e:
        logger.error(f"确保字体设置时出错: {e}")

# 调用字体检查
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
        """获取线路颜色，如果没有配置则生成默认颜色"""
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
            # 检查当前字体
            if not plt.rcParams['font.sans-serif']:
                plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'DejaVu Sans', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
        except:
            pass

    def plot_compact_pie_chart(self):
        """紧凑型饼图：更适合小屏幕查看"""
        try:
            self._ensure_font()
            
            proportions = self.data_collector.get_latest_line_proportions()
            latest_date = self.data_collector.get_latest_date()
            
            # 获取总客流量
            latest_data = self.data_collector.get_latest_data()
            total_passenger = latest_data['passenger_data'].get('总客流量', 0)
            
            if not proportions:
                logger.warning("没有找到最新数据")
                return None
            
            # 按占比排序
            sorted_items = sorted(proportions.items(), key=lambda x: x[1], reverse=True)
            
            lines = [item[0] for item in sorted_items]
            values = [item[1] for item in sorted_items]
            
            # 计算每条线路的实际客流量
            actual_passengers = []
            for value in values:
                actual = total_passenger * value / 100
                actual_passengers.append(actual)
            
            # 获取颜色
            colors = [self.line_colors.get(line, '#CCCCCC') for line in lines]
            if len(sorted_items) > top_n:
                colors[-1] = '#E0E0E0'
            
            fig, ax = plt.subplots(figsize=(12, 10))
            
            # 使用外部的标签，避免重叠
            wedges, texts = ax.pie(
                values,
                colors=colors,
                startangle=90,
                wedgeprops=dict(width=0.4, edgecolor='white'),
                labels=None  # 不显示内部标签
            )
            
            # 创建图例，显示完整信息（占比和实际客流量）
            legend_labels = []
            for line, value, actual in zip(lines, values, actual_passengers):
                if line.startswith("其他"):
                    legend_labels.append(f"{line}: {value:.1f}%\n({actual:.1f}万)")
                else:
                    legend_labels.append(f"{line}: {value:.1f}%\n({actual:.1f}万)")
            
            # 将图例放在图表右侧
            ax.legend(wedges, legend_labels,
                     title="线路客流信息",
                     loc="center left",
                     bbox_to_anchor=(1, 0, 0.5, 1),
                     fontsize=9,
                     title_fontsize=11)
            
            # 在饼图中心添加总客流量信息
            center_text = f"{latest_date}\n总客流\n{total_passenger:.1f}万"
            ax.text(0, 0, center_text,
                   ha='center', va='center',
                   fontsize=14, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            
            ax.set_title('南京地铁客流占比分析', fontsize=16, fontweight='bold')
            ax.axis('equal')
            
            plt.tight_layout()
            
            # 保存为额外的小屏幕版本
            os.makedirs('docs/images', exist_ok=True)
            fig.savefig('docs/images/昨日客流线路占比图.png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            logger.info("紧凑型饼图已生成")
            return fig
            
        except Exception as e:
            logger.error(f"生成紧凑型饼图时出错: {e}", exc_info=True)
            return None
    
    def plot_last_n_days_line_trend(self, n_days=7):
        """绘制最近n天站点客流强度变化趋势图
        站点客流强度 = 客流量 / 站点数量（取整）
        """
        try:
            self._ensure_font()
            
            df = self.data_collector.get_last_n_days_line_data(n_days)
            
            if df.empty:
                logger.warning(f"没有找到最近{n_days}天的数据")
                return None
            
            # 获取各线路站点数量信息
            line_info = self.data_collector.line_info
            
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # 绘制每条线路的站点客流强度趋势线
            for line in self.data_collector.all_lines:
                if line in df.columns:
                    # 只显示有数据的线路
                    if df[line].notna().any():
                        color = self.line_colors.get(line, '#CCCCCC')
                        
                        # 获取站点数量
                        stations = line_info.get(line, {}).get('stations', 1)
                        if stations == 0:
                            stations = 1  # 避免除零错误
                        
                        # 计算站点客流强度 = 客流量 / 站点数量
                        station_intensity = df[line] / stations
                        
                        # 在图例中显示线路名称和站点数
                        ax.plot(df['date'], station_intensity, 
                               label=f'{line} ({stations}站)', 
                               color=color,
                               marker='o',
                               linewidth=2.5,
                               markersize=8)
            
            # 设置中文标签和标题
            ax.set_xlabel('日期', fontsize=12, fontweight='bold')
            ax.set_ylabel('站点客流强度（万/站）', fontsize=12, fontweight='bold')
            ax.set_title(f'最近{n_days}天南京地铁各线路站点客流强度变化趋势\n(站点客流强度 = 客流量 ÷ 站点数)', 
                        fontsize=14, fontweight='bold', pad=20)
            
            # 添加图例
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9, title="线路(站点数)")
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # 设置x轴标签旋转
            plt.xticks(rotation=45, ha='right')
            
            # 设置y轴从0开始
            ax.set_ylim(bottom=0)
            
            # 添加站点客流强度计算公式说明
            ax.text(0.02, 0.98, '计算公式：站点客流强度 = 客流量 ÷ 站点数量',
                   transform=ax.transAxes,
                   fontsize=9,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            plt.tight_layout()
            
            # 保存图片
            os.makedirs('docs/images', exist_ok=True)
            fig.savefig(f'docs/images/最近{n_days}天客流强度变化趋势图.png', 
                       dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            logger.info(f"最近{n_days}天站点客流强度变化趋势图已生成")
            
            # 检查图片文件
            if os.path.exists(f'docs/images/最近{n_days}天客流强度变化趋势图.png'):
                file_size = os.path.getsize(f'docs/images/最近{n_days}天客流强度变化趋势图.png')
                logger.info(f"站点客流强度趋势图文件大小: {file_size} bytes")
            
            return fig
            
        except Exception as e:
            logger.error(f"生成站点客流强度趋势图时出错: {e}", exc_info=True)
            return None
    
    def plot_comprehensive_analysis(self, n_days=7):
        """绘制综合分析仪表板"""
        try:
            self._ensure_font()
            
            fig = plt.figure(figsize=(18, 12))
            gs = fig.add_gridspec(3, 3)
            
            df = self.data_collector.get_last_n_days_line_data(n_days)
            
            if not df.empty:
                # 饼图
                proportions = self.data_collector.get_latest_line_proportions()
                if proportions:
                    ax1 = fig.add_subplot(gs[0, 0])
                    sorted_items = sorted(proportions.items(), key=lambda x: x[1], reverse=True)
                    top5_lines = [item[0] for item in sorted_items[:5]]
                    top5_values = [item[1] for item in sorted_items[:5]]
                    top5_colors = [self.line_colors.get(line, '#CCCCCC') for line in top5_lines]
                    
                    # 获取总客流量
                    latest_data = self.data_collector.get_latest_data()
                    total_passenger = latest_data['passenger_data'].get('总客流量', 0)
                    
                    # 自定义autopct函数，正确计算实际客流量
                    def autopct_func(pct):
                        actual = total_passenger * pct / 100
                        return f'{pct:.1f}%\n({actual:.1f}万)'
                    
                    ax1.pie(top5_values, labels=top5_lines, autopct=autopct_func,
                           colors=top5_colors, startangle=90)
                    ax1.set_title('TOP5线路占比', fontsize=12, fontweight='bold')
                
                # 总客流趋势
                ax2 = fig.add_subplot(gs[0, 1:])
                if 'total' in df.columns:
                    ax2.plot(df['date'], df['total'], 'b-o', linewidth=2, markersize=8)
                    ax2.fill_between(df['date'], df['total'], alpha=0.2)
                    ax2.set_xlabel('日期')
                    ax2.set_ylabel('总客流量（万）')
                    ax2.set_title(f'最近{n_days}天总客流趋势', fontsize=12, fontweight='bold')
                    ax2.grid(True, alpha=0.3)
                    ax2.set_xticklabels(df['date'], rotation=45, ha='right')
                
                # 热力图
                ax3 = fig.add_subplot(gs[1:, :])
                main_lines = self.data_collector.all_lines[:8]
                
                heatmap_data = []
                valid_lines = []
                for line in main_lines:
                    if line in df.columns and df[line].notna().any():
                        heatmap_data.append(df[line].values)
                        valid_lines.append(line)
                
                if heatmap_data:
                    heatmap_data = np.array(heatmap_data)
                    im = ax3.imshow(heatmap_data, aspect='auto', cmap='YlOrRd', interpolation='nearest')
                    
                    ax3.set_yticks(range(len(valid_lines)))
                    ax3.set_yticklabels(valid_lines)
                    ax3.set_xticks(range(len(df)))
                    ax3.set_xticklabels(df['date'], rotation=45, ha='right')
                    
                    cbar = plt.colorbar(im, ax=ax3)
                    cbar.set_label('客流量（万）')
                    
                    for i in range(len(valid_lines)):
                        for j in range(len(df)):
                            value = heatmap_data[i, j]
                            if not np.isnan(value):
                                ax3.text(j, i, f'{value:.0f}', 
                                        ha='center', va='center', 
                                        color='white' if value > heatmap_data.max()/2 else 'black',
                                        fontsize=20)
                    
                    ax3.set_title(f'主要线路客流量热力图（最近{n_days}天）', fontsize=14, fontweight='bold')
                
                # 统计信息
                ax4 = fig.add_subplot(gs[2, 0])
                ax4.axis('off')

                if 'total' in df.columns:
                    avg_total = df['total'].mean()
                    max_total = df['total'].max()
                    min_total = df['total'].min()
                    latest_total = df['total'].iloc[0]
                    
                    if len(df) >= 2:
                        change = df['total'].iloc[0] - df['total'].iloc[1]
                        change_pct = (change / df['total'].iloc[1]) * 100 if df['total'].iloc[1] != 0 else 0

            fig.suptitle('南京地铁客流综合分析仪表板', fontsize=16, fontweight='bold')
            plt.tight_layout()
            
            # 保存图片
            os.makedirs('docs/images', exist_ok=True)
            fig.savefig('docs/images/综合分析仪表板.png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            logger.info("综合分析仪表板已生成")
            return fig
            
        except Exception as e:
            logger.error(f"生成分析仪表板时出错: {e}")
            return None

def main():
    """主函数"""
    logger.info("开始收集南京地铁客流数据...")
    
    try:
        # 初始化数据收集器
        collector = NanjingSubwayDataCollector("config.json")
        
        # 收集数据
        passenger_records = collector.collect_data()
        
        logger.info(f"共收集到 {len(passenger_records)} 条客流记录")
        
        if passenger_records:
            latest_date = collector.get_latest_date()
            latest_data = collector.get_latest_data()
            total = latest_data['passenger_data'].get('总客流量', 0)
            
            logger.info(f"最新数据: {latest_date}")
            logger.info(f"总客流量: {total:.1f}万")
            
            # 显示线路信息
            logger.info("=== 线路配置信息 ===")
            for line in collector.all_lines:
                info = collector.get_line_info(line)
                stations = info.get('stations', 'N/A')
                logger.info(f"{line}: {stations}站 - {info.get('description', '')}")
            
            # 初始化可视化器
            visualizer = NanjingSubwayVisualizer(collector)
            
            # 1. 绘制线路占比饼图（适合小屏幕）
            logger.info("1. 正在绘制紧凑型饼图...")
            fig2 = visualizer.plot_compact_pie_chart()
            if fig2:
                logger.info("  线路占比饼图已保存")
            
            # 2. 绘制最近7天站点客流强度变化趋势图
            logger.info("2. 正在绘制最近7天站点客流强度变化趋势图...")
            fig3 = visualizer.plot_last_n_days_line_trend(7)
            if fig3:
                logger.info("  站点客流强度趋势图已保存")
            
            # 3. 绘制综合分析仪表板
            logger.info("3. 正在绘制综合分析仪表板...")
            fig4 = visualizer.plot_comprehensive_analysis(7)
            if fig4:
                logger.info("  综合分析仪表板已保存")
            
            # 保存数据到文件
            os.makedirs('docs/data', exist_ok=True)
            df = collector.get_last_n_days_line_data(7)
            if not df.empty:
                # 保存为CSV
                df.to_csv('docs/data/最近7天客流数据.csv', index=False, encoding='utf-8-sig')
                
                # 保存为JSON（便于网页直接读取）
                json_data = {
                    'latest_date': latest_date,
                    'latest_total': float(total),
                    'data': df.to_dict('records'),
                    'update_time': datetime.now().isoformat(),
                    'line_info': {}
                }
                
                # 添加线路站点信息
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
            
            # 打印总结信息
            print("\n" + "="*60)
            print("✅ 南京地铁客流分析完成！")
            print("="*60)
            print(f"📅 最新数据日期: {latest_date}")
            print(f"👥 总客流量: {total:.1f}万")
            print(f"📊 生成图表数: 3张")
            print(f"📈 图表类型: 线路占比图、站点客流强度趋势图、综合分析仪表板")
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
