import os
import sys
import json
from PySide6.QtCore import QStringListModel, QPropertyAnimation, QEasingCurve, QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QDialog, QCompleter, QGraphicsOpacityEffect,
    QPushButton, QLineEdit, QSystemTrayIcon, QStyle, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame, QApplication
)

from frontend.ui_main import WeatherUI
from frontend.workers import FetchWeatherWorker, GlobalSearchWorker, AutoLocationWorker
from frontend.translations import TRANSLATIONS, CONDITIONS_AR


def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        bundle_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(bundle_path):
            return bundle_path
        flat_path = os.path.join(sys._MEIPASS, os.path.basename(relative_path))
        if os.path.exists(flat_path):
            return flat_path

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dev_path = os.path.join(base_dir, relative_path)
    if os.path.exists(dev_path):
        return dev_path

    curr_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(relative_path))
    if os.path.exists(curr_dir_path):
        return curr_dir_path

    return relative_path


SETTINGS_FILE = "settings.json"


class SettingsManager:
    @staticmethod
    def load_settings() -> dict:
        defaults = {
            "last_city": "Amman",
            "lang": "en",
            "favorites": ["Amman", "Dubai", "London", "Riyadh"]
        }
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "favorites" not in data:
                        data["favorites"] = defaults["favorites"]
                    return data
            except Exception as e:
                print("Error loading settings:", e)
        return defaults

    @staticmethod
    def save_settings(data: dict):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print("Error saving settings:", e)


