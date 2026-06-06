"""SQLite veritabanı işlemleri."""
import aiosqlite
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path("/tmp/tarla.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS farmers ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "session_id TEXT UNIQUE NOT NULL, "
            "il TEXT NOT NULL, urun TEXT NOT NULL, "
            "ekim_ayi TEXT NOT NULL, ekim_tarihi TEXT NOT NULL, "
            "kayit_tarihi TEXT NOT NULL, aktif INTEGER NOT NULL DEFAULT 1)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS recommendations ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "farmer_id INTEGER NOT NULL, tip TEXT, baslik TEXT, "
            "detay TEXT, hava_ozeti TEXT, "
            "created_at TEXT NOT NULL)"
        )
        await db.commit()

async def kayit_ekle(session_id, il, urun, ekim_ayi, ekim_tarihi):
    async with aiosqlite.connect(DB_PATH) as db:
        sql = ("INSERT INTO farmers (session_id,il,urun,ekim_ayi,ekim_tarihi,kayit_tarihi) "
               "VALUES (?,?,?,?,?,?) "
               "ON CONFLICT(session_id) DO UPDATE SET "
               "il=excluded.il, urun=excluded.urun, "
               "ekim_ayi=excluded.ekim_ayi, ekim_tarihi=excluded.ekim_tarihi, "
               "kayit_tarihi=excluded.kayit_tarihi")
        cursor = await db.execute(sql, (
            session_id, il, urun, ekim_ayi,
            ekim_tarihi.isoformat(), datetime.now().isoformat()
        ))
        await db.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        row = await (await db.execute(
            "SELECT id FROM farmers WHERE session_id=?", (session_id,)
        )).fetchone()
        return row[0] if row else 0

async def oneri_kaydet(farmer_id, tip, baslik, detay, hava_ozeti):
    async with aiosqlite.connect(DB_PATH) as db:
        sql = ("INSERT INTO recommendations "
               "(farmer_id,tip,baslik,detay,hava_ozeti,created_at) "
               "VALUES (?,?,?,?,?,?)")
        await db.execute(sql, (
            farmer_id, tip, baslik, detay,
            hava_ozeti, datetime.now().isoformat()
        ))
        await db.commit()
