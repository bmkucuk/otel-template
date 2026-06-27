#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Veritabanı katmanı — SQLite"""
import sqlite3
import config_loader as _cfg
from pathlib import Path
from datetime import date, datetime

import os
_data_dir = '/data' if os.path.isdir('/data') else '.'
DB_PATH = os.path.join(_data_dir, 'muhasebe.db')

def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _yevmiye_ekle(conn, tarih, islem_tipi, borc, alacak, tutar, aciklama='', otel='GENEL', belge_no='', fatura_no='', kaynak_tablo=None, kaynak_id=None):
    """İç yevmiye kaydı — otomatik tetikleme için."""
    if not tarih: tarih = date.today().isoformat()
    try:
        yil = int(tarih[:4]); ay = int(tarih[5:7])
    except:
        yil = date.today().year; ay = date.today().month
    conn.execute("""
        INSERT INTO yevmiye (tarih,belge_no,islem_tipi,borc_hesap,alacak_hesap,
                             tutar,aciklama,otel,fatura_no,yil,ay,kaynak_tablo,kaynak_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (tarih, belge_no, islem_tipi, borc, alacak, tutar, aciklama, otel, fatura_no, yil, ay, kaynak_tablo, kaynak_id))

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS hesaplar (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        kod     TEXT NOT NULL UNIQUE,
        ad      TEXT NOT NULL,
        tip     TEXT NOT NULL,  -- Aktif/Pasif/Gelir/Gider/Ozkaynak
        grup    TEXT NOT NULL,  -- Nakit/Banka/Acente/Ortak/Gelir/Gider...
        aktif   INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS bankalar (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        kod     TEXT NOT NULL UNIQUE,
        ad      TEXT NOT NULL,
        hesap_no TEXT,
        aktif   INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS acenteler (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        kod             TEXT NOT NULL UNIQUE,
        ad              TEXT NOT NULL,
        komisyon_orani  REAL DEFAULT 15.0,
        aktif           INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS yevmiye (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih       TEXT NOT NULL,
        belge_no    TEXT,
        islem_tipi  TEXT NOT NULL,
        borc_hesap  TEXT NOT NULL,
        alacak_hesap TEXT NOT NULL,
        tutar       REAL NOT NULL,
        aciklama    TEXT,
        otel        TEXT DEFAULT 'GENEL',
        fatura_no   TEXT,
        yil         INTEGER,
        ay          INTEGER,
        kaynak_tablo TEXT,
        kaynak_id   INTEGER,
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS personel (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_soyad    TEXT NOT NULL,
        ise_giris   TEXT,
        gorev       TEXT,
        net_maas    REAL DEFAULT 0,
        banka_iban  TEXT,
        telefon     TEXT,
        tc_kimlik   TEXT,
        aktif       INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS personel_avans (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih       TEXT NOT NULL,
        personel_id INTEGER NOT NULL,
        tutar       REAL NOT NULL,
        odeme_sekli TEXT DEFAULT '100',
        aciklama    TEXT,
        otel        TEXT DEFAULT 'GENEL'
    );

    CREATE TABLE IF NOT EXISTS personel_maas (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih       TEXT NOT NULL,
        personel_id INTEGER REFERENCES personel(id),
        donem_yil   INTEGER,
        donem_ay    INTEGER,
        net_odeme   REAL NOT NULL,
        yol_parasi  REAL DEFAULT 0,
        fazla_mesai REAL DEFAULT 0,
        izin_parasi REAL DEFAULT 0,
        gelmedi_gun INTEGER DEFAULT 0,
        avans_dusum REAL DEFAULT 0,
        odeme_banka TEXT,
        aciklama    TEXT,
        otel        TEXT DEFAULT 'GENEL'
    );

    CREATE TABLE IF NOT EXISTS stok (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih       TEXT NOT NULL,
        belge_no    TEXT,
        aciklama    TEXT NOT NULL,
        kategori    TEXT,
        tutar       REAL NOT NULL,
        odeme_hesap TEXT,
        fatura_var  INTEGER DEFAULT 0,
        otel        TEXT DEFAULT 'GENEL',
        not_        TEXT
    );

    CREATE TABLE IF NOT EXISTS demirbaş (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih       TEXT NOT NULL,
        aciklama    TEXT NOT NULL,
        miktar      REAL DEFAULT 1,
        birim_fiyat REAL NOT NULL,
        toplam      REAL,
        odeme_hesap TEXT,
        fatura_no   TEXT,
        otel        TEXT DEFAULT 'GENEL',
        not_        TEXT
    );

    CREATE TABLE IF NOT EXISTS vergi (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih       TEXT,
        donem_yil   INTEGER,
        donem_ay    INTEGER,
        vergi_turu  TEXT NOT NULL,
        matrah      REAL DEFAULT 0,
        tutar       REAL NOT NULL,
        odeme_banka TEXT,
        durum       TEXT DEFAULT 'Bekliyor',
        aciklama    TEXT
    );

    CREATE TABLE IF NOT EXISTS acente_cari (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih           TEXT NOT NULL,
        acente_kod      TEXT NOT NULL,
        foy_no          INTEGER,
        rez_no          TEXT,
        misafir         TEXT,
        rez_tutari      REAL NOT NULL,
        komisyon_oran   REAL,
        komisyon_tl     REAL,
        gelen_odeme     REAL DEFAULT 0,
        otel            TEXT DEFAULT 'LEO'
    );

    CREATE TABLE IF NOT EXISTS ortak_cari (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih       TEXT NOT NULL,
        ortak       TEXT NOT NULL,   -- LK / BT
        belge_no    TEXT,
        aciklama    TEXT NOT NULL,
        gider_kategori TEXT,
        tutar       REAL NOT NULL,
        odeme_sekli TEXT,
        iade        REAL DEFAULT 0,
        otel        TEXT DEFAULT 'GENEL'
    );

    CREATE TABLE IF NOT EXISTS gelir_ozet (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        yil             INTEGER NOT NULL,
        ay              INTEGER NOT NULL,
        otel            TEXT NOT NULL,   -- LEO / CV
        konaklama       REAL DEFAULT 0,
        restoran        REAL DEFAULT 0,
        nakit_tahsilat  REAL DEFAULT 0,
        kk_tahsilat     REAL DEFAULT 0,
        havale_tahsilat REAL DEFAULT 0,
        kapora          REAL DEFAULT 0,
        acik_bakiye     REAL DEFAULT 0,
        aktarim_tarihi  TEXT,
        UNIQUE(yil, ay, otel)
    );

    CREATE TABLE IF NOT EXISTS parametreler (
        anahtar TEXT PRIMARY KEY,
        deger   TEXT
    );
    """)

    # Varsayılan hesap planı
    hesaplar = [
        ("100",    "Kasa TL",                   "Aktif",     "Nakit"),
        ("102-1",  "İş Bankası",                "Aktif",     "Banka"),
        ("102-2",  "Ziraat Bankası",             "Aktif",     "Banka"),
        ("102-3",  "Denizbank",                 "Aktif",     "Banka"),
        ("120",    "Müşteri Cari",               "Aktif",     "Alacak"),
        ("150",    "Stok",                       "Aktif",     "Stok"),
        ("153",    "Stok/Market Gideri",         "Gider",     "Gider"),
        ("195",    "Personel Avans",             "Aktif",     "Dönen Varlık"),
        ("255",    "Demirbaş Gideri",             "Gider",     "Gider"),
        ("320-1",  "Booking Cari",               "Pasif",     "Acente"),
        ("320-2",  "Expedia Cari",               "Pasif",     "Acente"),
        ("320-3",  "JollyTur Cari",              "Pasif",     "Acente"),
        ("320-4",  "TatilSepeti Cari",           "Pasif",     "Acente"),
        ("320-5",  "ETSTUR Cari",                "Pasif",     "Acente"),
        ("360",    "Ödenecek Vergi",             "Pasif",     "Vergi"),
        ("340",    "Alınan Avanslar (Kaparo)",              "Pasif",     "Kaparo"),
        ("649",    "Diğer Olağan Gelir ve Karlar",  "Gelir",     "Diğer"),
        ("600",    "Konaklama Geliri",          "Gelir",     "Gelir"),
        ("610",    "Adisyon Geliri",             "Gelir",     "Gelir"),

        ("720",    "Personel Maaşları",          "Gider",     "Gider"),
        ("730",    "Acente Komisyonları",        "Gider",     "Gider"),
        ("740",    "Elektrik/Su/Doğalgaz",       "Gider",     "Gider"),
        ("741",    "Market/Gıda/Stok",           "Gider",     "Gider"),
        ("742",    "Bakım/Onarım",               "Gider",     "Gider"),
        ("743",    "Sigorta",                    "Gider",     "Gider"),
        ("744",    "Muhasebe/Danışmanlık",       "Gider",     "Gider"),
        ("745",    "Kira",                       "Gider",     "Gider"),
        ("770",    "Vergi Giderleri",            "Gider",     "Gider"),
        ("780",    "Diğer Giderler",             "Gider",     "Gider"),
    ]
    for h in hesaplar:
        c.execute("INSERT OR IGNORE INTO hesaplar(kod,ad,tip,grup) VALUES(?,?,?,?)", h)

    bankalar = [
        ("KASA",  "Kasa TL",        ""),
        ("IS",    "İş Bankası",     ""),
        ("ZRH",   "Ziraat Bankası", ""),
        ("DNZ",   "Denizbank",     ""),

    ]
    for b in bankalar:
        c.execute("INSERT OR IGNORE INTO bankalar(kod,ad,hesap_no) VALUES(?,?,?)", b)

    # Ortak cari hesaplarını ve kişisel banka hesaplarını config'den oluştur
    try:
        ortaklar = _cfg.load_config().get('ortaklar', [])
        for o in ortaklar:
            kod   = o.get('kod', '')
            ad    = o.get('ad', '')
            kisalt = o.get('kisalt', kod)
            if not kod: continue
            # Ortak cari hesabı
            c.execute("INSERT OR IGNORE INTO hesaplar(kod,ad,tip,grup) VALUES(?,?,?,?)",
                (f"500-{kod}", f"{kisalt} Cari ({ad})", "Ozkaynak", "Ortak"))
            # Kişisel banka hesapları
            c.execute("INSERT OR IGNORE INTO bankalar(kod,ad,hesap_no) VALUES(?,?,?)",
                (f"{kod}-NKT", f"{ad.split()[0]} Nakit", ""))
            c.execute("INSERT OR IGNORE INTO bankalar(kod,ad,hesap_no) VALUES(?,?,?)",
                (f"{kod}-KK", f"{ad.split()[0]} KK", ""))
    except Exception as e:
        print(f"Ortak hesap oluşturma hatası: {e}")

    # Migration: BT hesap adı Barış Taşdelen'den Burçin Taşdelen'e düzeltildi (sadece eski sistemlerde)
    # Migration: Booking.com -> Booking adı düzeltildi
    c.execute("UPDATE hesaplar SET ad='Booking Cari' WHERE kod='320-1'")
    c.execute("UPDATE acenteler SET ad='Booking' WHERE kod='BKG'")
    # Migration: eski ayrı Burçin kişisel hesabı varsa resmi BT ortak hesabına birleştir
    c.execute("SELECT 1 FROM hesaplar WHERE kod='500-BC'")
    if c.fetchone():
        c.execute("UPDATE yevmiye SET borc_hesap='500-BT' WHERE borc_hesap='500-BC'")
        c.execute("UPDATE yevmiye SET alacak_hesap='500-BT' WHERE alacak_hesap='500-BC'")
        c.execute("DELETE FROM hesaplar WHERE kod='500-BC'")
        c.execute("DELETE FROM bankalar WHERE kod='BC-NKT' OR kod='BC-KK'")

    # Migration: acente_cari tablosuna fatura_no kolonu (sonradan eklendi)
    acente_cari_cols = [r[1] for r in c.execute("PRAGMA table_info(acente_cari)").fetchall()]
    if 'fatura_no' not in acente_cari_cols:
        c.execute("ALTER TABLE acente_cari ADD COLUMN fatura_no TEXT")

    # Migration: personel tablosuna sonradan eklenen kolonlar (eski canlı DB'lerde yoktu)
    pers_cols = [r[1] for r in c.execute("PRAGMA table_info(personel)").fetchall()]
    if 'telefon' not in pers_cols:
        c.execute("ALTER TABLE personel ADD COLUMN telefon TEXT")
    if 'tc_kimlik' not in pers_cols:
        c.execute("ALTER TABLE personel ADD COLUMN tc_kimlik TEXT")

    # Migration: personel_maas tablosuna sonradan eklenen kolonlar (eski canlı DB'lerde yoktu)
    maas_cols = [r[1] for r in c.execute("PRAGMA table_info(personel_maas)").fetchall()]
    for col, ddl in [
        ('yol_parasi',  "ALTER TABLE personel_maas ADD COLUMN yol_parasi REAL DEFAULT 0"),
        ('fazla_mesai', "ALTER TABLE personel_maas ADD COLUMN fazla_mesai REAL DEFAULT 0"),
        ('izin_parasi', "ALTER TABLE personel_maas ADD COLUMN izin_parasi REAL DEFAULT 0"),
        ('gelmedi_gun', "ALTER TABLE personel_maas ADD COLUMN gelmedi_gun INTEGER DEFAULT 0"),
        ('avans_dusum', "ALTER TABLE personel_maas ADD COLUMN avans_dusum REAL DEFAULT 0"),
    ]:
        if col not in maas_cols:
            c.execute(ddl)

    acenteler = [
        ("BKG",     "Booking",  15.0),
        ("EXP",     "Expedia",      15.0),
        ("JLY",     "JollyTur",     15.0),
        ("TTS",     "TatilSepeti",  15.0),
        ("ETS",     "ETSTUR",       15.0),
        ("Telefon", "Telefon",       0.0),
        ("Kapidan", "Kapidan",       0.0),
    ]
    for a in acenteler:
        c.execute("INSERT OR IGNORE INTO acenteler(kod,ad,komisyon_orani) VALUES(?,?,?)", a)

    conn.commit()
    conn.close()

