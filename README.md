# 🏨 Otel Yönetim Sistemi — Template

Tek otel için web tabanlı otel yönetim sistemi.  
Rezervasyon, muhasebe, housekeeping, Telegram entegrasyonu ve daha fazlası.

---

## 🚀 Yeni Otel Kurulumu (Adım Adım)

### 1. Repoyu Fork Et
GitHub'da bu repoyu fork et → yeni otel adıyla rename et  
Örn: `park-otel-yonetim`

### 2. Render'da Yeni Servis Oluştur
- [render.com](https://render.com) → New → Web Service
- GitHub reposunu bağla
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Plan:** Starter (veya üzeri)
- **Disk ekle:** 1 GB persistent disk → mount path: `/opt/render/project/src`

### 3. Environment Variables Ekle
Render → Environment bölümüne şunları ekle:

| Key | Açıklama |
|-----|----------|
| `SUPERADMIN_KEY` | Süper admin paneli için gizli anahtar (sen belirle) |
| `GMAIL_USER` | Yedek mail gönderecek Gmail adresi |
| `GMAIL_APP_PASSWORD` | Gmail uygulama şifresi |
| `TELEGRAM_TOKEN` | Telegram bot token (kurulum sihirbazında da girilebilir) |
| `TELEGRAM_CHAT_ID` | Telegram grup chat ID (kurulum sihirbazında da girilebilir) |

### 4. Deploy Et
Render otomatik deploy eder.  
İlk açılışta **Kurulum Sihirbazı** karşılar → tüm bilgileri gir → Kur.

### 5. Süper Admin Paneli
`https://siteadresi.onrender.com/sadmin`  
Admin anahtarı: `SUPERADMIN_KEY` değeri

---

## 📋 Özellikler

- ✅ Rezervasyon yönetimi (föy, check-in/out)
- ✅ Muhasebe (yevmiye, kasa/banka, mizan)
- ✅ Acente muhasebesi (Booking, Expedia vb.)
- ✅ Housekeeping listesi + Telegram bildirimleri
- ✅ Günlük liste (giriş/çıkış/kahvaltı)
- ✅ Personel & avans takibi
- ✅ Stok ve demirbaş
- ✅ Gece otomatik Excel yedeği (e-posta)
- ✅ Karanlık / Açık tema
- ✅ Demo modu (3 gün, 5 oda limiti)
- ✅ Lisans / Askıya alma sistemi

---

## 👥 Kullanıcı Rolleri

| Rol | Erişim |
|-----|--------|
| `admin` | Her şey — tam yetki |
| `partner` | Rezervasyon + Muhasebe |
| `resepsiyon` | Yalnızca rezervasyon ve operasyon |

---

## 💬 Telegram HK Komutları

Housekeeping grubundan oda durumunu güncellemek için:

| Komut | Anlamı |
|-------|--------|
| `18T` | Oda 18 → Temiz |
| `18B` | Oda 18 → Temizleniyor |
| `18G` | Oda 18 → Geri al (Bekliyor) |

Büyük/küçük harf fark etmez: `18t`, `18T`, `18b` hepsi çalışır.

---

## 🔧 Lokal Geliştirme

```bash
pip install -r requirements.txt
python app.py
```

Tarayıcıda: `http://localhost:5000`

---

## 📞 Destek

Sistem yöneticinizle iletişime geçin.
