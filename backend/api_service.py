import os
import sys
import time
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

if hasattr(sys, '_MEIPASS'):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(BASE_DIR, ".env"))

API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()

CACHE = {}
CACHE_TTL = 900


class WeatherProvider:
    CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
    AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

    @staticmethod
    async def resolve_coordinates_async(client: httpx.AsyncClient, query: str) -> tuple:
        if not query:
            return None, None, ""

        clean_q = query.split(" - ")[0].split(",")[0].strip()

        if "بغداد" in clean_q or "baghdad" in clean_q.lower():
            return 33.3152, 44.3661, "بغداد, العراق"

        try:
            close_client = False
            if client is None:
                client = httpx.AsyncClient(timeout=3.5)
                close_client = True

            url = "https://api.openweathermap.org/geo/1.0/direct"
            params = {"q": clean_q, "limit": 1, "appid": API_KEY}
            res = await client.get(url, params=params)

            if close_client:
                await client.aclose()

            if res.status_code == 200:
                locations = res.json()
                if locations:
                    top = locations[0]
                    lat = top.get("lat")
                    lon = top.get("lon")
                    name = top.get("name", clean_q)
                    country = top.get("country", "")
                    state = top.get("state", "")
                    local_names = top.get("local_names", {})
                    display_name = local_names.get("ar", name)
                    
                    parts = [display_name]
                    if state:
                        parts.append(state)
                    if country:
                        parts.append(country)
                    display = ", ".join(parts)
                    return float(lat), float(lon), display

        except Exception as err:
            print("Geocoding error:", err)

        return None, None, query

    @staticmethod
    async def fetch_weather_data_async(query: str, lat: float = None, lon: float = None, display_name: str = None, lang: str = "en") -> dict:
        if not API_KEY:
            raise ValueError("OPENWEATHER_API_KEY is missing from .env file")

        if (query and ("بغداد" in query or "baghdad" in query.lower())) or (display_name and ("بغداد" in display_name or "baghdad" in display_name.lower())):
            lat = 33.3152
            lon = 44.3661
            display_name = "بغداد, العراق"
            query = "Baghdad"

        cache_key = f"{query}_{lat}_{lon}_{lang}".lower()
        if cache_key in CACHE:
            cached_data, timestamp = CACHE[cache_key]
            if time.time() - timestamp < CACHE_TTL:
                return cached_data

        target_lang = lang

        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        async with httpx.AsyncClient(limits=limits, timeout=6.0) as client:
            if lat is None or lon is None:
                lat, lon, resolved_name = await WeatherProvider.resolve_coordinates_async(client, query)
                if not display_name:
                    display_name = resolved_name

            params = {"appid": API_KEY, "units": "metric", "lang": target_lang}
            if lat is not None and lon is not None:
                params["lat"] = lat
                params["lon"] = lon
            else:
                params["q"] = query

            task_curr = client.get(WeatherProvider.CURRENT_URL, params=params)
            task_fore = client.get(WeatherProvider.FORECAST_URL, params=params)
            task_aqi = (
                client.get(WeatherProvider.AIR_POLLUTION_URL, params={"lat": lat, "lon": lon, "appid": API_KEY})
                if (lat is not None and lon is not None) else None
            )

            results = await asyncio.gather(task_curr, task_fore, task_aqi, return_exceptions=True)
            res_curr, res_fore, res_aqi = results

            if isinstance(res_curr, Exception) or res_curr.status_code != 200:
                raise LookupError(f"Could not find weather data for '{query}'.")

            current_data = res_curr.json()
            forecast_data = res_fore.json() if (not isinstance(res_fore, Exception) and res_fore.status_code == 200) else {}

            aqi_info = {"index": 1, "label": "Good"}
            if not isinstance(res_aqi, Exception) and res_aqi and res_aqi.status_code == 200:
                try:
                    aqi_level = res_aqi.json()["list"][0]["main"]["aqi"]
                    labels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Hazardous"}
                    aqi_info = {"index": aqi_level, "label": labels.get(aqi_level, "Fair")}
                except Exception:
                    pass

        tz_offset = current_data.get("timezone", 0)
        tz = timezone(timedelta(seconds=tz_offset))
        current_city_time = datetime.now(tz)

        sys_data = current_data.get("sys", {})
        sunrise_ts = sys_data.get("sunrise", 0)
        sunset_ts = sys_data.get("sunset", 0)
        current_ts = current_data.get("dt", int(time.time()))

        sunrise_dt = datetime.fromtimestamp(sunrise_ts, tz=tz) if sunrise_ts else current_city_time
        sunset_dt = datetime.fromtimestamp(sunset_ts, tz=tz) if sunset_ts else current_city_time

        remaining_hours = None
        if sunrise_ts and sunset_ts:
            if current_ts < sunrise_ts - 3600 or current_ts > sunset_ts + 3600:
                time_phase = "night"
                sun_progress = 0.0 if current_ts < sunrise_ts else 1.0
            elif sunrise_ts - 3600 <= current_ts <= sunrise_ts + 1800:
                time_phase = "dawn"
                sun_progress = 0.1
            elif sunset_ts - 1800 <= current_ts <= sunset_ts + 3600:
                time_phase = "sunset"
                sun_progress = 0.95
            else:
                time_phase = "day"
                sun_progress = round((current_ts - sunrise_ts) / (sunset_ts - sunrise_ts), 2)
                remaining_hours = round((sunset_ts - current_ts) / 3600, 1)
        else:
            time_phase = "day" if 6 <= current_city_time.hour < 18 else "night"
            sun_progress = 0.5

        sun_data = {
            "sunrise": sunrise_dt.strftime("%I:%M %p"),
            "sunset": sunset_dt.strftime("%I:%M %p"),
            "progress": sun_progress,
            "remaining_hours": remaining_hours
        }

        daily_forecast = []
        hourly_forecast = []
        days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        items = forecast_data.get("list", [])
        for item in items[:8]:
            time_part = item["dt_txt"].split(" ")[1]
            hour_val = int(time_part.split(":")[0])
            period = "AM" if hour_val < 12 else "PM"
            disp_hour = hour_val % 12
            disp_hour = 12 if disp_hour == 0 else disp_hour
            cond_main = item["weather"][0]["main"]
            hourly_forecast.append({
                "time": f"{disp_hour}:00 {period}",
                "icon": WeatherProvider._get_icon(cond_main),
                "temp": round(item["main"]["temp"]),
                "rain_prob": round(item.get("pop", 0) * 100)
            })

        for item in items[::8][:7]:
            dt = datetime.strptime(item["dt_txt"], "%Y-%m-%d %H:%M:%S")
            cond_main = item["weather"][0]["main"]
            daily_forecast.append({
                "day": days_names[dt.weekday()],
                "rain_prob": round(item.get("pop", 0) * 100),
                "icon": WeatherProvider._get_icon(cond_main),
                "condition": item["weather"][0]["description"].title(),
                "max_temp": round(item["main"]["temp_max"]),
                "min_temp": round(item["main"]["temp_min"])
            })

        final_city_name = display_name if display_name else current_data.get("name", query)
        if query and ("بغداد" in query or "baghdad" in query.lower()):
            final_city_name = "بغداد"
        elif lang == "ar" and display_name:
            final_city_name = display_name.split(" - ")[0].split(",")[0].strip()

        cond_main = current_data["weather"][0]["main"]

        result = {
            "query": query,
            "city": final_city_name,
            "lat": lat or current_data.get("coord", {}).get("lat", 0),
            "lon": lon or current_data.get("coord", {}).get("lon", 0),
            "temp": round(current_data["main"]["temp"]),
            "feels_like": round(current_data["main"]["feels_like"]),
            "max_today": round(current_data["main"]["temp_max"]),
            "min_today": round(current_data["main"]["temp_min"]),
            "time_text": f"{days_names[current_city_time.weekday()]} {current_city_time.strftime('%I:%M %p')}",
            "condition": current_data["weather"][0]["description"].title(),
            "cond_type": cond_main.lower(),
            "time_phase": time_phase,
            "icon": WeatherProvider._get_icon(cond_main),
            "wind": round(current_data.get("wind", {}).get("speed", 0) * 3.6, 1),
            "humidity": current_data["main"]["humidity"],
            "aqi": aqi_info,
            "sun": sun_data,
            "daily": daily_forecast,
            "hourly": hourly_forecast
        }

        CACHE[cache_key] = (result, time.time())
        return result

    @staticmethod
    def _get_icon(main_status: str) -> str:
        icons = {
            "Clear": "☀️", "Clouds": "⛅", "Rain": "🌧️", "Drizzle": "🌦️",
            "Thunderstorm": "⛈️", "Snow": "❄️", "Mist": "🌫️", "Fog": "🌫️", "Haze": "🌫️"
        }
        return icons.get(main_status, "🌤️")