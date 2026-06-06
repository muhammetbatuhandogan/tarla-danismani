"""
Open-Meteo entegrasyonu
Ücretsiz, API key gerektirmez.
"""
import httpx
from datetime import date, timedelta
from typing import Optional

# Türkiye illeri → (enlem, boylam)
IL_KOORDINATLARI: dict[str, tuple[float, float]] = {
    "Adana": (37.00, 35.32),
    "Adıyaman": (37.76, 38.28),
    "Afyonkarahisar": (38.75, 30.56),
    "Ağrı": (39.72, 43.05),
    "Aksaray": (38.37, 34.04),
    "Amasya": (40.65, 35.84),
    "Ankara": (39.93, 32.86),
    "Antalya": (36.88, 30.71),
    "Ardahan": (41.11, 42.70),
    "Artvin": (41.18, 41.82),
    "Aydın": (37.84, 27.85),
    "Balıkesir": (39.65, 27.88),
    "Bartın": (41.63, 32.34),
    "Batman": (37.88, 41.14),
    "Bayburt": (40.26, 40.22),
    "Bilecik": (40.15, 30.07),
    "Bingöl": (38.89, 40.50),
    "Bitlis": (38.39, 42.12),
    "Bolu": (40.74, 31.61),
    "Burdur": (37.72, 30.29),
    "Bursa": (40.18, 29.07),
    "Çanakkale": (40.16, 26.41),
    "Çankırı": (40.60, 33.61),
    "Çorum": (40.55, 34.96),
    "Denizli": (37.78, 29.09),
    "Diyarbakır": (37.91, 40.23),
    "Düzce": (40.84, 31.16),
    "Edirne": (41.68, 26.56),
    "Elazığ": (38.68, 39.23),
    "Erzincan": (39.75, 39.49),
    "Erzurum": (39.90, 41.27),
    "Eskişehir": (39.78, 30.52),
    "Gaziantep": (37.07, 37.38),
    "Giresun": (40.91, 38.39),
    "Gümüşhane": (40.44, 39.48),
    "Hakkari": (37.57, 43.74),
    "Hatay": (36.20, 36.16),
    "Iğdır": (39.92, 44.05),
    "Isparta": (37.76, 30.56),
    "İstanbul": (41.01, 28.98),
    "İzmir": (38.42, 27.13),
    "Kahramanmaraş": (37.59, 36.94),
    "Karabük": (41.21, 32.62),
    "Karaman": (37.18, 33.23),
    "Kars": (40.60, 43.10),
    "Kastamonu": (41.38, 33.78),
    "Kayseri": (38.73, 35.48),
    "Kırıkkale": (39.85, 33.52),
    "Kırklareli": (41.73, 27.22),
    "Kırşehir": (39.14, 34.17),
    "Kilis": (36.72, 37.12),
    "Kocaeli": (40.85, 29.88),
    "Konya": (37.87, 32.48),
    "Kütahya": (39.42, 29.98),
    "Malatya": (38.36, 38.31),
    "Manisa": (38.62, 27.43),
    "Mardin": (37.32, 40.73),
    "Mersin": (36.80, 34.63),
    "Muğla": (37.22, 28.36),
    "Muş": (38.74, 41.49),
    "Nevşehir": (38.69, 34.69),
    "Niğde": (37.97, 34.68),
    "Ordu": (40.99, 37.88),
    "Osmaniye": (37.07, 36.25),
    "Rize": (41.02, 40.52),
    "Sakarya": (40.69, 30.44),
    "Samsun": (41.29, 36.33),
    "Siirt": (37.93, 41.95),
    "Sinop": (42.02, 35.15),
    "Sivas": (39.75, 37.02),
    "Şanlıurfa": (37.16, 38.80),
    "Şırnak": (37.52, 42.46),
    "Tekirdağ": (40.98, 27.51),
    "Tokat": (40.32, 36.55),
    "Trabzon": (41.00, 39.72),
    "Tunceli": (39.11, 39.55),
    "Uşak": (38.68, 29.41),
    "Van": (38.49, 43.41),
    "Yalova": (40.65, 29.27),
    "Yozgat": (39.82, 34.81),
    "Zonguldak": (41.46, 31.80),
}

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_koordinat(il: str) -> tuple[float, float]:
    """İl adından koordinat döner. Bulunamazsa Ankara döner."""
    # Büyük/küçük harf normalizasyonu
    il_normalized = il.strip().title()
    # Türkçe karakter normalizasyonu için birkaç yaygın hata
    replacements = {"Istanbul": "İstanbul", "Izmir": "İzmir"}
    il_normalized = replacements.get(il_normalized, il_normalized)
    return IL_KOORDINATLARI.get(il_normalized, (39.93, 32.86))  # default: Ankara


async def get_forecast(il: str) -> dict:
    """Önümüzdeki 7 günlük hava tahminini çeker."""
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
    """Geçmiş hava verilerini çeker (GDD hesabı için). Hata durumunda boş döner."""
    _empty = {"daily": {"temperature_2m_max": [], "temperature_2m_min": [], "time": []}}
    lat, lon = get_koordinat(il)
    end = end or (date.today() - timedelta(days=1))
    # Archive API bir gün geriden gelir
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
        # Archive API erişilemezse GDD sıfırdan başlar, forecast yine de çalışır
        return _empty


def hava_ozeti(forecast: dict) -> str:
    """Hava durumunu kısa Türkçe metine dönüştürür."""
    d = forecast.get("daily", {})
    if not d.get("temperature_2m_max"):
        return "Hava verisi alınamadı."

    max_t = max(d["temperature_2m_max"][:7])
    min_t = min(d["temperature_2m_min"][:7])
    total_rain = sum(d["precipitation_sum"][:7])
    max_rain_prob = max(d["precipitation_probability_max"][:7])

    temp_line = f"🌡️ Bu hafta: {min_t:.0f}°C — {max_t:.0f}°C"

    if total_rain > 20:
        rain_line = "🌧️ Yoğun yağış bekleniyor"
    elif total_rain > 5:
        rain_line = "🌦️