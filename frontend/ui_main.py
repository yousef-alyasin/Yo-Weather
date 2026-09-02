import math
import random
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QLinearGradient, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QLabel, QFrame, QScrollArea, QGraphicsDropShadowEffect
)


class WeatherParticleCanvas(QWidget):
    """Background widget that draws moving particles (rain, snow, stars)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.particles = []
        self.weather_type = "clear"

        # Frame timer (~40 fps)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_particles)
        self.anim_timer.start(25)

    def set_weather_mode(self, weather_type: str):
        """Reinitialize particles for new weather condition or time"""
        self.weather_type = weather_type.lower()
        self.particles.clear()
        w = max(self.width(), 800)
        h = max(self.height(), 600)

        count = 70 if "rain" in self.weather_type or "drizzle" in self.weather_type else 45
        for _ in range(count):
            self.particles.append({
                "x": random.uniform(0, w),
                "y": random.uniform(0, h),
                "speed": random.uniform(5, 12) if "rain" in self.weather_type else random.uniform(1, 3),
                "size": random.uniform(1.5, 3.5),
                "alpha": random.randint(70, 180),
                "angle": random.uniform(-0.15, 0.15)
            })
        self.update()

    def update_particles(self):
        """Update particle coordinates each frame"""
        if not self.particles:
            return
        w = self.width()
        h = self.height()

        for p in self.particles:
            if "rain" in self.weather_type or "drizzle" in self.weather_type:
                p["y"] += p["speed"]
                p["x"] += p["speed"] * 0.15
                if p["y"] > h:
                    p["y"] = -10
                    p["x"] = random.uniform(0, w)
            elif "snow" in self.weather_type:
                p["y"] += p["speed"] * 0.6
                p["x"] += math.sin(p["y"] * 0.05) * 1.2
                if p["y"] > h:
                    p["y"] = -10
                    p["x"] = random.uniform(0, w)
            else:
                # Slight twinkle for night sky
                p["alpha"] += random.choice([-2, 2])
                p["alpha"] = max(40, min(160, p["alpha"]))

        self.update()

    def paintEvent(self, event):
        """Draw particles on widget canvas"""
        if not self.particles:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for p in self.particles:
            if "rain" in self.weather_type or "drizzle" in self.weather_type:
                pen = QPen(QColor(180, 220, 255, p["alpha"]), p["size"] * 0.6)
                painter.setPen(pen)
                painter.drawLine(int(p["x"]), int(p["y"]), int(p["x"] + 2), int(p["y"] + 8 + p["speed"]))
            elif "snow" in self.weather_type:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(240, 248, 255, p["alpha"]))
                painter.drawEllipse(int(p["x"]), int(p["y"]), int(p["size"]), int(p["size"]))
            else:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(255, 255, 200, p["alpha"]))
                painter.drawEllipse(int(p["x"]), int(p["y"]), int(p["size"] * 0.8), int(p["size"] * 0.8))


class SunArcWidget(QWidget):
    """Custom widget to draw sun position trajectory arc"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self.progress = 0.5

    def set_progress(self, progress: float):
        self.progress = max(0.0, min(1.0, progress))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        padding = 16
        rect_w = w - 2 * padding
        rect_h = (h - 6) * 2

        # Draw dotted trajectory arc
        pen = QPen(QColor(255, 200, 50, 90), 2, Qt.DashLine)
        painter.setPen(pen)
        painter.drawArc(padding, 6, rect_w, rect_h, 0 * 16, 180 * 16)

        # Calculate sun position along the arc
        angle_rad = math.pi * (1.0 - self.progress)
        cx = padding + rect_w / 2.0
        cy = 6 + rect_h / 2.0
        rx = rect_w / 2.0
        ry = rect_h / 2.0

        sun_x = cx + rx * math.cos(angle_rad)
        sun_y = cy - ry * math.sin(angle_rad)

        # Draw sun glow and center circle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 215, 0, 80))
        painter.drawEllipse(int(sun_x - 7), int(sun_y - 7), 14, 14)

        painter.setBrush(QColor(255, 223, 0))
        painter.drawEllipse(int(sun_x - 4), int(sun_y - 4), 8, 8)


