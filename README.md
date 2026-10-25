# RSI Uyumsuzluk Sinyal Botu

Bot, Binance'teki kripto paraların 5 dakikalık mumlarında RSI uyumsuzluğu
(divergence) arar. Uyumsuzluk bulunca Telegram'a mesaj gönderir.

```
🟢 BTCUSDT 5m — Pozitif uyumsuzluk
Fiyat daha düşük dip, RSI daha yüksek dip
Fiyat: 67210.5 → 66980.1
RSI: 27.84 → 33.10
Pivot mumu: 25.10.2026 14:35 (TSİ)
Son kapanış: 67102.3
```

## Hangi sinyaller gelir?

| Sinyal | Fiyat | RSI | Varsayılan |
|---|---|---|---|
| 🟢 Pozitif uyumsuzluk | Daha düşük dip | Daha yüksek dip | Açık |
| 🔴 Negatif uyumsuzluk | Daha yüksek tepe | Daha düşük tepe | Açık |
| 🟩 Gizli pozitif uyumsuzluk | Daha yüksek dip | Daha düşük dip | `--hidden` ile |
| 🟥 Gizli negatif uyumsuzluk | Daha düşük tepe | Daha yüksek tepe | `--hidden` ile |

Mantık, TradingView'daki yerleşik **"RSI Divergence Indicator"** ile aynıdır:
RSI 14, pivot sol/sağ 5 mum, iki pivot arası 5–60 mum. Bu yüzden sinyalleri
TradingView grafiğinde kontrol edebilirsiniz.

**Önemli:** Bir dip veya tepe, sağında 5 mum kapanınca kesinleşir. Bu yüzden
5 dakikalık grafikte sinyal, pivot mumundan yaklaşık 25 dakika sonra gelir.
Daha hızlı sinyal için `--pivot-right 2` kullanın. Bu ayarda yanlış sinyal
sayısı artar.

## Kurulum

Python 3.8 veya daha yeni bir sürüm gerekir.

```bash
pip install -r requirements.txt
```

## Telegram ayarı

1. Telegram'da **@BotFather** ile konuşun, `/newbot` yazın ve bir bot yapın.
   BotFather size bir **token** verir.
2. Yeni botunuza bir mesaj gönderin (örneğin `/start`).
3. Tarayıcıda `https://api.telegram.org/bot<TOKEN>/getUpdates` adresini açın.
   `"chat":{"id": ...}` içindeki sayı sizin **chat id** değerinizdir.
4. Bu iki değeri ortam değişkeni olarak ayarlayın:

   Linux / macOS:
   ```bash
   export TELEGRAM_BOT_TOKEN="123456:ABC..."
   export TELEGRAM_CHAT_ID="123456789"
   ```

   Windows (PowerShell):
   ```powershell
   $env:TELEGRAM_BOT_TOKEN="123456:ABC..."
   $env:TELEGRAM_CHAT_ID="123456789"
   ```

Telegram ayarı yoksa bot sinyalleri sadece konsola yazar.

## Çalıştırma

```bash
python bot.py --symbols BTCUSDT ETHUSDT SOLUSDT
```

Bot her mum kapanışından 3 saniye sonra bütün sembolleri kontrol eder.
Başlarken Telegram'a "bot başladı" mesajı gönderir. Bu mesaj gelirse Telegram
ayarınız doğrudur. Durdurmak için `Ctrl+C` tuşlarına basın.

Son mumlardaki uyumsuzlukları görmek için (son ~500 mum, 5m'de yaklaşık 41 saat):

```bash
python bot.py --symbols BTCUSDT --history
```

Bu komut Telegram'a mesaj göndermez. Sonuçları TradingView ile karşılaştırmak
için kullanın.

## Parametreler

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `--symbols` | `BTCUSDT` | Binance spot sembolleri |
| `--interval` | `5m` | Mum periyodu: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h |
| `--rsi-length` | `14` | RSI periyodu |
| `--pivot-left` | `5` | Pivotun solundaki mum sayısı |
| `--pivot-right` | `5` | Pivotun sağındaki mum sayısı. Sinyal pivottan bu kadar mum sonra gelir. |
| `--min-range` | `5` | İki pivot arası en az mum |
| `--max-range` | `60` | İki pivot arası en çok mum |
| `--hidden` | kapalı | Gizli uyumsuzlukları da gönderir |
| `--history` | kapalı | Son mumlardaki uyumsuzlukları listeler ve çıkar |

## Notlar

- Bot sadece çalıştığı sürece sinyal gönderir. Bilgisayar kapanırsa sinyal
  gelmez. 7/24 sinyal için botu bir VPS'te çalıştırın.
- Bot spot fiyatlarını kullanır. Vadeli (futures) fiyatları biraz farklı olabilir.
- Binance bazı ülkelerden (örneğin ABD) gelen istekleri engeller.
- Ağ hatası olursa bot bir sonraki turda tekrar dener. O arada kesinleşen
  sinyalleri de gönderir.
- Bu bot yatırım tavsiyesi değildir.

## Test

```bash
python -m unittest -v
```
