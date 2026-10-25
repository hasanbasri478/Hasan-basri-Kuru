"""Binance mumlarında RSI uyumsuzluğu arar ve Telegram'a sinyal gönderir.

Kullanım:
    python bot.py --symbols BTCUSDT ETHUSDT
    python bot.py --symbols BTCUSDT --history   # son mumlardaki uyumsuzlukları listeler
"""

import argparse
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

import requests

from divergence import (
    HIDDEN_BEARISH,
    HIDDEN_BULLISH,
    REGULAR_BEARISH,
    REGULAR_BULLISH,
    find_divergences,
    rsi,
)

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"
# RSI'nin TradingView ile aynı çıkması için yeterli geçmiş.
CANDLE_LIMIT = 500
# Mum kapandıktan sonra Binance'e istek atmadan önce beklenecek süre.
CLOSE_DELAY_SECONDS = 3
REQUEST_TIMEOUT_SECONDS = 10
# Türkiye 2016'dan beri yıl boyu UTC+3 kullanır.
TURKEY_TZ = timezone(timedelta(hours=3))
INTERVAL_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900,
    "30m": 1800, "1h": 3600, "2h": 7200, "4h": 14400,
}
LABELS = {
    REGULAR_BULLISH: ("🟢", "Pozitif uyumsuzluk", "Fiyat daha düşük dip, RSI daha yüksek dip"),
    HIDDEN_BULLISH: ("🟩", "Gizli pozitif uyumsuzluk", "Fiyat daha yüksek dip, RSI daha düşük dip"),
    REGULAR_BEARISH: ("🔴", "Negatif uyumsuzluk", "Fiyat daha yüksek tepe, RSI daha düşük tepe"),
    HIDDEN_BEARISH: ("🟥", "Gizli negatif uyumsuzluk", "Fiyat daha düşük tepe, RSI daha yüksek tepe"),
}

log = logging.getLogger("rsi-divergence")


class Candle(NamedTuple):
    open_time: int
    high: float
    low: float
    close: float


def fetch_closed_candles(session, symbol, interval):
    response = session.get(
        BINANCE_KLINES_URL,
        params={"symbol": symbol, "interval": interval, "limit": CANDLE_LIMIT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    # Listenin son elemanı henüz kapanmamış mumdur.
    return [Candle(int(k[0]), float(k[2]), float(k[3]), float(k[4])) for k in response.json()[:-1]]


def scan(candles, args):
    rsi_values = rsi([c.close for c in candles], args.rsi_length)
    return find_divergences(
        [c.high for c in candles],
        [c.low for c in candles],
        rsi_values,
        left=args.pivot_left,
        right=args.pivot_right,
        min_range=args.min_range,
        max_range=args.max_range,
        hidden=args.hidden,
    )


def format_price(value):
    return f"{value:.10f}".rstrip("0").rstrip(".")


def format_time(open_time_ms):
    return datetime.fromtimestamp(open_time_ms / 1000, TURKEY_TZ).strftime("%d.%m.%Y %H:%M")


def format_message(symbol, interval, div, candles):
    icon, title, detail = LABELS[div.kind]
    return (
        f"{icon} {symbol} {interval} — {title}\n"
        f"{detail}\n"
        f"Fiyat: {format_price(div.prev_price)} → {format_price(div.price)}\n"
        f"RSI: {div.prev_rsi:.2f} → {div.rsi:.2f}\n"
        f"Pivot mumu: {format_time(candles[div.index].open_time)} (TSİ)\n"
        f"Son kapanış: {format_price(candles[-1].close)}"
    )


class Notifier:
    def __init__(self, session, token, chat_id):
        self.session = session
        self.token = token
        self.chat_id = chat_id

    def send(self, text):
        log.info("\n%s", text)
        if not self.token:
            return
        try:
            response = self.session.post(
                TELEGRAM_URL.format(token=self.token),
                data={"chat_id": self.chat_id, "text": text},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            # Hata metni token içeren URL'yi taşıyabilir, onu loga yazma.
            log.warning("Telegram mesajı gönderilemedi (%s)", type(exc).__name__)


def check_symbol(session, notifier, symbol, args, last_seen):
    candles = fetch_closed_candles(session, symbol, args.interval)
    latest = candles[-1].open_time
    # İlk turda eski sinyalleri gönderme. Sonraki turlarda, ağ hatası yüzünden
    # atlanan mumlarda kesinleşen sinyaller de gönderilir.
    since = last_seen.get(symbol, latest)
    for div in scan(candles, args):
        if candles[div.confirm_index].open_time > since:
            notifier.send(format_message(symbol, args.interval, div, candles))
    last_seen[symbol] = latest


def sleep_until_next_close(step):
    time.sleep(step - time.time() % step + CLOSE_DELAY_SECONDS)


def print_history(session, args):
    for symbol in args.symbols:
        candles = fetch_closed_candles(session, symbol, args.interval)
        divergences = scan(candles, args)
        print(f"\n=== {symbol} {args.interval}: son {len(candles)} mumda {len(divergences)} uyumsuzluk ===")
        for div in divergences:
            print(format_message(symbol, args.interval, div, candles) + "\n")


def run(session, args):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and not chat_id:
        raise SystemExit("TELEGRAM_CHAT_ID ayarlı değil.")
    if not token:
        log.warning("TELEGRAM_BOT_TOKEN ayarlı değil. Sinyaller sadece konsola yazılacak.")

    notifier = Notifier(session, token, chat_id)
    notifier.send(f"RSI uyumsuzluk botu başladı: {', '.join(args.symbols)} ({args.interval})")
    step = INTERVAL_SECONDS[args.interval]
    last_seen = {}
    while True:
        for symbol in args.symbols:
            try:
                check_symbol(session, notifier, symbol, args, last_seen)
            except (requests.RequestException, ValueError, IndexError) as exc:
                log.warning("%s kontrol edilemedi: %s", symbol, exc)
        sleep_until_next_close(step)


def parse_args():
    parser = argparse.ArgumentParser(description="Binance RSI uyumsuzluk sinyal botu")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT"], type=str.upper,
                        help="Binance spot sembolleri (varsayılan: BTCUSDT)")
    parser.add_argument("--interval", default="5m", choices=INTERVAL_SECONDS,
                        help="Mum periyodu (varsayılan: 5m)")
    parser.add_argument("--rsi-length", type=int, default=14)
    parser.add_argument("--pivot-left", type=int, default=5, help="Pivotun solundaki mum sayısı")
    parser.add_argument("--pivot-right", type=int, default=5,
                        help="Pivotun sağındaki mum sayısı. Sinyal pivottan bu kadar mum sonra gelir.")
    parser.add_argument("--min-range", type=int, default=5, help="İki pivot arası en az mum")
    parser.add_argument("--max-range", type=int, default=60, help="İki pivot arası en çok mum")
    parser.add_argument("--hidden", action="store_true", help="Gizli uyumsuzlukları da gönder")
    parser.add_argument("--history", action="store_true",
                        help="Son mumlardaki uyumsuzlukları listele ve çık (Telegram'a göndermez)")
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    with requests.Session() as session:
        if args.history:
            print_history(session, args)
        else:
            run(session, args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
