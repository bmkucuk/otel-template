# Otel Leo & Cunda Villa — Web Yönetim (SQLite Sürümü)

## Yerel Çalıştırma (Windows)

```
CALISTIR.bat  ←  çift tıkla, tarayıcı otomatik açılır
```
Sonra: **http://localhost:5000**

---

## Railway'e Deploy (Ücretsiz — İnternetten Erişim)

### Adım 1 — GitHub'a yükle

```bash
# Bu klasörde terminal aç
git init
git add .
git commit -m "ilk commit"

# GitHub'da yeni repo oluştur (github.com/new)
# Repo adı: otel-yonetim  (private yapabilirsin)

git remote add origin https://github.com/SENIN_KULLANICI_ADIN/otel-yonetim.git
git push -u origin main
```

### Adım 2 — Railway hesabı aç

1. **https://railway.app** → "Start a New Project"
2. "Deploy from GitHub repo" seç
3. `otel-yonetim` reposunu seç → Deploy

### Adım 3 — Kalıcı Disk Ekle (ÖNEMLİ)

Railway'de SQLite veritabanının silinmemesi için:

1. Proje sayfasında servisine tıkla
2. **"Volumes"** sekmesi → **"Add Volume"**
3. Mount Path: `/data`
4. Size: 1 GB (ücretsiz)

### Adım 4 — Environment Variable Ekle

1. **"Variables"** sekmesi → **"Add Variable"**
2. `SECRET_KEY` = `otel2026gizliAnahtar123` (istediğin bir şey)

### Adım 5 — Domain Al

1. **"Settings"** sekmesi → **"Generate Domain"**
2. Örnek: `otel-yonetim.up.railway.app`
3. Bu adresi herkes her yerden açabilir

### Adım 6 — Excel Verisini Aktar

1. Uygulamayı aç → sol altta **"📥 Excel Aktar"**
2. `Otel_Oda_Durumu_VS_2_0.xlsx` dosyasını yükle
3. **"Aktarımı Başlat"** → Bitti!

---

## Güncelleme (Veri Değişince)

```bash
git add .
git commit -m "güncelleme"
git push
```
Railway otomatik yeniden deploy eder (~1 dk).

---

## Ücretsiz Plan Limitleri

| Platform | Limit | Yeterli mi? |
|---|---|---|
| Railway | $5/ay kredi (yaklaşık 500 saat) | ✅ Küçük otel için yeterli |
| Render | Sınırsız ama 15 dk uyku | ⚠️ Uyanma gecikmesi var |

> Railway ücretsiz tier: kredi kartı girmeden $5 kredi veriyor.
> 1 worker + SQLite ile aylık ~$0.50-1.00 harcıyor. Yani aylarca ücretsiz.

---

## Dosya Yapısı

```
otelweb2/
├── app.py          ← Flask sunucu
├── database.py     ← SQLite CRUD işlemleri
├── requirements.txt
├── Procfile        ← Railway/Render için başlatma komutu
├── railway.json    ← Railway config
├── CALISTIR.bat    ← Windows başlatıcı
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── rezervasyonlar.html
    ├── oda_durumu.html
    ├── cari.html
    ├── adisyon.html
    └── import.html   ← Excel yükleme sayfası
```