# ── CRUD Yardımcıları ─────────────────────────────────────────────────────────

def get_hesaplar(tip=None):
    conn = get_conn()
    if tip:
        rows = conn.execute(
            "SELECT * FROM hesaplar WHERE tip=? AND aktif=1 ORDER BY kod", (tip,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM hesaplar WHERE aktif=1 ORDER BY kod"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_hesap_adlari():
    rows = get_hesaplar()
    return [f"{r['kod']} — {r['ad']}" for r in rows]

def get_bankalar():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM bankalar WHERE aktif=1").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_acenteler():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM acenteler WHERE aktif=1").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_personel(sadece_aktif=True):
    conn = get_conn()
    q = "SELECT * FROM personel"
    if sadece_aktif: q += " WHERE aktif=1"
    q += " ORDER BY ad_soyad"
    rows = [dict(r) for r in conn.execute(q).fetchall()]
    # Kalan (kapanmamış) avans bakiyesi: verilen avans toplamı - maaştan o ana kadar düşülen toplam
    verilen = {r['personel_id']: r['t'] for r in conn.execute(
        "SELECT personel_id, COALESCE(SUM(tutar),0) as t FROM personel_avans GROUP BY personel_id")}
    dusulen = {r['personel_id']: r['t'] for r in conn.execute(
        "SELECT personel_id, COALESCE(SUM(avans_dusum),0) as t FROM personel_maas GROUP BY personel_id")}
    for r in rows:
        r['kalan_avans'] = round((verilen.get(r['id'], 0) or 0) - (dusulen.get(r['id'], 0) or 0), 2)
    conn.close()
    return rows

def ekle_yevmiye(tarih, belge_no, islem_tipi, borc, alacak, tutar,
                  aciklama="", otel="GENEL", fatura_no="", kaynak_tablo=None, kaynak_id=None,
                  doviz_cinsi="", doviz_tutar=0, kur=0):
    conn = get_conn()
    t = tarih if isinstance(tarih, str) else tarih.isoformat()
    yil = int(t[:4]); ay = int(t[5:7])
    conn.execute("""
        INSERT INTO yevmiye
        (tarih,belge_no,islem_tipi,borc_hesap,alacak_hesap,tutar,
         aciklama,otel,fatura_no,yil,ay,kaynak_tablo,kaynak_id,
         doviz_cinsi,doviz_tutar,kur)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (t, belge_no, islem_tipi, borc, alacak, tutar,
          aciklama, otel, fatura_no, yil, ay, kaynak_tablo, kaynak_id,
          doviz_cinsi or '', doviz_tutar or 0, kur or 0))
    conn.commit(); conn.close()

def get_yevmiye(yil=None, ay=None, hesap=None, limit=None, order='DESC'):
    conn = get_conn()
    q = "SELECT * FROM yevmiye WHERE 1=1"
    params = []
    if yil:   q += " AND yil=?";              params.append(yil)
    if ay:    q += " AND ay=?";               params.append(ay)
    if hesap: q += " AND (borc_hesap=? OR alacak_hesap=?)"; params += [hesap, hesap]
    q += f" ORDER BY tarih {order}, id {order}"
    if limit:
        q += f" LIMIT {limit}"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def ekle_personel(ad_soyad, ise_giris="", gorev="", net_maas=0, iban="", telefon="", tc_kimlik=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO personel(ad_soyad,ise_giris,gorev,net_maas,banka_iban,telefon,tc_kimlik)
        VALUES(?,?,?,?,?,?,?)
    """, (ad_soyad, ise_giris, gorev, net_maas, iban, telefon, tc_kimlik))
    conn.commit(); conn.close()

def ekle_avans(tarih, personel_id, tutar, odeme_sekli='100', aciklama='', otel='GENEL'):
    conn = get_conn()
    t = tarih if isinstance(tarih, str) else tarih.isoformat()
    yil = int(t[:4]); ay = int(t[5:7])
    p = conn.execute("SELECT ad_soyad FROM personel WHERE id=?", (personel_id,)).fetchone()
    p_ad = p[0] if p else str(personel_id)
    conn.execute("""
        INSERT INTO personel_avans(tarih,personel_id,tutar,odeme_sekli,aciklama,otel)
        VALUES(?,?,?,?,?,?)
    """, (t, personel_id, tutar, odeme_sekli, aciklama, otel))
    avans_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    _yevmiye_ekle(conn, t, 'Personel Avans', '195', odeme_sekli,
                  tutar, f'{p_ad} avans', otel,
                  kaynak_tablo='personel_avans', kaynak_id=avans_id)
    conn.commit(); conn.close()

def get_avans(personel_id=None, yil=None, ay=None):
    conn = get_conn()
    q = """SELECT a.*, p.ad_soyad FROM personel_avans a
           JOIN personel p ON p.id=a.personel_id WHERE 1=1"""
    params = []
    if personel_id: q += " AND a.personel_id=?"; params.append(personel_id)
    if yil: q += " AND strftime('%Y',a.tarih)=?"; params.append(str(yil))
    if ay: q += " AND strftime('%m',a.tarih)=?"; params.append(f"{ay:02d}")
    q += " ORDER BY a.tarih ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def ekle_maas(tarih, personel_id, donem_yil, donem_ay,
               net_odeme, odeme_banka="", aciklama="", otel="GENEL",
               yol_parasi=0, fazla_mesai=0, izin_parasi=0, gelmedi_gun=0, avans_dusum=0):
    conn = get_conn()
    t = tarih if isinstance(tarih, str) else tarih.isoformat()
    yil = int(t[:4]); ay = int(t[5:7])
    toplam = (net_odeme or 0) + (yol_parasi or 0) + (fazla_mesai or 0) + (izin_parasi or 0) - (avans_dusum or 0)
    # Personel adını al
    p = conn.execute("SELECT ad_soyad FROM personel WHERE id=?", (personel_id,)).fetchone()
    p_ad = p[0] if p else str(personel_id)
    conn.execute("""
        INSERT INTO personel_maas
        (tarih,personel_id,donem_yil,donem_ay,net_odeme,yol_parasi,fazla_mesai,izin_parasi,gelmedi_gun,avans_dusum,odeme_banka,aciklama,otel)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (t, personel_id, donem_yil, donem_ay, net_odeme,
           yol_parasi or 0, fazla_mesai or 0, izin_parasi or 0, gelmedi_gun or 0,
           avans_dusum or 0, odeme_banka, aciklama, otel))
    # Yevmiye: Personel Gideri borç / Banka alacak (net ödenen tutar)
    # Avans düşümü varsa, avans hesabını (195) da kapatmak için ayrı satır yazılır;
    # aksi halde avans hesabı hiç kapanmaz ve sonsuza kadar açık görünür.
    maas_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    if avans_dusum and avans_dusum > 0:
        _yevmiye_ekle(conn, t, 'Personel Maaşı (Avans Mahsubu)', '720', '195',
                      avans_dusum, f'{p_ad} {donem_ay}/{donem_yil} avans mahsubu', otel,
                      kaynak_tablo='personel_maas', kaynak_id=maas_id)
    if toplam > 0:
        _yevmiye_ekle(conn, t, 'Personel Maaşı', '720', odeme_banka or '102-1',
                      toplam, f'{p_ad} {donem_ay}/{donem_yil} maaş+yol', otel,
                      kaynak_tablo='personel_maas', kaynak_id=maas_id)
    conn.commit(); conn.close()

def ekle_stok(tarih, aciklama, tutar, kategori="", belge_no="",
               odeme_hesap="", fatura_var=False, otel="GENEL", not_=""):
    conn = get_conn()
    t = tarih if isinstance(tarih, str) else tarih.isoformat()
    yil = int(t[:4]); ay = int(t[5:7])
    conn.execute("""
        INSERT INTO stok(tarih,belge_no,aciklama,kategori,tutar,
                         odeme_hesap,fatura_var,otel,not_)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (t, belge_no, aciklama, kategori, tutar,
          odeme_hesap, int(fatura_var), otel, not_))
    # Yevmiye: Stok Gideri borç / Ödeme hesabı alacak
    if tutar > 0:
        stok_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("""
            INSERT INTO yevmiye(tarih,yil,ay,belge_no,islem_tipi,borc_hesap,alacak_hesap,tutar,aciklama,otel,kaynak_tablo,kaynak_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (t, yil, ay, belge_no, 'Stok Alımı', '153', odeme_hesap or '100',
                tutar, f'{kategori}: {aciklama}', otel, 'stok', stok_id))
    conn.commit(); conn.close()

def ekle_demirbaş(tarih, aciklama, miktar, birim_fiyat, odeme_hesap="",
                   fatura_no="", otel="GENEL", not_=""):
    conn = get_conn()
    t = tarih if isinstance(tarih, str) else tarih.isoformat()
    yil = int(t[:4]); ay = int(t[5:7])
    toplam = miktar * birim_fiyat
    conn.execute("""
        INSERT INTO demirbaş(tarih,aciklama,miktar,birim_fiyat,toplam,
                             odeme_hesap,fatura_no,otel,not_)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (t, aciklama, miktar, birim_fiyat, toplam,
          odeme_hesap, fatura_no, otel, not_))
    # Yevmiye: Demirbaş borç / Ödeme hesabı alacak
    if toplam > 0:
        dem_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("""
            INSERT INTO yevmiye(tarih,yil,ay,belge_no,islem_tipi,borc_hesap,alacak_hesap,tutar,aciklama,otel,kaynak_tablo,kaynak_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (t, yil, ay, fatura_no, 'Demirbaş Alımı', '255', odeme_hesap or '100',
                toplam, aciklama, otel, 'demirbaş', dem_id))
    conn.commit(); conn.close()

def ekle_vergi(donem_yil, donem_ay, vergi_turu, tutar, matrah=0,
               tarih="", odeme_banka="", durum="Bekliyor", aciklama=""):
    conn = get_conn()
    t = tarih or f"{donem_yil}-{str(donem_ay).zfill(2)}-01"
    conn.execute("""
        INSERT INTO vergi(tarih,donem_yil,donem_ay,vergi_turu,matrah,
                          tutar,odeme_banka,durum,aciklama)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (t, donem_yil, donem_ay, vergi_turu, matrah,
          tutar, odeme_banka, durum, aciklama))
    # Yevmiye: sadece Ödendi ise
    if durum == 'Ödendi' and tutar > 0:
        conn.execute("""
            INSERT INTO yevmiye(tarih,yil,ay,belge_no,islem_tipi,borc_hesap,alacak_hesap,tutar,aciklama,otel)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (t, donem_yil, donem_ay, '', 'Vergi Ödemesi', '360', odeme_banka or '102-1',
                tutar, f'{vergi_turu} {donem_ay}/{donem_yil}', 'GENEL'))
    conn.commit(); conn.close()

def ekle_acente_cari(tarih, acente_kod, rez_tutari, komisyon_oran,
                      foy_no=None, rez_no="", misafir="", otel="LEO"):
    conn = get_conn()
    t = tarih if isinstance(tarih, str) else tarih.isoformat()
    komisyon_tl = rez_tutari * komisyon_oran / 100
    conn.execute("""
        INSERT INTO acente_cari
        (tarih,acente_kod,foy_no,rez_no,misafir,rez_tutari,
         komisyon_oran,komisyon_tl,otel)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (t, acente_kod, foy_no, rez_no, misafir, rez_tutari,
          komisyon_oran, komisyon_tl, otel))
    conn.commit(); conn.close()

