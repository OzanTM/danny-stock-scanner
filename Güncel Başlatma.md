# RCYC Bullish Bearish Tarayici - Baslatma Rehberi

---

## ✅ Başlatmadan Önce Kontrol Listesi

Her oturumda app.py'yi çalıştırmadan önce şunları kontrol et:

| # | Kontrol | Nasıl Anlarsın? |
|---|---------|-----------------|
| 1 | **İnternet bağlantısı var mı?** | Tarayıcıda [finance.yahoo.com](https://finance.yahoo.com) açılıyor mu? |
| 2 | **Terminal doğru klasörde mi?** | `pwd` yaz → `/Users/Ozan/Desktop/Projeler/Danny` görünmeli |
| 3 | **venv aktif mi?** | Terminal satırı `(venv)` ile başlamalı |
| 4 | **Başka bir server çalışıyor mu?** | Port 5000 meşgulse hata alırsın |

---

## Gereksinimler

- Python 3.10 veya uzeri
- Internet baglantisi (Yahoo Finance verisi icin)

---

## İlk Kurulum (Tek Seferlik)

```bash
cd /Users/Ozan/Desktop/Projeler/Danny

# Sanal ortam olustur
python3 -m venv venv

# Sanal ortami aktif et
source venv/bin/activate

# Bagimliliklari yukle
pip install -r requirements.txt
```

---

## Uygulamayi Baslatma

```bash
cd /Users/Ozan/Desktop/Projeler/Danny
source venv/bin/activate
python app.py
```

Çıktı şöyle görünecek:

```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

Tarayıcıda aç: **http://127.0.0.1:5000**

---

## Kullanim

1. **Taramayi Baslat** butonuna tikla
2. Tarama arka planda calisir (yaklasik 2-5 dakika)
3. Sayfa otomatik guncellenir
4. Filtreleme, siralama ve CSV export ozellikleri kullanilabilir

---

## Sayfa Adresleri

| Sayfa | Adres |
|-------|-------|
| Ana Sayfa | http://127.0.0.1:5000 |
| Ozet | http://127.0.0.1:5000/summary |
| Sinyal Paneli | http://127.0.0.1:5000/signals |
| Sinyal Rehberi | http://127.0.0.1:5000/signals-guide |

---

## Testleri Calistirma

```bash
cd /Users/Ozan/Desktop/Projeler/Danny
source venv/bin/activate
python -m pytest tests/ -v
```

---

## Durdurma

Terminalde `Ctrl + C` ile durdurulur.

---

## 🔧 Sorun Giderme

### "ModuleNotFoundError" hatası:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Port 5000 kullanımda:
```bash
FLASK_PORT=5001 python app.py
```

### 🔴 Yahoo Finance'e bağlanılamıyor (DNS hatası):

Terminalde şu hatalar çıkıyorsa:
```
DNSError: Could not resolve host: query1.finance.yahoo.com
ConnectionError: Failed to connect to query2.finance.yahoo.com
```

**Adım adım çözüm:**

1. **Tarayıcıda kontrol et:** https://finance.yahoo.com açılıyor mu?

2. **DNS cache temizle** (Terminal'de):
   ```bash
   sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
   ```

3. **VPN varsa:** Kapat veya farklı sunucu dene

4. **Birkaç dakika bekle** ve tekrar dene — Yahoo Finance geçici kısıtlama uygulayabiliyor

5. **Server'ı yeniden başlat:**
   ```bash
   # Ctrl+C ile durdur, sonra:
   python app.py
   ```

### 🟡 Tarama Sonuçları Eksik veya Yanlış Geliyorsa:

**Olası sebepler:**
- Yahoo Finance aynı anda çok fazla istek aldığında bazı hisseleri blokluyor
- İnternet bağlantısı tarama sırasında geçici olarak kesildi
- Tarama tamamlanmadan sayfayı kapattın

**Çözüm:**
1. 2-3 dakika bekle
2. Tekrar **Tarama Başlat**'a tıkla
3. Terminal'de hata mesajı yoksa tarama tamamlanmıştır

### 🟠 "Geçici ağ/sunucu sorunu" mesajı:

Bu mesaj tarayıcıda çıkıyorsa, server ile bağlantı kesilmiş demektir.

1. Terminal'de server hâlâ çalışıyor mu kontrol et
2. `python app.py` ile yeniden başlat
3. Sayfayı yenile (F5)

### 🔵 "unable to open database file" hatası:

Terminalde bu hata görünüyorsa `data/` klasörü oluşturulmamış olabilir:
```bash
mkdir -p /Users/Ozan/Desktop/Projeler/Danny/data
```
Sonra server'ı yeniden başlat.
