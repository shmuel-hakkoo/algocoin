
from binance_bulk_downloader.downloader import BinanceBulkDownloader

# Download 1-minute klines for BTCUSDT perpetual futures
# Saved on ~/hakkoo/algocoin/data/futures/um/monthly/klines/BTCUSDT/1m
downloader_1m = BinanceBulkDownloader(
    data_type="klines",
    data_frequency="1m",
    asset="um",
    timeperiod_per_file="monthly",
    symbols=["BTCUSDT"]
)
downloader_1m.run_download()