def ekle_ortak_cari(tarih, ortak, aciklama, tutar, gider_kategori="",
                     belge_no="", odeme_sekli="KK", iade=0, otel="GENEL"):
    conn = get_conn()
    t = tarih if isinstance(tarih, str) else tarih.isoformat()
    conn.execute("""
        INSERT INTO ortak_cari
        (tarih,ortak,belge_no,aciklama,gider_kategori,tutar,odeme_sekli,iade,otel)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (t, ortak, belge_no, aciklama, gider_kategori, tutar,
          odeme_sekli, iade, otel))
    conn.commit(); conn.close()

def temizle_gelir_ozet(yil):
    """Yıla ait tüm gelir özet kayıtlarını sil — temiz aktarım için."""
    conn = get_conn()
    conn.execute("DELETE FROM gelir_ozet WHERE yil=?", (yil,))
    conn.commit(); conn.close()

def kaydet_gelir_ozet(yil, ay, otel, konaklama, restoran,
                       nakit, kk, havale, kapora, acik, rezervasyonlar=None):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO gelir_ozet
        (yil,ay,otel,konaklama,restoran,nakit_tahsilat,kk_tahsilat,
         havale_tahsilat,kapora,acik_bakiye,aktarim_tarihi)
        VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))
    """, (yil, ay, otel, konaklama, restoran, nakit, kk, havale, kapora, acik))
    # Mevcut yevmiye kayıtlarını temizle (aynı ay/otel için)
    aciklama_prefix = f"[OTEL-AKTARIM] {yil}/{ay:02d} {otel}"
    conn.execute("DELETE FROM yevmiye WHERE aciklama LIKE ?", (f"%{aciklama_prefix}%",))
    gelir_hesap = '600' if otel == 'LEO' else '601'

    if rezervasyonlar:
        # Gerçek tarihlerle her rezervasyonu ayrı kaydet
        for r in rezervasyonlar:
            tarih = r.get('giris') or f"{yil}-{ay:02d}-01"
            foy = r.get('foy_no', '')
            musteri = r.get('musteri', '')
            aciklama_rez = f"{aciklama_prefix} Föy#{foy} {musteri}"
            toplam = float(r.get('toplam_fiyat') or 0)
            if toplam > 0:
                _yevmiye_ekle(conn, tarih, 'Konaklama Geliri', '120', gelir_hesap,
                              toplam, aciklama_rez, otel)
            tah = float(r.get('rez_tahsilat') or 0)
            odeme = str(r.get('rez_odeme_sekli') or '').lower()
            if tah > 0:
                if 'nakit' in odeme:
                    _yevmiye_ekle(conn, tarih, 'Tahsilat - Nakit', '100', '120',
                                  tah, aciklama_rez, otel)
                elif 'kk' in odeme or 'kart' in odeme:
                    _yevmiye_ekle(conn, tarih, 'Tahsilat - KK', '102-1', '120',
                                  tah, aciklama_rez, otel)
                elif 'havale' in odeme or 'eft' in odeme:
                    _yevmiye_ekle(conn, tarih, 'Tahsilat - Havale', '102-1', '120',
                                  tah, aciklama_rez, otel)
    else:
        # Eski davranış: aylık özet
        tarih = f"{yil}-{ay:02d}-01"
        if konaklama > 0:
            _yevmiye_ekle(conn, tarih, 'Konaklama Geliri', '120', gelir_hesap,
                          konaklama, f"{aciklama_prefix} konaklama", otel)
        if restoran > 0:
            _yevmiye_ekle(conn, tarih, 'Adisyon Geliri', '120', '610',
                          restoran, f"{aciklama_prefix} restoran", otel)
        if nakit > 0:
            _yevmiye_ekle(conn, tarih, 'Tahsilat - Nakit', '100', '120',
                          nakit, f"{aciklama_prefix} nakit tahsilat", otel)
        if kk > 0:
            _yevmiye_ekle(conn, tarih, 'Tahsilat - KK', '102-1', '120',
                          kk, f"{aciklama_prefix} kk tahsilat", otel)
        if havale > 0:
            _yevmiye_ekle(conn, tarih, 'Tahsilat - Havale', '102-1', '120',
                          havale, f"{aciklama_prefix} havale tahsilat", otel)
    conn.commit(); conn.close()

