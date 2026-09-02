import asyncio
from PySide6.QtCore import QThread, Signal
from api_client import WeatherApiClient


class FetchWeatherWorker(QThread):
    """Worker thread to fetch weather asynchronously without freezing the UI"""
    data_received = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, city_name: str, lat: float = None, lon: float = None, parent=None):
        super().__init__(parent)
        self.city_name = city_name
        self.lat = lat
        self.lon = lon

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            data = loop.run_until_complete(
                WeatherApiClient.get_weather_async(self.city_name, self.lat, self.lon)
            )
            loop.close()

            if data:
                self.data_received.emit(data)
            else:
                self.error_occurred.emit("لم يتم العثور على نتائج للطقس.")
        except Exception as err:
            self.error_occurred.emit(f"خطأ أثناء جلب البيانات: {str(err)}")


class GlobalSearchWorker(QThread):
    """Worker thread for city autocomplete search suggestions"""
    results_ready = Signal(list)

    def __init__(self, query_text: str, parent=None):
        super().__init__(parent)
        self.query_text = query_text

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(
                WeatherApiClient.search_cities_async(self.query_text)
            )
            loop.close()
            self.results_ready.emit(results)
        except Exception:
            self.results_ready.emit([])


class AutoLocationWorker(QThread):
    """Worker thread to detect current user city by IP address"""
    location_found = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loc_data = loop.run_until_complete(
                WeatherApiClient.auto_locate_async()
            )
            loop.close()

            if loc_data:
                self.location_found.emit(loc_data)
            else:
                self.error_occurred.emit("تعذر تحديد الموقع التلقائي.")
        except Exception as err:
            self.error_occurred.emit(f"خطأ في تحديد الموقع: {str(err)}")