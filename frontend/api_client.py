import sys
import os
import httpx

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.api_service import WeatherProvider, API_KEY


class WeatherApiClient:
    @staticmethod
    async def get_weather_async(city: str, lat: float = None, lon: float = None, lang: str = "en", display_name: str = None) -> dict:
        return await WeatherProvider.fetch_weather_data_async(city, lat=lat, lon=lon, display_name=display_name, lang=lang)

    @staticmethod
    async def search_cities_async(query: str, lang: str = "en") -> list:
        clean_q = query.strip()
        if len(clean_q) < 2:
            return []

        if not API_KEY:
            return []

        url = "https://api.openweathermap.org/geo/1.0/direct"
        params = {
            "q": clean_q,
            "limit": 5,
            "appid": API_KEY
        }

        country_names_ar = {
            "AF": "أفغانستان", "AL": "ألبانيا", "DZ": "الجزائر", "AD": "أندورا",
            "AO": "أنغولا", "AG": "أنتيغوا وباربودا", "AR": "الأرجنتين", "AM": "أرمينيا",
            "AU": "أستراليا", "AT": "النمسا", "AZ": "أذربيجان", "BS": "الباهاما",
            "BH": "البحرين", "BD": "بنغلاديش", "BB": "باربادوس", "BY": "بيلاروسيا",
            "BE": "بلجيكا", "BZ": "بليز", "BJ": "بنين", "BT": "بوتان",
            "BO": "بوليفيا", "BA": "البوسنة والهرسك", "BW": "بوتسوانا", "BR": "البرازيل",
            "BN": "بروناي", "BG": "بلغاريا", "BF": "بوركينا فاسو", "BI": "بوروندي",
            "CV": "الرأس الأخضر", "KH": "كمبوديا", "CM": "الكاميرون", "CA": "كندا",
            "CF": "أفريقيا الوسطى", "TD": "تشاد", "CL": "تشيلي", "CN": "الصين",
            "CO": "كولومبيا", "KM": "جزر القمر", "CG": "الكونغو", "CD": "الكونغو الديمقراطية",
            "CR": "كوستاريكا", "CI": "ساحل العاج", "HR": "كرواتيا", "CU": "كوبا",
            "CY": "قبرص", "CZ": "التشيك", "DK": "الدنمارك", "DJ": "جيبوتي",
            "DM": "دومينيكا", "DO": "الدومينيكان", "EC": "الإكوادور", "EG": "مصر",
            "SV": "السلفادور", "GQ": "غينيا الاستوائية", "ER": "إريتريا", "EE": "إستونيا",
            "SZ": "إيسواتيني", "ET": "إثيوبيا", "FJ": "فيجي", "FI": "فنلندا",
            "FR": "فرنسا", "GA": "الغابون", "GM": "غامبيا", "GE": "جورجيا",
            "DE": "ألمانيا", "GH": "غانا", "GR": "اليونان", "GD": "غرينادا",
            "GT": "غواتيمالا", "GN": "غينيا", "GW": "غينيا بيساو", "GY": "غيانا",
            "HT": "هايتي", "HN": "هندوراس", "HU": "المجر", "IS": "آيسلندا",
            "IN": "الهند", "ID": "إندونيسيا", "IR": "إيران", "IQ": "العراق",
            "IE": "أيرلندا", "IL": "إسرائيل", "IT": "إيطاليا", "JM": "جامايكا",
            "JP": "اليابان", "JO": "الأردن", "KZ": "كازاخستان", "KE": "كينيا",
            "KI": "كيريباتي", "KP": "كوريا الشمالية", "KR": "كوريا الجنوبية", "KW": "الكويت",
            "KG": "قرغيزستان", "LA": "لاوس", "LV": "لاتفيا", "LB": "لبنان",
            "LS": "ليسوتو", "LR": "ليبيريا", "LY": "ليبيا", "LI": "ليختنشتاين",
            "LT": "ليتوانيا", "LU": "لوكسمبورغ", "MG": "مدغشقر", "MW": "مالاوي",
            "MY": "ماليزيا", "MV": "جزر المالديف", "ML": "مالي", "MT": "مالطا",
            "MR": "موريتانيا", "MU": "موريشيوس", "MX": "المكسيك", "FM": "ميكرونيزيا",
            "MD": "مولدوفا", "MC": "موناكو", "MN": "منغوليا", "ME": "الجبل الأسود",
            "MA": "المغرب", "MZ": "موزمبيق", "MM": "ميانمار", "NA": "ناميبيا",
            "NP": "نيبال", "NL": "هولندا", "NZ": "نيوزيلندا", "NI": "نيكاراغوا",
            "NE": "النيجر", "NG": "نيجيريا", "NO": "النرويج", "OM": "عمان",
            "PK": "باكستان", "PS": "فلسطين", "PA": "بنما", "PG": "بابوا غينيا الجديدة",
            "PY": "باراغواي", "PE": "بيرو", "PH": "الفلبين", "PL": "بولندا",
            "PT": "البرتغال", "QA": "قطر", "RO": "رومانيا", "RU": "روسيا",
            "RW": "رواندا", "SA": "السعودية", "SN": "السنغال", "RS": "صربيا",
            "SG": "سنغافورة", "SK": "سلوفاكيا", "SI": "سلوفينيا", "SO": "الصومال",
            "ZA": "جنوب أفريقيا", "ES": "إسبانيا", "LK": "سريلانكا", "SD": "السودان",
            "SE": "السويد", "CH": "سويسرا", "SY": "سوريا", "TW": "تايوان",
            "TJ": "طاجيكستان", "TZ": "تنزانيا", "TH": "تايلاند", "TL": "تيمور الشرقية",
            "TG": "توغو", "TN": "تونس", "TR": "تركيا", "TM": "تركمانستان",
            "UG": "أوغندا", "UA": "أوكرانيا", "AE": "الإمارات العربية المتحدة",
            "GB": "المملكة المتحدة", "US": "الولايات المتحدة الأمريكية", "UY": "أوروغواي",
            "UZ": "أوزبكستان", "VE": "فنزويلا", "VN": "فيتنام", "YE": "اليمن",
            "ZM": "زامبيا", "ZW": "زيمبابوي"
        }

        country_names_en = {
            "AF": "Afghanistan", "AL": "Albania", "DZ": "Algeria", "AD": "Andorra",
            "AO": "Angola", "AG": "Antigua and Barbuda", "AR": "Argentina", "AM": "Armenia",
            "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan", "BS": "Bahamas",
            "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados", "BY": "Belarus",
            "BE": "Belgium", "BZ": "Belize", "BJ": "Benin", "BT": "Bhutan",
            "BO": "Bolivia", "BA": "Bosnia and Herzegovina", "BW": "Botswana", "BR": "Brazil",
            "BN": "Brunei", "BG": "Bulgaria", "BF": "Burkina Faso", "BI": "Burundi",
            "CV": "Cape Verde", "KH": "Cambodia", "CM": "Cameroon", "CA": "Canada",
            "CF": "Central African Republic", "TD": "Chad", "CL": "Chile", "CN": "China",
            "CO": "Colombia", "KM": "Comoros", "CG": "Congo", "CD": "Democratic Republic of the Congo",
            "CR": "Costa Rica", "CI": "Ivory Coast", "HR": "Croatia", "CU": "Cuba",
            "CY": "Cyprus", "CZ": "Czech Republic", "DK": "Denmark", "DJ": "Djibouti",
            "DM": "Dominica", "DO": "Dominican Republic", "EC": "Ecuador", "EG": "Egypt",
            "SV": "El Salvador", "GQ": "Equatorial Guinea", "ER": "Eritrea", "EE": "Estonia",
            "SZ": "Eswatini", "ET": "Ethiopia", "FJ": "Fiji", "FI": "Finland",
            "FR": "France", "GA": "Gabon", "GM": "Gambia", "GE": "Georgia",
            "DE": "Germany", "GH": "Ghana", "GR": "Greece", "GD": "Grenada",
            "GT": "Guatemala", "GN": "Guinea", "GW": "Guinea-Bissau", "GY": "Guyana",
            "HT": "Haiti", "HN": "Honduras", "HU": "Hungary", "IS": "Iceland",
            "IN": "India", "ID": "Indonesia", "IR": "Iran", "IQ": "Iraq",
            "IE": "Ireland", "IL": "Israel", "IT": "Italy", "JM": "Jamaica",
            "JP": "Japan", "JO": "Jordan", "KZ": "Kazakhstan", "KE": "Kenya",
            "KI": "Kiribati", "KP": "North Korea", "KR": "South Korea", "KW": "Kuwait",
            "KG": "Kyrgyzstan", "LA": "Laos", "LV": "Latvia", "LB": "Lebanon",
            "LS": "Lesotho", "LR": "Liberia", "LY": "Libya", "LI": "Liechtenstein",
            "LT": "Lithuania", "LU": "Luxembourg", "MG": "Madagascar", "MW": "Malawi",
            "MY": "Malaysia", "MV": "Maldives", "ML": "Mali", "MT": "Malta",
            "MR": "Mauritania", "MU": "Mauritius", "MX": "Mexico", "FM": "Micronesia",
            "MD": "Moldova", "MC": "Monaco", "MN": "Mongolia", "ME": "Montenegro",
            "MA": "Morocco", "MZ": "Mozambique", "MM": "Myanmar", "NA": "Namibia",
            "NP": "Nepal", "NL": "Netherlands", "NZ": "New Zealand", "NI": "Nicaragua",
            "NE": "Niger", "NG": "Nigeria", "NO": "Norway", "OM": "Oman",
            "PK": "Pakistan", "PS": "Palestine", "PA": "Panama", "PG": "Papua New Guinea",
            "PY": "Paraguay", "PE": "Peru", "PH": "Philippines", "PL": "Poland",
            "PT": "Portugal", "QA": "Qatar", "RO": "Romania", "RU": "Russia",
            "RW": "Rwanda", "SA": "Saudi Arabia", "SN": "Senegal", "RS": "Serbia",
            "SG": "Singapore", "SK": "Slovakia", "SI": "Slovenia", "SO": "Somalia",
            "ZA": "South Africa", "ES": "Spain", "LK": "Sri Lanka", "SD": "Sudan",
            "SE": "Sweden", "CH": "Switzerland", "SY": "Syria", "TW": "Taiwan",
            "TJ": "Tajikistan", "TZ": "Tanzania", "TH": "Thailand", "TL": "East Timor",
            "TG": "Togo", "TN": "Tunisia", "TR": "Turkey", "TM": "Turkmenistan",
            "UG": "Uganda", "UA": "Ukraine", "AE": "United Arab Emirates",
            "GB": "United Kingdom", "US": "United States", "UY": "Uruguay",
            "UZ": "Uzbekistan", "VE": "Venezuela", "VN": "Vietnam", "YE": "Yemen",
            "ZM": "Zambia", "ZW": "Zimbabwe"
        }

        country_names = country_names_ar if lang == "ar" else country_names_en

        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                res = await client.get(url, params=params)
                if res.status_code != 200:
                    return []
                locations = res.json()

            if not locations:
                return []

            structured = []
            seen_coords = set()

            for item in locations:
                lat = item.get("lat")
                lon = item.get("lon")
                if lat is None or lon is None:
                    continue

                coord_key = (round(lat, 2), round(lon, 2))
                if coord_key in seen_coords:
                    continue
                seen_coords.add(coord_key)

                name = item.get("name", "")
                code = item.get("country", "").upper()
                state = item.get("state", "")
                local_names = item.get("local_names", {})
                
                if lang == "ar":
                    display_name = local_names.get("ar", name)
                else:
                    display_name = name

                country_full = country_names.get(code, code)

                parts = [display_name]
                if state and state != display_name:
                    parts.append(state)
                if country_full:
                    parts.append(country_full)

                label = " - ".join(parts)
                structured.append({
                    "label": label,
                    "lat": lat,
                    "lon": lon
                })

            return structured[:5]

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
                        
                        url = "https://api.openweathermap.org/geo/1.0/reverse"
                        rev_res = await client.get(url, params={"lat": lat, "lon": lon, "limit": 1, "appid": API_KEY})
                        if rev_res.status_code == 200:
                            rev_data = rev_res.json()
                            if rev_data:
                                item = rev_data[0]
                                name = item.get("local_names", {}).get("ar", item.get("name", ""))
                                country = item.get("country", "")
                                if name and country:
                                    city_name = f"{name}, {country}"
                                elif name:
                                    city_name = name
        except Exception as e:
            print("Auto-locate error:", e)

        return {
            "lat": lat,
            "lon": lon,
            "city": city_name
        }