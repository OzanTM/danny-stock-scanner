# RCYC Bullish/Bearish Tarayıcı

Flask tabanlı hisse tarayıcı. `all_tickers.txt` içindeki semboller için Yahoo Finance verisini çekip KDJ (`J` değeri 50 kesişimi) sinyali üretir.

## Mimari

- `app.py`: Web katmanı (route + session + CSV)
- `scanner/config.py`: Konfigürasyon
- `scanner/repository.py`: Ticker dosyası erişimi
- `scanner/market_data.py`: Yahoo veri istemcisi
- `scanner/indicators.py`: KDJ/RMA hesapları
- `scanner/service.py`: Tarama ve filtreleme iş akışı
- `templates/index.html`: UI
- `static/styles.css`: Stil

## Kurulum

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Çalıştırma

```bash
export FLASK_SECRET_KEY='strong-random-secret'
python app.py
```

Uygulama varsayılan olarak `http://127.0.0.1:5000` üzerinde açılır.

## Sinyal Mantığı

- `KDJ length`: 9
- `signal`: 3
- `J = 3*pK - 2*pD`
- Bullish: `J` son barda `50` seviyesini aşağıdan yukarı keser
- Bearish: `J` son barda `50` seviyesini yukarıdan aşağı keser

Tabloda `Sinyal (Bugün)` gerçekten son barı, `1/2/3/4 Önceki Gün` sütunları da doğru geriye dönük sıralamayı gösterir.
