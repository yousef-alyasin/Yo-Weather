import sys
import os
import httpx

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.api_service import WeatherProvider


class WeatherApiClient:
    @staticmethod
    async def get_weather_async(city: str, lat: float = None, lon: float = None, lang: str = "en") -> dict:
        return await WeatherProvider.fetch_weather_data_async(city, lat=lat, lon=lon, lang=lang)

    @staticmethod
    async def search_cities_async(query: str) -> list:
        clean_q = query.strip()
        if len(clean_q) < 2:
            return []

        url = "https://photon.komoot.io/api/"
        params = {
            "q": clean_q,
            "limit": 15,
            "lang": "default"
        }
        headers = {"User-Agent": "YoWeather/5.0"}

        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                res = await client.get(url, params=params, headers=headers)
                if res.status_code != 200:
                    return []
                data = res.json()

            features = data.get("features", [])
            if not features:
                return []

            filtered_features = []
            excluded_types = ["mall", "shop", "amenity", "commercial", "supermarket", "parking"]

            for item in features:
                props = item.get("properties", {})
                osm_value = props.get("osm_value", "")
                osm_key = props.get("osm_key", "")
                
                if osm_value in excluded_types or osm_key in ["shop", "amenity", "leisure"]:
                    continue
                filtered_features.append(item)

            if not filtered_features:
                filtered_features = features

            def rank_feature(item):
                props = item.get("properties", {})
                osm_type = props.get("osm_value", "")
                name = props.get("name", "")
                
                score = 0
                if osm_type == "capital" or props.get("city") == name:
                    score += 1000000
                elif osm_type == "city":
                    score += 500000
                elif osm_type == "administrative":
                    score += 200000
                elif osm_type == "locality":
                    score += 50000
                return score

            sorted_features = sorted(filtered_features, key=rank_feature, reverse=True)

            structured = []
            seen_coords = set()

            for item in sorted_features:
                props = item.get("properties", {})
                coords = item.get("geometry", {}).get("coordinates", [0, 0])
                lon, lat = coords[0], coords[1]

                coord_key = (round(lat, 2), round(lon, 2))
                if coord_key in seen_coords:
                    continue
                seen_coords.add(coord_key)

                name = props.get("name", "")
                country = props.get("country", "")
                state = props.get("state", "")

                parts = [name]
                if state and state != name:
                    parts.append(state)
                if country and country != name:
                    parts.append(country)

                label = " - ".join(parts)
                structured.append({
                    "label": label,
                    "lat": lat,
                    "lon": lon
                })

            return structured[:6]

        except Exception as e:
            print("Search error:", e)
            return []

    @staticmethod
    async def auto_locate_async() -> dict:
        lat, lon = 31.9552, 35.9450
        city_name = "عمان، الأردن"
        
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                res = await client.get("http://ip-api.com/json/")
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "success":
                        lat = float(data.get("lat"))
                        lon = float(data.get("lon"))
                        
                        rev_url = "https://photon.komoot.io/reverse/"
                        rev_res = await client.get(rev_url, params={"lat": lat, "lon": lon, "lang": "ar"})
                        if rev_res.status_code == 200:
                            features = rev_res.json().get("features", [])
                            if features:
                                props = features[0].get("properties", {})
                                name = props.get("name", data.get("city", ""))
                                country = props.get("country", data.get("country", ""))
                                if name and country:
                                    city_name = f"{name}, {country}"
                                elif name:
                                    city_name = name
                        else:
                            city_name = f"{data.get('city')}, {data.get('country')}"
        except Exception as e:
            print("Auto-locate error:", e)

        return {
            "lat": lat,
            "lon": lon,
            "city": city_name
        }