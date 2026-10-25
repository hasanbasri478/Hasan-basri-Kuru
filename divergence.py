"""RSI ve RSI uyumsuzluğu hesapları. Ağ veya dosya işlemi içermez.

Mantık TradingView'daki yerleşik "RSI Divergence Indicator" ile aynıdır:
pivotlar RSI üzerinde bulunur, fiyat o pivot mumlarının dip/tepe değeriyle
karşılaştırılır ve her pivot bir önceki aynı tür pivotla kıyaslanır.
"""

from dataclasses import dataclass

REGULAR_BULLISH = "regular_bullish"
HIDDEN_BULLISH = "hidden_bullish"
REGULAR_BEARISH = "regular_bearish"
HIDDEN_BEARISH = "hidden_bearish"


@dataclass(frozen=True)
class Divergence:
    kind: str
    prev_index: int
    index: int
    # Pivotun kesinleştiği mum: sağında `right` mum kapanınca pivot belli olur.
    confirm_index: int
    prev_price: float
    price: float
    prev_rsi: float
    rsi: float


def rsi(closes, length=14):
    """Wilder RSI (TradingView ta.rsi ile aynı). İlk `length` değer None olur."""
    values = [None] * len(closes)
    if len(closes) <= length:
        return values

    gain = loss = 0.0
    for i in range(1, length + 1):
        change = closes[i] - closes[i - 1]
        gain += max(change, 0.0)
        loss += max(-change, 0.0)
    avg_gain = gain / length
    avg_loss = loss / length
    values[length] = _rsi_value(avg_gain, avg_loss)

    for i in range(length + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (length - 1) + max(change, 0.0)) / length
        avg_loss = (avg_loss * (length - 1) + max(-change, 0.0)) / length
        values[i] = _rsi_value(avg_gain, avg_loss)
    return values


def _rsi_value(avg_gain, avg_loss):
    if avg_loss == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def _is_pivot(values, i, left, right, low):
    center = values[i]
    before = values[i - left:i]
    after = values[i + 1:i + right + 1]
    if center is None or None in before:
        return False
    if low:
        return all(center < v for v in before) and all(center <= v for v in after)
    return all(center > v for v in before) and all(center >= v for v in after)


def find_divergences(highs, lows, rsi_values, left=5, right=5,
                     min_range=5, max_range=60, hidden=False):
    """Seride kesinleşmiş tüm uyumsuzlukları eskiden yeniye döndürür."""
    found = []
    prev_low = prev_high = None

    for i in range(left, len(rsi_values) - right):
        if _is_pivot(rsi_values, i, left, right, low=True):
            p = prev_low
            if p is not None and min_range <= i - p <= max_range:
                kind = None
                if lows[i] < lows[p] and rsi_values[i] > rsi_values[p]:
                    kind = REGULAR_BULLISH
                elif hidden and lows[i] > lows[p] and rsi_values[i] < rsi_values[p]:
                    kind = HIDDEN_BULLISH
                if kind:
                    found.append(Divergence(kind, p, i, i + right, lows[p], lows[i],
                                            rsi_values[p], rsi_values[i]))
            prev_low = i

        if _is_pivot(rsi_values, i, left, right, low=False):
            p = prev_high
            if p is not None and min_range <= i - p <= max_range:
                kind = None
                if highs[i] > highs[p] and rsi_values[i] < rsi_values[p]:
                    kind = REGULAR_BEARISH
                elif hidden and highs[i] < highs[p] and rsi_values[i] > rsi_values[p]:
                    kind = HIDDEN_BEARISH
                if kind:
                    found.append(Divergence(kind, p, i, i + right, highs[p], highs[i],
                                            rsi_values[p], rsi_values[i]))
            prev_high = i

    return found
