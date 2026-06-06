"""
GDD (Growing Degree Days) hesabı ve büyüme evresi belirleme.
Akış diyagramı 06 — GDD Tabanlı Büyüme Evresi Akışı
"""
from datetime import date
from typing import Optional

AY_MAP = {
    "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4,
    "Mayıs": 5, "Haziran": 6, "Temmuz": 7, "Ağustos": 8,
    "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12,
}

# Her ürün için: Tbase (°C) ve büyüme evreleri (kümülatif GDD eşikleri)
URUN_GDD = {
    "bugday": {
        "isim": "Buğday",
        "tbase": 0,
        "evreler": [
            {"isim": "Çıkış / Çimlenme", "min_gdd": 0,   "max_gdd": 150,  "kritik": False},
            {"isim": "Vejetatif Büyüme",  "min_gdd": 150, "max_gdd": 500,  "kritik": True},
            {"isim": "Çiçeklenme",        "min_gdd": 500, "max_gdd": 800,  "kritik": True},
            {"isim": "Meyve / Hasat",     "min_gdd": 800, "max_gdd": 1400, "kritik": False},
        ],
    },
    "aycicek": {
        "isim": "Ayçiçeği",
        "tbase": 6,
        "evreler": [
            {"isim": "Çıkış / Çimlenme", "min_gdd": 0,   "max_gdd": 200,  "kritik": False},
            {"isim": "Vejetatif Büyüme",  "min_gdd": 200, "max_gdd": 600,  "kritik": True},
            {"isim": "Çiçeklenme",        "min_gdd": 600, "max_gdd": 900,  "kritik": True},
            {"isim": "Tohum Doldurma",    "min_gdd": 900, "max_gdd": 1400, "kritik": False},
        ],
    },
    "pancar": {
        "isim": "Şeker Pancarı",
        "tbase": 3,
        "evreler": [
            {"isim": "Çıkış / Çimlenme", "min_gdd": 0,    "max_gdd": 200,  "kritik": False},
            {"isim": "Vejetatif Büyüme",  "min_gdd": 200,  "max_gdd": 700,  "kritik": True},
            {"isim": "Kök Gelişimi",      "min_gdd": 700,  "max_gdd": 1400, "kritik": True},
            {"isim": "Olgunluk",          "min_gdd": 1400, "max_gdd": 2000, "kritik": False},
        ],
    },
    "misir": {
        "isim": "Mısır",
        "tbase": 10,
        "evreler": [
            {"isim": "Çıkış / Çimlenme", "min_gdd": 0,   "max_gdd": 200,  "kritik": False},
            {"isim": "Vejetatif Büyüme",  "min_gdd": 200, "max_gdd": 600,  "kritik": True},
            {"isim": "Tepe Püskülü",      "min_gdd": 600, "max_gdd": 900,  "kritik": True},
            {"isim": "Koçan Doldurma",    "min_gdd": 900, "max_gdd": 1400, "kritik": True},
        ],
    },
}

# Bilinmeyen ürün için varsayılan
DEFAULT_GDD = {
    "isim": "Genel Ürün",
    "tbase": 5,
    "evreler": [
        {"isim": "Erken Dönem",   "min_gdd": 0,   "max_gdd": 300,  "kritik": False},
        {"isim": "Orta Dönem",    "min_gdd": 300, "max_gdd": 800,  "kritik": True},
        {"isim": "Son Dönem",     "min_gdd": 800, "max_gdd": 1400, "kritik": False},
    ],
}


def normalize_urun(urun: str) -> str:
    """Ürün adını normalize eder."""
    mapping = {
        "buğday": "bugday", "bugday": "bugday",
        "ayçiçeği": "aycicek", "aycicek": "aycicek", "ayçiçek": "aycicek",
        "şeker pancarı": "pancar", "pancar": "pancar",
        "mısır": "misir", "misir": "misir",
    }
    return mapping.get(urun.lower().strip(), urun.lower().strip())


def ekim_tarihi_hesapla(ekim_ayi: str) -> date:
    """Ekim ayı adından ekim tarihini hesaplar (en yakın geçmiş tarih)."""
    ay_no = AY_MAP.get(ekim_ayi, 10)
    today = date.today()

    # Bu yıl veya geçen yılın o ayı — bitki hala tarlada olabilecek mi?
    for year in [today.year, today.year - 1]:
        try:
            ekim = date(year, ay_no, 1)
            if ekim <= today:
                return ekim
        except ValueError:
            pass
    return date(today.year - 1, ay_no, 1)


def hesapla_gdd(max_temps: list[float], min_temps: list[float], tbase: float) -> float:
    """Kümülatif GDD hesaplar."""
    total = 0.0
    for tmax, tmin in zip(max_temps, min_temps):
        daily = max(0.0, (tmax + tmin) / 2 - tbase)
        total += daily
    return total


def buyume_evresi(gdd_birikmis: float, urun_key: str) -> dict:
    """Birikmiş GDD'den büyüme evresini belirler."""
    urun_info = URUN_GDD.get(urun_key, DEFAULT_GDD)
    evreler = urun_info["evreler"]

    mevcut_evre = evreler[-1]  # default: son evre
    for evre in evreler:
        if gdd_birikmis <= evre["max_gdd"]:
            mevcut_evre = evre
            break

    return {
        "urun_isim": urun_info["isim"],
        "evre_isim": mevcut_evre["isim"],
        "kritik_donem": mevcut_evre["kritik"],
        "gdd_birikmis": round(gdd_birikmis, 0),
        "gdd_hedef": mevcut_evre["max_gdd"],
        "tbase": urun_info["tbase"],
    }


def gdd_ozeti(gdd_info: dict) -> str:
    """GDD bilgisini Türkçe kısa metin olarak döner."""
    return (
        f"🌱 Büyüme evresi: {gdd_info['evre_isim']} "
        f"(GDD: {gdd_info['gdd_birikmis']:.0f})"
    )
