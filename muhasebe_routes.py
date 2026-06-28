#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muhasebe modülü — Flask route'ları"""
from datetime import date
from flask import Blueprint, render_template, request, jsonify, session, redirect
import muhasebe_db as mdb
import database as db
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            return redirect('/login')
        if session.get('role') not in ('admin', 'partner'):
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

def muhasebe_required(f):
    """Muhasebe modülüne erişim: admin + partner. resepsiyon (kısıtlı) erişemez."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            return redirect('/login')
        if session.get('role') not in ('admin', 'partner'):
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

muh = Blueprint('muhasebe', __name__)

@muh.before_request
def _muhasebe_blueprint_guard():
    """Tüm /muhasebe ve /api/muhasebe rotaları: sadece admin + partner. resepsiyon erişemez."""
    if not session.get('user'):
        return redirect('/login')
    if session.get('role') not in ('admin', 'partner'):
        return redirect('/')

AYLAR = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
         "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

# ── Sayfalar ──────────────────────────────────────────────────────────────────

@muh.route('/muhasebe')
@admin_required
def muhasebe_index():
    return render_template('muhasebe/gosterge.html')

@muh.route('/muhasebe/yevmiye')
@admin_required
def muhasebe_yevmiye():
    return render_template('muhasebe/yevmiye.html')

@muh.route('/muhasebe/kasa-banka')
@muhasebe_required
def muhasebe_kasa():
    return render_template('muhasebe/kasa_banka.html')

@muh.route('/muhasebe/personel')
@admin_required
def muhasebe_personel():
    return render_template('muhasebe/personel.html')

@muh.route('/muhasebe/stok')
@muhasebe_required
def muhasebe_stok():
    return render_template('muhasebe/stok.html')

@muh.route('/muhasebe/demirbaş')
@muhasebe_required
def muhasebe_demirbaş():
    return render_template('muhasebe/demirbaş.html')

@muh.route('/muhasebe/vergi')
@admin_required
def muhasebe_vergi():
    return render_template('muhasebe/vergi.html')

@muh.route('/muhasebe/acente')
@muhasebe_required
def muhasebe_acente():
    return render_template('muhasebe/acente.html')

@muh.route('/muhasebe/gider-girisleri')
@muhasebe_required
def muhasebe_gider():
    return render_template('muhasebe/gider_girisleri.html')

@muh.route('/muhasebe/ortak-cari')
@admin_required
def muhasebe_ortak():
    return render_template('muhasebe/ortak_cari.html')

@muh.route('/muhasebe/mizan')
@admin_required
def muhasebe_mizan():
    return render_template('muhasebe/mizan.html')


# ── API — Gösterge ────────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/gosterge')
def api_gosterge():
    yil = request.args.get('yil', date.today().year, type=int)

    # Yevmiyeden doğrudan oku
    conn = mdb.get_conn()
    def yev_sum(borc=None, alacak=None, tip=None):
        q = "SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=?"
        p = [yil]
        if borc:   q += " AND borc_hesap=?";   p.append(borc)
        if alacak: q += " AND alacak_hesap=?"; p.append(alacak)
        if tip:    q += " AND islem_tipi=?";   p.append(tip)
        return conn.execute(q, p).fetchone()[0] or 0

    leo_kon  = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND islem_tipi IN ('Konaklama Geliri','Kapora Yanması') AND otel='LEO'", (yil,)).fetchone()[0] or 0
    cv_kon   = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND islem_tipi IN ('Konaklama Geliri','Kapora Yanması') AND otel='CV'", (yil,)).fetchone()[0] or 0
    restoran = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND islem_tipi='Adisyon Geliri'", (yil,)).fetchone()[0] or 0
    # Tüm nakit girişleri (tahsilat + kapora)
    nakit    = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap='100'", (yil,)).fetchone()[0] or 0
    # Tüm banka girişleri (tahsilat + kapora)
    kk       = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap='102-1'", (yil,)).fetchone()[0] or 0
    havale   = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap='102-1' AND islem_tipi LIKE '%Havale%'", (yil,)).fetchone()[0] or 0
    kapora_gelen = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND islem_tipi='Kapora'", (yil,)).fetchone()[0] or 0
    kapora_yanan = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND islem_tipi='Kapora Yanması'", (yil,)).fetchone()[0] or 0
    kapora   = kapora_gelen - kapora_yanan
    # Açık bakiye = müşteri cari borç - alacak
    muc_borc  = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap='120'", (yil,)).fetchone()[0] or 0
    muc_alacak= conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND alacak_hesap='120'", (yil,)).fetchone()[0] or 0
    acik = max(0, muc_borc - muc_alacak)
    conn.close()

    mizan = mdb.get_mizan_ozet(yil)
    maas  = mizan['maas']
    vergi = mizan['vergi']
    stok  = mizan['stok']
    dem   = mizan.get('demirbaş', 0)
    ortak_lk = mizan.get('ortak_lk', 0) or 0
    ortak_bt = mizan.get('ortak_bt', 0) or 0
    ortak_fk = mizan.get('ortak_fk', 0) or 0

    # Acente komisyon toplamı
    _ac = mdb.get_conn()
    acente_kom = _ac.execute(
        "SELECT COALESCE(SUM(komisyon_tl),0) FROM acente_cari WHERE strftime('%Y',tarih)=?",
        (str(yil),)).fetchone()[0] or 0
    _ac.close()

    toplam_gelir = leo_kon + cv_kon + restoran
    toplam_gider = maas + stok + vergi + acente_kom + ortak_lk + ortak_bt + ortak_fk + dem
    net = toplam_gelir - toplam_gider

    # Aylık özet
    import sqlite3
    conn = mdb.get_conn()
    maas_ay = {row[0]: row[1] for row in conn.execute(
        "SELECT donem_ay, SUM(net_odeme) FROM personel_maas WHERE donem_yil=? GROUP BY donem_ay", (yil,)).fetchall()}
    vergi_ay = {row[0]: row[1] for row in conn.execute(
        "SELECT donem_ay, SUM(tutar) FROM vergi WHERE donem_yil=? AND durum='Ödendi' GROUP BY donem_ay", (yil,)).fetchall()}
    conn.close()

    # Aylık özet yevmiyeden
    conn2 = mdb.get_conn()
    aylik = []
    for i, ay_adi in enumerate(AYLAR):
        ay = i + 1
        leo  = conn2.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND ay=? AND islem_tipi IN ('Konaklama Geliri','Kapora Yanması') AND otel='LEO'", (yil,ay)).fetchone()[0] or 0
        cv_k = conn2.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND ay=? AND islem_tipi IN ('Konaklama Geliri','Kapora Yanması') AND otel='CV'", (yil,ay)).fetchone()[0] or 0
        rest = conn2.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND ay=? AND islem_tipi='Adisyon Geliri'", (yil,ay)).fetchone()[0] or 0
        gel  = leo + cv_k + rest
        pers = maas_ay.get(ay, 0) or 0
        vg   = vergi_ay.get(ay, 0) or 0
        n    = gel - pers - vg
        aylik.append({'ay': ay_adi, 'leo': leo, 'cv': cv_k, 'rest': rest,
                      'gel': gel, 'pers': pers, 'vergi': vg, 'net': n})

    conn2.close()
    return jsonify({
        'kartlar': {
            'leo_kon': leo_kon, 'cv_kon': cv_kon, 'restoran': restoran,
            'nakit': nakit, 'kk': kk, 'havale': havale,
            'tahsilat': nakit + kk + havale, 'acik': acik, 'kapora': kapora,
            'maas': maas, 'stok': stok, 'dem': dem, 'vergi': vergi, 'acente_kom': acente_kom,
            'ortak_lk': ortak_lk, 'ortak_bt': ortak_bt, 'ortak_fk': ortak_fk,
            'toplam_gelir': toplam_gelir, 'toplam_gider': toplam_gider, 'net': net,
        },
        'aylik': aylik,
    })


# ── API — Yevmiye ─────────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/yevmiye')
@admin_required
def api_yevmiye():
    yil = request.args.get('yil', date.today().year, type=int)
    ay  = request.args.get('ay', 0, type=int) or None
    q   = request.args.get('q', '')
    hesap = request.args.get('hesap', '')
    order = request.args.get('order', 'DESC').upper()
    if order not in ('ASC', 'DESC'): order = 'DESC'
    rows = mdb.get_yevmiye(yil, ay, hesap=hesap or None, order=order)
    if q:
        rows = [r for r in rows if any(q.lower() in str(v).lower() for v in r.values())]
    return jsonify(rows)

@muh.route('/api/muhasebe/yevmiye/ekle', methods=['POST'])
@admin_required
def api_yevmiye_ekle():
    try:
        d = request.get_json()
        d['aciklama'] = uc(d.get('aciklama','')); mdb.ekle_yevmiye(**d)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/yevmiye/sil', methods=['POST'])
@admin_required
def api_yevmiye_sil():
    try:
        import re as _re, sqlite3 as _sq
        d = request.get_json()
        yev_id = int(d['id'])
        conn = mdb.get_conn()
        yev = conn.execute(
            "SELECT kaynak_tablo, kaynak_id, islem_tipi, tutar, aciklama FROM yevmiye WHERE id=?",
            (yev_id,)).fetchone()
        if yev:
            tablo, kid, islem, tutar, aciklama = yev[0], yev[1], yev[2] or '', yev[3] or 0, yev[4] or ''
            guvenli = ['stok', 'demirbaş', 'personel_maas', 'acente_cari', 'vergi', 'ortak_cari']
            if tablo and kid and tablo in guvenli:
                conn.execute(f'DELETE FROM "{tablo}" WHERE id=?', (kid,))

            m = _re.search(r'Föy#(\d+)', aciklama)
            foy_no = int(m.group(1)) if m else None

            if 'Tahsilat' in islem and tutar > 0 and foy_no:
                oc = _sq.connect('/data/otel.db')
                if 'Adisyon' in islem:
                    oc.execute('UPDATE rezervasyonlar SET adis_tahsilat=adis_tahsilat-?,adis_bakiye=adis_bakiye+? WHERE foy_no=?', (tutar, tutar, foy_no))
                    # Adisyon no varsa odendi/odenen_tutar güncelle
                    ma = _re.search(r'Adis#(\d+)', aciklama)
                    if ma:
                        adis_no = int(ma.group(1))
                        oc.execute('UPDATE adisyonlar SET odendi=0, odenen_tutar=MAX(0,odenen_tutar-?) WHERE adisyon_no=?', (tutar, adis_no))
                        oc.execute('DELETE FROM adisyon_odemeler WHERE adisyon_no=? AND tutar=? ORDER BY id DESC LIMIT 1', (adis_no, tutar))
                else:
                    oc.execute('UPDATE rezervasyonlar SET rez_tahsilat=rez_tahsilat-?,rez_bakiye=rez_bakiye+? WHERE foy_no=?', (tutar, tutar, foy_no))
                oc.commit(); oc.close()

            elif islem == 'Adisyon Geliri' and tutar > 0 and foy_no:
                # Adisyon geliri silinince adisyon tablosunu güncelle
                oc = _sq.connect('/data/otel.db')
                oc.execute('UPDATE rezervasyonlar SET adisyon=MAX(0,adisyon-?), adis_bakiye=MAX(0,adis_bakiye-?) WHERE foy_no=?', (tutar, tutar, foy_no))
                ma = _re.search(r'Adis#(\d+)', aciklama)
                if ma:
                    adis_no = int(ma.group(1))
                    oc.execute('DELETE FROM adisyonlar WHERE adisyon_no=?', (adis_no,))
                oc.commit(); oc.close()

            elif islem == 'Konaklama Geliri' and tutar > 0 and foy_no:
                oc = _sq.connect('/data/otel.db')
                oc.execute('DELETE FROM rezervasyonlar WHERE foy_no=?', (foy_no,))
                oc.execute('DELETE FROM adisyonlar WHERE foy_no=?', (foy_no,))
                oc.execute('DELETE FROM adisyon_odemeler WHERE foy_no=?', (foy_no,))
                oc.commit(); oc.close()

            elif islem == 'Kapora' and tutar > 0 and foy_no:
                oc = _sq.connect('/data/otel.db')
                oc.execute('UPDATE rezervasyonlar SET kapora=MAX(0,kapora-?), rez_bakiye=rez_bakiye+? WHERE foy_no=?', (tutar, tutar, foy_no))
                oc.commit(); oc.close()

        conn.execute("DELETE FROM yevmiye WHERE id=?", (yev_id,))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/yevmiye/guncelle', methods=['POST'])
@admin_required
def api_yevmiye_guncelle():
    try:
        d = request.get_json()
        yev_id   = int(d['id'])
        tarih    = d['tarih']
        tutar    = float(d['tutar'])
        aciklama = d.get('aciklama', '')
        islem    = d.get('islem_tipi', '')
        borc     = d.get('borc', '')
        alacak   = d.get('alacak', '')
        yil      = int(tarih[:4]); ay = int(tarih[5:7])
        conn = mdb.get_conn()
        sets = "tarih=?, tutar=?, aciklama=?, islem_tipi=?, yil=?, ay=?"
        vals = [tarih, tutar, aciklama, islem, yil, ay]
        if borc:
            sets += ", borc_hesap=?"; vals.append(borc)
        if alacak:
            sets += ", alacak_hesap=?"; vals.append(alacak)
        vals.append(yev_id)
        SISTEM_TIPLERI = {
            'Konaklama Geliri','Adisyon Geliri','Tahsilat - Nakit','Tahsilat - KK',
            'Tahsilat - Havale','Personel Maaşı','Personel Maaşı (Avans Mahsubu)',
            'Personel Avans','Stok Alımı','Demirbaş Alımı','Acente Ödemesi',
            'Acente Komisyonu','Vergi Ödemesi','Ortak Çekimi','Ortak Yatırımı',
            'Kasa - Banka Virman'
        }
        # kaynak_tablo dolu VEYA sistem islem tipiyse düzenlenemez
        mevcut = conn.execute("SELECT kaynak_tablo, islem_tipi FROM yevmiye WHERE id=?", (yev_id,)).fetchone()
        if not mevcut or mevcut[0] or (mevcut[1] in SISTEM_TIPLERI):
            conn.close()
            return jsonify({'ok': False, 'error': 'Bu kayıt düzenlenemez (sisteme bağlı kayıt)'}), 400
        conn.execute(f"UPDATE yevmiye SET {sets} WHERE id=?", vals)
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/hesaplar')
def api_hesaplar():
    return jsonify(mdb.get_hesap_adlari())

@muh.route('/api/muhasebe/bankalar')
def api_bankalar():
    return jsonify(mdb.get_bankalar())


# ── API — Kasa/Banka ─────────────────────────────────────────────────────────

# Banka kodu → yevmiye hesap kodu eşleştirmesi
def uc(s):
    """Açıklama metinlerini Türkçe büyük harfe çevirir (i→İ, ı→I vb.)"""
    if not s: return s
    s = str(s)
    s = s.replace('i', 'İ').replace('ı', 'I')
    return s.upper()

ACENTE_HESAP = {'BKG': '320-1', 'EXP': '320-2', 'JLY': '320-3', 'TTS': '320-4', 'ETS': '320-5'}

BANKA_HESAP = {
    'KASA':     '100',
    'IS':       '102-1',
    'ZRH':      '102-2',
    'DNZ':      '102-3',
    'KASA-EUR': '100-EUR',
    'KASA-USD': '100-USD',
}

@muh.route('/api/muhasebe/kasa')
def api_kasa():
    yil = request.args.get('yil', date.today().year, type=int)
    hesap = request.args.get('hesap', '')
    bankalar = mdb.get_bankalar()
    conn = mdb.get_conn()
    bakiyeler = []
    for b in bankalar:
        h_kodu = BANKA_HESAP.get(b['kod'], b['kod'])
        giris = conn.execute(
            "SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap=?",
            (yil, h_kodu)).fetchone()[0]
        cikis = conn.execute(
            "SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND alacak_hesap=?",
            (yil, h_kodu)).fetchone()[0]
        bakiye = giris - cikis
        entry = {'kod': b['kod'], 'ad': b['ad'], 'hesap_kodu': h_kodu,
                 'giris': giris, 'cikis': cikis, 'bakiye': bakiye}
        # Döviz kasaları için ayrıca döviz bakiyesi
        if b['kod'] in ('KASA-EUR', 'KASA-USD'):
            doviz = 'EUR' if b['kod'] == 'KASA-EUR' else 'USD'
            doviz_giris = conn.execute(
                "SELECT COALESCE(SUM(doviz_tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap=? AND doviz_cinsi=?",
                (yil, h_kodu, doviz)).fetchone()[0]
            doviz_cikis = conn.execute(
                "SELECT COALESCE(SUM(doviz_tutar),0) FROM yevmiye WHERE yil=? AND alacak_hesap=? AND doviz_cinsi=?",
                (yil, h_kodu, doviz)).fetchone()[0]
            entry['doviz_cinsi'] = doviz
            entry['doviz_bakiye'] = doviz_giris - doviz_cikis
        bakiyeler.append(entry)
    hareketler = []
    if hesap:
        h_kodu = BANKA_HESAP.get(hesap, hesap)
        rows = mdb.get_yevmiye(yil, hesap=h_kodu, order='ASC', limit=None)
        # islem_tipi ekle
        for r in rows:
            r['islem_tipi'] = r.get('islem_tipi', '')
        bakiye = 0
        for r in rows:
            # Aktif hesap: borç hesabında görünüyorsa para girişi
            giris_mi = h_kodu in str(r['borc_hesap'])
            g = r['tutar'] if giris_mi else 0
            c = r['tutar'] if not giris_mi else 0
            bakiye += g - c
            hareketler.append({**r, 'giris': g, 'cikis': c, 'bakiye_kum': bakiye,
                               'karsi': r['borc_hesap'] if giris_mi else r['alacak_hesap']})
    conn.close()
    return jsonify({'bakiyeler': bakiyeler, 'hareketler': hareketler})


# ── API — Personel ────────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/personel')
@admin_required
def api_personel():
    return jsonify(mdb.get_personel())

@muh.route('/api/muhasebe/personel/ekle', methods=['POST'])
@admin_required
def api_personel_ekle():
    try:
        d = request.get_json()
        mdb.ekle_personel(d['ad_soyad'], d.get('ise_giris'), d.get('gorev'),
                         float(d.get('net_maas', 0)), d.get('banka_iban', ''),
                         d.get('telefon', ''), d.get('tc_kimlik', ''))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/maaslar')
@admin_required
def api_maaslar():
    yil = request.args.get('yil', date.today().year, type=int)
    conn = mdb.get_conn()
    rows = conn.execute("""
        SELECT pm.id, pm.tarih, p.ad_soyad, pm.donem_ay, pm.donem_yil,
               pm.net_odeme, COALESCE(pm.yol_parasi,0), COALESCE(pm.fazla_mesai,0),
               COALESCE(pm.avans_dusum,0), COALESCE(pm.izin_parasi,0), COALESCE(pm.gelmedi_gun,0),
               pm.odeme_banka, pm.otel, pm.aciklama, pm.personel_id
        FROM personel_maas pm JOIN personel p ON pm.personel_id=p.id
        WHERE pm.donem_yil=? ORDER BY pm.tarih ASC
    """, (yil,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            'id': r[0], 'tarih': r[1], 'ad_soyad': r[2],
            'donem_ay': r[3], 'donem_yil': r[4],
            'net_odeme': r[5], 'yol_parasi': r[6], 'fazla_mesai': r[7],
            'avans_dusum': r[8], 'izin_parasi': r[9], 'gelmedi_gun': r[10],
            'odeme_banka': r[11], 'otel': r[12], 'aciklama': r[13],
            'personel_id': r[14]
        })
    return jsonify(result)

@muh.route('/api/muhasebe/personel/odemeler')
@admin_required
def api_personel_odemeler():
    """Maaş ve avans ödemelerini birleşik liste olarak döner."""
    yil = request.args.get('yil', date.today().year, type=int)
    conn = mdb.get_conn()
    # Maaş ödemeleri
    maas_rows = conn.execute("""
        SELECT pm.id, pm.tarih, p.ad_soyad, pm.donem_ay, pm.donem_yil,
               pm.net_odeme, COALESCE(pm.yol_parasi,0), COALESCE(pm.fazla_mesai,0),
               COALESCE(pm.avans_dusum,0), COALESCE(pm.izin_parasi,0),
               pm.odeme_banka, pm.aciklama, pm.personel_id
        FROM personel_maas pm JOIN personel p ON pm.personel_id=p.id
        WHERE pm.donem_yil=? ORDER BY pm.tarih ASC
    """, (yil,)).fetchall()
    # Avans ödemeleri
    avans_rows = conn.execute("""
        SELECT a.id, a.tarih, p.ad_soyad, a.tutar, a.odeme_sekli, a.aciklama, a.personel_id
        FROM personel_avans a JOIN personel p ON p.id=a.personel_id
        WHERE strftime('%Y', a.tarih)=? ORDER BY a.tarih ASC
    """, (str(yil),)).fetchall()
    conn.close()

    AYLAR = ['','Ocak','Şubat','Mart','Nisan','Mayıs','Haziran',
             'Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık']
    ODEME = {'100':'Nakit','101':'Kasa 2','102':'Banka 1','103':'Banka 2',
             '104':'Banka 3','105':'Banka 4','POS':'POS'}

    result = []
    for r in maas_rows:
        net = r[5]; yol = r[6]; mesai = r[7]; avans_d = r[8]; izin = r[9]
        toplam = net + yol + mesai + izin - avans_d
        donem = f"{AYLAR[r[3]]} {r[4]}" if 1 <= r[3] <= 12 else f"{r[3]}/{r[4]}"
        result.append({
            'id': r[0], 'tarih': r[1], 'ad_soyad': r[2],
            'tur': 'Maaş', 'donem': donem,
            'tutar': toplam,
            'detay': {'net': net, 'yol': yol, 'mesai': mesai, 'izin': izin, 'avans_dusum': avans_d},
            'odeme_sekli': ODEME.get(r[10], r[10] or '—'),
            'aciklama': r[11] or '',
            'personel_id': r[12],
            'kaynak': 'maas'
        })
    for r in avans_rows:
        result.append({
            'id': r[0], 'tarih': r[1], 'ad_soyad': r[2],
            'tur': 'Avans', 'donem': '—',
            'tutar': r[3],
            'detay': {},
            'odeme_sekli': ODEME.get(str(r[4]), str(r[4]) if r[4] else '—'),
            'aciklama': r[5] or '',
            'personel_id': r[6],
            'kaynak': 'avans'
        })

    result.sort(key=lambda x: x['tarih'])
    return jsonify(result)

@muh.route("/api/muhasebe/maas/ekle", methods=["POST"])
@admin_required
def api_maas_ekle():
    try:
        d = request.get_json()
        mdb.ekle_maas(d['tarih'], int(d['personel_id']), int(d['donem_yil']),
                     int(d['donem_ay']), float(d['net_odeme']),
                     d.get('odeme_banka', ''), d.get('aciklama', ''), d.get('otel', 'GENEL'),
                     yol_parasi=float(d.get('yol_parasi', 0)),
                     fazla_mesai=float(d.get('fazla_mesai', 0)),
                     izin_parasi=float(d.get('izin_parasi', 0)),
                     gelmedi_gun=int(d.get('gelmedi_gun', 0)),
                     avans_dusum=float(d.get('avans_dusum', 0)))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── API — Stok ────────────────────────────────────────────────────────────────

KATEGORI_HESAP_KOD = {
    'Elektrik': '740', 'Su': '740', 'Doğalgaz': '740',
    'Elektrik/Su/Doğalgaz': '740',
    'Market/Gıda': '741', 'Market': '741', 'Gıda': '741', 'İçecek': '741',
    'Market/Gıda/Stok': '741', 'Temizlik': '741', 'Kırtasiye': '741',
    'Bakım/Onarım': '742', 'Tamir': '742', 'Bakım': '742',
    'Sigorta': '743',
    'Muhasebe/Danışmanlık': '744', 'Muhasebe': '744', 'Danışmanlık': '744',
    'Kira': '745',
    'Telefon': '780', 'İnternet': '780', 'Diğer': '780', 'Diğer Giderler': '780',
}

@muh.route('/api/muhasebe/stok')
def api_stok():
    yil = request.args.get('yil', date.today().year, type=int)
    kat = request.args.get('kat', '')
    hesap_kodu = request.args.get('hesap_kodu', '')
    conn = mdb.get_conn()
    q = "SELECT * FROM stok WHERE strftime('%Y',tarih)=?"
    params = [str(yil)]
    if kat:
        q += " AND kategori=?"; params.append(kat)
    if hesap_kodu:
        kat_adlari = [k for k, v in KATEGORI_HESAP_KOD.items() if v == hesap_kodu]
        placeholders = ','.join(['?'] * len(kat_adlari))
        if kat_adlari:
            q += f" AND (hesap_kodu=? OR (hesap_kodu IS NULL OR hesap_kodu='') AND kategori IN ({placeholders}))"
        else:
            q += " AND hesap_kodu=?"
        params.extend([hesap_kodu] + kat_adlari)
    q += " ORDER BY tarih ASC"
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return jsonify(rows)

@muh.route('/api/muhasebe/stok/ekle', methods=['POST'])
def api_stok_ekle():
    try:
        d = request.get_json()
        odeme_kod = BANKA_AD_KODU.get(d.get('odeme_hesap',''), d.get('odeme_hesap',''))
        mdb.ekle_stok(d['tarih'], uc(d['aciklama']), float(d['tutar']),
                     d.get('kategori', 'Diğer'), d.get('belge_no', ''),
                     odeme_kod, bool(d.get('fatura_var', False)),
                     d.get('otel', 'GENEL'), d.get('not_', ''),
                     d.get('hesap_kodu', ''))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── API — Demirbaş ───────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/demirbas')
def api_demirbas():
    yil = request.args.get('yil', date.today().year, type=int)
    conn = mdb.get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM [demirbaş] WHERE strftime('%Y',tarih)=? ORDER BY tarih ASC",
        (str(yil),)).fetchall()]
    conn.close()
    return jsonify(rows)

# Banka adı → hesap kodu
BANKA_AD_KODU = {
    'Kasa TL': '100', 'İş Bankası': '102-1',
    'Ziraat Bankası': '102-2', 'Denizbank': '102-3', 'Deniz Bank': '102-3',
    'Fırat Nakit': '500-FK', 'Fırat KK': '500-FK',
    'Levent Nakit': '500-LK', 'Levent KK': '500-LK',
    'Burçin Nakit': '500-BT', 'Burçin KK': '500-BT',
}
BANKA_HESAP_KODU = {'100': '100', '102-1': '102-1', '102-2': '102-2', '102-3': '102-3',
                    'KASA': '100', 'IS': '102-1', 'ZRH': '102-2', 'DNZ': '102-3',
                    'FK-NKT': '500-FK', 'FK-KK': '500-FK',
                    'LK-NKT': '500-LK', 'LK-KK': '500-LK',
                    'BT-NKT': '500-BT', 'BT-KK': '500-BT'}


@muh.route('/api/muhasebe/demirbas/ekle', methods=['POST'])
def api_demirbas_ekle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        toplam = float(d.get('miktar', 1)) * float(d['birim_fiyat'])
        t = d['tarih']
        yil = int(t[:4]); ay = int(t[5:7])
        odeme_ad = d.get('odeme_hesap', '')
        odeme_kod = BANKA_AD_KODU.get(odeme_ad, odeme_ad)
        conn.execute("""
            INSERT INTO [demirbaş] (tarih,aciklama,miktar,birim_fiyat,toplam,odeme_hesap,fatura_no,otel,not_)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (t, d['aciklama'],
                float(d.get('miktar', 1)), float(d['birim_fiyat']), toplam,
                odeme_ad, d.get('fatura_no', ''),
                d.get('otel', 'GENEL'), d.get('not_', '')))
        # Yevmiye - aynı conn üzerinden
        dem_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if toplam > 0:
            conn.execute("""
                INSERT INTO yevmiye (tarih,yil,ay,belge_no,islem_tipi,borc_hesap,alacak_hesap,tutar,aciklama,otel,kaynak_tablo,kaynak_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (t, yil, ay, d.get('fatura_no',''), 'Demirbaş Alımı',
                    '255', odeme_kod or '100', toplam,
                    uc(d['aciklama']), d.get('otel','GENEL'), 'demirbaş', dem_id))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/demirbas/sil', methods=['POST'])
def api_demirbas_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute('DELETE FROM yevmiye WHERE kaynak_tablo=? AND kaynak_id=?', ('demirbaş', d['id']))
        conn.execute('DELETE FROM [demirbaş] WHERE id=?', (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── API — Vergi ────────────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/vergi')
@admin_required
def api_vergi():
    yil = request.args.get('yil', date.today().year, type=int)
    conn = mdb.get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM vergi WHERE donem_yil=? ORDER BY donem_ay, vergi_turu", (yil,)).fetchall()]
    conn.close()
    for r in rows:
        if r.get('donem_ay') and 1 <= r['donem_ay'] <= 12:
            r['donem_ay_adi'] = AYLAR[r['donem_ay']-1]
    return jsonify(rows)

@muh.route('/api/muhasebe/vergi/ekle', methods=['POST'])
@admin_required
def api_vergi_ekle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute("""
            INSERT INTO vergi (tarih,donem_yil,donem_ay,vergi_turu,matrah,tutar,odeme_banka,durum,aciklama)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (d.get('tarih'), int(d['donem_yil']), int(d['donem_ay']),
              d['vergi_turu'], float(d.get('matrah', 0)), float(d['tutar']),
              d.get('odeme_banka', ''), d.get('durum', 'Bekliyor'), d.get('aciklama', '')))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/vergi/onayla', methods=['POST'])