class SunTrackerCard(QFrame):
    """Card containing sunrise, sunset, and sun progression widget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(120)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        top_layout = QHBoxLayout()
        self.title_lbl = QLabel("☀️ Sun & Daylight")
        self.title_lbl.setObjectName("statTitle")
        self.status_lbl = QLabel("--")
        self.status_lbl.setObjectName("statSub")
        top_layout.addWidget(self.title_lbl)
        top_layout.addStretch()
        top_layout.addWidget(self.status_lbl)

        self.sun_arc = SunArcWidget()

        bot_layout = QHBoxLayout()
        self.sunrise_lbl = QLabel("🌅 --:--")
        self.sunrise_lbl.setObjectName("statSub")
        self.sunset_lbl = QLabel("🌇 --:--")
        self.sunset_lbl.setObjectName("statSub")
        bot_layout.addWidget(self.sunrise_lbl)
        bot_layout.addStretch()
        bot_layout.addWidget(self.sunset_lbl)

        layout.addLayout(top_layout)
        layout.addWidget(self.sun_arc)
        layout.addLayout(bot_layout)

    def update_info(self, sun_data: dict):
        self.sunrise_lbl.setText(f"🌅 {sun_data.get('sunrise', '--')}")
        self.sunset_lbl.setText(f"🌇 {sun_data.get('sunset', '--')}")
        self.status_lbl.setText(sun_data.get('status', ''))
        self.sun_arc.set_progress(sun_data.get('progress', 0.5))


class StatCard(QFrame):
    """Reusable card for single metrics (wind, humidity, etc.)"""
    def __init__(self, icon: str, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(120)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        top_layout = QHBoxLayout()
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setObjectName("statIcon")
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("statTitle")
        top_layout.addWidget(self.icon_lbl)
        top_layout.addWidget(self.title_lbl)
        top_layout.addStretch()

        self.val_lbl = QLabel("--")
        self.val_lbl.setObjectName("statValue")
        self.sub_lbl = QLabel("--")
        self.sub_lbl.setObjectName("statSub")

        layout.addLayout(top_layout)
        layout.addWidget(self.val_lbl)
        layout.addWidget(self.sub_lbl)

    def update_info(self, value: str, subtext: str = ""):
        self.val_lbl.setText(value)
        self.sub_lbl.setText(subtext)


class HourlyItem(QFrame):
    """Individual clickable forecast hour widget"""
    clicked = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hourlyItem")
        self.setFixedWidth(85)
        self.setFixedHeight(130)
        self.setCursor(Qt.PointingHandCursor)
        self.hour_data = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self.time_lbl = QLabel("--")
        self.time_lbl.setObjectName("hourTime")
        self.icon_lbl = QLabel("☀️")
        self.icon_lbl.setObjectName("hourIcon")
        self.temp_lbl = QLabel("--°")
        self.temp_lbl.setObjectName("hourTemp")
        self.rain_lbl = QLabel("💧 0%")
        self.rain_lbl.setObjectName("hourRain")

        layout.addWidget(self.time_lbl)
        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.temp_lbl)
        layout.addWidget(self.rain_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.hour_data:
            self.clicked.emit(self.hour_data)
        super().mousePressEvent(event)

    def set_data(self, data: dict, is_celsius: bool = True):
        self.hour_data = data
        self.time_lbl.setText(data.get("time", "--"))
        self.icon_lbl.setText(data.get("icon", "☀️"))
        t = data.get("temp", 0) if is_celsius else round(data.get("temp", 0) * 9/5 + 32)
        self.temp_lbl.setText(f"{t}°")
        self.rain_lbl.setText(f"💧 {data.get('rain_prob', 0)}%")


class DailyRow(QFrame):
    """Single row showing one day from the 7-day forecast"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dailyRow")
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self.day_lbl = QLabel("--")
        self.day_lbl.setObjectName("dailyDay")
        self.day_lbl.setFixedWidth(50)

        self.rain_lbl = QLabel("💧 0%")
        self.rain_lbl.setObjectName("dailyRain")
        self.rain_lbl.setFixedWidth(60)

        self.icon_lbl = QLabel("☀️")
        self.icon_lbl.setObjectName("dailyIcon")
        self.icon_lbl.setFixedWidth(30)

        self.cond_lbl = QLabel("--")
        self.cond_lbl.setObjectName("dailyCond")

        self.temp_lbl = QLabel("--° / --°")
        self.temp_lbl.setObjectName("dailyTemp")
        self.temp_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self.day_lbl)
        layout.addWidget(self.rain_lbl)
        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.cond_lbl)
        layout.addStretch()
        layout.addWidget(self.temp_lbl)

    def set_data(self, data: dict, is_celsius: bool = True):
        self.day_lbl.setText(data.get("day", "--"))
        self.rain_lbl.setText(f"💧 {data.get('rain_prob', 0)}%")
        self.icon_lbl.setText(data.get("icon", "☀️"))
        self.cond_lbl.setText(data.get("condition", "--"))
        max_t = data.get("max_temp", 0) if is_celsius else round(data.get("max_temp", 0) * 9/5 + 32)
        min_t = data.get("min_temp", 0) if is_celsius else round(data.get("min_temp", 0) * 9/5 + 32)
        self.temp_lbl.setText(f"{max_t}°  {min_t}°")


