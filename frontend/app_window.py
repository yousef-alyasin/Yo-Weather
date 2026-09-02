import os
import sys
import json
from PySide6.QtCore import QStringListModel, QPropertyAnimation, QEasingCurve, QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QDialog, QCompleter, QGraphicsOpacityEffect,
    QPushButton, QLineEdit, QSystemTrayIcon, QStyle, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame
)

from ui_main import WeatherUI
from workers import FetchWeatherWorker, GlobalSearchWorker, AutoLocationWorker


def get_resource_path(relative_path: str) -> str:
    """البحث الشامل عن الملفات داخل بيئة الـ EXE أو بيئة التطوير"""
    # 1. فحص مسار الحزمة المؤقتة لـ PyInstaller
    if hasattr(sys, '_MEIPASS'):
        bundle_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(bundle_path):
            return bundle_path
        # تجربة البحث باسم الملف مباشرة داخل الجذر المؤقت
        base_name = os.path.basename(relative_path)
        flat_path = os.path.join(sys._MEIPASS, base_name)
        if os.path.exists(flat_path):
            return flat_path

    # 2. فحص مسار مجلد المشروع الأساسي أثناء التطوير
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dev_path = os.path.join(base_dir, relative_path)
    if os.path.exists(dev_path):
        return dev_path

    # 3. فحص مجلد frontend الحالي
    curr_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(relative_path))
    if os.path.exists(curr_dir_path):
        return curr_dir_path

    return relative_path


SETTINGS_FILE = "settings.json"


class SettingsManager:
    """Load and save user preferences to local JSON file"""
    @staticmethod
    def load_settings() -> dict:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print("Error loading settings:", e)
        return {"last_city": "Amman", "favorites": ["عمان", "السلط", "دبي", "London"]}

    @staticmethod
    def save_settings(data: dict):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print("Error saving settings:", e)