@admin_required
def api_vergi_onayla():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        tarih = d.get('tarih', date.today().isoformat())
        row = conn.execute("SELECT * FROM vergi WHERE id=?", (int(d['id']),)).fetchone()
        conn.execute("UPDATE vergi SET durum='Ödendi', tarih=? WHERE id=?",
                     (tarih, int(d['id'])))
        if row:
            import muhasebe_db as mdb2
            banka = row['odeme_banka'] or 'IS'
            if banka in ('100','102-1','102-2','102-3') or banka.startswith('500-'):
                banka_hesap = banka
            else:
                banka_hesap = '100' if banka=='KASA' else '102-2' if banka=='ZRH' else '102-3' if banka=='DNZ' else '102-1'
            mdb2._yevmiye_ekle(conn, tarih, 'Vergi Ödemesi', '770', banka_hesap,
                               row['tutar'], f"{row['vergi_turu']} {row['donem_yil']}/{row['donem_ay']}", 'GENEL',
                               kaynak_tablo='vergi', kaynak_id=int(d['id']))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── API — Acente Cari ─────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/acente-bakiye')
def api_acente_bakiye():
    """Acente cari hesabının (320-x) yevmiyeden gerçek bakiyesi: + ise acente bize borçlu."""
    kod = request.args.get('kod', '')
    hesap = ACENTE_HESAP.get(kod)
    if not hesap:
        return jsonify({'bakiye': 0, 'hesap': None, 'borc': 0, 'alacak': 0})
    conn = mdb.get_conn()
    borc = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE borc_hesap=?", (hesap,)).fetchone()[0]
    alacak = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE alacak_hesap=?", (hesap,)).fetchone()[0]
    conn.close()
    return jsonify({'bakiye': borc - alacak, 'hesap': hesap, 'borc': borc, 'alacak': alacak})

