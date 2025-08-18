import os
import shutil
from decimal import Decimal
from pathlib import Path

import pandas as pd

from nautilus_trader.adapters.binance.loaders import BinanceOrderBookDeltaDataLoader
from nautilus_trader.backtest.node import BacktestDataConfig
from nautilus_trader.backtest.node import BacktestEngineConfig
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.backtest.node import BacktestRunConfig
from nautilus_trader.backtest.node import BacktestVenueConfig
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model import OrderBookDelta
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.persistence.wranglers import OrderBookDeltaDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider


DATA_DIR = "/home/henry/hakkoo/algocoin/data"

data_path = Path(DATA_DIR).expanduser() / "binance" / "python" / "data" / "spot" / "monthly" / "klines"
print(data_path)

raw_files = list(data_path.iterdir())
assert raw_files, f"Unable to find any histdata files in directory {data_path}"
print(raw_files)











