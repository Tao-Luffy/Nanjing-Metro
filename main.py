#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

# Then import other libraries
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
        logging.FileHandler('metro_analysis.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Ensure Chinese font settings (kept for compatibility, but not used in output)

# Set chart style
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['figure.figsize'] = (14, 8)


class NanjingSubwayVisualizer:
    """Nanjing Metro Data Visualizer"""

    def __init__(self, data_collector):
        self.data_collector = data_collector
        self.line_colors = self._get_line_colors()

    def _get_line_colors(self):
        """Get line colors"""
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
        """Ensure font settings are correct"""
        try:
            if not plt.rcParams['font.sans-serif']:
                plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'DejaVu Sans', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
        except:
            pass

    def plot_compact_pie_chart(self):
        """Proportion pie chart"""
        try:
            self._ensure_font()

            proportions = self.data_collector.get_latest_line_proportions()
            latest_date = self.data_collector.get_latest_date()

            latest_data = self.data_collector.get_latest_data()
            total_passenger = latest_data['passenger_data'].get('total_passengers', 0)

            if not proportions:
                logger.warning("No latest data found")
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

            # Modify legend text format: remove line breaks, combine into one line
            legend_labels = []
            for line, value, actual in zip(lines, values, actual_passengers):
                if line.startswith("Other"):
                    legend_labels.append(f"{line}: {value:.1f}% ({actual:.1f} ten thousand)")
                else:
                    legend_labels.append(f"{line}: {value:.1f}% ({actual:.1f} ten thousand)")

            # Place legend below chart, two columns
            ax.legend(wedges, legend_labels,
                      loc='upper center',
                      bbox_to_anchor=(0, -0.2, 1, 0.2),
                      ncol=2,  # Two columns
                      fontsize=20)

            center_text = f"{latest_date}\nTotal Passengers\n{total_passenger:.1f} w"
            ax.text(0, 0, center_text,
                    ha='center', va='center',
                    fontsize=28, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            ax.axis('equal')

            plt.tight_layout()

            os.makedirs('docs/images', exist_ok=True)
            fig.savefig('docs/images/yesterday_passenger_line_proportion.png', dpi=300, bbox_inches='tight')
            plt.close(fig)

            logger.info("Proportion pie chart generated")
            return fig

        except Exception as e:
            logger.error(f"Error generating proportion pie chart: {e}", exc_info=True)
            return None

    def plot_total_passenger_trend(self, n_days=60):
        """Plot total passenger trend chart"""
        try:
            self._ensure_font()

            # Get raw data (Weibo data is reversed, latest first)
            df = self.data_collector.get_last_n_days_line_data(n_days)

            if df.empty:
                logger.warning(f"No data found for the last {n_days} days")
                return None

            # Reverse data to correct chronological order
            df = df.iloc[::-1].reset_index(drop=True)

            fig, ax = plt.subplots(figsize=(14, 8))

            if 'total' in df.columns:
                # Draw filled area (blue gradient shadow) first
                ax.fill_between(df['date'], df['total'],
                                alpha=0.3,
                                color='#1f77b4',
                                edgecolor='none',
                                interpolate=True)

                # Then draw the line
                ax.plot(df['date'], df['total'],
                        color='#1f77b4',
                        marker='o',
                        linewidth=2.5,
                        markersize=8)

            ax.set_xlabel('Date', fontsize=30, fontweight='bold')
            ax.set_ylabel('Total Passengers (w)', fontsize=30, fontweight='bold')

            ax.legend(['Total Passengers'], loc='lower right', fontsize=30, title=None)
            ax.grid(True, alpha=0.3, linestyle='--')

            plt.xticks(rotation=45, ha='right', fontsize=12)
            plt.yticks(fontsize=12)

            ax.set_ylim(bottom=0)

            plt.tight_layout()

            os.makedirs('docs/images', exist_ok=True)
            fig.savefig(f'docs/images/last_{n_days}_days_total_passenger_trend.png',
                        dpi=300, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"Last {n_days} days total passenger trend chart generated")

            return fig

        except Exception as e:
            logger.error(f"Error generating total passenger trend chart: {e}", exc_info=True)
            return None

    def plot_last_n_days_line_trend(self, n_days=30):
        """Plot station passenger intensity trend chart"""
        try:
            self._ensure_font()

            # Get raw data (Weibo data is reversed, latest first)
            df = self.data_collector.get_last_n_days_line_data(n_days)

            if df.empty:
                logger.warning(f"No data found for the last {n_days} days")
                return None

            # Reverse data to correct chronological order
            df = df.iloc[::-1].reset_index(drop=True)

            line_info = self.data_collector.line_info

            # Increase chart height to leave space for legend at bottom
            fig, ax = plt.subplots(figsize=(14, 21))

            # Store legend information
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

                    # Save legend handles and labels
                    legend_handles.append(line_plot[0])
                    legend_labels.append(f'{line} ({stations} stations)')

            ax.set_xlabel('Date', fontsize=30, fontweight='bold')
            ax.set_ylabel('Station Intensity (w/station)', fontsize=30, fontweight='bold')

            ax.grid(True, alpha=0.3, linestyle='--')

            plt.xticks(rotation=45, ha='right', fontsize=12)
            plt.yticks(fontsize=12)

            ax.set_ylim(bottom=0)

            # Place legend below chart, three columns
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

            logger.info(f"Last {n_days} days station passenger intensity trend chart generated")

            return fig

        except Exception as e:
            logger.error(f"Error generating station passenger intensity trend chart: {e}", exc_info=True)
            return None

    def plot_line_proportion_trend(self, n_days=30):
        """Plot line passenger proportion trend chart"""
        try:
            self._ensure_font()

            # Get raw data (Weibo data is reversed, latest first)
            df = self.data_collector.get_last_n_days_line_data(n_days)

            if df.empty:
                logger.warning(f"No data found for the last {n_days} days")
                return None

            # Reverse data to correct chronological order
            df = df.iloc[::-1].reset_index(drop=True)

            # Get all line columns (excluding 'total' and 'date')
            line_columns = [col for col in df.columns if col not in ['total', 'date']]

            # Use known line list to ensure only valid line data is calculated
            valid_line_columns = [col for col in line_columns if col in self.data_collector.all_lines]

            if not valid_line_columns:
                logger.warning("No valid line data found")
                return None

            # Calculate daily total passengers (sum of all lines)
            total_passengers = df[valid_line_columns].sum(axis=1).values

            # Avoid division by zero
            total_passengers = np.where(total_passengers == 0, 1, total_passengers)

            # Increase chart height to leave space for legend at bottom
            fig, ax = plt.subplots(figsize=(14, 19))

            # Store legend information
            legend_handles = []
            legend_labels = []

            for line in self.data_collector.all_lines:
                if line in df.columns and df[line].notna().any():
                    color = self.line_colors.get(line, '#CCCCCC')

                    # Calculate daily proportion
                    proportions = (df[line].values / total_passengers) * 100

                    line_plot = ax.plot(df['date'], proportions,
                                        color=color,
                                        marker='o',
                                        linewidth=2.5,
                                        markersize=8)

                    # Save legend handles and labels
                    legend_handles.append(line_plot[0])
                    legend_labels.append(line)

            ax.set_xlabel('Date', fontsize=30, fontweight='bold')
            ax.set_ylabel('Line Proportion (%)', fontsize=30, fontweight='bold')

            ax.grid(True, alpha=0.3, linestyle='--')

            plt.xticks(rotation=45, ha='right', fontsize=12)
            plt.yticks(fontsize=12)

            ax.set_ylim(bottom=0)

            # Place legend below chart, horizontal arrangement
            ax.legend(legend_handles, legend_labels,
                      loc='upper center',
                      bbox_to_anchor=(0, -0.45, 1, 0.2),
                      ncol=min(4, len(legend_labels)),  # At most 4 columns, adjust by line count
                      mode="expand",
                      borderaxespad=0,
                      fontsize=30,
                      frameon=True,
                      fancybox=True)

            # Adjust layout to leave more space for bottom legend
            plt.tight_layout(rect=[0, 0.25, 1, 0.95])

            os.makedirs('docs/images', exist_ok=True)
            fig.savefig(f'docs/images/last_{n_days}_days_line_proportion_trend.png',
                        dpi=300, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"Last {n_days} days line passenger proportion trend chart generated")

            return fig

        except Exception as e:
            logger.error(f"Error generating line passenger proportion trend chart: {e}", exc_info=True)
            return None


def main():
    """Main function"""
    logger.info("Starting Nanjing Metro passenger data collection...")

    try:
        collector = NanjingSubwayDataCollector("config.json")
        passenger_records = collector.collect_data()

        logger.info(f"Collected {len(passenger_records)} passenger records")

        if passenger_records:
            latest_date = collector.get_latest_date()
            latest_data = collector.get_latest_data()
            total = latest_data['passenger_data'].get('total_passengers', 0)

            logger.info(f"Latest data: {latest_date}")
            logger.info(f"Total passengers: {total:.1f} ten thousand")

            logger.info("=== Line Configuration Information ===")
            for line in collector.all_lines:
                info = collector.get_line_info(line)
                stations = info.get('stations', 'N/A')
                logger.info(f"{line}: {stations} stations - {info.get('description', '')}")

            visualizer = NanjingSubwayVisualizer(collector)

            logger.info("1. Generating line proportion pie chart...")
            fig1 = visualizer.plot_compact_pie_chart()
            if fig1:
                logger.info("   Line proportion pie chart saved")

            logger.info("2. Generating total passenger trend chart...")
            fig2 = visualizer.plot_total_passenger_trend()
            if fig2:
                logger.info("   Total passenger trend chart saved")

            logger.info("3. Generating station passenger intensity trend chart...")
            fig3 = visualizer.plot_last_n_days_line_trend()
            if fig3:
                logger.info("   Station passenger intensity trend chart saved")

            logger.info("4. Generating line passenger proportion trend chart...")
            fig4 = visualizer.plot_line_proportion_trend()
            if fig4:
                logger.info("   Line passenger proportion trend chart saved")

            os.makedirs('docs/data', exist_ok=True)
            df = collector.get_last_n_days_line_data()
            if not df.empty:
                df.to_csv('docs/data/recent_passenger_data.csv', index=False, encoding='utf-8-sig')

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

                logger.info("Data saved in CSV and JSON formats")

            logger.info("Analysis completed!")

            print("\n" + "=" * 60)
            print("Nanjing Metro Passenger Analysis Completed!")
            print("=" * 60)
            print(f"Latest data date: {latest_date}")
            print(f"Total passengers: {total:.1f} ten thousand")
            print(f"Charts generated: 4")
            print(
                f"Chart types: Line proportion pie chart, total passenger trend, station intensity trend, line proportion trend")
            print(f"Data file: recent_passenger_data.csv")
            print(f"JSON file: latest_data.json")
            print("=" * 60)
            print(f"Report URL: After deployment visit https://Unqualified-Developers.github.io/Nanjing-Metro/")
            print("=" * 60)

        else:
            logger.warning("No data collected")
            print("No data collected. Please check data source or network connection.")

    except Exception as e:
        logger.error(f"Error occurred during execution: {e}", exc_info=True)
        print(f"Execution error: {e}")
        raise


if __name__ == "__main__":
    main()