@muh.route('/api/muhasebe/acente-detay')
def api_acente_detay():
    """Acente cari hesabının (320-x) föy bazlı dökümü — fatura kesmek için.
    Her föy için: rez. bedeli (borç), komisyon (alacak), net bakiye, ve o föye
    ait bankadan gelen fatura tahsilatları (varsa) ayrı satırda gösterilir."""
    kod = request.args.get('kod', '')
    yil = request.args.get('yil', date.today().year, type=int)
    hesap = ACENTE_HESAP.get(kod)

    # Tüm acenteler modu: her acentenin detayını birleştir
    if not hesap:
        tum_foyler = []
        tum_kesilen = []
        for a_kod, a_hesap in ACENTE_HESAP.items():
            det = _acente_detay_hesapla(a_hesap, a_kod, yil)
            for f in det['foyler']:
                f['acente_kod'] = a_kod
            tum_foyler.extend(det['foyler'])
            tum_kesilen.extend(det['kesilen_faturalar'])
        tum_foyler.sort(key=lambda x: x['tarih'])
        return jsonify({'foyler': tum_foyler, 'fatura_disi_bakiye': 0,
                        'kesilen_faturalar': tum_kesilen})

    det = _acente_detay_hesapla(hesap, kod, yil)
    return jsonify(det)