class CompareDialog(QDialog):
    """Side-by-side weather comparison dialog"""
    def __init__(self, current_data: dict, is_celsius: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مقارنة الطقس بين مدينتين")
        self.resize(650, 380)
        self.is_celsius = is_celsius

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        search_bar = QHBoxLayout()
        self.compare_input = QLineEdit()
        self.compare_input.setObjectName("searchInput")
        self.compare_input.setPlaceholderText("أدخل المدينة للمقارنة (مثال: دبي، لندن، السلط)...")
        self.compare_btn = QPushButton("مقارنة")
        self.compare_btn.setObjectName("toolBtn")
        search_bar.addWidget(self.compare_input, stretch=1)
        search_bar.addWidget(self.compare_btn)
        layout.addLayout(search_bar)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.left_card = self.create_city_card(current_data)
        self.right_card = self.create_empty_card("أدخل مدينة في الأعلى للمقارنة")

        cards_layout.addWidget(self.left_card)
        cards_layout.addWidget(self.right_card)
        layout.addLayout(cards_layout)

        self.compare_btn.clicked.connect(self.do_compare)
        self.compare_input.returnPressed.connect(self.do_compare)
        self.worker = None

    def create_city_card(self, data: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("mainCard")
        l = QVBoxLayout(card)
        l.setAlignment(Qt.AlignCenter)
        l.setSpacing(6)

        c_name = QLabel(data.get("city", "--"))
        c_name.setObjectName("mainCity")
        t = data.get("temp", 0) if self.is_celsius else round(data.get("temp", 0) * 9/5 + 32)
        c_temp = QLabel(f"{t}°")
        c_temp.setObjectName("mainTemp")
        c_cond = QLabel(f"{data.get('icon', '☀️')} {data.get('condition', '--')}")
        c_cond.setObjectName("mainCondition")

        c_details = QLabel(f"الرياح: {data.get('wind', 0)} km/h | الرطوبة: {data.get('humidity', 0)}%")
        c_details.setObjectName("mainSub")

        l.addWidget(c_name)
        l.addWidget(c_temp)
        l.addWidget(c_cond)
        l.addWidget(c_details)
        return card

    def create_empty_card(self, msg: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        l = QVBoxLayout(card)
        l.setAlignment(Qt.AlignCenter)
        lbl = QLabel(msg)
        lbl.setObjectName("mainSub")
        l.addWidget(lbl)
        return card

    def do_compare(self):
        city = self.compare_input.text().strip()
        if not city:
            return
        self.worker = FetchWeatherWorker(city, parent=self)
        self.worker.data_received.connect(self.on_second_data)
        self.worker.start()

    def on_second_data(self, data: dict):
        new_card = self.create_city_card(data)
        parent_layout = self.layout().itemAt(1).layout()
        parent_layout.replaceWidget(self.right_card, new_card)
        self.right_card.deleteLater()
        self.right_card = new_card


class WeatherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Weather Dashboard")
        self.resize(1120, 750)
        self.setMinimumSize(960, 640)

        self.worker = None
        self.search_worker = None
        self.loc_worker = None

        self.is_celsius = True
        self.current_data = {}
        self.geo_results = {}

        self.settings = SettingsManager.load_settings()

        self.ui = WeatherUI()
        self.ui.setup_ui(self)
        self.load_qss()

        self.setup_tray_icon()

        self.hero_opacity = QGraphicsOpacityEffect(self.ui.hero_card)
        self.ui.hero_card.setGraphicsEffect(self.hero_opacity)

        self.completer_model = QStringListModel([], self)
        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(self.completer.caseSensitivity().CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.completer.setMaxVisibleItems(8)
        self.ui.city_input.setCompleter(self.completer)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.trigger_global_search)

        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.setInterval(30 * 60 * 1000)
        self.auto_refresh_timer.timeout.connect(self.fetch_weather)
        self.auto_refresh_timer.start()

        self.ui.city_input.textEdited.connect(self.on_text_edited)
        self.ui.city_input.returnPressed.connect(self.fetch_weather)
        self.completer.activated.connect(self.select_suggestion)
        self.ui.unit_btn.clicked.connect(self.toggle_units)
        self.ui.loc_btn.clicked.connect(self.auto_detect_location)
        self.ui.fav_btn.clicked.connect(self.toggle_favorite_current_city)
        self.ui.compare_btn.clicked.connect(self.open_compare_dialog)

        for item in self.ui.hourly_items:
            item.clicked.connect(self.on_hour_selected)

        self.setup_shortcuts()
        self.render_favorite_chips()

        last_city = self.settings.get("last_city", "Amman")
        self.ui.city_input.setText(last_city)
        self.fetch_weather()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self.ui, "particle_layer"):
            self.ui.particle_layer.resize(self.centralWidget().size())

    def setup_tray_icon(self):
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Weather Dashboard")
        self.tray_icon.show()

    def open_compare_dialog(self):
        if self.current_data:
            dlg = CompareDialog(self.current_data, self.is_celsius, self)
            dlg.setStyleSheet(self.styleSheet())
            dlg.exec()

    def generate_smart_advice(self, data: dict) -> str:
        temp = data.get("temp", 25)
        wind = data.get("wind", 0)
        cond = data.get("cond_type", "clear")

        if "rain" in cond or "thunderstorm" in cond:
            return "☔ يُنصح باصطحاب مظلة، فرصة هطول أمطار!"
        elif temp >= 34:
            return "☀️ احرص على شرب الماء وتجنب أشعة الشمس المباشرة!"
        elif temp <= 10:
            return "🧥 الطقس بارد، يُفضل ارتداء معطف دافئ!"
        elif wind >= 30:
            return "💨 رياح نشطة، يُنصح بالحذر أثناء القيادة."
        return "✨ طقس لطيف ومثالي للأنشطة الخارجية والرياضة!"

    def setup_shortcuts(self):
        QShortcut(QKeySequence("/"), self, activated=lambda: self.ui.city_input.setFocus())
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.ui.city_input.setFocus())
        QShortcut(QKeySequence("Escape"), self, activated=lambda: self.ui.city_input.clear())

    def render_favorite_chips(self):
        while self.ui.fav_chips_layout.count():
            item = self.ui.fav_chips_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for fav in self.settings.get("favorites", []):
            btn = QPushButton(fav)
            btn.setProperty("class", "favChip")
            btn.clicked.connect(lambda _, c=fav: self.search_from_chip(c))
            self.ui.fav_chips_layout.addWidget(btn)

    def search_from_chip(self, city_name: str):
        self.ui.city_input.setText(city_name)
        self.fetch_weather()

    def toggle_favorite_current_city(self):
        city = self.ui.city_input.text().strip()
        if not city:
            return
        favs = self.settings.get("favorites", [])
        if city in favs:
            favs.remove(city)
            self.ui.status_lbl.setText(f"تمت إزالة {city} من المفضلة")
        else:
            favs.append(city)
            self.ui.status_lbl.setText(f"تمت إضافة {city} إلى المفضلة ⭐")
        self.settings["favorites"] = favs
        SettingsManager.save_settings(self.settings)
        self.render_favorite_chips()

    def auto_detect_location(self):
        self.ui.status_lbl.setText("جاري تحديد موقعك الجغرافي تلقائياً...")
        self.loc_worker = AutoLocationWorker(self)
        self.loc_worker.location_found.connect(self.on_auto_location_found)
        self.loc_worker.start()

    def on_auto_location_found(self, loc_data: dict):
        city = loc_data.get("city", "Amman")
        lat = loc_data.get("lat")
        lon = loc_data.get("lon")
        self.ui.city_input.setText(city)
        self.fetch_weather_by_coords(city, lat, lon)

    def on_text_edited(self, text: str):
        txt = text.strip()
        if len(txt) >= 2:
            self.search_timer.start(220)

    def trigger_global_search(self):
        txt = self.ui.city_input.text().strip()
        if len(txt) >= 2:
            if self.search_worker and self.search_worker.isRunning():
                self.search_worker.quit()
                self.search_worker.wait()

            self.search_worker = GlobalSearchWorker(txt, self)
            self.search_worker.results_ready.connect(self.update_autocomplete_list)
            self.search_worker.start()

    def update_autocomplete_list(self, results: list):
        self.geo_results = {r["label"]: (r.get("lat"), r.get("lon")) for r in results}
        labels = list(self.geo_results.keys())
        self.completer_model.setStringList(labels)
        if labels and self.ui.city_input.hasFocus():
            self.completer.complete()

    def select_suggestion(self, text: str):
        self.ui.city_input.setText(text.strip())
        coords = self.geo_results.get(text.strip())
        if coords and coords[0] is not None:
            self.fetch_weather_by_coords(text.strip(), coords[0], coords[1])
        else:
            self.fetch_weather()

    def toggle_units(self):
        self.is_celsius = not self.is_celsius
        self.ui.unit_btn.setText("°C" if self.is_celsius else "°F")
        if self.current_data:
            self.update_ui(self.current_data)

    def fetch_weather(self):
        city = self.ui.city_input.text().strip()
        if not city:
            return
        self.fetch_weather_by_coords(city, None, None)

    def fetch_weather_by_coords(self, city: str, lat: float = None, lon: float = None):
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

        self.ui.status_lbl.setText("جاري جلب بيانات الطقس...")
        self.worker = FetchWeatherWorker(city, lat, lon, self)
        self.worker.data_received.connect(self.on_success)
        self.worker.error_occurred.connect(lambda err: self.ui.status_lbl.setText(err))
        self.worker.start()

    def on_success(self, data: dict):
        self.current_data = data
        self.settings["last_city"] = data.get("city", "").split(",")[0].strip()
        SettingsManager.save_settings(self.settings)

        cond_type = data.get("cond_type", "clear")
        time_phase = data.get("time_phase", "night")

        self.apply_adaptive_background(cond_type, time_phase)
        self.ui.particle_layer.set_weather_mode(cond_type if cond_type in ["rain", "snow", "thunderstorm"] else time_phase)
        self.animate_transition(lambda: self.update_ui(data))

    def apply_adaptive_background(self, cond_type: str, time_phase: str):
        if "rain" in cond_type or "thunderstorm" in cond_type:
            style = "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #050c1a, stop:0.5 #0f1e36, stop:1 #1c2b45);"
        elif "snow" in cond_type:
            style = "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a2634, stop:0.5 #2d3e52, stop:1 #3f556d);"
        elif time_phase == "night":
            style = "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #030712, stop:0.5 #0b1329, stop:1 #111d3d);"
        elif time_phase == "dawn":
            style = "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1f1c2c, stop:0.5 #423854, stop:1 #92535d);"
        elif time_phase == "sunset":
            style = "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1f1235, stop:0.5 #562852, stop:1 #8e4745);"
        else:
            style = "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f3460, stop:0.5 #164e87, stop:1 #1a659e);"

        self.ui.central_widget.setStyleSheet(f"#centralWidget {{ {style} }}")

    def animate_transition(self, callback):
        fade_out = QPropertyAnimation(self.hero_opacity, b"opacity")
        fade_out.setDuration(120)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.15)

        def on_finished():
            callback()
            fade_in = QPropertyAnimation(self.hero_opacity, b"opacity")
            fade_in.setDuration(180)
            fade_in.setStartValue(0.15)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.OutCubic)
            fade_in.start()
            self._fade_in = fade_in

        fade_out.finished.connect(on_finished)
        fade_out.start()
        self._fade_out = fade_out

    def on_hour_selected(self, hour_data: dict):
        t = hour_data['temp'] if self.is_celsius else round(hour_data['temp'] * 9/5 + 32)
        self.ui.temp_lbl.setText(f"{t}")
        self.ui.hero_icon.setText(hour_data.get("icon", "☀️"))
        self.ui.time_lbl.setText(f"Forecast at {hour_data['time']}")
        self.ui.status_lbl.setText(f"تم اختيار توقعات الساعة {hour_data['time']}")

    def update_ui(self, data: dict):
        if not data:
            return
        self.current_data = data

        def conv(c_t):
            return c_t if self.is_celsius else round(c_t * 9/5 + 32)

        self.ui.status_lbl.setText("")
        self.ui.city_lbl.setText(data.get("city", ""))
        self.ui.temp_lbl.setText(f"{conv(data.get('temp', 0))}")
        self.ui.min_max_lbl.setText(f"↑ {conv(data.get('max_today', 0))}° / ↓ {conv(data.get('min_today', 0))}°")
        self.ui.feels_lbl.setText(f"Feels like {conv(data.get('feels_like', 0))}°")
        self.ui.time_lbl.setText(data.get("time_text", ""))
        self.ui.hero_icon.setText(data.get("icon", "☀️"))
        self.ui.cond_lbl.setText(data.get("condition", ""))

        self.ui.wind_card.update_info(f"{data.get('wind', 0)} km/h", "Wind Speed")
        self.ui.humidity_card.update_info(f"{data.get('humidity', 0)}%", "Humidity")

        sun_data = data.get("sun", {})
        self.ui.sun_card.update_info(sun_data)

        advice = self.generate_smart_advice(data)
        self.ui.smart_advice_lbl.setText(f"💡 {advice}")

        for i, row in enumerate(self.ui.daily_rows):
            if i < len(data.get("daily", [])):
                row.set_data(data["daily"][i], self.is_celsius)
                row.show()
            else:
                row.hide()

        hourly_data = data.get("hourly", [])
        chart_temps = []
        chart_rain_probs = []
        for i, item in enumerate(self.ui.hourly_items):
            if i < len(hourly_data):
                item.set_data(hourly_data[i], self.is_celsius)
                chart_temps.append(conv(hourly_data[i]["temp"]))
                chart_rain_probs.append(hourly_data[i].get("rain_prob", 0))
                item.show()
            else:
                item.hide()

        self.ui.chart_view.set_data(chart_temps, chart_rain_probs)

    # --- تم تحديث الدالة لتفحص كل المسارات المحتملة لملف styles.qss ---
    def load_qss(self):
        possible_paths = [
            get_resource_path("frontend/styles.qss"),
            get_resource_path("styles.qss"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.qss"),
            os.path.join(os.path.abspath("."), "frontend", "styles.qss"),
            os.path.join(os.path.abspath("."), "styles.qss"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.setStyleSheet(f.read())
                    return
                except Exception as e:
                    print(f"Error loading QSS from {path}: {e}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.quit()
            self.search_worker.wait()
        if self.loc_worker and self.loc_worker.isRunning():
            self.loc_worker.quit()
            self.loc_worker.wait()
        event.accept()