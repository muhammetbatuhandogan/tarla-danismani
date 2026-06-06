"""
Tarla Danışmanı — FastAPI Backend
"""
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from weather import get_forecast, get_historical
from gdd import normalize_urun, ekim_tarihi_hesapla, hesapla_gdd, buyume_evresi
from decision_engine import karar_ver
from database import init_db, kayit_ekle, oneri_kaydet


# ── Uygulama başlatma ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Tarla Danışmanı API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic modeller ────────────────────────────────────────────────────────
class KayitIstegi(BaseModel):
    session_id: str | None = None
    il: str
    urun: str
    ekim_ayi: str


class OneriYaniti(BaseModel):
    tip: str
    renk: str
    baslik: str
    detay: str
    hava_ozeti: str
    ilacla_not: str | None
    gdd_ozeti: str | None
    buyume_evresi: str
    gdd_birikmis: float
    il: str
    urun_isim: str
    ekim_tarihi: str


# ── Yardımcı: öneri hesapla ──────────────────────────────────────────────────
async def _oneri_hesapla(il: str, urun: str, ekim_ayi: str) -> tuple[dict, dict]:
    """Hava + GDD verilerini çekip karar verir. (forecast, gdd_info) döner."""
    urun_key = normalize_urun(urun)
    ekim = ekim_tarihi_hesapla(ekim_ayi)

    # Paralel istekler
    import asyncio
    forecast, historical = await asyncio.gather(
        get_forecast(il),
        get_historical(il, ekim),
    )

    hist_d = historical.get("daily", {})
    tmax_h = hist_d.get("temperature_2m_max", [])
    tmin_h = hist_d.get("temperature_2m_min", [])

    from gdd import URUN_GDD, DEFAULT_GDD
    urun_info = URUN_GDD.get(urun_key, DEFAULT_GDD)
    tbase = urun_info["tbase"]

    gdd_toplam = hesapla_gdd(tmax_h, tmin_h, tbase)
    gdd_info = buyume_evresi(gdd_toplam, urun_key)

    return forecast, gdd_info, ekim


# ── API endpoint'leri ────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Tarla Danışmanı"}


@app.post("/api/register")
async def register(istek: KayitIstegi):
    """Çiftçi kaydeder ve hemen öneri üretir."""
    session_id = istek.session_id or str(uuid.uuid4())
    urun_key = normalize_urun(istek.urun)

    try:
        forecast, gdd_info, ekim = await _oneri_hesapla(istek.il, urun_key, istek.ekim_ayi)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Hava verisi alınamadı: {e}")

    farmer_id = await kayit_ekle(
        session_id, istek.il, urun_key, istek.ekim_ayi, ekim
    )

    oneri = karar_ver(forecast, gdd_info)

    await oneri_kaydet(
        farmer_id, oneri.tip, oneri.baslik, oneri.detay, oneri.hava_ozeti
    )

    return {
        "session_id": session_id,
        "farmer_id": farmer_id,
        "oneri": {
            "tip": oneri.tip,
            "renk": oneri.renk,
            "baslik": oneri.baslik,
            "detay": oneri.detay,
            "hava_ozeti": oneri.hava_ozeti,
            "ilacla_not": oneri.ilacla_not,
            "gdd_ozeti": oneri.gdd_ozeti,
            "buyume_evresi": gdd_info["evre_isim"],
            "gdd_birikmis": gdd_info["gdd_birikmis"],
            "il": istek.il,
            "urun_isim": gdd_info["urun_isim"],
            "ekim_tarihi": ekim.isoformat(),
        },
    }


@app.get("/api/simulate")
async def simulate(
    il: str = Query(..., description="İl adı (ör: Konya)"),
    urun: str = Query(..., description="Ürün kodu (bugday, aycicek, pancar, misir)"),
    ekim_ayi: str = Query(..., description="Ekim ayı (ör: Ekim)"),
):
    """
    Kayıt olmadan gerçek veriyle öneri simüle eder.
    Frontend demo için kullanılır.
    """
    urun_key = normalize_urun(urun)

    try:
        forecast, gdd_info, ekim = await _oneri_hesapla(il, urun_key, ekim_ayi)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Hava verisi alınamadı: {e}")

    oneri = karar_ver(forecast, gdd_info)

    return {
        "tip": oneri.tip,
        "renk": oneri.renk,
        "baslik": oneri.baslik,
        "detay": oneri.detay,
        "hava_ozeti": oneri.hava_ozeti,
        "ilacla_not": oneri.ilacla_not,
        "gdd_ozeti": oneri.gdd_ozeti,
        "buyume_evresi": gdd_info["evre_isim"],
        "gdd_birikmis": gdd_info["gdd_birikmis"],
        "il": il,
        "urun_isim": gdd_info["urun_isim"],
        "ekim_tarihi": ekim.isoformat(),
    }


@app.get("/api/weather")
async def weather_raw(il: str = Query(...)):
    """Ham hava verisi (debug/geliştirme için)."""
    try:
        forecast = await get_forecast(il)
        return forecast
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Static dosyalar (frontend) — EN SONDA OLMALI ───────────────────────────
import os
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