def _acente_detay_hesapla(hesap, kod, yil):
    import re as _re
    conn = mdb.get_conn()
    rows = conn.execute("""
        SELECT tarih, islem_tipi, borc_hesap, alacak_hesap, tutar, aciklama
        FROM yevmiye
        WHERE (borc_hesap=? OR alacak_hesap=?) AND yil=?
        ORDER BY tarih ASC, id ASC
    """, (hesap, hesap, yil)).fetchall()
    conn.close()

    foyler = {}
    faturalanan = set()
    kesilen_faturalar = []
    fatura_disi_bakiye = 0.0
    BANKA_AD = {'102-1': 'İş Bankası', '102-2': 'Ziraat Bankası', '102-3': 'Denizbank'}
    for r in rows:
        m = _re.search(r'[Ff][Öö][Yy]#(\d+)\s+(.*?)\s+\[ACENTE-OTO\]', r['aciklama'] or '', _re.IGNORECASE)
        if m:
            foy_no, misafir = m.group(1), m.group(2)
            f = foyler.setdefault(foy_no, {'foy_no': foy_no, 'misafir': misafir,
                                            'tarih': r['tarih'], 'rez_tutari': 0, 'komisyon': 0})
            if r['borc_hesap'] == hesap:
                f['rez_tutari'] += r['tutar']
            else:
                f['komisyon'] += r['tutar']
            continue
        mf = _re.search(r'[Ff][Öö][Yy]#(\d+)\s+(.*?)\s+\[ACENTE-FATURA\]', r['aciklama'] or '', _re.IGNORECASE)
        if mf:
            faturalanan.add(mf.group(1))
            fn = _re.search(r'\[FATURA:(.*?)\]', r['aciklama'] or '')
            kesilen_faturalar.append({
                'tarih': r['tarih'], 'foy_no': mf.group(1), 'misafir': mf.group(2),
                'tutar': r['tutar'], 'fatura_no': fn.group(1) if fn else '',
                'tahsil_edildi': False  # sonra tahsilat kaydına bakılacak
            })
            continue
        mt = _re.search(r'[Ff][Öö][Yy]#(\d+)\s+(.*?)\s+\[ACENTE-TAHSILAT\]', r['aciklama'] or '', _re.IGNORECASE)
        if mt:
            # Tahsilat kaydını kesilen_faturalar listesindeki ilgili föye işaretle
            for kf in kesilen_faturalar:
                if kf['foy_no'] == mt.group(1):
                    kf['tahsil_edildi'] = True
                    kf['tahsilat_tarihi'] = r['tarih']
                    banka_kodu = r['borc_hesap'] if r['borc_hesap'] != hesap else r['alacak_hesap']
                    kf['banka'] = BANKA_AD.get(banka_kodu, banka_kodu)
                    kf['banka_kodu'] = banka_kodu
                    break
            continue
        # föy'e bağlı olmayan (genel fatura tahsilatı) hareket
        tutar = r['tutar'] if r['borc_hesap'] == hesap else -r['tutar']
        fatura_disi_bakiye += tutar
    kesilen_faturalar.sort(key=lambda x: x['tarih'], reverse=True)

    sonuc = []
    for f in foyler.values():
        f['net'] = round(f['rez_tutari'] - f['komisyon'], 2)
        f['fatura_edildi'] = f['foy_no'] in faturalanan
        sonuc.append(f)
    sonuc.sort(key=lambda x: x['tarih'])
    return {'foyler': sonuc, 'fatura_disi_bakiye': round(fatura_disi_bakiye, 2),
            'kesilen_faturalar': kesilen_faturalar}

@muh.route('/api/muhasebe/acente-fatura-kes', methods=['POST'])
def api_acente_fatura_kes():
    """Seçilen föyleri 'faturalandı' işaretler: her föy için net tutar kadar
    banka borç / acente hesabı alacak kaydı açar (tek tek, föy etiketli — böylece
    hangi föylerin faturalandığı sonradan da görülebilir)."""
    import re as _re
    try:
        d = request.get_json()
        kod = d.get('acente_kod') or d.get('kod')
        foy_nolar = [str(x) for x in d.get('foy_nolar', [])]
        tarih = d.get('tarih') or date.today().isoformat()
        banka = d.get('odeme_banka', 'IS')
        otel = d.get('otel', 'LEO')
        fatura_no = (d.get('fatura_no') or '').strip()
        hesap = ACENTE_HESAP.get(kod)
        if not hesap or not foy_nolar:
            return jsonify({'ok': False, 'error': 'Acente veya föy seçimi eksik'}), 400
        if not fatura_no:
            return jsonify({'ok': False, 'error': 'Fatura No zorunludur'}), 400
        banka_hesap = '102-2' if banka == 'ZRH' else '102-3' if banka == 'DNZ' else '102-1'

        conn = mdb.get_conn()
        # Mükerrer fatura no kontrolü
        mukerrer = conn.execute(
            "SELECT 1 FROM yevmiye WHERE aciklama LIKE ? AND aciklama LIKE '%[ACENTE-FATURA]%'",
            (f'%[FATURA:{fatura_no}]%',)
        ).fetchone()
        if mukerrer:
            conn.close()
            return jsonify({'ok': False, 'error': f'"{fatura_no}" numaralı fatura zaten kesilmiş'}), 400
        toplam = 0.0
        detaylar = []
        for foy_no in foy_nolar:
            rows = conn.execute("""
                SELECT borc_hesap, alacak_hesap, tutar, aciklama FROM yevmiye
                WHERE (borc_hesap=? OR alacak_hesap=?) AND aciklama LIKE ? AND aciklama LIKE '%[ACENTE-OTO]%'
            """, (hesap, hesap, f'Föy#{foy_no} %')).fetchall()
            if not rows:
                continue
            zaten_var = conn.execute("""
                SELECT 1 FROM yevmiye WHERE aciklama LIKE ? AND aciklama LIKE '%[ACENTE-FATURA]%'
            """, (f'Föy#{foy_no} %',)).fetchone()
            if zaten_var:
                continue
            net = 0.0
            misafir = ''
            for r in rows:
                mm = _re.search(r'Föy#\d+\s+(.*?)\s+\[ACENTE-OTO\]', r['aciklama'] or '')
                if mm:
                    misafir = mm.group(1)
                net += r['tutar'] if r['borc_hesap'] == hesap else -r['tutar']
            net = round(net, 2)
            if net <= 0:
                continue
            # Sadece fatura kaydı — banka yok, acente borçlanıyor (320 BORÇ / 600 ALACAK zaten ACENTE-OTO'da var)
            # [ACENTE-FATURA] etiketi + fatura tarihi + fatura no kaydediliyor
            mdb._yevmiye_ekle(conn, tarih, 'Acente Fatura Kesildi', hesap, hesap, net,
                              f'Föy#{foy_no} {misafir} [ACENTE-FATURA] fatura kesildi' +
                              (f' [FATURA:{fatura_no}]' if fatura_no else ''), otel)
            toplam += net
            detaylar.append({'foy_no': foy_no, 'misafir': misafir, 'net': net})
        conn.commit(); conn.close()
        return jsonify({'ok': True, 'toplam': round(toplam, 2), 'detaylar': detaylar})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/acente-fatura-iptal', methods=['POST'])
def api_acente_fatura_iptal():
    """Tek bir föy için kesilmiş faturayı (bankaya gelen tahsilat kaydını) geri alır.
    Föy yeniden 'Bekliyor' durumuna döner, dilenirse tekrar faturalandırılabilir."""
    try:
        d = request.get_json()
        foy_no = str(d.get('foy_no', ''))
        if not foy_no:
            return jsonify({'ok': False, 'error': 'Föy no eksik'}), 400
        conn = mdb.get_conn()
        silinen = conn.execute("""
            DELETE FROM yevmiye WHERE aciklama LIKE ? AND aciklama LIKE '%[ACENTE-FATURA]%'
        """, (f'Föy#{foy_no} %',))
        adet = silinen.rowcount
        conn.commit(); conn.close()
        if adet == 0:
            return jsonify({'ok': False, 'error': 'Bu föy için faturalandırılmış kayıt bulunamadı'}), 404
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/acente-fatura-duzenle', methods=['POST'])
def api_acente_fatura_duzenle():
    """Kesilmiş bir föy faturasının tarihini, fatura no'sunu veya bankasını düzeltir
    (tutar değişmez — tutarı değiştirmek için önce iptal edip föyü yeniden faturalandırın)."""
    try:
        d = request.get_json()
        foy_no = str(d.get('foy_no', ''))
        tarih = d.get('tarih')
        fatura_no = (d.get('fatura_no') or '').strip()
        banka = d.get('odeme_banka', 'IS')
        if not foy_no or not tarih:
            return jsonify({'ok': False, 'error': 'Föy no veya tarih eksik'}), 400
        banka_hesap = '102-2' if banka == 'ZRH' else '102-3' if banka == 'DNZ' else '102-1'

        conn = mdb.get_conn()
        row = conn.execute("""
            SELECT id, aciklama, alacak_hesap FROM yevmiye
            WHERE aciklama LIKE ? AND aciklama LIKE '%[ACENTE-FATURA]%'
        """, (f'Föy#{foy_no} %',)).fetchone()
        if not row:
            conn.close()
            return jsonify({'ok': False, 'error': 'Bu föy için faturalandırılmış kayıt bulunamadı'}), 404

        import re as _re
        eski_aciklama = row['aciklama']
        if _re.search(r'\[FATURA:.*?\]', eski_aciklama):
            yeni_aciklama = _re.sub(r'\[FATURA:.*?\]', f'[FATURA:{fatura_no}]', eski_aciklama) if fatura_no \
                else _re.sub(r'\s*\[FATURA:.*?\]', '', eski_aciklama)
        elif fatura_no:
            yeni_aciklama = f'{eski_aciklama} [FATURA:{fatura_no}]'
        else:
            yeni_aciklama = eski_aciklama

        conn.execute("""
            UPDATE yevmiye SET tarih=?, borc_hesap=?, aciklama=? WHERE id=?
        """, (tarih, banka_hesap, yeni_aciklama, row['id']))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/acente')
