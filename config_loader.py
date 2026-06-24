"""
Config yöneticisi — config.json'ı yükler ve uygulama genelinde kullanılabilir kılar.
"""
import json, os
from datetime import date

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def get(path, default=None):
    """Noktalı yol ile değer al: get('otel.ad') → 'Otel Adı'"""
    cfg = load_config()
    keys = path.split('.')
    val = cfg
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return default
    return val if val is not None else default

# ── Lisans kontrolü ────────────────────────────────────────────────────────

def lisans_durumu():
    """
    Döner: 'aktif' | 'demo' | 'demo_bitti' | 'askida'
    """
    cfg = load_config()
    sis = cfg.get('sistem', {})

    if sis.get('askiya_alindi'):
        return 'askida'

    if sis.get('lisans_aktif'):
        return 'aktif'

    # Demo kontrolü
    baslangic_str = sis.get('demo_baslangic', '')
    sure = sis.get('demo_sure_gun', 3)

    if not baslangic_str:
        # İlk kez açılıyor — demo başlat
        cfg['sistem']['demo_baslangic'] = date.today().isoformat()
        save_config(cfg)
        return 'demo'

    baslangic = date.fromisoformat(baslangic_str)
    gecen = (date.today() - baslangic).days

    if gecen >= sure:
        return 'demo_bitti'

    return 'demo'

def demo_kalan_gun():
    cfg = load_config()
    sis = cfg.get('sistem', {})
    baslangic_str = sis.get('demo_baslangic', '')
    sure = sis.get('demo_sure_gun', 3)
    if not baslangic_str:
        return sure
    baslangic = date.fromisoformat(baslangic_str)
    gecen = (date.today() - baslangic).days
    return max(0, sure - gecen)

def demo_oda_limiti():
    """Demo modunda max oda sayısı"""
    return 5

def otel_bilgi():
    cfg = load_config()
    return cfg.get('otel', {})

def tema_mod():
    return get('tema.mod', 'dark')
