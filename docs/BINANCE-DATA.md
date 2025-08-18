## Binance Market Data


* [binance-historical](https://github.com/binance/binance-public-data?tab=readme-ov-file)


# 1. **Trades Data**

* **Source:** `/api/v3/historicalTrades` (Spot), `/fapi/v1/trades` (Futures).
* **Granularity:** **Raw tick-by-tick trades** – every executed transaction on the order book.
* **Fields:** `tradeId`, `price`, `qty`, `quoteQty`, `time`, `isBuyerMaker`, `isBestMatch`.
* **Characteristics:**

  * Each line = one trade event.
  * No aggregation: maximum detail.

✅ **Advantages:**

* Best for high-frequency trading (HFT) and microstructure research.
* You can reconstruct **order flow** and compute custom indicators (e.g., VWAP, delta, aggressor activity).
* Useful for **backtesting scalping strategies** or order-book imbalance models.

❌ **Disadvantages:**

* **Huge data size** → storage and memory heavy.
* Harder to process in real time without specialized infra (Kafka, ClickHouse, etc.).
* Noise — small trades can drown signal if you don’t filter.

---

# 2. **AggTrades (Aggregated Trades)**

* **Source:** `/api/v3/aggTrades` (Spot), `/fapi/v1/aggTrades` (Futures).
* **Granularity:** Binance groups trades that happen **at the same price, same time window, and aggressor side** into one "aggregate trade".
* **Fields:** `aggTradeId`, `price`, `quantity`, `firstTradeId`, `lastTradeId`, `timestamp`, `isBuyerMaker`.
* **Characteristics:**

  * Similar to `trade`, but **compressed** (bundles consecutive trades).
  * Smaller files than raw trades.

✅ **Advantages:**

* Much lighter than raw trades while still capturing **tick-level movement**.
* Preserves most **order flow features**.
* Easier to backtest intraday strategies without huge infra.

❌ **Disadvantages:**

* Loses exact tick-by-tick detail (you can’t replay *every single trade*).
* Still too granular for higher-timeframe strategies — you might just use klines instead.

---

# 3. **Klines (Candlesticks)**

* **Source:** `/api/v3/klines` (Spot), `/fapi/v1/klines` (Futures).
* **Granularity:** **OHLCV data** aggregated into a fixed interval (1s → 1mo).
* **Fields:** `openTime`, `open`, `high`, `low`, `close`, `volume`, `quoteVolume`, `numberOfTrades`, taker-buy volumes.
* **Characteristics:**

  * The most compressed view: a candle per interval.
  * Common in **TA (technical analysis)** and retail trading.

✅ **Advantages:**

* Very lightweight, fast to process.
* Perfect for **trend-following, swing trading, or ML models** that don’t need tick data.
* Can add volume and order-flow features via taker-buy columns.

❌ **Disadvantages:**

* Loses **intra-candle detail** (you don’t know order of trades inside the bar).
* Useless for HFT — too aggregated.
* Candlestick patterns can be misleading without tick context.

---

# 🔑 Summary Table

| Dataset       | Granularity                            | Best For                                           | Pros                                       | Cons                                |
| ------------- | -------------------------------------- | -------------------------------------------------- | ------------------------------------------ | ----------------------------------- |
| **Trades**    | Every executed trade (tick)            | HFT, microstructure analysis, VWAP, flow imbalance | Max detail, custom indicators possible     | Heavy data, storage/infra intensive |
| **AggTrades** | Bundled trades at same price/time/side | Intraday strategies, mid-frequency algos           | Lighter than trades, keeps order flow feel | Loses per-trade detail              |
| **Klines**    | OHLCV per interval                     | Swing/trend following, ML models                   | Very lightweight, easy to use              | No intra-candle detail, lagging     |

---

👉 For algo trading:

* **HFT / market making** → use **Trades** or **AggTrades**.
* **Intraday momentum / scalping** → **AggTrades** balances speed & size.
* **Swing / trend following / ML models** → **Klines** are enough.

---

### Daily

* [BTCUSD_PERP](https://data.binance.vision/?prefix=data/futures/cm/daily/trades/BTCUSD_PERP/)


### Montly

* [BTCUSD_PERP](https://data.binance.vision/?prefix=data/futures/cm/monthly/trades/BTCUSD_PERP/)



---

# Binance Public Data Downloader – Quick Guide

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) Set default storage directory
export STORE_DIRECTORY=<your path>
```

---

### 2. Download Data

```bash
# ----------- KLINES (candlestick OHLCV) -----------
# Download all symbols, spot by default
python3 download-kline.py -t <spot|um|cm>

# Example: ETH, BTC, BNB weekly spot klines for Feb & Dec 2020 with checksum
python3 download-kline.py -t spot -s ETHUSDT BTCUSDT BNBBUSD -i 1w -y 2020 -m 02 12 -c 1

# Example: All USD-M 1m klines between Jan–Feb 2021 (skip monthly files)
python3 download-kline.py -t um -i 1m -skip-monthly 1 -startDate 2021-01-01 -endDate 2021-02-02


# ----------- TRADES (raw trade data) -----------
# Download all trades
python3 download-trade.py -t <spot|um|cm>

# Example: ETH, BTC, BNB spot trades for Feb & Dec 2020 with checksum
python3 download-trade.py -t spot -s ETHUSDT BTCUSDT BNBBUSD -y 2020 -m 02 12 -c 1

# Example: All USD-M trades between Jan–Feb 2021
python3 download-trade.py -t um -skip-monthly 1 -startDate 2021-01-01 -endDate 2021-02-02


# ----------- AGGTRADES (aggregated trades) -----------
# Download aggregated trades
python3 download-aggTrade.py -t <spot|um|cm>

# Example: ETH, BTC, BNB spot aggTrades for Feb & Dec 2020 with checksum
python3 download-aggTrade.py -t spot -s ETHUSDT BTCUSDT BNBBUSD -y 2020 -m 02 12 -c 1

# Example: All USD-M aggTrades between Jan–Feb 2021
python3 download-aggTrade.py -t um -skip-monthly 1 -startDate 2021-01-01 -endDate 2021-02-02


# ----------- FUTURES-ONLY DATA (index/mark/premium price klines) -----------
# Index Price
python3 download-futures-indexPriceKlines.py -t <um|cm>
# Example: BTCUSDT index price (USD-M)
python3 download-futures-indexPriceKlines.py -t um -s BTCUSDT

# Mark Price
python3 download-futures-markPriceKlines.py -t <um|cm>
# Example: ETH, BTC, BNB markPrice weekly klines (USD-M) in Feb & Dec 2020 with checksum
python3 download-futures-markPriceKlines.py -t um -s ETHUSDT BTCUSDT BNBUSDT -i 1w -y 2020 -m 02 12 -c 1

# Premium Index Price
python3 download-futures-premiumPriceKlines.py -t <um|cm>
# Example: All COIN-M premiumPrice 1m klines between Jan–Feb 2021
python3 download-futures-premiumPriceKlines.py -t cm -i 1m -skip-monthly 1 -startDate 2021-01-01 -endDate 2021-02-02
```

---

👉 All scripts support the same arguments:

* `-t` (**mandatory**): `spot`, `um` (USD-M Futures), `cm` (COIN-M Futures)
* `-s` symbols, `-i` intervals, `-y` years, `-m` months, `-d` dates
* `-startDate`, `-endDate` (YYYY-MM-DD)
* `-skip-monthly 1` / `-skip-daily 1`
* `-folder <dir>` for storage, `-c 1` for checksum

---