def api_acente():
    yil = request.args.get('yil', date.today().year, type=int)
    acente = request.args.get('acente', '')
    conn = mdb.get_conn()

    # Föy'e bağlı (otomatik) kayıtları, rezervasyonun GÜNCEL fiyatı ve acentenin
    # GÜNCEL komisyon oranıyla yeniden hesaplayıp senkronize et (fiyat sonradan
    # değiştirilmiş olabilir, eski komisyon donuk kalmasın).
    try:
        oto_rows = conn.execute(
            "SELECT id, foy_no, acente_kod, komisyon_tl, rez_tutari FROM acente_cari "
            "WHERE foy_no IS NOT NULL AND TRIM(CAST(foy_no AS TEXT))!=''"
        ).fetchall()
        if oto_rows:
            rez_conn = db.get_conn()
            for r in oto_rows:
                try:
                    foy_no = int(r['foy_no'])
                except (TypeError, ValueError):
                    continue
                rez = rez_conn.execute(
                    "SELECT toplam_fiyat FROM rezervasyonlar WHERE foy_no=?", (foy_no,)
                ).fetchone()
                if not rez:
                    continue
                guncel_tutar = float(rez['toplam_fiyat'] or 0)
                a = conn.execute(
                    "SELECT komisyon_orani FROM acenteler WHERE kod=?", (r['acente_kod'],)
                ).fetchone()
                oran = float(a['komisyon_orani']) if a else 0.0
                guncel_kom = round(guncel_tutar * oran / 100, 2)
                if abs(guncel_tutar - float(r['rez_tutari'] or 0)) > 0.005 or abs(guncel_kom - float(r['komisyon_tl'] or 0)) > 0.005:
                    conn.execute(
                        "UPDATE acente_cari SET rez_tutari=?, komisyon_oran=?, komisyon_tl=? WHERE id=?",
                        (guncel_tutar, oran, guncel_kom, r['id'])
                    )
            rez_conn.close()
        conn.commit()
    except Exception as e:
        print(f'Acente senkron hatasi: {e}')
        conn.rollback()

    q = "SELECT * FROM acente_cari WHERE strftime('%Y',tarih)=?"
    params = [str(yil)]
    if acente: q += " AND acente_kod=?"; params.append(acente)
    q += " ORDER BY tarih ASC"
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    acenteler = [dict(r) for r in conn.execute("SELECT * FROM acenteler WHERE aktif=1").fetchall()]
    conn.close()
    return jsonify({'rows': rows, 'acenteler': acenteler})

