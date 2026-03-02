# RCYC Bullish Bearish Tarayici - Baslatma Rehberi

## Gereksinimler

- Python 3.10 veya uzeri
- Internet baglantisi (Yahoo Finance verisi icin)

## Ilk Kurulum (Tek Seferlik)

```bash
cd /Users/Ozan/Desktop/Projeler/Danny

# Sanal ortam olustur
python3 -m venv venv

# Sanal ortami aktif et
source venv/bin/activate

# Bagimliliklari yukle
pip install -r requirements.txt
```

## Uygulamayi Baslatma

```bash
cd /Users/Ozan/Desktop/Projeler/Danny
source venv/bin/activate
python app.py
```

Cikti su sekilde gorunecek:

```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

Tarayicida ac: **http://127.0.0.1:5000**

## Kullanim

1. **Taramayi Baslat** butonuna tikla
2. Tarama arka planda calisir (yaklasik 1-3 dakika)
3. Sayfa otomatik guncellenir
4. Filtreleme, siralama ve CSV export ozellikleri kullanilabilir

## Sayfa Adresleri

| Sayfa | Adres |
|-------|-------|
| Ana Sayfa | http://127.0.0.1:5000 |
| Ozet | http://127.0.0.1:5000/summary |
| Sinyal Paneli | http://127.0.0.1:5000/signals |
| Sinyal Rehberi | http://127.0.0.1:5000/signals-guide |

## Testleri Calistirma

```bash
cd /Users/Ozan/Desktop/Projeler/Danny
source venv/bin/activate
python -m pytest tests/ -v
```

## Durdurma

Terminalde `Ctrl + C` ile durdurulur.

## Sorun Giderme

**"ModuleNotFoundError" hatasi:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Port 5000 kullanimda:**
```bash
FLASK_PORT=5001 python app.py
```

**Yahoo Finance'e baglanilamiyor:**
Internet baglantisini ve DNS ayarlarini kontrol et.
