# 开发者：陈工
# 开发团队：广州智尘梦科技工作室
# 时间：2025/06/14
# 版本：1.0.0
# 基于Qt上位机的数据可视化系统

import os
import sys
import site
from pathlib import Path

# 直接从site-packages中查找PyQt5相关路径
site_packages = site.getsitepackages()
for site_package in site_packages:
    # 检查PyQt5-Qt5路径
    qt5_plugins_path = os.path.join(site_package, "PyQt5", "Qt5", "plugins")
    if os.path.exists(qt5_plugins_path):
        os.environ["QT_PLUGIN_PATH"] = qt5_plugins_path
        print(f"设置QT_PLUGIN_PATH为: {qt5_plugins_path}")
        break
    
    # 检查pyqt5_plugins路径
    pyqt5_plugins_path = os.path.join(site_package, "pyqt5_plugins")
    if os.path.exists(pyqt5_plugins_path):
        os.environ["QT_PLUGIN_PATH"] = pyqt5_plugins_path
        print(f"设置QT_PLUGIN_PATH为: {pyqt5_plugins_path}")
        break

# 检查虚拟环境中的路径
venv_path = os.path.dirname(os.path.dirname(sys.executable))
venv_site_packages = os.path.join(venv_path, "Lib", "site-packages")
qt5_plugins_path = os.path.join(venv_site_packages, "PyQt5", "Qt5", "plugins")
if os.path.exists(qt5_plugins_path):
    os.environ["QT_PLUGIN_PATH"] = qt5_plugins_path
    print(f"设置QT_PLUGIN_PATH为: {qt5_plugins_path}")

import os
import time
import random
import math
import sqlite3
import serial
import serial.tools.list_ports
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                            QComboBox, QGroupBox, QRadioButton, QMessageBox,
                            QSplitter)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QDateTime, QPointF
from PyQt5.QtGui import QPainter, QFont, QColor, QPen
from PyQt5.QtChart import (QChart, QChartView, QLineSeries, QDateTimeAxis, 
                          QValueAxis, QScatterSeries)