@muh.route('/api/muhasebe/acente/ekle', methods=['POST'])
def api_acente_ekle():
    """Acentelerden gelen FATURA TAHSİLATINI kaydeder (her zaman banka).
    Rezervasyon bazlı borç/komisyon kayıtları artık rezervasyon kaydedilirken
    otomatik oluşturuluyor (bkz. app.py acente_jolly_oto_kaydet)."""
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        gelen = float(d.get('gelen_odeme', d.get('tutar', 0)))
        fatura_no = (d.get('fatura_no') or '').strip()
        conn.execute("""
            INSERT INTO acente_cari
            (tarih,acente_kod,foy_no,rez_no,misafir,rez_tutari,komisyon_oran,komisyon_tl,gelen_odeme,otel,fatura_no)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (d['tarih'], d['acente_kod'], None, '', 'Fatura Tahsilatı', 0, 0, 0,
              gelen, d.get('otel', 'LEO'), fatura_no))
        acente_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if gelen > 0:
            banka = d.get('odeme_banka', 'IS')
            banka_hesap = '102-2' if banka=='ZRH' else '102-3' if banka=='DNZ' else '102-1'
            acente_hesap = ACENTE_HESAP.get(d['acente_kod'], '320-1')
            aciklama = f"{d['acente_kod']} fatura tahsilatı" + (f" [FATURA:{fatura_no}]" if fatura_no else "")
            mdb._yevmiye_ekle(conn, d['tarih'], 'Acente Fatura Tahsilatı',
                              banka_hesap, acente_hesap, gelen,
                              aciklama, d.get('otel','LEO'),
                              kaynak_tablo='acente_cari', kaynak_id=acente_id)
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── API — Ortak Cari ──────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/ortak')
@admin_required
def api_ortak():
    yil = request.args.get('yil', date.today().year, type=int)
    ortak = request.args.get('ortak', '')
    conn = mdb.get_conn()
    q = "SELECT * FROM ortak_cari WHERE strftime('%Y',tarih)=?"
    params = [str(yil)]
    if ortak: q += " AND ortak=?"; params.append(ortak)
    q += " ORDER BY tarih ASC"
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return jsonify(rows)

def _ortak_yevmiye_yaz(conn, ortak_id, d):
    """Bir ortak_cari kaydı için yevmiye satırını (yeniden) yazar."""
    tutar = float(d['tutar'])
    iade = float(d.get('iade', 0))
    net = tutar - iade
    islem_tipi = d.get('islem_tipi', 'Ortak Gider (Kendi Cebinden)')
    if net <= 0:
        return
    ortak_hesap = f"500-{d['ortak']}"
    odeme = d.get('odeme_sekli', '')
    banka_hesap = '100' if 'Nakit' in odeme else '102-2' if 'Ziraat' in odeme else '102-3' if 'Deniz' in odeme else '102-1'

    if islem_tipi == 'Ortaga Geri Odeme':
        mdb._yevmiye_ekle(conn, d['tarih'], 'Ortağa Geri Ödeme',
                          ortak_hesap, banka_hesap,
                          net, d['aciklama'], d.get('otel','GENEL'),
                          kaynak_tablo='ortak_cari', kaynak_id=ortak_id)
    else:
        gider_hesap = '741' if 'Market' in d.get('gider_kategori','') else '742' if 'Tamir' in d.get('gider_kategori','') else '740' if 'Elektrik' in d.get('gider_kategori','') else '780'
        mdb._yevmiye_ekle(conn, d['tarih'], 'Ortak Gider (Kendi Cebinden)',
                          gider_hesap, ortak_hesap,
                          net, d['aciklama'], d.get('otel','GENEL'),
                          kaynak_tablo='ortak_cari', kaynak_id=ortak_id)


@muh.route('/api/muhasebe/ortak/ekle', methods=['POST'])
@admin_required
def api_ortak_ekle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        tutar = float(d['tutar'])
        iade = float(d.get('iade', 0))
        conn.execute("""
            INSERT INTO ortak_cari
            (tarih,ortak,belge_no,aciklama,gider_kategori,tutar,odeme_sekli,iade,otel)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (d['tarih'], d['ortak'], d.get('belge_no', ''), uc(d['aciklama']),
              d.get('gider_kategori', ''), tutar,
              d.get('odeme_sekli', ''), iade, d.get('otel', 'GENEL')))
        ortak_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        _ortak_yevmiye_yaz(conn, ortak_id, d)
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── API — Mizan ───────────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/mizan')
@login_required
@admin_required
def api_mizan():
    """Mizan - dogrudan otel.db tablolarından hesaplar, yevmiyeye bagımlı değil."""
    yil = request.args.get('yil', date.today().year, type=int)
    yil_str = str(yil)

    import database as otel_db
    otel = otel_db.get_conn()
    muh_conn = mdb.get_conn()

    # Rezervasyonları yıldan filtrele (giriş tarihine göre)
    rezler = [dict(r) for r in otel.execute(
        "SELECT * FROM rezervasyonlar WHERE strftime('%Y',giris)=? AND durum!='Kapora Yandı'",
        (yil_str,)).fetchall()]

    def _f(v): return float(v or 0)

    # ── AKTİF (VARLIKLAR) ──
    # 100 Kasa - Nakit tahsilatlar
    nakit_rez = sum(_f(r['rez_tahsilat']) for r in rezler if r.get('rez_odeme_sekli','') == 'Nakit')
    nakit_adis = otel.execute(
        "SELECT COALESCE(SUM(ao.tutar),0) FROM adisyon_odemeler ao JOIN rezervasyonlar r ON ao.foy_no=r.foy_no WHERE ao.odeme_sekli='Nakit' AND strftime('%Y',r.giris)=?",
        (yil_str,)).fetchone()[0] or 0
    # Manuel yevmiye nakit giriş/çıkışları
    yev_nakit_borc = muh_conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap='100' AND islem_tipi NOT LIKE 'Rezervasyon Tahsilat%' AND islem_tipi NOT LIKE 'Adisyon Tahsilat%' AND islem_tipi != 'Kapora'", (yil,)).fetchone()[0] or 0
    yev_nakit_alacak = muh_conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND alacak_hesap='100'", (yil,)).fetchone()[0] or 0
    kasa_borc = nakit_rez + nakit_adis + yev_nakit_borc
    kasa_alacak = yev_nakit_alacak
    kasa_bak = kasa_borc - kasa_alacak

    # 102-1 İş Bankası - banka tahsilatlar (acente üzerinden ödenen rezervasyonlar hariç —
    # onlar gerçekten bankaya gelmedi, acente cari hesabına yazılır, fatura kesilince banka girer)
    banka_rez = sum(_f(r['rez_tahsilat']) for r in rezler
                     if r.get('rez_odeme_sekli','') not in ('Nakit','') and not str(r.get('rez_odeme_sekli','')).startswith('Acente'))
    acente_rez = sum(_f(r['rez_tahsilat']) for r in rezler if str(r.get('rez_odeme_sekli','')).startswith('Acente'))
    banka_kapora = sum(_f(r['kapora']) for r in rezler)
    banka_adis = otel.execute(
        "SELECT COALESCE(SUM(ao.tutar),0) FROM adisyon_odemeler ao JOIN rezervasyonlar r ON ao.foy_no=r.foy_no WHERE ao.odeme_sekli!='Nakit' AND strftime('%Y',r.giris)=?",
        (yil_str,)).fetchone()[0] or 0
    # Manuel/otomatik yevmiye banka hareketleri — acente fatura tahsilatı dahil (gerçekten bankaya giren para)
    yev_banka_borc = muh_conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap='102-1' AND islem_tipi NOT LIKE 'Rezervasyon Tahsilat%' AND islem_tipi NOT LIKE 'Adisyon Tahsilat%' AND islem_tipi != 'Kapora'", (yil,)).fetchone()[0] or 0
    yev_banka_alacak = muh_conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND alacak_hesap='102-1'", (yil,)).fetchone()[0] or 0
    banka_borc = banka_rez + banka_kapora + banka_adis + yev_banka_borc
    banka_alacak = yev_banka_alacak
    banka_bak = banka_borc - banka_alacak

    # 320-x Acente Cari — JollyTur vb. (yevmiyeden gerçek bakiye; rezervasyon yılına göre değil
    # hesabın o ana kadarki toplam hareketine göre — Mizan'da "bakiye" mantığı bu şekilde tutarlı kalır)
    acente_satirlari = []
    for kod, hesap in ACENTE_HESAP.items():
        a_borc = muh_conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap=?", (yil, hesap)).fetchone()[0] or 0
        a_alacak = muh_conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND alacak_hesap=?", (yil, hesap)).fetchone()[0] or 0
        if a_borc or a_alacak:
            adi = {'BKG':'Booking Cari','EXP':'Expedia Cari','JLY':'JollyTur Cari','TTS':'TatilSepeti Cari','ETS':'ETSTUR Cari'}.get(kod, f'{kod} Cari')
            acente_satirlari.append((hesap, adi, a_borc, a_alacak))

    # 120 Müşteri Cari
    muc_borc = sum(_f(r['toplam_fiyat']) for r in rezler)  # konaklama geliri
    adis_gelir = otel.execute(
        "SELECT COALESCE(SUM(a.tutar),0) FROM adisyonlar a JOIN rezervasyonlar r ON a.foy_no=r.foy_no WHERE strftime('%Y',r.giris)=?",
        (yil_str,)).fetchone()[0] or 0
    muc_borc += adis_gelir

    muc_alacak = (banka_rez + banka_kapora + banka_adis +
                  nakit_rez + nakit_adis + acente_rez)
    muc_bak = muc_borc - muc_alacak

    # ── GELİRLER ──
    leo_kon = sum(_f(r['toplam_fiyat']) for r in rezler if r.get('otel')=='LEO')
    cv_kon  = sum(_f(r['toplam_fiyat']) for r in rezler if r.get('otel')=='CV')
    adis_gel = adis_gelir

    # ── GİDERLER (yevmiyeden) ──
    mizan_yev = mdb.get_mizan_ozet(yil)
    maas  = mizan_yev.get('maas', 0) or 0
    vergi = mizan_yev.get('vergi', 0) or 0
    stok  = mizan_yev.get('stok', 0) or 0
    dem   = mizan_yev.get('demirbaş', 0) or 0
    ortak = (mizan_yev.get('ortak_lk',0) or 0) + (mizan_yev.get('ortak_bt',0) or 0) + (mizan_yev.get('ortak_fk',0) or 0)
    komisyon = muh_conn.execute("SELECT COALESCE(SUM(tutar),0) FROM yevmiye WHERE yil=? AND borc_hesap='730'", (yil,)).fetchone()[0] or 0

    otel.close(); muh_conn.close()

    # Satirlar
    satirlar = []
    toplam_borc = 0; toplam_alacak = 0

    def satir(kod, ad, borc, alacak, tip='Aktif'):
        nonlocal toplam_borc, toplam_alacak
        if borc==0 and alacak==0: return
        toplam_borc += borc; toplam_alacak += alacak
        bak = alacak-borc if tip in ('Gelir','Pasif','Ozkaynak') else borc-alacak
        satirlar.append({'tip':'veri','kod':kod,'ad':ad,'borc':round(borc,2),'alacak':round(alacak,2),'bakiye':round(bak,2)})

    satirlar.append({'tip':'baslik','kod':'━━','ad':'AKTİF (VARLIKLAR)','borc':0,'alacak':0})
    satir('100',   'Kasa TL',     kasa_borc,  kasa_alacak)
    satir('102-1', 'İş Bankası',  banka_borc, banka_alacak)
    satir('120',   'Müşteri Cari',muc_borc,   muc_alacak)
    for hesap, adi, a_borc, a_alacak in acente_satirlari:
        satir(hesap, adi, a_borc, a_alacak)
    satirlar.append({'tip':'bos'})

    satirlar.append({'tip':'baslik','kod':'━━','ad':'GELİRLER','borc':0,'alacak':0})
    satir('600', 'Konaklama Geliri - Leo', 0, leo_kon, 'Gelir')
    satir('601', 'Konaklama Geliri - CV',  0, cv_kon,  'Gelir')
    satir('610', 'Adisyon Geliri',         0, adis_gel,'Gelir')
    satirlar.append({'tip':'bos'})

    satirlar.append({'tip':'baslik','kod':'━━','ad':'GİDERLER','borc':0,'alacak':0})
    if maas:     satir('720','Personel Maaş', maas,  0, 'Gider')
    if komisyon: satir('730','Acente Komisyonu', komisyon, 0, 'Gider')
    if vergi:    satir('770','Vergi',         vergi, 0, 'Gider')
    if dem:      satir('255','Demirbaş',      dem,   0, 'Gider')

    # Yevmiyeden kaydedilmiş diğer tüm gider hesapları (740-780 arası ve 255 hariç zaten işlenenler)
    islenecekler = {'720','730','770','255','500'}  # 740 yevmiyede 153 olarak yazılır
    muh_conn2 = mdb.get_conn()
    gider_hesaplar = muh_conn2.execute("""
        SELECT h.kod, h.ad,
               COALESCE(SUM(CASE WHEN y.borc_hesap=h.kod THEN y.tutar ELSE 0 END),0) AS borc,
               COALESCE(SUM(CASE WHEN y.alacak_hesap=h.kod THEN y.tutar ELSE 0 END),0) AS alacak
        FROM hesaplar h
        LEFT JOIN yevmiye y ON (y.borc_hesap=h.kod OR y.alacak_hesap=h.kod) AND y.yil=?
        WHERE h.tip='Gider' AND h.aktif=1
        GROUP BY h.kod
        HAVING borc>0 OR alacak>0
        ORDER BY h.kod
    """, (yil,)).fetchall()
    muh_conn2.close()
    for row in gider_hesaplar:
        if row[0] not in islenecekler:
            satir(row[0], row[1], row[2], row[3], 'Gider')
            islenecekler.add(row[0])

    satirlar.append({'tip':'bos'})

    satirlar.append({'tip':'baslik','kod':'━━','ad':'ÖZKAYNAKLAR','borc':0,'alacak':0})
    satirlar.append({'tip':'bos'})

    gelir_toplam = leo_kon + cv_kon + adis_gel
    # Gider toplamı: yevmiyedeki TÜM gider hesap borçları
    muh_conn3 = mdb.get_conn()
    gider_toplam_yev = muh_conn3.execute("""
        SELECT COALESCE(SUM(y.tutar),0)
        FROM yevmiye y JOIN hesaplar h ON y.borc_hesap=h.kod
        WHERE h.tip='Gider' AND y.yil=?
    """, (yil,)).fetchone()[0] or 0
    muh_conn3.close()
    # personel_maas ve vergi tablosu kaynaklı giderler de dahil (bunlar yevmiyede olmayabilir)
    gider_toplam = max(gider_toplam_yev, maas + vergi + stok + dem + ortak + komisyon)
    net = gelir_toplam - gider_toplam

    satirlar.append({'tip':'net','kod':'NET','ad':'NET KÂR / ZARAR',
                     'borc': round(abs(net),2) if net<0 else 0,
                     'alacak': round(net,2) if net>=0 else 0,
                     'bakiye': round(net,2)})

    return jsonify({'satirlar': satirlar, 'net': round(net,2),
                    'toplam_borc': round(toplam_borc,2),
                    'toplam_alacak': round(toplam_alacak,2)})


# ── API — Gelir Aktarım (Otel DB → Muhasebe DB) ───────────────────────────────

@muh.route('/api/muhasebe/gelir-aktar', methods=['POST'])
def api_gelir_aktar():
    """Otel SQLite veritabanından muhasebe gelir_ozet tablosuna aktarır."""
    try:
        import database as otel_db
        yil = request.get_json().get('yil', date.today().year)
        otel_rez = otel_db.get_rezervasyonlar()

        from collections import defaultdict
        def empty():
            return dict(konaklama=0, restoran=0, nakit=0, kk=0, havale=0, kapora=0, acik=0)
        ozet = defaultdict(empty)

        for r in otel_rez:
            giris = r.get('giris')
            if not giris: continue
            if giris[:4] != str(yil): continue
            ay = int(giris[5:7])
            otel = r.get('otel', 'LEO')
            key = (ay, otel)
            ozet[key]['konaklama'] += float(r.get('toplam_fiyat') or 0)
            ozet[key]['kapora']    += float(r.get('kapora') or 0)
            odeme = str(r.get('rez_odeme_sekli') or '').lower()
            tah = float(r.get('rez_tahsilat') or 0)
            if 'nakit' in odeme:   ozet[key]['nakit'] += tah
            elif 'kk' in odeme or 'kart' in odeme: ozet[key]['kk'] += tah
            elif 'havale' in odeme or 'eft' in odeme: ozet[key]['havale'] += tah
            adis_odeme = str(r.get('adis_odeme_sekli') or '').lower()
            adis_tah = float(r.get('adis_tahsilat') or 0)
            if 'nakit' in adis_odeme:   ozet[key]['nakit'] += adis_tah
            elif 'kk' in adis_odeme or 'kart' in adis_odeme: ozet[key]['kk'] += adis_tah
            elif 'havale' in adis_odeme: ozet[key]['havale'] += adis_tah

        # Adisyonlar restoran geliri
        otel_adis = otel_db.get_adisyonlar()
        for a in otel_adis:
            tarih = a.get('tarih')
            if not tarih or tarih[:4] != str(yil): continue
            ay = int(tarih[5:7])
            otel = a.get('otel') or 'LEO'
            ozet[(ay, otel)]['restoran'] += float(a.get('tutar') or 0)
            ozet[(ay, otel)]['acik'] += float(a.get('tutar') or 0) - float(a.get('tutar') or 0)

        # Açık bakiye
        for r in otel_rez:
            giris = r.get('giris')
            if not giris or giris[:4] != str(yil): continue
            ay = int(giris[5:7])
            otel = r.get('otel', 'LEO')
            ozet[(ay, otel)]['acik'] += float(r.get('rez_bakiye') or 0) + float(r.get('adis_bakiye') or 0)

        # Rezervasyonları ay/otel bazında grupla (gerçek tarihler için)
        from collections import defaultdict
        rez_gruplar = defaultdict(list)
        for r in otel_rez:
            giris = r.get('giris')
            if not giris or giris[:4] != str(yil): continue
            ay = int(giris[5:7])
            otel = r.get('otel', 'LEO')
            rez_gruplar[(ay, otel)].append(dict(r))

        mdb.temizle_gelir_ozet(yil)
        count = 0
        for (ay, otel), d in sorted(ozet.items()):
            rez_listesi = rez_gruplar.get((ay, otel), [])
            mdb.kaydet_gelir_ozet(yil, ay, otel, d['konaklama'], d['restoran'],
                                  d['nakit'], d['kk'], d['havale'], d['kapora'], d['acik'],
                                  rezervasyonlar=rez_listesi)
            count += 1

        return jsonify({'ok': True, 'kayit': count, 'yil': yil})
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()}), 400

