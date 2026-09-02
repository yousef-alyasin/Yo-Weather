# 🌦️ Weather Dashboard & Analytics Desktop Application

A modern, responsive, and cross-platform desktop weather application engineered with **Python**, **PySide6 (Qt for Python)**, and an asynchronous backend service using **FastAPI** and **HTTPX**. 

The application delivers real-time weather metrics, smart daily recommendations, dynamic visual physics, and interactive data visualization with an elegant dark glassmorphism interface.

---

### ✨ Key Features

* **Real-time Global Weather Data:** Fetches up-to-the-minute weather conditions, humidity, wind speeds, air quality (AQI), and temperature trends using OpenWeatherMap.
* **Dynamic Celestial & Particle System:** Built-in 40 FPS particle canvas rendering animated rain, snow, and night sky twinkles adapted dynamically to current weather conditions and daylight phase.
* **Sun & Daylight Arc Tracker:** Interactive custom-painted widget calculating real-time sun progression, sunrise, and sunset trajectory.
* **Interactive Forecast & Visual Charts:** Custom spline curve visualizing 24-hour temperature trends alongside precipitation probability bars.
* **Dual City Comparison:** Dedicated side-by-side weather comparative tool to analyze atmospheric metrics between two locations simultaneously.
* **Intelligent Location & Search:** 
  * Auto-detect user coordinates via IP geolocation.
  * Debounced global search bar with instant bilingual (Arabic/English) autocomplete suggestions.
* **User Preferences:** Local caching mechanism, favorite cities quick-chips, and seamless unit toggling (°C / °F).
* **Standalone Executable:** Fully packaged as an independent Windows `.exe` using PyInstaller.

---

### 🛠️ Tech Stack & Architecture

* **GUI Framework:** PySide6 (Qt6), Custom QPainter Canvas, QSS Styling.
* **Backend Engine:** FastAPI, Asyncio, HTTPX (Asynchronous non-blocking requests).
* **Multi-threading:** Dedicated `QThread` workers eliminating UI freeze during network calls.
* **Packaging:** PyInstaller.
