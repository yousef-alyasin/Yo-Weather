import sys
import os

# Add backend directory to path so frontend can invoke functions directly or via API
BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.api_service import WeatherProvider
import httpx


class WeatherApiClient:
    @staticmethod
    async def get_weather_async(city: str, lat: float = None, lon: float = None) -> dict:
        """Direct async call to WeatherProvider engine"""
        return await WeatherProvider.fetch_weather_data_async(city, lat=lat, lon=lon)

    @staticmethod
    async def search_cities_async(query: str) -> list:
        """Fetch city suggestions for autocomplete"""
        search_query = query.strip().lower()
        aliases = {
            "salt": "As-Salt",
            "السلط": "As-Salt",
            "سلط": "As-Salt",
            "عمان": "Amman",
            "عَمّان": "Amman"
        }
        search_query = aliases.get(search_query, search_query)

        url = "https://geocoding-api.open-meteo.com/v1/search"
        headers = {"User-Agent": "WeatherClient/2.0"}
        params = {"name": search_query, "count": 6, "language": "ar", "format": "json"}

        async with httpx.AsyncClient(timeout=2.5) as client:
            res = await client.get(url, params=params, headers=headers)
            results = res.json().get("results", []) if res.status_code == 200 else []

            if not results:
                params["language"] = "en"
                res_en = await client.get(url, params=params, headers=headers)
                results = res_en.json().get("results", []) if res_en.status_code == 200 else []

        structured = []
        for r in results:
            name = r.get("name", "")
            country = r.get("country", "")
            admin = r.get("admin1", "")
            parts = [name]
            if admin and admin != name:
                parts.append(admin)
            if country:
                parts.append(country)
            structured.append({
                "label": " - ".join(parts),
                "lat": r.get("latitude"),
                "lon": r.get("longitude")
            })

        return structured

    @staticmethod
    async def auto_locate_async() -> dict:
        """Detect coordinates automatically via IP"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get("http://ip-api.com/json/")
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "success":
                        return {
                            "lat": float(data.get("lat")),
                            "lon": float(data.get("lon")),
                            "city": f"{data.get('city')}, {data.get('country')}"
                        }
        except Exception:
            pass
        return {"lat": 31.9552, "lon": 35.9450, "city": "عمّان, الأردن"}