# ── Sil Route'ları ────────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/stok/sil', methods=['POST'])
def api_stok_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute('DELETE FROM yevmiye WHERE kaynak_tablo=? AND kaynak_id=?', ('stok', d['id']))
        conn.execute('DELETE FROM stok WHERE id=?', (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/vergi/sil', methods=['POST'])
@admin_required
def api_vergi_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute('DELETE FROM yevmiye WHERE kaynak_tablo=? AND kaynak_id=?', ('vergi', d['id']))
        conn.execute('DELETE FROM vergi WHERE id=?', (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/personel/maas/sil', methods=['POST'])
@admin_required
def api_maas_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute('DELETE FROM yevmiye WHERE kaynak_tablo=? AND kaynak_id=?', ('personel_maas', d['id']))
        conn.execute('DELETE FROM personel_maas WHERE id=?', (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/ortak-cari/sil', methods=['POST'])
@admin_required
def api_ortak_cari_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute('DELETE FROM yevmiye WHERE kaynak_tablo=? AND kaynak_id=?', ('ortak_cari', d['id']))
        conn.execute('DELETE FROM ortak_cari WHERE id=?', (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/kasa/sil', methods=['POST'])
def api_kasa_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute('DELETE FROM yevmiye WHERE id=?', (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/acente/sil', methods=['POST'])
def api_acente_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute("DELETE FROM yevmiye WHERE kaynak_tablo='acente_cari' AND kaynak_id=?", (d['id'],))
        conn.execute('DELETE FROM yevmiye WHERE kaynak_tablo=? AND kaynak_id=?', ('acente_cari', d['id']))
        conn.execute('DELETE FROM acente_cari WHERE id=?', (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

# ── Gider Sekmeleri: yevmiyeden borc_hesap koduna göre ───────────────────────

@muh.route('/api/muhasebe/gider_sekme')
def api_gider_sekme():
    """7xx hesap koduna göre yevmiye kayıtlarını döndürür (tüm kaynaklar)."""
    yil        = request.args.get('yil', date.today().year, type=int)
    hesap_kodu = request.args.get('hesap_kodu', '')
    if not hesap_kodu:
        return jsonify([])
    conn = mdb.get_conn()
    rows = conn.execute("""
        SELECT y.id, y.tarih, y.aciklama, y.tutar, y.borc_hesap,
               y.alacak_hesap, y.kaynak_tablo, y.kaynak_id, y.islem_tipi
        FROM yevmiye y
        WHERE y.yil=? AND y.borc_hesap=?
        ORDER BY y.tarih ASC
    """, (yil, hesap_kodu)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])



# ── KK Komisyon ──────────────────────────────────────────────────────────────

@muh.route('/api/muhasebe/kk_komisyon')
def api_kk_komisyon():
    yil = request.args.get('yil', date.today().year, type=int)
    conn = mdb.get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM kk_komisyon WHERE strftime('%Y',tarih)=? ORDER BY tarih ASC",
        (str(yil),)
    ).fetchall()]
    conn.close()
    return jsonify(rows)

@muh.route('/api/muhasebe/kk_komisyon/ekle', methods=['POST'])
def api_kk_komisyon_ekle():
    try:
        d = request.get_json()
        t = d['tarih']
        yil = int(t[:4]); ay = int(t[5:7])
        tutar = float(d['tutar'])
        alacak = d.get('alacak_hesap', '102-1')
        otel = d.get('otel', 'GENEL')
        conn = mdb.get_conn()
        conn.execute(
            "INSERT INTO kk_komisyon(tarih,foy_no,aciklama,tutar,alacak_hesap,otel) VALUES(?,?,?,?,?,?)",
            (t, d.get('foy_no'), uc(d.get('aciklama','')), tutar, alacak, otel)
        )
        kid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # Yevmiye: 760 borç / alacak hesap alacak
        conn.execute("""
            INSERT INTO yevmiye(tarih,yil,ay,belge_no,islem_tipi,borc_hesap,alacak_hesap,tutar,aciklama,otel,kaynak_tablo,kaynak_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (t, yil, ay, '', 'KK Komisyon Gideri', '760', alacak,
              tutar, d.get('aciklama','KK Komisyonu'), otel, 'kk_komisyon', kid))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/kk_komisyon/guncelle', methods=['POST'])
def api_kk_komisyon_guncelle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute(
            "UPDATE kk_komisyon SET tarih=?,foy_no=?,aciklama=?,tutar=?,alacak_hesap=? WHERE id=?",
            (d['tarih'], d.get('foy_no'), uc(d.get('aciklama','')),
             float(d['tutar']), d.get('alacak_hesap','102-1'), d['id'])
        )
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/kk_komisyon/sil', methods=['POST'])
def api_kk_komisyon_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute("DELETE FROM yevmiye WHERE kaynak_tablo='kk_komisyon' AND kaynak_id=?", (d['id'],))
        conn.execute("DELETE FROM kk_komisyon WHERE id=?", (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── Acente Tahsilat Al (fatura kesildi, para bankaya geldi) ──────────────────

@muh.route('/api/muhasebe/acente-tahsilat-al', methods=['POST'])
def api_acente_tahsilat_al():
    """Kesilmiş fatura için ödeme tahsilatı — bankaya giriş yapar, acente borcunu kapatır."""
    import re as _re
    try:
        d = request.get_json()
        kod = d.get('acente_kod')
        foy_no = str(d.get('foy_no', ''))
        tarih = d.get('tarih') or date.today().isoformat()
        banka = d.get('odeme_banka', 'IS')
        otel = d.get('otel', 'LEO')
        hesap = ACENTE_HESAP.get(kod)
        if not hesap or not foy_no:
            return jsonify({'ok': False, 'error': 'Acente veya föy eksik'}), 400
        banka_hesap = '102-2' if banka == 'ZRH' else '102-3' if banka == 'DNZ' else '102-1'

        conn = mdb.get_conn()
        # Zaten tahsil edildi mi?
        zaten = conn.execute("""
            SELECT 1 FROM yevmiye WHERE aciklama LIKE ? AND aciklama LIKE '%[ACENTE-TAHSILAT]%'
        """, (f'Föy#{foy_no} %',)).fetchone()
        if zaten:
            conn.close()
            return jsonify({'ok': False, 'error': 'Bu föy için tahsilat zaten yapılmış'}), 400

        # Fatura tutarını bul
        fat = conn.execute("""
            SELECT tutar, aciklama FROM yevmiye
            WHERE aciklama LIKE ? AND aciklama LIKE '%[ACENTE-FATURA]%'
        """, (f'Föy#{foy_no} %',)).fetchone()
        if not fat:
            conn.close()
            return jsonify({'ok': False, 'error': 'Bu föy için kesilmiş fatura bulunamadı'}), 404

        tutar = fat['tutar']
        misafir = _re.search(r'Föy#\d+\s+(.*?)\s+\[ACENTE-FATURA\]', fat['aciklama'] or '')
        misafir = misafir.group(1) if misafir else ''
        fn = _re.search(r'\[FATURA:(.*?)\]', fat['aciklama'] or '')
        fatura_no = fn.group(1) if fn else ''

        # Tahsilat: banka borç / acente alacak
        mdb._yevmiye_ekle(conn, tarih, 'Acente Tahsilat', banka_hesap, hesap, tutar,
                          f'Föy#{foy_no} {misafir} [ACENTE-TAHSILAT]' +
                          (f' [FATURA:{fatura_no}]' if fatura_no else ''), otel)
        conn.commit(); conn.close()
        return jsonify({'ok': True, 'tutar': tutar, 'misafir': misafir})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/acente-alacak-ozet')
def api_acente_alacak_ozet():
    """Tüm acentelerin ödenmemiş fatura özeti — alacak takip paneli için."""
    import re as _re
    conn = mdb.get_conn()
    bugun = date.today()
    rows = conn.execute("""
        SELECT id, tarih, aciklama, tutar, alacak_hesap
        FROM yevmiye
        WHERE aciklama LIKE '%[ACENTE-FATURA]%'
        ORDER BY tarih ASC
    """).fetchall()

    ozet = {}  # acente_kod -> {toplam, faturalar}
    for r in rows:
        foy_m = _re.search(r'Föy#(\d+)\s+(.*?)\s+\[ACENTE-FATURA\]', r['aciklama'] or '')
        if not foy_m:
            continue
        foy_no = foy_m.group(1)
        misafir = foy_m.group(2)
        fn_m = _re.search(r'\[FATURA:(.*?)\]', r['aciklama'] or '')
        fatura_no = fn_m.group(1) if fn_m else ''

        # Tahsil edildi mi?
        tahsil = conn.execute("""
            SELECT 1 FROM yevmiye WHERE aciklama LIKE ? AND aciklama LIKE '%[ACENTE-TAHSILAT]%'
        """, (f'Föy#{foy_no} %',)).fetchone()
        if tahsil:
            continue  # ödendi, geç

        # Hangi acente?
        acente_kod = None
        for k, h in ACENTE_HESAP.items():
            if h == r['alacak_hesap']:
                acente_kod = k
                break
        if not acente_kod:
            continue

        gun_fark = (bugun - date.fromisoformat(r['tarih'])).days
        if acente_kod not in ozet:
            ozet[acente_kod] = {'acente_kod': acente_kod, 'toplam': 0, 'faturalar': []}
        ozet[acente_kod]['toplam'] += r['tutar']
        ozet[acente_kod]['faturalar'].append({
            'foy_no': foy_no, 'misafir': misafir, 'tutar': r['tutar'],
            'tarih': r['tarih'], 'fatura_no': fatura_no,
            'gun_fark': gun_fark,
            'durum': 'gecikti' if gun_fark > 15 else 'uyari' if gun_fark > 7 else 'normal'
        })

    conn.close()
    return jsonify({
        'acenteler': list(ozet.values()),
        'toplam_alacak': sum(v['toplam'] for v in ozet.values()),
    })


# ── Güncelle Route'ları ───────────────────────────────────────────────────────

@muh.route('/api/muhasebe/stok/guncelle', methods=['POST'])
def api_stok_guncelle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute("""UPDATE stok SET tarih=?,belge_no=?,aciklama=?,kategori=?,hesap_kodu=?,tutar=?,
                     odeme_hesap=?,fatura_var=?,otel=?,not_=? WHERE id=?""",
            (d['tarih'], d.get('belge_no',''), uc(d['aciklama']), d.get('kategori',''),
             d.get('hesap_kodu',''), float(d['tutar']), d.get('odeme_hesap',''),
             int(d.get('fatura_var',False)), d.get('otel','GENEL'), d.get('not_',''), d['id']))
        # Yevmiye güncelle
        conn.execute("""UPDATE yevmiye SET tarih=?,tutar=?,aciklama=?,alacak_hesap=?
                     WHERE kaynak_tablo='stok' AND kaynak_id=?""",
            (d['tarih'], float(d['tutar']), f"{d.get('kategori','')}: {d['aciklama']}",
             d.get('odeme_hesap','100'), d['id']))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/vergi/guncelle', methods=['POST'])
@admin_required
def api_vergi_guncelle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute("""UPDATE vergi SET tarih=?,vergi_turu=?,matrah=?,tutar=?,
                     odeme_banka=?,durum=?,aciklama=? WHERE id=?""",
            (d.get('tarih',''), d['vergi_turu'], float(d.get('matrah',0)),
             float(d['tutar']), d.get('odeme_banka',''), d.get('durum','Bekliyor'),
             d.get('aciklama',''), d['id']))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/personel/maas/guncelle', methods=['POST'])
@admin_required
def api_maas_guncelle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        yol = float(d.get('yol_parasi', 0))
        mesai = float(d.get('fazla_mesai', 0))
        izin = float(d.get('izin_parasi', 0))
        avans_dusum = float(d.get('avans_dusum', 0))
        net_odeme = float(d['net_odeme'])
        toplam = net_odeme + yol + mesai + izin - avans_dusum
        odeme_banka = d.get('odeme_banka', '')
        otel = d.get('otel', 'GENEL')
        maas_id = int(d['id'])
        conn.execute("""UPDATE personel_maas SET tarih=?,net_odeme=?,yol_parasi=?,fazla_mesai=?,izin_parasi=?,gelmedi_gun=?,avans_dusum=?,odeme_banka=?,aciklama=?,otel=?
                     WHERE id=?""",
            (d['tarih'], net_odeme, yol, mesai, izin,
             int(d.get('gelmedi_gun',0)), avans_dusum, odeme_banka,
             d.get('aciklama',''), otel, maas_id))
        # Personel adını al
        p_row = conn.execute(
            "SELECT p.ad_soyad FROM personel_maas pm JOIN personel p ON p.id=pm.personel_id WHERE pm.id=?",
            (maas_id,)).fetchone()
        p_ad = p_row['ad_soyad'] if p_row else ''
        donem_ay = d.get('donem_ay', '')
        donem_yil = d.get('donem_yil', '')
        # Eski yevmiye kayıtlarını sil, güncel bilgilerle yeniden yaz (avans mahsubu dahil)
        conn.execute("DELETE FROM yevmiye WHERE kaynak_tablo='personel_maas' AND kaynak_id=?", (maas_id,))
        if avans_dusum > 0:
            mdb._yevmiye_ekle(conn, d['tarih'], 'Personel Maaşı (Avans Mahsubu)', '720', '195',
                              avans_dusum, f'{p_ad} {donem_ay}/{donem_yil} avans mahsubu', otel,
                              kaynak_tablo='personel_maas', kaynak_id=maas_id)
        if toplam > 0:
            mdb._yevmiye_ekle(conn, d['tarih'], 'Personel Maaşı', '720', odeme_banka or '102-1',
                              toplam, f'{p_ad} {donem_ay}/{donem_yil} maaş+yol', otel,
                              kaynak_tablo='personel_maas', kaynak_id=maas_id)
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/ortak-cari/guncelle', methods=['POST'])
@admin_required
def api_ortak_cari_guncelle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        ortak_id = int(d['id'])
        conn.execute("""UPDATE ortak_cari SET tarih=?,ortak=?,belge_no=?,aciklama=?,
                     gider_kategori=?,tutar=?,odeme_sekli=?,iade=?,otel=? WHERE id=?""",
            (d['tarih'], d['ortak'], d.get('belge_no',''), d['aciklama'],
             d.get('gider_kategori',''), float(d['tutar']), d.get('odeme_sekli',''),
             float(d.get('iade',0)), d.get('otel','GENEL'), ortak_id))
        # Eski yevmiye kaydını sil, güncel bilgilerle (ortak/işlem tipi değişmiş olabilir) yeniden yaz
        conn.execute("DELETE FROM yevmiye WHERE kaynak_tablo='ortak_cari' AND kaynak_id=?", (ortak_id,))
        _ortak_yevmiye_yaz(conn, ortak_id, d)
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/demirbas/guncelle', methods=['POST'])
def api_demirbas_guncelle():
    try:
        d = request.get_json()
        toplam = float(d.get('miktar',1)) * float(d['birim_fiyat'])
        conn = mdb.get_conn()
        conn.execute("""UPDATE [demirbaş] SET tarih=?,aciklama=?,miktar=?,birim_fiyat=?,
                     toplam=?,odeme_hesap=?,fatura_no=?,otel=?,not_=? WHERE id=?""",
            (d['tarih'], uc(d['aciklama']), float(d.get('miktar',1)), float(d['birim_fiyat']),
             toplam, d.get('odeme_hesap',''), d.get('fatura_no',''),
             d.get('otel','GENEL'), d.get('not_',''), d['id']))
        conn.execute("""UPDATE yevmiye SET tarih=?,tutar=?,aciklama=?,alacak_hesap=?
                     WHERE kaynak_tablo='demirbaş' AND kaynak_id=?""",
            (d['tarih'], toplam, d['aciklama'], d.get('odeme_hesap','100'), d['id']))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/acente/guncelle', methods=['POST'])
def api_acente_guncelle():
    try:
        d = request.get_json()
        gelen = float(d.get('gelen_odeme', d.get('tutar', 0)))
        fatura_no = (d.get('fatura_no') or '').strip()
        conn = mdb.get_conn()
        conn.execute("""UPDATE acente_cari SET tarih=?,acente_kod=?,gelen_odeme=?,otel=?,fatura_no=?
                     WHERE id=?""",
            (d['tarih'], d['acente_kod'], gelen, d.get('otel','LEO'), fatura_no, d['id']))
        # Yevmiye güncelle (tutar + hesap kodu, banka değişmiş olabilir)
        banka = d.get('odeme_banka', 'IS')
        banka_hesap = '102-2' if banka=='ZRH' else '102-3' if banka=='DNZ' else '102-1'
        acente_hesap = ACENTE_HESAP.get(d['acente_kod'], '320-1')
        aciklama = f"{d['acente_kod']} fatura tahsilatı" + (f" [FATURA:{fatura_no}]" if fatura_no else "")
        conn.execute("""UPDATE yevmiye SET tarih=?,tutar=?,borc_hesap=?,alacak_hesap=?,aciklama=?
                     WHERE kaynak_tablo='acente_cari' AND kaynak_id=?""",
            (d['tarih'], gelen, banka_hesap, acente_hesap, aciklama, d['id']))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── API — Personel Avans ──────────────────────────────────────────────────────

@muh.route('/api/muhasebe/avans', methods=['GET'])
@admin_required
def api_avans():
    personel_id = request.args.get('personel_id', type=int)
    yil = request.args.get('yil', type=int)
    ay = request.args.get('ay', type=int)
    return jsonify(mdb.get_avans(personel_id=personel_id, yil=yil, ay=ay))

@muh.route('/api/muhasebe/avans/ekle', methods=['POST'])
@admin_required
def api_avans_ekle():
    try:
        d = request.get_json()
        mdb.ekle_avans(d['tarih'], int(d['personel_id']),
                       float(d['tutar']), d.get('odeme_sekli', '100'),
                       d.get('aciklama', ''), d.get('otel', 'GENEL'))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/avans/sil', methods=['POST'])
@admin_required
def api_avans_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute("DELETE FROM yevmiye WHERE kaynak_tablo='personel_avans' AND kaynak_id=?", (d['id'],))
        conn.execute("DELETE FROM personel_avans WHERE id=?", (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/avans/guncelle', methods=['POST'])
@admin_required
def api_avans_guncelle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        avans_id = int(d['id'])
        tarih = d['tarih']
        tutar = float(d['tutar'])
        odeme_sekli = d.get('odeme_sekli', '100')
        aciklama = d.get('aciklama', '')
        otel = d.get('otel', 'GENEL')
        row = conn.execute("SELECT personel_id FROM personel_avans WHERE id=?", (avans_id,)).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Avans kaydı bulunamadı'}), 404
        p = conn.execute("SELECT ad_soyad FROM personel WHERE id=?", (row['personel_id'],)).fetchone()
        p_ad = p['ad_soyad'] if p else ''
        conn.execute("""UPDATE personel_avans SET tarih=?,tutar=?,odeme_sekli=?,aciklama=?,otel=? WHERE id=?""",
            (tarih, tutar, odeme_sekli, aciklama, otel, avans_id))
        # Eski yevmiye kaydını sil, güncel bilgilerle yeniden yaz
        conn.execute("DELETE FROM yevmiye WHERE kaynak_tablo='personel_avans' AND kaynak_id=?", (avans_id,))
        mdb._yevmiye_ekle(conn, tarih, 'Personel Avans', '195', odeme_sekli,
                          tutar, aciklama or f'{p_ad} avans', otel,
                          kaynak_tablo='personel_avans', kaynak_id=avans_id)
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── API — Personel Güncelle / Sil ────────────────────────────────────────────

@muh.route('/api/muhasebe/personel/guncelle', methods=['POST'])
@admin_required
def api_personel_guncelle():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute("""UPDATE personel SET ad_soyad=?,ise_giris=?,gorev=?,net_maas=?,
                     banka_iban=?,telefon=?,tc_kimlik=? WHERE id=?""",
            (d['ad_soyad'], d.get('ise_giris'), d.get('gorev'),
             float(d.get('net_maas', 0)), d.get('banka_iban', ''),
             d.get('telefon', ''), d.get('tc_kimlik', ''), d['id']))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@muh.route('/api/muhasebe/personel/sil', methods=['POST'])
@admin_required
def api_personel_sil():
    try:
        d = request.get_json()
        conn = mdb.get_conn()
        conn.execute("UPDATE personel SET aktif=0 WHERE id=?", (d['id'],))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