class SmoothTempChart(QWidget):
    """Temperature spline curve with rain probability bars"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(95)
        self.temperatures = []
        self.rain_probs = []

    def set_data(self, temps: list, rain_probs: list = None):
        self.temperatures = temps
        self.rain_probs = rain_probs or [0] * len(temps)
        self.update()

    def paintEvent(self, event):
        if len(self.temperatures) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        padding_x = 42
        padding_y = 18

        min_t = min(self.temperatures)
        max_t = max(self.temperatures)
        t_range = max((max_t - min_t), 1)

        points = []
        step_x = (w - 2 * padding_x) / (len(self.temperatures) - 1)

        # Draw rain bars
        bar_w = 12
        for i, prob in enumerate(self.rain_probs):
            x = padding_x + i * step_x
            if prob > 0:
                bar_h = max(4, int((prob / 100.0) * (h * 0.42)))
                bar_y = h - bar_h - 2
                grad_bar = QLinearGradient(x, bar_y, x, h)
                grad_bar.setColorAt(0, QColor(0, 195, 255, 170))
                grad_bar.setColorAt(1, QColor(0, 110, 255, 40))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(grad_bar))
                painter.drawRoundedRect(int(x - bar_w / 2), int(bar_y), int(bar_w), int(bar_h), 3, 3)

        # Calculate smooth temperature path
        for i, temp in enumerate(self.temperatures):
            x = padding_x + i * step_x
            y = h - padding_y - ((temp - min_t) / t_range) * (h - 2 * padding_y - 8)
            points.append((x, y))

        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        for i in range(len(points) - 1):
            p0 = points[i]
            p1 = points[i + 1]
            ctrl_x1 = p0[0] + (p1[0] - p0[0]) / 2.0
            ctrl_y1 = p0[1]
            ctrl_x2 = p0[0] + (p1[0] - p0[0]) / 2.0
            ctrl_y2 = p1[1]
            path.cubicTo(ctrl_x1, ctrl_y1, ctrl_x2, ctrl_y2, p1[0], p1[1])

        # Fill below curve
        fill_path = QPainterPath(path)
        fill_path.lineTo(points[-1][0], h)
        fill_path.lineTo(points[0][0], h)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(0, 210, 255, 55))
        grad.setColorAt(1, QColor(0, 210, 255, 0))
        painter.fillPath(fill_path, grad)

        # Draw line & data points
        pen = QPen(QColor(0, 210, 255), 2.5)
        painter.setPen(pen)
        painter.drawPath(path)

        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 210, 255), 2))
        for x, y in points:
            painter.drawEllipse(int(x - 3), int(y - 3), 6, 6)


class WeatherUI:
    """Builds and lays out the entire interface"""
    def setup_ui(self, main_window):
        self.main_window = main_window
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        main_window.setCentralWidget(self.central_widget)

        # Background particle layer
        self.particle_layer = WeatherParticleCanvas(self.central_widget)
        self.particle_layer.lower()

        root_layout = QVBoxLayout(self.central_widget)
        root_layout.setContentsMargins(24, 18, 24, 18)
        root_layout.setSpacing(12)

        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.city_input = QLineEdit()
        self.city_input.setObjectName("searchInput")
        self.city_input.setPlaceholderText("🔍 ابحث عن أي مدينة أو دولة في العالم... (اضغط / للبحث)")
        self.city_input.setClearButtonEnabled(True)

        self.loc_btn = QPushButton("📍")
        self.loc_btn.setObjectName("toolBtn")
        self.loc_btn.setToolTip("تحديد موقعي التلقائي (Auto-Detect)")

        self.fav_btn = QPushButton("⭐")
        self.fav_btn.setObjectName("toolBtn")
        self.fav_btn.setToolTip("إضافة/إزالة من المفضلة")

        self.compare_btn = QPushButton("⚖️")
        self.compare_btn.setObjectName("toolBtn")
        self.compare_btn.setToolTip("مقارنة الطقس بين مدينتين (Dual Compare)")

        self.unit_btn = QPushButton("°C")
        self.unit_btn.setObjectName("unitToggleBtn")
        self.unit_btn.setToolTip("التبديل بين مئوي وفهرنهايت")

        top_bar.addWidget(self.city_input, stretch=1)
        top_bar.addWidget(self.loc_btn)
        top_bar.addWidget(self.fav_btn)
        top_bar.addWidget(self.compare_btn)
        top_bar.addWidget(self.unit_btn)
        root_layout.addLayout(top_bar)

        # Favorites Chips + Smart Advice
        sub_bar = QHBoxLayout()
        self.fav_chips_layout = QHBoxLayout()
        self.fav_chips_layout.setSpacing(6)
        self.fav_chips_layout.setAlignment(Qt.AlignLeft)

        self.smart_advice_lbl = QLabel("💡 جاري قراءة التوصيات اليومية...")
        self.smart_advice_lbl.setObjectName("smartAdviceLabel")
        self.smart_advice_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        sub_bar.addLayout(self.fav_chips_layout)
        sub_bar.addStretch()
        sub_bar.addWidget(self.smart_advice_lbl)
        root_layout.addLayout(sub_bar)

        # Content Grid
        content_grid = QGridLayout()
        content_grid.setHorizontalSpacing(16)
        content_grid.setVerticalSpacing(16)

        # Hero Card
        self.hero_card = QFrame()
        self.hero_card.setObjectName("mainCard")
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setAlignment(Qt.AlignCenter)

        self.city_lbl = QLabel("--")
        self.city_lbl.setObjectName("mainCity")
        self.temp_lbl = QLabel("--")
        self.temp_lbl.setObjectName("mainTemp")

        self.min_max_lbl = QLabel("↑ --° / ↓ --°")
        self.min_max_lbl.setObjectName("mainSub")
        self.feels_lbl = QLabel("Feels like --°")
        self.feels_lbl.setObjectName("mainSub")
        self.time_lbl = QLabel("--")
        self.time_lbl.setObjectName("mainTime")
        self.hero_icon = QLabel("☀️")
        self.hero_icon.setObjectName("mainWeatherIcon")
        self.cond_lbl = QLabel("--")
        self.cond_lbl.setObjectName("mainCondition")

        hero_layout.addWidget(self.city_lbl)
        hero_layout.addWidget(self.temp_lbl)
        hero_layout.addWidget(self.min_max_lbl)
        hero_layout.addWidget(self.feels_lbl)
        hero_layout.addWidget(self.time_lbl)
        hero_layout.addWidget(self.hero_icon)
        hero_layout.addWidget(self.cond_lbl)

        # Stats Column
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(10)

        self.wind_card = StatCard("💨", "Wind Speed")
        self.humidity_card = StatCard("💧", "Humidity")
        self.sun_card = SunTrackerCard()

        stats_layout.addWidget(self.wind_card)
        stats_layout.addWidget(self.humidity_card)
        stats_layout.addWidget(self.sun_card)

        # 7-Day Forecast Column
        self.daily_card = QFrame()
        self.daily_card.setObjectName("card")
        daily_layout = QVBoxLayout(self.daily_card)
        daily_layout.setContentsMargins(12, 10, 12, 10)
        daily_layout.setSpacing(4)

        self.daily_rows = []
        for _ in range(7):
            row = DailyRow()
            self.daily_rows.append(row)
            daily_layout.addWidget(row)

        content_grid.addWidget(self.hero_card, 0, 0, 1, 1)
        content_grid.addLayout(stats_layout, 0, 1, 1, 1)
        content_grid.addWidget(self.daily_card, 0, 2, 1, 1)

        content_grid.setColumnStretch(0, 3)
        content_grid.setColumnStretch(1, 3)
        content_grid.setColumnStretch(2, 4)
        root_layout.addLayout(content_grid, stretch=1)

        # Bottom Frame (Chart + Hourly List)
        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottomFrame")
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(14, 8, 14, 8)
        bottom_layout.setSpacing(4)

        self.chart_view = SmoothTempChart()
        bottom_layout.addWidget(self.chart_view)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(135)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_widget = QWidget()
        self.hourly_layout = QHBoxLayout(scroll_widget)
        self.hourly_layout.setContentsMargins(0, 0, 0, 0)
        self.hourly_layout.setSpacing(10)

        self.hourly_items = []
        for _ in range(8):
            item = HourlyItem()
            self.hourly_items.append(item)
            self.hourly_layout.addWidget(item)

        scroll.setWidget(scroll_widget)
        bottom_layout.addWidget(scroll)
        root_layout.addWidget(bottom_frame)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("statusLabel")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(self.status_lbl)