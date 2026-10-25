import unittest

from divergence import (
    HIDDEN_BEARISH,
    HIDDEN_BULLISH,
    REGULAR_BEARISH,
    REGULAR_BULLISH,
    find_divergences,
    rsi,
)


def dips(length, points, base=50.0):
    """`points` ({index: değer}) noktalarında V şeklinde dipler olan seri."""
    values = [base] * length
    for index, value in points.items():
        for j in range(length):
            values[j] = min(values[j], value + abs(j - index) * 2)
    return values


def peaks(length, points, base=50.0):
    """`points` noktalarında ters V şeklinde tepeler olan seri."""
    values = [base] * length
    for index, value in points.items():
        for j in range(length):
            values[j] = max(values[j], value - abs(j - index) * 2)
    return values


def kinds(divergences):
    return [d.kind for d in divergences]


class RsiTest(unittest.TestCase):
    def test_matches_stockcharts_example(self):
        # StockCharts "RSI" örneği. Kaynak ara değerleri yuvarladığı için tolerans 0.1.
        closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
                  45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
                  46.21, 46.25, 45.71, 46.45, 45.78, 45.35, 44.03, 44.18, 44.22, 44.57,
                  43.42, 42.66, 43.13]
        expected = [70.53, 66.32, 66.55, 69.41, 66.36, 57.97, 62.93, 63.26, 56.06, 62.38,
                    54.71, 50.42, 39.99, 41.46, 41.87, 45.46, 37.30, 33.08, 37.77]
        values = rsi(closes)
        self.assertEqual(values[:14], [None] * 14)
        for actual, want in zip(values[14:], expected):
            self.assertAlmostEqual(actual, want, delta=0.1)

    def test_only_gains_is_100(self):
        self.assertEqual(rsi(list(range(20)))[-1], 100.0)

    def test_short_series_has_no_values(self):
        self.assertEqual(rsi([1, 2, 3], length=14), [None] * 3)


class DivergenceTest(unittest.TestCase):
    length = 60
    flat = [100.0] * 60

    def test_regular_bullish(self):
        lows = list(self.flat)
        lows[15], lows[35] = 95.0, 90.0  # fiyat daha düşük dip
        rsi_values = dips(self.length, {15: 25.0, 35: 30.0})  # RSI daha yüksek dip

        found = find_divergences(self.flat, lows, rsi_values)

        self.assertEqual(kinds(found), [REGULAR_BULLISH])
        div = found[0]
        self.assertEqual((div.prev_index, div.index, div.confirm_index), (15, 35, 40))
        self.assertEqual((div.prev_price, div.price), (95.0, 90.0))
        self.assertEqual((div.prev_rsi, div.rsi), (25.0, 30.0))

    def test_regular_bearish(self):
        highs = list(self.flat)
        highs[15], highs[35] = 105.0, 110.0  # fiyat daha yüksek tepe
        rsi_values = peaks(self.length, {15: 75.0, 35: 70.0})  # RSI daha düşük tepe

        found = find_divergences(highs, self.flat, rsi_values)

        self.assertEqual(kinds(found), [REGULAR_BEARISH])
        self.assertEqual(found[0].confirm_index, 40)

    def test_no_signal_when_price_and_rsi_agree(self):
        lows = list(self.flat)
        lows[15], lows[35] = 95.0, 90.0
        rsi_values = dips(self.length, {15: 30.0, 35: 25.0})

        self.assertEqual(find_divergences(self.flat, lows, rsi_values), [])

    def test_hidden_only_when_enabled(self):
        lows = list(self.flat)
        lows[15], lows[35] = 90.0, 95.0  # fiyat daha yüksek dip
        rsi_values = dips(self.length, {15: 30.0, 35: 25.0})  # RSI daha düşük dip
        highs = list(self.flat)
        highs[15], highs[35] = 110.0, 105.0  # fiyat daha düşük tepe
        rsi_peaks = peaks(self.length, {15: 70.0, 35: 75.0})  # RSI daha yüksek tepe

        self.assertEqual(find_divergences(self.flat, lows, rsi_values), [])
        self.assertEqual(kinds(find_divergences(self.flat, lows, rsi_values, hidden=True)),
                         [HIDDEN_BULLISH])
        self.assertEqual(kinds(find_divergences(highs, self.flat, rsi_peaks, hidden=True)),
                         [HIDDEN_BEARISH])

    def test_pivots_outside_range_are_ignored(self):
        lows = list(self.flat)
        lows[10], lows[50] = 95.0, 90.0
        rsi_values = dips(self.length, {10: 25.0, 50: 30.0})

        self.assertEqual(find_divergences(self.flat, lows, rsi_values, max_range=30), [])
        self.assertEqual(kinds(find_divergences(self.flat, lows, rsi_values, max_range=40)),
                         [REGULAR_BULLISH])

    def test_pivot_needs_right_side_candles(self):
        lows = list(self.flat)
        lows[15], lows[57] = 95.0, 90.0
        rsi_values = dips(self.length, {15: 25.0, 57: 30.0})

        # Son pivotun sağında 5 mum yok, sinyal henüz kesinleşmedi.
        self.assertEqual(find_divergences(self.flat, lows, rsi_values, max_range=60), [])


if __name__ == "__main__":
    unittest.main()
