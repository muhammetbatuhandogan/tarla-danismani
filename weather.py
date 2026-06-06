"""
Open-Meteo entegrasyonu
Ucretsiz, API key gerektirmez.
"""
import httpx
from datetime import date, timedelta
from typing import Optional

IL_KOORDINATLARI: dict[str, tuple[float, float]] = {
    "Adana": (37.00, 35.32),
    "Adiyaman": (37.76, 38.28),
    "Afyonkarahisar": (38.75, 30.56),
    "Agri": (39.72, 43.05),
    "Aksaray": (38.37, 34.04),
    "Amasya": (40.65, 35.84),
    "Ankara": (39.93, 32.86),
    "Antalya": (36.88, 30.71),
    "Ardahan": (41.11, 42.70),
    "Artvin": (41.18, 41.82),
    "Aydin": (37.84, 27.85),
    "Balikesir": (39.65, 27.88),
    "Bartin": (41.63, 32.34),
    "Batman": (37.88, 41.14),
    "Bayburt": (40.26, 40.22),
    "Bilecik": (40.15, 30.07),
    "Bingol": (38.89, 40.50),
    "Bitlis": (38.39, 42.12),
    "Bolu": (40.74, 31.61),
    "Burdur": (37.72, 30.29),
    "Bursa": (40.18, 29.07),
    "Canakkale": (40.16, 26.41),
    "Cankiri": (40.60, 33.61),
    "Corum": (40.55, 34.96),
    "Denizli": (37.78, 29.09),
    "Diyarbakir": (37.91, 40.23),
    "Duzce": (40.84, 31.16),
    "Edirne": (41.68, 26.56),
    "Elazig": (38.68, 39.23),
    "Erzincan": (39.75, 39.49),
    "Erzurum": (39.90, 41.27),
    "Eskisehir": (39.78, 30.52),
    "Gaziantep": (37.07, 37.38),
    "Giresun": (40.91, 38.39),
    "Gumushane": (40.44, 39.48),
    "Hakkari": (37.57, 43.74),
    "Hatay": (36.20, 36.16),
    "Igdir": (39.92, 44.05),
    "Isparta": (37.76, 30.56),
    "Istanbul": (41.01, 28.98),
    "Izmir": (38.42, 27.13),
    "Kahramanmaras": (37.59, 36.94),
    "Karabuk": (41.21, 32.62),
    "Karaman": (37.18, 33.23),
    "Kars": (40.60, 43.10),
    "Kastamonu": (41.38, 33.78),
    "Kayseri": (38.73, 35.48),
    "Kirikkale": (39.85, 33.52),
    "Kirklareli": (41.73, 27.22),
    "Kirsehir": (39.14, 34.17),
    "Kilis": (36.72, 37.12),
    "Kocaeli": (40.85, 29.88),
    "Konya": (37.87, 32.48),
    "Kutahya": (39.42, 29.98),
    "Malatya": (38.36, 38.31),
    "Manisa": (38.62, 27.43),
    "Mardin": (37.32, 40.73),
    "Mersin": (36.80, 34.63),
    "Mugla": (37.22, 28.36),
    "Mus": (38.74, 41.49),
    "Nevsehir": (38.69, 34.69),
    "Nigde": (37.97, 34.68),
    "Ordu": (40.99, 37.88),
    "Osmaniye": (37.07, 36.25),
    "Rize": (41.02, 40.52),
    "Sakarya": (40.69, 30.44),
    "Samsun": (41.29, 36.33),
    "Siirt": (37.93, 41.95),
    "Sinop": (42.02, 35.15),
    "Sivas": (39.75, 37.02),
    "Sanliurfa": (37.16, 38.80),
    "Sirnak": (37.52, 42.46),
    "Tekirdag": (40.98, 27.51),
    "Tokat": (40.32, 36.55),
    "Trabzon": (41.00, 39.72),
    "Tunceli": (39.11, 39.55),
    "Usak": (38.68, 29.41),
    "Van": (38.49, 43.41),
    "Yalova": (40.65, 29.27),
    "Yozgat": (39.82, 34.81),
    "Zonguldak": (41.46, 31.80),
}

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_koordinat(il: str) -> tuple[float, float]:
    """Il adindan koordinat doner. Bulunamazsa Ankara doner."""
    il_normalized = il.strip().title()
    return IL_KOORDINATLARI.get(il_normalized, (39.93, 32.86))


async def get_forecast(il: str) -> dict:
    """Onumuzdeki 7 gunluk hava tahminini ceker."""
    lat, lon = get_koordinat(il)
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "windspeed_10m_max",
            "et0_fao_evapotranspiration",
        ]),
        "forecast_days": 7,
        "timezone": "Europe/Istanbul",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(FORECAST_URL, params=params)
        resp.raise_for_status()
        return resp.json()


async def get_historical(il: str, start: date, end: Optional[date] = None) -> dict:
    """Gecmis hava verilerini ceker (GDD hesabi icin). Hata durumunda bos doner."""
    _empty = {"daily": {"temperature_2m_max": [], "temperature_2m_min": [], "time": []}}
    lat, lon = get_koordinat(il)
    end = end or (date.today() - timedelta(days=1))
    if start >= end:
        return _empty
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "Europe/Istanbul",
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(ARCHIVE_URL, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return _empty


def hava_ozeti(forecast: dict) -> str:
    """Hava durumunu kisa Turkce metine donusturur."""
    d = forecast.get("daily", {})
    if not d.get("temperature_2m_max"):
        return "Hava verisi alinamadi."

    max_t = max(d["temperature_2m_max"][:7])
    min_t = min(d["temperature_2m_min"][:7])
    total_rain = sum(d["precipitation_sum"][:7])
    max_rain_prob = max(d["precipitation_probability_max"][:7])

    temp_line = f"Bu hafta: {min_t:.0f}C - {max_t:.0f}C"

    if total_rain > 20:
        rain_line = "Yogun yagis bekleniyor"
    elif total_rain > 5:
        rain_line = "Ara ara yagisli"
    elif max_rain_prob > 60:
        rain_line = "Yagmur ihtimali yuksek"
    else:
        rain_line = "Buyuk olcude acik"

    return f"{temp_line}\n{rain_line}"
