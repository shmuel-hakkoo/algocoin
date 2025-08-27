# src/clickhouse.py
from __future__ import annotations

import os
import re
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
from clickhouse_driver import Client

load_dotenv()

# ── ClickHouse connection settings ──────────────────────────────── #
CH_HOST = os.getenv("CH_HOST")
CH_USER = os.getenv("CH_USER")
CH_PASSWORD = os.getenv("CH_PASSWORD")
CH_DATABASE = os.getenv("CH_DATABASE")

EXCHANGE_NAME_TO_ID: Dict[str, int] = {
    "BINANCE": 1,
}

INTERVAL_STR_TO_CODE: Dict[str, int] = {
    "1s": 1, "1m": 2, "3m": 3, "5m": 4, "15m": 5, "30m": 6,
    "1h": 7, "2h": 8, "4h": 9, "6h": 10, "8h": 11, "12h": 12,
    "1d": 13, "3d": 14, "1w": 15, "1mo": 16,
}
MKT_ENUM: Dict[str, int] = {"spot": 1, "usdm": 2, "coinm": 3}

# ── Utilities ───────────────────────────────────────────────────── #
_SYMBOL_RE = re.compile(
    r"^(.*?)(USDT|BUSD|FDUSD|USDC|BTC|ETH|BNB|SOL|TRX|TRY|EUR|GBP|AUD|RUB|USD)$"
)

def parse_symbol(sym: str) -> Tuple[str, str]:
    """Split a Binance ticker into base and quote currencies."""
    m = _SYMBOL_RE.match(sym)
    if m:
        return m.group(1), m.group(2)
    mid = len(sym) // 2
    return sym[:mid], sym[mid:]

# ── ClickHouse Connector ────────────────────────────────────────── #
class ClickHouseConnector:
    """Lightweight wrapper around ``clickhouse-driver``."""

    def __init__(
        self,
        host: str = CH_HOST,
        user: str = CH_USER,
        password: str = CH_PASSWORD,
        database: str = CH_DATABASE,
    ):
        try:
            self.cli = Client(
                host=host,
                user=user,
                password=password,
                database=database,
                secure=True,
            )
            self.cli.execute("SELECT 1")
        except Exception as exc:
            raise ConnectionError(
                f"Failed to connect to ClickHouse (host={host}, db={database}): {exc}"
            ) from exc

    def candles(
        self,
        *,
        exchange: str,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        mkt: str = "spot",
        debug: bool = False,
        auto_clip: bool = False,
    ) -> pd.DataFrame:
        """Return a DataFrame with klines data."""
        params = {
            "symbol": symbol,
            "interval": timeframe,
        }
        conds = [
            "symbol = %(symbol)s",
            "interval = %(interval)s",
        ]
        if start:
            params["start"] = start
            conds.append("open_time >= %(start)s")
        if end:
            params["end"] = end
            conds.append("open_time <= %(end)s")

        sql = f"""
        SELECT
            open_time, open, high, low, close,
            volume, quote_vol, trades, taker_base, taker_quote
        FROM klines
        WHERE {' AND '.join(conds)}
        ORDER BY open_time
        """
        rows = self.cli.execute(sql, params)
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(
            rows,
            columns=[
                "open_time", "open", "high", "low", "close",
                "volume", "quote_vol", "trades", "taker_base", "taker_quote",
            ],
        )
        df["timestamp"] = pd.to_datetime(df["open_time"], utc=True)
        df.set_index("timestamp", inplace=True)
        df = df.drop(columns=["open_time"])
        num_cols = [
            "open", "high", "low", "close", "volume",
            "quote_vol", "trades", "taker_base", "taker_quote",
        ]
        df[num_cols] = df[num_cols].astype("float64")
        return df

    def sentiment(
        self,
        *,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Return a DataFrame with sentiment data."""
        params = {}
        conds = []
        if start:
            params["ts0"] = start
            conds.append("timestamp >= %(ts0)s")
        if end:
            params["ts1"] = end
            conds.append("timestamp <= %(ts1)s")

        where_clause = f"WHERE {' AND '.join(conds)}" if conds else ""
        sql = f"SELECT * FROM {CH_DATABASE}.sentiment {where_clause} ORDER BY timestamp"

        rows, columns = self.cli.execute(sql, params, with_column_types=True)
        if not rows:
            return pd.DataFrame()

        column_names = [c[0] for c in columns]
        df = pd.DataFrame(rows, columns=column_names)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df.set_index("timestamp", inplace=True)
        return df
