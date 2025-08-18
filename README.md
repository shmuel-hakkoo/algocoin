# Algocoin


## Dependencies


* [nautilus](https://github.com/nautechsystems/nautilus_trader)
* [uv](https://docs.astral.sh/uv/)


## Setup

### Prerequisites
Install UV before starting: https://docs.astral.sh/uv/#installation

add to your .zshrc or .bashrc
```
export PATH="/home/henry/.venv/bin:$PATH"
```

### Makefile Commands

- `make activate` - Activate the virtual environment (if you choosed the home dir)
- `make install-nautilus` - Install nautilus_trader package


## Market Data


* [binance-historical](https://github.com/binance/binance-public-data?tab=readme-ov-file)


### Daily

* [BTCUSD_PERP](https://data.binance.vision/?prefix=data/futures/cm/daily/trades/BTCUSD_PERP/)


### Montly

* [BTCUSD_PERP](https://data.binance.vision/?prefix=data/futures/cm/monthly/trades/BTCUSD_PERP/)
