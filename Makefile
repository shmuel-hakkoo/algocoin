.PHONY: activate


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
