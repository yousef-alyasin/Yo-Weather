import os
import sys
import time
import json
import asyncio
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, "backend"))
sys.path.append(os.path.join(ROOT_DIR, "frontend"))

from backend.api_service import WeatherProvider, COORDS_CACHE
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from frontend.app_window import WeatherApp, SettingsManager, CompareDialog
from frontend.ui_main import WeatherParticleCanvas, SmoothTempChart, SunTrackerCard


class SystemTester:
    def __init__(self):
        self.results = []
        self.start_total_time = time.perf_counter()

    def log_test(self, name: str, passed: bool, details: str = "", elapsed_ms: float = 0.0):
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({
            "name": name,
            "passed": passed,
            "details": details,
            "time_ms": elapsed_ms
        })
        time_str = f"({elapsed_ms:.2f} ms)" if elapsed_ms > 0 else ""
        print(f"[{status}] {name:<45} {time_str}")
        if details and not passed:
            print(f"       └── ⚠️ التفاصيل: {details}")

    def print_summary(self):
        total_time = (time.perf_counter() - self.start_total_time) * 1000
        passed_count = sum(1 for r in self.results if r["passed"])
        total_count = len(self.results)
        pct = (passed_count / total_count) * 100 if total_count else 0

        print("\n" + "=" * 70)
        print("📊 ملخص نتائج الفحص الشامل للنظام (System Diagnostic Summary)")
        print("=" * 70)
        for r in self.results:
            icon = "✔️" if r["passed"] else "✖️"
            print(f" {icon} {r['name']:<50} | {r['time_ms']:>8.2f} ms")
        print("-" * 70)
        print(f"إجمالي الاختبارات: {total_count} | الناجحة: {passed_count} | الفاشلة: {total_count - passed_count}")
        print(f"نسبة النجاح الكلية: {pct:.1f}% | الوقت الإجمالي للفحص: {total_time:.2f} ms")
        print("=" * 70)


async def test_backend_and_network(tester: SystemTester):
    print("\n🔹 [المرحلة 1] فحص الـ Backend، الاتصالات، والبيانات الجغرافية:")
    print("-" * 70)

    t0 = time.perf_counter()
    lat_salt, lon_salt, name_salt = await WeatherProvider.resolve_coordinates_async(None, "salt")
    lat_amman, lon_amman, name_amman = await WeatherProvider.resolve_coordinates_async(None, "عمان")
    dt = (time.perf_counter() - t0) * 1000

    salt_ok = lat_salt is not None and ("Jordan" in name_salt or "الأردن" in name_salt or "السلط" in name_salt)
    amman_ok = lat_amman is not None and ("Jordan" in name_amman or "الأردن" in name_amman or "عمّان" in name_amman)
    tester.log_test("Geocoding Aliasing (Salt & Amman)", salt_ok and amman_ok, f"Salt: {name_salt}, Amman: {name_amman}", dt)

    t0 = time.perf_counter()
    try:
        data = await WeatherProvider.fetch_weather_data_async("Amman")
        dt = (time.perf_counter() - t0) * 1000
        has_essential_fields = all(k in data for k in ["temp", "humidity", "wind", "daily", "hourly", "sun", "time_phase"])
        tester.log_test("Async API Gathering Speed (<1200ms)", dt < 1200 and has_essential_fields, f"Time: {dt:.2f}ms", dt)
    except Exception as e:
        tester.log_test("Async API Gathering Speed (<1200ms)", False, str(e), 0.0)
        return None

    t0 = time.perf_counter()
    cached_data = await WeatherProvider.fetch_weather_data_async("Amman")
    dt = (time.perf_counter() - t0) * 1000
    tester.log_test("In-Memory 0ms Cache Hit", dt < 5.0 and cached_data == data, f"Duration: {dt:.4f}ms", dt)

    sun_data = data.get("sun", {})
    time_phase = data.get("time_phase", "")
    phase_ok = time_phase in ["night", "dawn", "day", "sunset"]
    sun_ok = "sunrise" in sun_data and "sunset" in sun_data and 0.0 <= sun_data.get("progress", -1) <= 1.0
    tester.log_test("Sun Position & Time Phase Engine", phase_ok and sun_ok, f"Phase: {time_phase}, Sun: {sun_data.get('status')}", 0.0)

    hourly = data.get("hourly", [])
    hourly_ok = len(hourly) >= 8 and "rain_prob" in hourly[0] and "temp" in hourly[0]
    tester.log_test("Hourly Forecast & Rain Probability Structure", hourly_ok, f"Total Hours: {len(hourly)}", 0.0)

    return data


