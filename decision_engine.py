"""
Kural tabanlı karar motoru.
Akış diyagramları 02 (Sulama), 03 (Don), 04 (Sıcaklık), 05 (İlaçlama), 07 (Karar Motoru)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Oneri:
    tip: str              # 'sula' | 'sulama' | 'don' | 'sicaklik' | 'ilacla' | 'normal'
    renk: str             # 'green' | 'white' | 'yellow' | 'red'
    baslik: str
    detay: str
    hava_ozeti: str
    ilacla_not: Optional[str] = None   # Ekstra ilaçlama notu (varsa)
    gdd_ozeti: Optional[str] = None


def karar_ver(forecast: dict, gdd_info: dict) -> Oneri:
    """
    Hava tahmini + GDD bilgisinden aksiyonel öneri üretir.

    Öncelik sırası (yüksekten düşüğe):
    1. Don riski (kritik kırmızı)
    2. Aşırı sıcaklık (kırmızı / sarı)
    3. Yağmur var → sulama yok (beyaz)
    4. Sulama gerekiyor (yeşil)
    5. Normal / izle (beyaz)
    """
    d = forecast.get("daily", {})
    if not d.get("temperature_2m_max"):
        return Oneri(
            tip="hata", renk="white",
            baslik="⚙️ Veri alınamadı.",
            detay="Hava verisi şu an alınamıyor. Lütfen daha sonra tekrar deneyin.",
            hava_ozeti="",
        )

    tmax_list = d["temperature_2m_max"]
    tmin_list = d["temperature_2m_min"]
    rain_list = d["precipitation_sum"]
    rain_prob_list = d["precipitation_probability_max"]
    wind_list = d["windspeed_10m_max"]

    tonight_min = tmin_list[0]
    today_max = tmax_list[0]
    next_48h_rain = sum(rain_list[:2])
    next_7d_rain = sum(rain_list[:7])
    max_rain_prob_48h = max(rain_prob_list[:2]) if rain_prob_list else 0
    today_wind = wind_list[0]
    week_min = min(tmin_list[:7])
    week_max = max(tmax_list[:7])

    kritik_donem = gdd_info.get("kritik_donem", False)
    evre_isim = gdd_info.get("evre_isim", "")
    gdd_ozeti_str = f"🌱 Büyüme evresi: {evre_isim} (GDD: {gdd_info.get('gdd_birikmis', 0):.0f})"

    # Hava özetini oluştur
    temp_line = f"🌡️ Bu hafta: {week_min:.0f}°C — {week_max:.0f}°C"
    if next_7d_rain > 20:
        rain_line = "🌧️ Yoğun yağış bekleniyor"
    elif next_7d_rain > 5:
        rain_line = "🌦️ Ara ara yağışlı"
    elif max_rain_prob_48h > 60:
        rain_line = f"⛅ Yağmur ihtimali yüksek (%{max_rain_prob_48h:.0f})"
    else:
        rain_line = "☀️ Büyük ölçüde açık"
    hw_ozet = f"{temp_line}\n{rain_line}"

    # ─── 1. DON RİSKİ (Akış 03) ────────────────────────────────────────────────
    if tonight_min <= 2:
        if tonight_min <= 0:
            baslik = "⚠️ Dikkat: Don riski var!"
            detay = (
                f"Bu gece sıcaklık {tonight_min:.0f}°C'ye düşecek — bitkileriniz zarar görebilir.\n"
                "Mümkünse akşam sulayın: toprak ısısı dondan korur."
            )
        else:
            baslik = "❄️ Don riski yaklaşıyor."
            detay = (
                f"Bu gece sıcaklık {tonight_min:.0f}°C'ye düşebilir.\n"
                "Hassas dönemde ise akşam sulamayı düşünün."
            )
        return Oneri(
            tip="don", renk="red",
            baslik=baslik, detay=detay,
            hava_ozeti=hw_ozet, gdd_ozeti=gdd_ozeti_str,
        )

    # ─── 2. AŞIRI SICAKLIK (Akış 04) ───────────────────────────────────────────
    if today_max >= 35:
        if kritik_donem:
            baslik = "🌡️ Aşırı sıcaklık — bitki stresi!"
            detay = (
                f"Bugün sıcaklık {today_max:.0f}°C'ye çıkacak, bitki kritik dönemde.\n"
                "11:00–17:00 arasında sulama YAPMAYIN. Sabah erken veya akşam sulayın."
            )
        else:
            baslik = "☀️ Sıcaklık yüksek."
            detay = (
                f"Bugün {today_max:.0f}°C bekleniyor.\n"
                "Sulama yapacaksanız sabah erken tercih edin."
            )
        return Oneri(
            tip="sicaklik", renk="red" if kritik_donem else "yellow",
            baslik=baslik, detay=detay,
            hava_ozeti=hw_ozet, gdd_ozeti=gdd_ozeti_str,
        )

    # ─── 3. SULAMA GEREKSİZ — YAĞMUR VAR (Akış 02) ────────────────────────────
    yagmur_gelecek = next_48h_rain > 10 or max_rain_prob_48h >= 70
    toprak_nemli = next_7d_rain > 20  # geçen hafta çok yağdıysa toprak zaten nemli

    if yagmur_gelecek:
        rain_days = [
            d for i, d in enumerate(["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
            if i < len(rain_list) and rain_list[i] > 3
        ]
        gun_str = " ve ".join(rain_days[:2]) if rain_days else "yakın günlerde"
        baslik = "☔ Bu hafta sulamayın."
        detay = (
            f"{gun_str} yağmur bekleniyor ({next_48h_rain:.0f} mm).\n"
            "Toprak zaten yeterince nemli olacak, su israfı önlenmiş olur."
        )
        return Oneri(
            tip="sulama", renk="white",
            baslik=baslik, detay=detay,
            hava_ozeti=hw_ozet, gdd_ozeti=gdd_ozeti_str,
        )

    # ─── 4. SULAMA KARAR (Akış 02) ─────────────────────────────────────────────
    if kritik_donem:
        baslik = "🚿 Bugün sulayın — kritik dönem!"
        detay = (
            f"Bitki şu an {evre_isim} evresinde — su ihtiyacı yüksek.\n"
            f"Hava kuru ({next_7d_rain:.0f} mm bekleniyor). En iyi zaman: sabah erken (07:00 öncesi)."
        )
        renk = "green"
    elif today_max >= 28:
        baslik = "🚿 Bugün sulayın."
        detay = (
            f"Hava sıcak ({today_max:.0f}°C) ve bu hafta yağmur yok.\n"
            "Sabah erken sulama önerilir."
        )
        renk = "green"
    else:
        baslik = "🚿 Bu hafta sulayın."
        detay = (
            "Hava kuru, yağmur yok. Sulamayı bu hafta içinde yapın.\n"
            "En verimli zaman: sabah erken veya akşam serin saatler."
        )
        renk = "green"

    # ─── İLAÇLAMA EK NOTU (Akış 05) ───────────────────────────────────────────
    ilacla_not = None
    ilacla_uygun = (
        next_48h_rain < 5
        and today_wind < 15
        and 10 <= today_max <= 30
        and not kritik_donem  # kritik dönemde ilaçlamayı ayrı belirt
    )
    if ilacla_uygun:
        ilacla_not = (
            "💊 İlaçlama için uygun koşullar: rüzgar düşük, yağmur yok.\n"
            "Sabah erken veya akşam uygulayın."
        )

    return Oneri(
        tip="sula", renk=renk,
        baslik=baslik, detay=detay,
        hava_ozeti=hw_ozet, gdd_ozeti=gdd_ozeti_str,
        ilacla_not=ilacla_not,
    )
