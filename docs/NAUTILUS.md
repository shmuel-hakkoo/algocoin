





- `Bar`: OHLCV (Open, High, Low, Close, Volume) bar/candle, aggregated using a specified *aggregation method*.
- `CryptoPerpetual`: Represents a crypto perpetual futures contract instrument (a.k.a. perpetual swap).

## Binance Klines Data Format

The downloaded Binance klines (candlestick) data contains 12 columns per row:

| Index | Field | Description | Example |
|-------|-------|-------------|---------|
| 0 | Open time | Kline open time (Unix timestamp in milliseconds) | 1585699200000 |
| 1 | Open | Opening price | 6407.10 |
| 2 | High | Highest price during the kline | 6422.82 |
| 3 | Low | Lowest price during the kline | 6407.10 |
| 4 | Close | Closing price | 6417.24 |
| 5 | Volume | Total volume traded | 427.762 |
| 6 | Close time | Kline close time (Unix timestamp in milliseconds) | 1585699259999 |
| 7 | Quote asset volume | Total traded value (volume * price) | 2744209.05214 |
| 8 | Number of trades | Number of individual trades | 1082 |
| 9 | Taker buy base asset volume | Volume of trades initiated by buyers | 249.357 |
| 10 | Taker buy quote asset volume | Value of trades initiated by buyers | 1599628.66410 |
| 11 | Ignore | Reserved field (always 0) | 0 |

### Example Data
```
1585699200000,6407.10,6422.82,6407.10,6417.24,427.762,1585699259999,2744209.05214,1082,249.357,1599628.66410,0
1585699260000,6417.23,6418.28,6410.24,6415.50,115.233,1585699319999,739144.57435,375,58.623,376060.00033,0
```

Each row represents one minute of BTCUSDT perpetual futures data, with precise OHLCV information and additional trading metrics.

### Working with Unix Timestamps

The timestamps in columns 0 and 6 are Unix timestamps in milliseconds. To convert them:

**Python:**
```python
import datetime

# Convert milliseconds to seconds and create datetime object
timestamp_ms = 1585699200000
timestamp_s = timestamp_ms / 1000
dt = datetime.datetime.fromtimestamp(timestamp_s, tz=datetime.timezone.utc)
print(dt)  # 2020-04-01 00:00:00+00:00

# Or using pandas
import pandas as pd
df['datetime'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
```

The example timestamp `1585699200000` corresponds to April 1, 2020, 00:00:00 UTC.