# 数据库管理类，负责数据的存储和查询
class DatabaseManager:
    
    def __init__(self, db_name="sensor_data.db"):

        # 初始化数据库连接并创建表
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):

        # 连接到数据库
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            print(f"成功连接到数据库: {self.db_name}")
        except sqlite3.Error as e:
            print(f"数据库连接错误: {e}")

    # 创建传感器数据表
    def create_tables(self):
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    thermal_value INTEGER,
                    light_value INTEGER
                )
            ''')
            self.conn.commit()
            print("数据表创建成功")
        except sqlite3.Error as e:
            print(f"创建表错误: {e}")

    # 插入传感器数据
    def insert_data(self, thermal_value, light_value):
        try:
            self.cursor.execute('''
                INSERT INTO sensor_data (timestamp, thermal_value, light_value)
                VALUES (datetime('now', 'localtime'), ?, ?)
            ''', (thermal_value, light_value))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"插入数据错误: {e}")
            return False

    # 获取最近指定分钟的数据
    def get_recent_data(self, minutes=60):
        try:
            self.cursor.execute('''
                SELECT timestamp, thermal_value, light_value
                FROM sensor_data
                WHERE timestamp >= datetime('now', 'localtime', ?)
                ORDER BY timestamp
            ''', (f'-{minutes} minutes',))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"查询数据错误: {e}")
            return []

    # 清理指定分钟之前的旧数据
    def clean_old_data(self, minutes=60):
        try:
            self.cursor.execute('''
                DELETE FROM sensor_data
                WHERE timestamp < datetime('now', 'localtime', ?)
            ''', (f'-{minutes} minutes',))
            self.conn.commit()
            print(f"已清理 {self.cursor.rowcount} 条旧数据")
        except sqlite3.Error as e:
            print(f"清理数据错误: {e}")

    # 关闭数据库连接
    def close(self):
        if self.conn:
            self.conn.close()
            print("数据库连接已关闭")

# 串口管理类，负责串口通信
class SerialManager(QObject):

    # 定义信号
    data_received = pyqtSignal(int, int)  # 热敏值, 光敏值
    connection_status = pyqtSignal(bool, str)  # 连接状态, 消息

    # 初始化串口管理器
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.is_connected = False
        self.port_name = ""
        self.baud_rate = 115200  # 默认波特率
        self.read_timer = QTimer()
        self.read_timer.timeout.connect(self.read_data)
        self.read_interval = 100  # 读取间隔(ms)

    # 获取可用的串口列表
    def get_available_ports(self):
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports

    # 连接到指定串口
    def connect_port(self, port_name, baud_rate=115200):
        if self.is_connected:
            self.disconnect_port()
        
        try:
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1
            )
            self.is_connected = True
            self.port_name = port_name
            self.baud_rate = baud_rate
            self.read_timer.start(self.read_interval)
            self.connection_status.emit(True, f"已连接到 {port_name}")
            print(f"已连接到串口: {port_name}, 波特率: {baud_rate}")
            return True
        except serial.SerialException as e:
            self.is_connected = False
            self.connection_status.emit(False, f"连接失败: {str(e)}")
            print(f"串口连接错误: {e}")
            return False

    # 断开串口连接
    def disconnect_port(self):
        if self.is_connected and self.serial_port:
            self.read_timer.stop()
            self.serial_port.close()
            self.is_connected = False
            self.connection_status.emit(False, f"已断开连接")
            print("串口连接已断开")

    # 读取串口数据
    def read_data(self):
        if not self.is_connected or not self.serial_port:
            return
        
        try:
            if self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('utf-8').strip()
                if line:
                    self.parse_data(line)
        except serial.SerialException as e:
            print(f"读取串口数据错误: {e}")
            self.disconnect_port()

    # 解析传感器数据
    def parse_data(self, data_str):
        try:
            # 数据格式: 热敏状态,光照值
            parts = data_str.split(',')
            if len(parts) >= 2:
                thermal_value = int(parts[0])
                light_value = int(parts[1])
                self.data_received.emit(thermal_value, light_value)
                print(f"接收到数据: 热敏={thermal_value}, 光敏={light_value}")
        except (ValueError, IndexError) as e:
            print(f"数据解析错误: {e}, 原始数据: {data_str}")

# 模拟数据生成器类
class DataSimulator(QObject):

    # 定义信号
    data_generated = pyqtSignal(int, int)  # 热敏值, 光敏值

    # 初始化模拟数据生成器
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.generate_data)
        self.interval = 1000  # 生成间隔(ms)

    # 开始生成模拟数据
    def start(self):
        self.is_running = True
        self.timer.start(self.interval)
        print("模拟数据生成器已启动")

    # 停止生成模拟数据
    def stop(self):
        self.is_running = False
        self.timer.stop()
        print("模拟数据生成器已停止")

    # 生成随机模拟数据
    def generate_data(self):

        # 热敏传感器: 0或1，增加1出现的概率
        # 每5次数据中随机出现1-2次高温(1)，模拟温度变化
        thermal_value = 1 if random.random() < 0.3 else 0
        
        # 光敏传感器: 100-2000范围，使数值变化更明显
        # 使用正弦波模拟光照变化，更接近真实场景
        time_factor = time.time() % 60  # 60秒周期
        base_value = 1000 + 800 * math.sin(time_factor * math.pi / 30)
        variation = random.randint(-100, 100)  # 添加随机波动
        light_value = int(base_value + variation)
        light_value = max(100, min(2000, light_value))  # 确保在范围内
        
        self.data_generated.emit(thermal_value, light_value)
        print(f"生成模拟数据: 热敏={thermal_value}, 光敏={light_value}")

# 图表管理类，负责图表的创建和更新
class ChartManager:

    # 初始化图表管理器
    def __init__(self, thermal_chart_view, light_chart_view):
        self.thermal_chart_view = thermal_chart_view
        self.light_chart_view = light_chart_view
        
        # 设置图表视图的最小尺寸
        self.thermal_chart_view.setMinimumSize(800, 400)
        self.light_chart_view.setMinimumSize(800, 400)
        
        # 创建热敏传感器图表
        self.thermal_chart = QChart()
        self.thermal_chart.setTitle("热敏传感器数据")
        self.thermal_chart.setTitleFont(QFont("Arial", 12, QFont.Bold))
        self.thermal_chart.setAnimationOptions(QChart.NoAnimation)  # 禁用动画以提高响应速度
        self.thermal_chart.legend().setVisible(True)
        self.thermal_chart.legend().setAlignment(Qt.AlignBottom)
        self.thermal_chart.legend().setFont(QFont("Arial", 10))
        
        # 创建光敏传感器图表
        self.light_chart = QChart()
        self.light_chart.setTitle("光敏传感器数据")
        self.light_chart.setTitleFont(QFont("Arial", 12, QFont.Bold))
        self.light_chart.setAnimationOptions(QChart.NoAnimation)  # 禁用动画以提高响应速度
        self.light_chart.legend().setVisible(True)
        self.light_chart.legend().setAlignment(Qt.AlignBottom)
        self.light_chart.legend().setFont(QFont("Arial", 10))
        
        # 创建数据系列
        self.thermal_series = QLineSeries()
        self.thermal_series.setName("热敏状态")
        pen = self.thermal_series.pen()
        pen.setWidth(2)  # 加粗线条
        self.thermal_series.setPen(pen)
        
        self.light_series = QLineSeries()
        self.light_series.setName("光照值")
        pen = self.light_series.pen()
        pen.setWidth(2)  # 加粗线条
        self.light_series.setPen(pen)
        
        # 创建散点系列（用于显示当前值）
        self.thermal_scatter = QScatterSeries()
        self.thermal_scatter.setName("当前值")
        self.thermal_scatter.setMarkerSize(12)  # 增大标记点大小
        self.thermal_scatter.setColor(Qt.red)  # 设置标记点颜色
        
        self.light_scatter = QScatterSeries()
        self.light_scatter.setName("当前值")
        self.light_scatter.setMarkerSize(12)  # 增大标记点大小
        self.light_scatter.setColor(Qt.red)  # 设置标记点颜色
        
        # 添加系列到图表
        self.thermal_chart.addSeries(self.thermal_series)
        self.thermal_chart.addSeries(self.thermal_scatter)
        self.light_chart.addSeries(self.light_series)
        self.light_chart.addSeries(self.light_scatter)
        
        # 创建坐标轴
        self.setup_axes()
        
        # 设置图表视图
        self.thermal_chart_view.setChart(self.thermal_chart)
        self.thermal_chart_view.setRenderHint(QPainter.Antialiasing)
        self.light_chart_view.setChart(self.light_chart)
        self.light_chart_view.setRenderHint(QPainter.Antialiasing)

    # 设置图表坐标轴
    def setup_axes(self):

        # 创建时间轴
        self.thermal_time_axis = QDateTimeAxis()
        self.thermal_time_axis.setFormat("HH:mm:ss")
        self.thermal_time_axis.setTitleText("时间")
        self.thermal_time_axis.setTitleFont(QFont("Arial", 10, QFont.Bold))
        self.thermal_time_axis.setLabelsFont(QFont("Arial", 9))
        self.thermal_time_axis.setTickCount(10)  # 增加刻度数量
        self.thermal_time_axis.setGridLineVisible(True)  # 显示网格线
        
        self.light_time_axis = QDateTimeAxis()
        self.light_time_axis.setFormat("HH:mm:ss")
        self.light_time_axis.setTitleText("时间")
        self.light_time_axis.setTitleFont(QFont("Arial", 10, QFont.Bold))
        self.light_time_axis.setLabelsFont(QFont("Arial", 9))
        self.light_time_axis.setTickCount(10)  # 增加刻度数量
        self.light_time_axis.setGridLineVisible(True)  # 显示网格线
        
        # 创建值轴
        self.thermal_value_axis = QValueAxis()
        self.thermal_value_axis.setRange(0, 1.5)  # 热敏传感器y轴范围: 0-1.5，使变化更明显
        self.thermal_value_axis.setTitleText("状态 (0=正常, 1=高温)")
        self.thermal_value_axis.setTitleFont(QFont("Arial", 10, QFont.Bold))
        self.thermal_value_axis.setLabelsFont(QFont("Arial", 9))
        self.thermal_value_axis.setTickCount(3)  # 设置刻度数量
        self.thermal_value_axis.setMinorTickCount(1)  # 添加小刻度
        self.thermal_value_axis.setGridLineVisible(True)  # 显示网格线
        self.thermal_value_axis.setGridLineColor(QColor(200, 200, 200))  # 设置网格线颜色
        
        self.light_value_axis = QValueAxis()
        self.light_value_axis.setRange(100, 4000)  # 光敏传感器y轴范围: 100-4000
        self.light_value_axis.setTitleText("光照值")
        self.light_value_axis.setTitleFont(QFont("Arial", 10, QFont.Bold))
        self.light_value_axis.setLabelsFont(QFont("Arial", 9))
        self.light_value_axis.setTickCount(10)  # 增加刻度数量
        self.light_value_axis.setMinorTickCount(1)  # 添加小刻度
        self.light_value_axis.setGridLineVisible(True)  # 显示网格线
        self.light_value_axis.setGridLineColor(QColor(200, 200, 200))  # 设置网格线颜色
        
        # 添加坐标轴到图表
        self.thermal_chart.addAxis(self.thermal_time_axis, Qt.AlignBottom)
        self.thermal_chart.addAxis(self.thermal_value_axis, Qt.AlignLeft)
        self.thermal_series.attachAxis(self.thermal_time_axis)
        self.thermal_series.attachAxis(self.thermal_value_axis)
        self.thermal_scatter.attachAxis(self.thermal_time_axis)
        self.thermal_scatter.attachAxis(self.thermal_value_axis)
        
        self.light_chart.addAxis(self.light_time_axis, Qt.AlignBottom)
        self.light_chart.addAxis(self.light_value_axis, Qt.AlignLeft)
        self.light_series.attachAxis(self.light_time_axis)
        self.light_series.attachAxis(self.light_value_axis)
        self.light_scatter.attachAxis(self.light_time_axis)
        self.light_scatter.attachAxis(self.light_value_axis)

    # 更新图表的时间范围，默认显示最近10分钟的数据，这样变化会更加明显
    def update_time_range(self, minutes=10):
        now = QDateTime.currentDateTime()
        start_time = now.addSecs(-minutes * 60)
        
        self.thermal_time_axis.setRange(start_time, now)
        self.light_time_axis.setRange(start_time, now)
        
        # 限制数据点数量，防止内存占用过大和图表过于拥挤
        self._limit_data_points(start_time.toMSecsSinceEpoch())

    # 限制数据点数量，删除时间范围外的点
    def _limit_data_points(self, min_timestamp_ms):

        # 删除时间范围外的点
        points_to_remove = 0
        for i in range(self.thermal_series.count()):
            if self.thermal_series.at(i).x() < min_timestamp_ms:
                points_to_remove += 1
            else:
                break
        
        if points_to_remove > 0:
            # 创建新的点列表，不包含要删除的点
            new_thermal_points = []
            for i in range(points_to_remove, self.thermal_series.count()):
                new_thermal_points.append(self.thermal_series.at(i))
            
            self.thermal_series.clear()
            self.thermal_series.append(new_thermal_points)
        
        # 对光敏传感器数据执行相同操作
        points_to_remove = 0
        for i in range(self.light_series.count()):
            if self.light_series.at(i).x() < min_timestamp_ms:
                points_to_remove += 1
            else:
                break
        
        if points_to_remove > 0:
            new_light_points = []
            for i in range(points_to_remove, self.light_series.count()):
                new_light_points.append(self.light_series.at(i))
            
            self.light_series.clear()
            self.light_series.append(new_light_points)

    # 添加数据点到图表
    def add_data_point(self, thermal_value, light_value):
        now = QDateTime.currentDateTime()
        timestamp_ms = now.toMSecsSinceEpoch()
        
        # 添加到折线图
        self.thermal_series.append(timestamp_ms, thermal_value)
        self.light_series.append(timestamp_ms, light_value)
        
        # 更新散点图（当前值），根据热敏值设置不同颜色
        self.thermal_scatter.clear()
        self.thermal_scatter.append(timestamp_ms, thermal_value)
        
        # 根据热敏值设置不同的颜色
        if thermal_value == 1:
            # 高温状态 - 红色
            self.thermal_scatter.setColor(Qt.red)
            self.thermal_scatter.setMarkerSize(15)  # 增大高温点的大小
        else:
            # 正常状态 - 绿色
            self.thermal_scatter.setColor(Qt.green)
            self.thermal_scatter.setMarkerSize(12)
        
        self.light_scatter.clear()
        self.light_scatter.append(timestamp_ms, light_value)
        
        # 更新时间范围 - 显示最近10分钟的数据，使变化更明显
        self.update_time_range(10)
        
        # 强制图表更新
        self.thermal_chart_view.update()
        self.light_chart_view.update()

    # 加载历史数据到图表
    def load_historical_data(self, data_list):
        self.thermal_series.clear()
        self.light_series.clear()
        
        # 创建两个不同的散点系列，分别用于正常温度和高温状态
        normal_points = []
        high_temp_points = []
        
        for timestamp_str, thermal_value, light_value in data_list:
            # 将SQLite时间戳字符串转换为QDateTime
            dt = QDateTime.fromString(timestamp_str, "yyyy-MM-dd HH:mm:ss")
            timestamp_ms = dt.toMSecsSinceEpoch()
            
            # 根据温度状态添加到不同的点集合
            if thermal_value == 1:
                high_temp_points.append(QPointF(timestamp_ms, thermal_value))
            else:
                normal_points.append(QPointF(timestamp_ms, thermal_value))
            
            # 添加到折线图
            self.thermal_series.append(timestamp_ms, thermal_value)
            self.light_series.append(timestamp_ms, light_value)
        
        # 如果有数据，更新散点图显示最后一个点
        if data_list:
            last_timestamp_str, last_thermal, last_light = data_list[-1]
            last_dt = QDateTime.fromString(last_timestamp_str, "yyyy-MM-dd HH:mm:ss")
            last_timestamp_ms = last_dt.toMSecsSinceEpoch()
            
            # 根据最后一个点的温度状态设置散点颜色和大小
            self.thermal_scatter.clear()
            self.thermal_scatter.append(last_timestamp_ms, last_thermal)
            
            if last_thermal == 1:
                self.thermal_scatter.setColor(Qt.red)
                self.thermal_scatter.setMarkerSize(15)
            else:
                self.thermal_scatter.setColor(Qt.green)
                self.thermal_scatter.setMarkerSize(12)
            
            self.light_scatter.clear()
            self.light_scatter.append(last_timestamp_ms, last_light)
        
        # 更新时间范围
        self.update_time_range()

# 主窗口类，负责UI和应用程序逻辑
class MainWindow(QMainWindow):

    # 初始化主窗口
    def __init__(self):
        super().__init__()
        
        # 设置窗口属性
        self.setWindowTitle("传感器数据可视化")
        self.resize(1200, 800)
        
        # 创建组件
        self.setup_ui()
        
        # 创建管理器
        self.db_manager = DatabaseManager()
        self.serial_manager = SerialManager()
        self.data_simulator = DataSimulator()
        self.chart_manager = ChartManager(self.thermal_chart_view, self.light_chart_view)
        
        # 连接信号和槽
        self.connect_signals_slots()
        
        # 初始化串口列表
        self.refresh_port_list()
        
        # 初始化定时器
        self.clean_timer = QTimer()
        self.clean_timer.timeout.connect(self.clean_old_data)
        self.clean_timer.start(60000)  # 每分钟清理一次旧数据
        
        # 加载历史数据
        self.load_historical_data()
        
        # 默认选择实际硬件模式
        self.hardware_radio.setChecked(True)
        self.on_mode_changed()
        
        print("应用程序初始化完成")

    # 设置用户界面
    def setup_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建顶部控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # 创建串口配置组
        serial_group = QGroupBox("串口配置")
        serial_layout = QGridLayout(serial_group)
        
        self.port_label = QLabel("串口:")
        self.port_combo = QComboBox()
        self.refresh_button = QPushButton("刷新")
        self.baud_label = QLabel("波特率:")
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")  # 默认波特率
        self.connect_button = QPushButton("连接")
        
        serial_layout.addWidget(self.port_label, 0, 0)
        serial_layout.addWidget(self.port_combo, 0, 1)
        serial_layout.addWidget(self.refresh_button, 0, 2)
        serial_layout.addWidget(self.baud_label, 1, 0)
        serial_layout.addWidget(self.baud_combo, 1, 1)
        serial_layout.addWidget(self.connect_button, 1, 2)
        
        # 创建模式选择组
        mode_group = QGroupBox("工作模式")
        mode_layout = QVBoxLayout(mode_group)
        
        self.hardware_radio = QRadioButton("实际硬件")
        self.simulation_radio = QRadioButton("模拟数据")
        
        mode_layout.addWidget(self.hardware_radio)
        mode_layout.addWidget(self.simulation_radio)
        
        # 创建状态显示组
        status_group = QGroupBox("当前状态")
        status_layout = QGridLayout(status_group)
        
        self.thermal_label = QLabel("热敏状态:")
        self.thermal_value = QLabel("--")
        self.thermal_value.setFont(QFont("Arial", 16, QFont.Bold))
        self.light_label = QLabel("光照值:")
        self.light_value = QLabel("--")
        self.light_value.setFont(QFont("Arial", 16, QFont.Bold))
        self.status_label = QLabel("状态:")
        self.status_value = QLabel("未连接")
        
        status_layout.addWidget(self.thermal_label, 0, 0)
        status_layout.addWidget(self.thermal_value, 0, 1)
        status_layout.addWidget(self.light_label, 1, 0)
        status_layout.addWidget(self.light_value, 1, 1)
        status_layout.addWidget(self.status_label, 2, 0)
        status_layout.addWidget(self.status_value, 2, 1)
        
        # 添加控制面板组件
        control_layout.addWidget(serial_group)
        control_layout.addWidget(mode_group)
        control_layout.addWidget(status_group)
        
        # 创建图表视图
        chart_splitter = QSplitter(Qt.Vertical)
        
        # 热敏传感器图表视图
        self.thermal_chart_view = QChartView()
        self.thermal_chart_view.setMinimumHeight(350)  # 增加高度
        self.thermal_chart_view.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        self.thermal_chart_view.setRubberBand(QChartView.RectangleRubberBand)  # 允许矩形选择缩放
        
        # 光敏传感器图表视图
        self.light_chart_view = QChartView()
        self.light_chart_view.setMinimumHeight(350)  # 增加高度
        self.light_chart_view.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        self.light_chart_view.setRubberBand(QChartView.RectangleRubberBand)  # 允许矩形选择缩放
        
        chart_splitter.addWidget(self.thermal_chart_view)
        chart_splitter.addWidget(self.light_chart_view)
        
        # 设置分割比例
        chart_splitter.setSizes([500, 500])  # 平均分配空间
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(chart_splitter, 1)  # 图表占据更多空间

    # 连接信号和槽
    def connect_signals_slots(self):
        # 串口管理
        self.refresh_button.clicked.connect(self.refresh_port_list)
        self.connect_button.clicked.connect(self.toggle_connection)
        
        # 模式切换
        self.hardware_radio.toggled.connect(self.on_mode_changed)
        self.simulation_radio.toggled.connect(self.on_mode_changed)
        
        # 数据接收
        self.serial_manager.data_received.connect(self.on_data_received)
        self.serial_manager.connection_status.connect(self.on_connection_status_changed)
        self.data_simulator.data_generated.connect(self.on_data_received)

    # 刷新可用串口列表
    def refresh_port_list(self):
        self.port_combo.clear()
        ports = self.serial_manager.get_available_ports()
        if ports:
            self.port_combo.addItems(ports)
            self.connect_button.setEnabled(True)
        else:
            self.port_combo.addItem("无可用串口")
            self.connect_button.setEnabled(False)

    # 切换串口连接状态
    def toggle_connection(self):
        if self.serial_manager.is_connected:
            self.serial_manager.disconnect_port()
            self.connect_button.setText("连接")
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.refresh_button.setEnabled(True)
            
            # 如果是模拟模式，停止模拟数据生成
            if self.simulation_radio.isChecked():
                self.data_simulator.stop()
        else:
            port = self.port_combo.currentText()
            baud = int(self.baud_combo.currentText())
            
            if self.serial_manager.connect_port(port, baud):
                self.connect_button.setText("断开")
                self.port_combo.setEnabled(False)
                self.baud_combo.setEnabled(False)
                self.refresh_button.setEnabled(False)
                
                # 如果是模拟模式，启动模拟数据生成
                if self.simulation_radio.isChecked():
                    self.data_simulator.start()

    # 处理工作模式变化
    def on_mode_changed(self):
        if self.hardware_radio.isChecked():
            print("切换到实际硬件模式")
            self.data_simulator.stop()
        else:
            print("切换到模拟数据模式")
            if self.serial_manager.is_connected:
                self.data_simulator.start()

    # 处理接收到的数据
    def on_data_received(self, thermal_value, light_value):

        # 更新UI显示，根据热敏值设置不同的颜色
        self.thermal_value.setText(str(thermal_value))
        if thermal_value == 1:
            self.thermal_value.setStyleSheet("color: red; font-weight: bold;")
            self.thermal_value.setText("1 (高温)")
        else:
            self.thermal_value.setStyleSheet("color: green; font-weight: bold;")
            self.thermal_value.setText("0 (正常)")
        
        self.light_value.setText(str(light_value))
        
        # 添加到图表
        self.chart_manager.add_data_point(thermal_value, light_value)
        
        # 存储到数据库
        self.db_manager.insert_data(thermal_value, light_value)

    # 处理连接状态变化
    def on_connection_status_changed(self, connected, message):
        self.status_value.setText(message)

    # 加载历史数据
    def load_historical_data(self):
        data = self.db_manager.get_recent_data(60)  # 获取最近60分钟的数据
        self.chart_manager.load_historical_data(data)

    # 清理旧数据
    def clean_old_data(self):
        self.db_manager.clean_old_data(60)  # 清理60分钟前的数据

    # 窗口关闭事件处理
    def closeEvent(self, event):

        # 断开串口连接
        if self.serial_manager.is_connected:
            self.serial_manager.disconnect_port()

        # 停止模拟数据生成
        self.data_simulator.stop()
        
        # 关闭数据库连接
        self.db_manager.close()
        
        # 接受关闭事件
        event.accept()

# 主函数
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()