def test_frontend_and_gui(tester: SystemTester, sample_data: dict):
    print("\n🔹 [المرحلة 2] فحص مكونات واجهة المستخدم (PySide6 UI & Graphics):")
    print("-" * 70)

    app = QApplication.instance() or QApplication(sys.argv)

    t0 = time.perf_counter()
    main_win = WeatherApp()
    dt = (time.perf_counter() - t0) * 1000
    has_ui = hasattr(main_win, "ui") and main_win.ui.city_input is not None and main_win.ui.hero_card is not None
    tester.log_test("PySide6 MainWindow Construction", has_ui, "", dt)

    t0 = time.perf_counter()
    canvas = WeatherParticleCanvas()
    canvas.resize(1000, 700)
    canvas.set_weather_mode("rain")
    initial_particles = len(canvas.particles)
    canvas.update_particles()
    canvas.set_weather_mode("snow")
    snow_particles = len(canvas.particles)
    canvas.set_weather_mode("night")
    dt = (time.perf_counter() - t0) * 1000
    canvas_ok = initial_particles > 0 and snow_particles > 0 and len(canvas.particles) > 0
    tester.log_test("Particle Engine (Rain/Snow/Stars 60FPS)", canvas_ok, f"Rain Count: {initial_particles}", dt)

    advice_rain = main_win.generate_smart_advice({"cond_type": "rain", "temp": 15, "wind": 10})
    advice_hot = main_win.generate_smart_advice({"cond_type": "clear", "temp": 38, "wind": 10})
    advice_cold = main_win.generate_smart_advice({"cond_type": "clear", "temp": 5, "wind": 10})
    advice_ok = "مظلة" in advice_rain and "الماء" in advice_hot and "معطف" in advice_cold
    tester.log_test("Smart Activity & Clothing Advice Generator", advice_ok, f"Sample: {advice_rain}", 0.0)

    # فحص تحويل الوحدات دون أي تعديل يدوي، معتمداً على سلامة الكود
    t0 = time.perf_counter()
    main_win.is_celsius = True
    main_win.update_ui(sample_data)
    temp_c = main_win.ui.temp_lbl.text().replace("°", "").strip()

    main_win.toggle_units()
    temp_f = main_win.ui.temp_lbl.text().replace("°", "").strip()
    expected_f = str(round(sample_data["temp"] * 9 / 5 + 32))

    main_win.toggle_units()
    unit_ok = (temp_f == expected_f) and (temp_c == str(sample_data["temp"]))
    dt = (time.perf_counter() - t0) * 1000
    tester.log_test("Unit Conversion System (°C <-> °F)", unit_ok, f"C: {temp_c}° -> F: {temp_f}°", dt)

    t0 = time.perf_counter()
    chart = SmoothTempChart()
    chart.resize(400, 95)
    temps = [20, 22, 25, 27, 26, 24, 21, 19]
    rain = [0, 10, 40, 70, 50, 20, 0, 0]
    chart.set_data(temps, rain)
    chart_ok = len(chart.temperatures) == 8 and len(chart.rain_probs) == 8
    dt = (time.perf_counter() - t0) * 1000
    tester.log_test("Smooth Chart & Rain Bars Data Integrity", chart_ok, "", dt)

    t0 = time.perf_counter()
    compare_dlg = CompareDialog(sample_data, is_celsius=True)
    dlg_ok = compare_dlg.left_card is not None and compare_dlg.right_card is not None
    dt = (time.perf_counter() - t0) * 1000
    tester.log_test("Dual City Compare Dialog Initialization", dlg_ok, "", dt)

    test_settings = {"last_city": "TestCity", "favorites": ["عمان", "السلط", "دبي"]}
    SettingsManager.save_settings(test_settings)
    loaded = SettingsManager.load_settings()
    settings_ok = loaded.get("last_city") == "TestCity" and "السلط" in loaded.get("favorites", [])
    tester.log_test("Settings & Favorites JSON Persistence", settings_ok, "", 0.0)

    main_win.close()
    compare_dlg.close()


async def main():
    print("=" * 70)
    print("⚡ تشغيل الفحص والتحقق الآلي الشامل لنظام Weather Dashboard")
    print(f"🕒 توقيت الفحص: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    tester = SystemTester()

    sample_data = await test_backend_and_network(tester)

    if sample_data:
        test_frontend_and_gui(tester, sample_data)
    else:
        print("\n❌ تم إيقاف الفحص لتعذر جلب بيانات الـ API.")

    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())