def get_gelir_ozet(yil=None):
    conn = get_conn()
    q = "SELECT * FROM gelir_ozet"
    params = []
    if yil: q += " WHERE yil=?"; params.append(yil)
    q += " ORDER BY yil, ay, otel"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_mizan_ozet(yil):
    """Yıllık mizan özeti döndür."""
    conn = get_conn()

    # Yevmiye toplamları
    borc = conn.execute("""
        SELECT borc_hesap as hesap, SUM(tutar) as toplam
        FROM yevmiye WHERE yil=? GROUP BY borc_hesap
    """, (yil,)).fetchall()

    alacak = conn.execute("""
        SELECT alacak_hesap as hesap, SUM(tutar) as toplam
        FROM yevmiye WHERE yil=? GROUP BY alacak_hesap
    """, (yil,)).fetchall()

    # Personel
    maas = conn.execute("""
        SELECT SUM(net_odeme + COALESCE(yol_parasi,0)) FROM personel_maas WHERE donem_yil=?
    """, (yil,)).fetchone()[0] or 0

    # Stok
    stok = conn.execute("""
        SELECT SUM(tutar) FROM stok WHERE strftime('%Y',tarih)=?
    """, (str(yil),)).fetchone()[0] or 0

    # Demirbaş
    dem = conn.execute("""
        SELECT SUM(toplam) FROM demirbaş WHERE strftime('%Y',tarih)=?
    """, (str(yil),)).fetchone()[0] or 0

    # Vergi ödenen
    vergi = conn.execute("""
        SELECT SUM(tutar) FROM vergi WHERE donem_yil=? AND durum='Ödendi'
    """, (yil,)).fetchone()[0] or 0

    # Gelir özeti
    gelir = conn.execute("""
        SELECT otel,
               SUM(konaklama)       as kon,
               SUM(restoran)        as rest,
               SUM(nakit_tahsilat)  as nakit,
               SUM(kk_tahsilat)     as kk,
               SUM(havale_tahsilat) as havale,
               SUM(nakit_tahsilat+kk_tahsilat+havale_tahsilat) as tahsilat,
               SUM(acik_bakiye)     as acik
        FROM gelir_ozet WHERE yil=? GROUP BY otel
    """, (yil,)).fetchall()

    # Acente komisyon toplamı
    komisyon = conn.execute("""
        SELECT COALESCE(SUM(komisyon_tl),0) FROM acente_cari
        WHERE strftime('%Y',tarih)=?
    """, (str(yil),)).fetchone()[0] or 0

    # Ortak cari toplamları (LK ve BT ayrı ayrı)
    ortak_lk = conn.execute("""
        SELECT COALESCE(SUM(tutar-iade),0) FROM ortak_cari
        WHERE ortak='LK' AND strftime('%Y',tarih)=?
    """, (str(yil),)).fetchone()[0] or 0

    ortak_bt = conn.execute("""
        SELECT COALESCE(SUM(tutar-iade),0) FROM ortak_cari
        WHERE ortak='BT' AND strftime('%Y',tarih)=?
    """, (str(yil),)).fetchone()[0] or 0

    ortak_fk = conn.execute("""
        SELECT COALESCE(SUM(tutar-iade),0) FROM ortak_cari
        WHERE ortak='FK' AND strftime('%Y',tarih)=?
    """, (str(yil),)).fetchone()[0] or 0

    conn.close()
    return {
        'borc':     {r['hesap']: r['toplam'] for r in borc},
        'alacak':   {r['hesap']: r['toplam'] for r in alacak},
        'maas': maas, 'stok': stok, 'demirbaş': dem,
        'vergi': vergi, 'komisyon': komisyon,
        'ortak_lk': ortak_lk, 'ortak_bt': ortak_bt, 'ortak_fk': ortak_fk,
        'gelir': [dict(r) for r in gelir],
    }

def silme_yevmiye(kayit_id):
    conn = get_conn()
    conn.execute("DELETE FROM yevmiye WHERE id=?", (kayit_id,))
    conn.commit(); conn.close()

def guncelle_personel(pid, **kwargs):
    conn = get_conn()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [pid]
    conn.execute(f"UPDATE personel SET {sets} WHERE id=?", vals)
    conn.commit(); conn.close()

if __name__ == "__main__":
    init_db()
    print("Veritabanı oluşturuldu:", DB_PATH)
