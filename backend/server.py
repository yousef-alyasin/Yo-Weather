from fastapi import FastAPI, HTTPException, Query
from api_service import WeatherProvider
from typing import Optional
import httpx
import uvicorn

app = FastAPI(title="Yo Weather API Service")

@app.get("/api/v1/weather")
async def get_weather(
    city: str = Query(..., description="City name"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    lang: str = Query("en", description="Language")
):
    try:
        if lat is not None and lon is not None:
            data = await WeatherProvider.fetch_weather_data_async(city="", lat=lat, lon=lon, lang=lang)
            return {"status": "success", "data": data}

        clean_city_name = city.split("-")[0].strip() if city else city
        data = await WeatherProvider.fetch_weather_data_async(clean_city_name, lat=None, lon=None, lang=lang)
        return {"status": "success", "data": data}

    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/auto-location")
async def auto_locate():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get("http://ip-api.com/json/")
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    return {
                        "status": "success",
                        "lat": float(data.get("lat")),
                        "lon": float(data.get("lon")),
                        "city": f"{data.get('city')}, {data.get('country')}"
                    }
    except Exception:
        pass
    return {"status": "success", "lat": 31.9552, "lon": 35.9450, "city": "Amman, Jordan"}

@app.get("/api/v1/search")
async def search_cities(q: str = Query(..., min_length=2)):
    try:
        clean_q = q.strip()
        if len(clean_q) < 2:
            return {"results": [], "suggestions": []}

        url = "https://geocoding-api.open-meteo.com/v1/search"
        headers = {"User-Agent": "YoWeather/5.0"}
        params = {"name": clean_q, "count": 10, "language": "ar", "format": "json"}

        async with httpx.AsyncClient(timeout=3.5) as client:
            res = await client.get(url, params=params, headers=headers)
            data = res.json() if res.status_code == 200 else {}
            results = data.get("results", [])

        if not results:
            return {"results": [], "suggestions": []}

        structured = []
        seen_labels = set()
        for r in results[:5]:
            name = r.get("name", "")
            country = r.get("country", "")
            admin = r.get("admin1", "")

            parts = [name]
            if admin and admin != name:
                parts.append(admin)
            if country and country != name:
                parts.append(country)

            label = " - ".join(parts)
            if label not in seen_labels:
                seen_labels.add(label)
                structured.append({
                    "label": label,
                    "lat": r.get("latitude"),
                    "lon": r.get("longitude")
                })

        return {
            "results": structured,
            "suggestions": [x["label"] for x in structured]
        }

    except Exception as e:
        print("Search error:", e)
        return {"results": [], "suggestions": []}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)