class CompareDialog(QDialog):
    def __init__(self, current_data: dict, is_celsius: bool, lang: str = "en", parent=None):
        super().__init__(parent)
        self.lang = lang
        t = TRANSLATIONS[self.lang]
        self.setWindowTitle(t["compare_title"])
        self.resize(650, 380)
        self.is_celsius = is_celsius
        self.setLayoutDirection(Qt.RightToLeft if lang == "ar" else Qt.LeftToRight)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        search_bar = QHBoxLayout()
        self.compare_input = QLineEdit()
        self.compare_input.setObjectName("searchInput")
        self.compare_input.setPlaceholderText(t["compare_placeholder"])
        self.compare_btn = QPushButton(t["compare_btn"])
        self.compare_btn.setObjectName("toolBtn")
        search_bar.addWidget(self.compare_input, stretch=1)
        search_bar.addWidget(self.compare_btn)
        layout.addLayout(search_bar)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.left_card = self.create_city_card(current_data)
        self.right_card = self.create_empty_card(t["compare_hint"])

        cards_layout.addWidget(self.left_card)
        cards_layout.addWidget(self.right_card)
        layout.addLayout(cards_layout)

        self.compare_btn.clicked.connect(self.do_compare)
        self.compare_input.returnPressed.connect(self.do_compare)
        self.worker = None

    def create_city_card(self, data: dict) -> QFrame:
        t_dict = TRANSLATIONS[self.lang]
        card = QFrame()
        card.setObjectName("mainCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        l = QVBoxLayout(card)
        l.setAlignment(Qt.AlignCenter)
        l.setSpacing(6)

        c_name = QLabel(data.get("city", "--"))
        c_name.setObjectName("mainCity")
        t = data.get("temp", 0) if self.is_celsius else round(data.get("temp", 0) * 9/5 + 32)
        c_temp = QLabel(f"{t}°")
        c_temp.setObjectName("mainTemp")

        cond_raw = data.get("condition", "--")
        cond_disp = CONDITIONS_AR.get(cond_raw, cond_raw) if self.lang == "ar" else cond_raw
        c_cond = QLabel(f"{data.get('icon', '☀️')} {cond_disp}")
        c_cond.setObjectName("mainCondition")

        c_details = QLabel(f"{t_dict['wind_label']}: {data.get('wind', 0)} km/h | {t_dict['humidity_label']}: {data.get('humidity', 0)}%")
        c_details.setObjectName("mainSub")

        l.addWidget(c_name)
        l.addWidget(c_temp)
        l.addWidget(c_cond)
        l.addWidget(c_details)
        return card

    def create_empty_card(self, msg: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setAttribute(Qt.WA_StyledBackground, True)
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
        self.worker = FetchWeatherWorker(city, lang=self.lang, parent=self)
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setStyleSheet("QMainWindow { background-color: #0b1329; border-radius: 16px; }")
        self.resize(1120, 750)
        self.setMinimumSize(980, 720)

        self.drag_position = None
        self.worker = None
        self.search_worker = None
        self.loc_worker = None

        self.is_celsius = True
        self.current_data = {}
        self.geo_results = {}

        self.settings = SettingsManager.load_settings()
        self.lang = self.settings.get("lang", "en")

        self.ui = WeatherUI()
        self.ui.setup_ui(self)

        self.load_qss()
        self.setup_tray_icon()

        self.ui.btn_min.clicked.connect(self.showMinimized)
        self.ui.btn_max.clicked.connect(self.toggle_maximize_restore)
        self.ui.btn_close.clicked.connect(self.close)

        self.hero_opacity = QGraphicsOpacityEffect(self.ui.hero_card)
        self.ui.hero_card.setGraphicsEffect(self.hero_opacity)

        self.completer_model = QStringListModel([], self)
        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.completer.setMaxVisibleItems(8)

        popup = self.completer.popup()
        popup.setObjectName("completerPopup")
        popup.setStyleSheet("""
            QListView#completerPopup {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 12px;
                padding: 6px;
                outline: none;
                font-size: 13px;
                selection-background-color: rgba(56, 189, 248, 0.3);
                selection-color: #38bdf8;
            }
            QListView#completerPopup::item {
                padding: 8px 12px;
                border-radius: 6px;
            }
            QListView#completerPopup::item:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
        """)
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
        self.ui.lang_btn.clicked.connect(self.toggle_language)

        for item in self.ui.hourly_items:
            item.clicked.connect(self.on_hour_selected)

        self.setup_shortcuts()
        self.apply_language_texts()

        last_city = self.settings.get("last_city", "Amman")
        self.ui.city_input.setText(last_city)
        self.render_favorite_chips()
        self.fetch_weather()

    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
            self.ui.btn_max.setText("🗖")
        else:
            self.showMaximized()
            self.ui.btn_max.setText("🗗")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.ui.title_bar.geometry().contains(event.position().toPoint()):
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_position is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.ui.title_bar.geometry().contains(event.position().toPoint()):
            self.toggle_maximize_restore()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def toggle_language(self):
        self.lang = "ar" if self.lang == "en" else "en"
        self.settings["lang"] = self.lang
        SettingsManager.save_settings(self.settings)
        self.apply_language_texts()
        self.render_favorite_chips()

        if self.current_data:
            self.fetch_weather()

    def apply_language_texts(self):
        t = TRANSLATIONS[self.lang]
        self.setWindowTitle("Yo Weather")
        self.ui.title_text.setText("Yo Weather")
        self.ui.city_input.setPlaceholderText(t["search_placeholder"])
        self.ui.loc_btn.setToolTip(t["tool_locate"])
        self.ui.fav_btn.setToolTip(t["tool_fav"])
        self.ui.compare_btn.setToolTip(t["tool_compare"])
        self.ui.unit_btn.setToolTip(t["tool_unit"])
        self.ui.lang_btn.setText(t["tool_lang"])
        self.ui.wind_card.set_title(t["wind_title"])
        self.ui.humidity_card.set_title(t["humidity_title"])
        self.ui.sun_card.set_title(t["sun_title"])

        target_dir = Qt.RightToLeft if self.lang == "ar" else Qt.LeftToRight
        QApplication.setLayoutDirection(target_dir)
        self.setLayoutDirection(target_dir)
        self.ui.central_widget.setLayoutDirection(target_dir)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self.ui, "particle_layer"):
            self.ui.particle_layer.resize(self.centralWidget().size())

    def setup_tray_icon(self):
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Yo Weather")
        self.tray_icon.show()

    def open_compare_dialog(self):
        if self.current_data:
            dlg = CompareDialog(self.current_data, self.is_celsius, self.lang, self)
            dlg.setStyleSheet(self.styleSheet())
            dlg.exec()

    def generate_smart_advice(self, data: dict) -> str:
        t = TRANSLATIONS[self.lang]
        temp = data.get("temp", 25)
        wind = data.get("wind", 0)
        cond = data.get("cond_type", "clear")

        if "rain" in cond or "thunderstorm" in cond:
            return t["advice_rain"]
        elif temp >= 34:
            return t["advice_hot"]
        elif temp <= 10:
            return t["advice_cold"]
        elif wind >= 30:
            return t["advice_wind"]
        return t["advice_pleasant"]

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

        chips = self.settings.get("favorites", ["Amman", "Dubai", "London", "Riyadh"])
        for fav in chips:
            display_text = fav.get("display", fav) if isinstance(fav, dict) else fav
            btn = QPushButton(display_text)
            btn.setProperty("class", "favChip")
            btn.clicked.connect(lambda _, f=fav: self.search_from_chip(f))
            self.ui.fav_chips_layout.addWidget(btn)

    def search_from_chip(self, fav_item):
        if isinstance(fav_item, dict):
            display = fav_item.get("display", "Amman")
            lat = fav_item.get("lat")
            lon = fav_item.get("lon")
            query = fav_item.get("query", display)
            self.ui.city_input.setText(display)
            self.fetch_weather_by_coords(query, lat, lon, display_name=display)
        else:
            clean_name = fav_item.split(" - ")[0].split(",")[0].strip()
            self.ui.city_input.setText(fav_item)
            self.fetch_weather_by_coords(clean_name, None, None, display_name=fav_item)

    def toggle_favorite_current_city(self):
        if not self.current_data:
            return
        t = TRANSLATIONS[self.lang]
        favs = self.settings.get("favorites", ["Amman", "Dubai", "London", "Riyadh"])

        current_display = self.current_data.get("city", self.ui.city_input.text().strip())
        current_lat = self.current_data.get("lat")
        current_lon = self.current_data.get("lon")
        current_query = self.current_data.get("query", current_display)

        existing_index = -1
        for i, fav in enumerate(favs):
            fav_display = fav.get("display") if isinstance(fav, dict) else fav
            if fav_display == current_display or (isinstance(fav, dict) and fav.get("lat") == current_lat and fav.get("lon") == current_lon):
                existing_index = i
                break

        if existing_index != -1:
            favs.pop(existing_index)
            self.ui.status_lbl.setText(f"{current_display} {t['status_fav_removed']}")
        else:
            fav_obj = {
                "display": current_display.split(" - ")[0].strip(),
                "lat": current_lat,
                "lon": current_lon,
                "query": current_query
            }
            favs.append(fav_obj)
            self.ui.status_lbl.setText(f"{current_display} {t['status_fav_added']}")

        self.settings["favorites"] = favs
        SettingsManager.save_settings(self.settings)
        self.render_favorite_chips()

    def auto_detect_location(self):
        t = TRANSLATIONS[self.lang]
        self.ui.status_lbl.setText(t["status_locating"])
        self.loc_worker = AutoLocationWorker(self)
        self.loc_worker.location_found.connect(self.on_auto_location_found)
        self.loc_worker.start()

    def on_auto_location_found(self, loc_data: dict):
        city = loc_data.get("city", "Amman, Jordan")
        lat = loc_data.get("lat")
        lon = loc_data.get("lon")
        self.ui.city_input.setText(city)
        self.fetch_weather_by_coords(city, lat, lon, display_name=city)

    def on_text_edited(self, text: str):
        txt = text.strip()
        if len(txt) >= 2:
            self.search_timer.start(220)
        elif len(txt) == 0:
            self.completer.popup().hide()

    def trigger_global_search(self):
        txt = self.ui.city_input.text().strip()
        if len(txt) >= 2:
            if self.search_worker and self.search_worker.isRunning():
                self.search_worker.quit()
                self.search_worker.wait()

            # تمرير اللغة للـ GlobalSearchWorker هنا
            self.search_worker = GlobalSearchWorker(txt, lang=self.lang, parent=self)
            self.search_worker.results_ready.connect(self.update_autocomplete_list)
            self.search_worker.start()

    def update_autocomplete_list(self, results: list):
        if not results:
            self.completer_model.setStringList([])
            self.completer.popup().hide()
            return

        self.geo_results = {r["label"]: (r.get("lat"), r.get("lon")) for r in results}
        labels = list(self.geo_results.keys())
        self.completer_model.setStringList(labels)

        if labels and self.ui.city_input.hasFocus():
            self.completer.complete()

    def select_suggestion(self, text: str):
        clean_text = text.strip()
        self.ui.city_input.setText(clean_text)
        coords = self.geo_results.get(clean_text)
        
        base_city_name = clean_text.split(" - ")[0].split(",")[0].strip()

        if coords and coords[0] is not None:
            self.fetch_weather_by_coords(base_city_name, coords[0], coords[1], display_name=clean_text)
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
        self.fetch_weather_by_coords(city, None, None, display_name=city)

    def fetch_weather_by_coords(self, city: str, lat: float = None, lon: float = None, display_name: str = None):
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

        t = TRANSLATIONS[self.lang]
        self.ui.status_lbl.setText(t["status_fetching"])

        self.worker = FetchWeatherWorker(city, lat, lon, lang=self.lang, display_name=display_name, parent=self)
            
        self.worker.data_received.connect(self.on_success)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def on_error(self, err_msg: str):
        self.ui.status_lbl.setText(err_msg)

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

        self.ui.central_widget.setStyleSheet(f"#centralWidget {{ {style} border-radius: 16px; }}")

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
        t_dict = TRANSLATIONS[self.lang]
        t = hour_data['temp'] if self.is_celsius else round(hour_data['temp'] * 9/5 + 32)
        self.ui.temp_lbl.setText(f"{t}")
        self.ui.hero_icon.setText(hour_data.get("icon", "☀️"))

        time_str = hour_data['time']
        if self.lang == "ar":
            time_str = time_str.replace("AM", "ص").replace("PM", "م")
            self.ui.time_lbl.setText(f"توقعات الساعة {time_str}")
        else:
            self.ui.time_lbl.setText(f"Forecast at {time_str}")

        self.ui.status_lbl.setText(f"{t_dict['status_hour_selected']} {time_str}")

    def get_translated_sun_status(self, data: dict) -> str:
        t = TRANSLATIONS[self.lang]
        phase = data.get("time_phase", "day")
        if phase == "night":
            return t["sun_night"]
        elif phase == "dawn":
            return t["sun_dawn"]
        elif phase == "sunset":
            return t["sun_sunset"]
        else:
            sun = data.get("sun", {})
            rem = sun.get("remaining_hours")
            if rem is not None:
                return f"{rem} {t['sun_day_remaining']}"
            return t["sun_day_ongoing"]

    def update_ui(self, data: dict):
        if not data:
            return
        self.current_data = data
        t_dict = TRANSLATIONS[self.lang]

        def conv(c_t):
            return c_t if self.is_celsius else round(c_t * 9/5 + 32)

        self.ui.status_lbl.setText("")
        
        current_city_name = data.get("city", "")
        self.ui.city_lbl.setText(current_city_name)
        
        self.ui.temp_lbl.setText(f"{conv(data.get('temp', 0))}")
        self.ui.min_max_lbl.setText(f"↑ {conv(data.get('max_today', 0))}° / ↓ {conv(data.get('min_today', 0))}°")
        self.ui.feels_lbl.setText(f"{t_dict['feels_like']} {conv(data.get('feels_like', 0))}°")

        raw_time = data.get("time_text", "")
        if self.lang == "ar":
            day_map = {"Mon": "الإثنين", "Tue": "الثلاثاء", "Wed": "الأربعاء", "Thu": "الخميس", "Fri": "الجمعة", "Sat": "السبت", "Sun": "الأحد"}
            for eng_d, ar_d in day_map.items():
                raw_time = raw_time.replace(eng_d, ar_d)
            raw_time = raw_time.replace("AM", "ص").replace("PM", "م")
        self.ui.time_lbl.setText(raw_time)

        self.ui.hero_icon.setText(data.get("icon", "☀️"))

        raw_cond = data.get("condition", "")
        cond_disp = CONDITIONS_AR.get(raw_cond, raw_cond) if self.lang == "ar" else raw_cond
        self.ui.cond_lbl.setText(cond_disp)

        self.ui.wind_card.update_info(f"{data.get('wind', 0)} km/h", "")
        self.ui.humidity_card.update_info(f"{data.get('humidity', 0)}%", "")

        sun_data = data.get("sun", {})
        sun_status = self.get_translated_sun_status(data)
        self.ui.sun_card.update_info(sun_data, status_text=sun_status, lang=self.lang)

        advice = self.generate_smart_advice(data)
        self.ui.smart_advice_lbl.setText(f"💡 {advice}")
        self.ui.smart_advice_lbl.setToolTip(advice)

        ar_days = {"Mon": "الإثنين", "Tue": "الثلاثاء", "Wed": "الأربعاء", "Thu": "الخميس", "Fri": "الجمعة", "Sat": "السبت", "Sun": "الأحد"}
        for i, row in enumerate(self.ui.daily_rows):
            if i < len(data.get("daily", [])):
                day_info = data["daily"][i]
                day_name = day_info.get("day", "")
                display_day = ar_days.get(day_name, day_name) if self.lang == "ar" else day_name
                row_cond = day_info.get("condition", "")
                display_cond = CONDITIONS_AR.get(row_cond, row_cond) if self.lang == "ar" else row_cond
                row.set_data(day_info, self.is_celsius, day_text=display_day, cond_text=display_cond)
                row.show()
            else:
                row.hide()

        hourly_data = data.get("hourly", [])
        chart_temps = []
        chart_rain_probs = []
        for i, item in enumerate(self.ui.hourly_items):
            if i < len(hourly_data):
                time_str = hourly_data[i]["time"]
                if self.lang == "ar":
                    time_str = time_str.replace("AM", "ص").replace("PM", "م")
                item.set_data(hourly_data[i], self.is_celsius, time_display=time_str)
                chart_temps.append(conv(hourly_data[i]["temp"]))
                chart_rain_probs.append(hourly_data[i].get("rain_prob", 0))
                item.show()
            else:
                item.hide()

        self.ui.chart_view.set_data(chart_temps, chart_rain_probs)

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