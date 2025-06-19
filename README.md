# 基于Qt上位机的数据可视化应用

## 项目简介
这是一个基于PyQt5开发的上位机数据可视化应用程序，用于实时显示和记录传感器数据。该应用程序可以通过串口接收传感器数据，并将数据以图表形式直观展示，同时将数据存储到本地数据库中以便后续分析。

### 主要功能
- 实时接收并显示热敏传感器和光敏传感器数据
- 以折线图形式可视化传感器数据变化趋势
- 支持实际硬件模式和模拟数据模式
- 数据自动存储到SQLite数据库
- 自动清理过期数据，优化存储空间

## 安装说明

### 依赖项
- Python 3.8+
- PyQt5
- PyQtChart
- pyserial
- sqlite3 (Python标准库)

### 安装步骤
1. 克隆仓库到本地
```bash
git clone https://github.com/Barton-2021/My-QT-python.git
cd My-QT-python
```

2. 创建并激活虚拟环境（可选但推荐）
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

3. 安装依赖项
```bash
pip install PyQt5 PyQtChart pyserial
```

## 使用方法

### 运行应用程序
```bash
python main.py
```

### 连接硬件
1. 将传感器设备通过USB连接到计算机
2. 在应用程序中选择正确的串口和波特率
3. 点击"连接"按钮建立连接
4. 连接成功后，应用程序将自动开始接收和显示数据

### 使用模拟模式
如果没有实际硬件设备，可以使用模拟模式：
1. 选择"模拟数据"单选按钮
2. 点击"连接"按钮启动模拟数据生成
3. 应用程序将生成随机模拟数据并显示

## 项目结构
- `main.py`: 主程序文件
- `sensor_data.db`: SQLite数据库文件，用于存储传感器数据

## 开发者信息
- 开发者：陈工
- 开发团队：广州智尘梦科技工作室
- 版本：1.0.0

## 许可证
本项目使用MIT许可证，详情请参阅LICENSE文件。