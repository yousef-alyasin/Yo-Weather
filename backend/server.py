from fastapi import FastAPI, HTTPException, Query
from api_service import WeatherProvider
from typing import Optional
import httpx
import uvicorn

app = FastAPI(title="Weather API Service")


@app.get("/api/v1/weather")
async def get_weather(
    city: str = Query(..., description="City name"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude")
):
    try:
        data = await WeatherProvider.fetch_weather_data_async(city, lat=lat, lon=lon)
        return {"status": "success", "data": data}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/auto-location")
async def auto_locate():
    """Detect client coordinates using IP geolocator"""
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
    # Default fallback to Amman
    return {"status": "success", "lat": 31.9552, "lon": 35.9450, "city": "عمّان, الأردن"}


@app.get("/api/v1/search")
async def search_cities(q: str = Query(..., min_length=1)):
    """Search for matching cities for autocomplete dropdown"""
    try:
        search_query = q.strip().lower()
        aliases = {
            "salt": "As-Salt",
            "السلط": "As-Salt",
            "سلط": "As-Salt",
            "عمان": "Amman",
            "عَمّان": "Amman"
        }
        search_query = aliases.get(search_query, search_query)

        url = "https://geocoding-api.open-meteo.com/v1/search"
        headers = {"User-Agent": "WeatherApp/2.0"}
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

        return {"results": structured, "suggestions": [x["label"] for x in structured]}
    except Exception:
        return {"results": [], "suggestions": []}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)