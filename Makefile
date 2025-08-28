.PHONY: activate test


test:
	@echo "Running tests..."
	@zsh -c "source ~/.venv/bin/activate && python -m unittest discover test"

# Install UV before [https://docs.astral.sh/uv/#installation]

activate:
	@zsh -c "source ~/.venv/bin/activate && exec zsh"

install-nautilus:
	uv pip install -U nautilus_trader --index-url=https://packages.nautechsystems.io/simple


jupyter:
	docker run -p 8888:8888 ghcr.io/nautechsystems/jupyterlab:nightly


binance-data-deps:
	uv pip install -r data/binance/python/requirements.txt


bt-ema:
	python refs/backtest/crypto_ema_cross_ethusdt_trade_ticks.py


# daily data for 2025, months 02 to 07 with checksum
data-btc:
	python ./data/binance/python/download-kline.py -t spot -s BTCUSDT -i 1d -y 2025 -m 02 03 04 05 06 07 -c 1


watch:
	echo src/load.py | entr -r python src/load.py


start:
	streamlit run app.py


# ClickHouse CSV Migration Commands

# Create database schema only
create-schema:
	python bin/upload_csv.py --data-dir data/futures/um/monthly/klines/BTCUSDT/1m --create-schema --pattern "*.csv"

# Upload single month (dry run)
upload-csv-dry:
	python bin/upload_csv.py --data-dir data/futures/um/monthly/klines/BTCUSDT/1m --dry-run --pattern "BTCUSDT-1m-2020-04.csv"

# Upload single month (actual upload)
upload-csv-month:
	python bin/upload_csv.py --data-dir data/futures/um/monthly/klines/BTCUSDT/1m --pattern "BTCUSDT-1m-2020-04.csv" --batch-size 10000

# Upload all BTCUSDT 1m data (WARNING: Large operation)
upload-csv-all:
	python bin/upload_csv.py --data-dir data/futures/um/monthly/klines/BTCUSDT/1m --batch-size 10000

# Upload all data with schema creation
upload-csv-full:
	python bin/upload_csv.py --data-dir data/futures/um/monthly/klines/BTCUSDT/1m --create-schema --batch-size 10000
