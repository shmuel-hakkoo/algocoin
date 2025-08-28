# src/clickhouse.py
from __future__ import annotations

import os
import re
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Optional, Tuple, Callable, Any, List

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

# ── Functional ClickHouse Connector ──────────────────────────────── #

def create_connection(
    host: str = CH_HOST,
    user: str = CH_USER,
    password: str = CH_PASSWORD,
    database: str = CH_DATABASE,
) -> Client:
    """Create and verify a ClickHouse client connection."""
    try:
        client = Client(
            host=host,
            user=user,
            password=password,
            database=database,
            secure=True,
        )
        client.execute("SELECT 1")
        return client
    except Exception as exc:
        raise ConnectionError(
            f"Failed to connect to ClickHouse (host={host}, db={database}): {exc}"
        ) from exc

def build_candles_query(
    symbol: str,
    timeframe: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Build the SQL query for candles data."""
    params = {"symbol": symbol, "interval": timeframe}
    conds = ["symbol = %(symbol)s", "interval = %(interval)s"]
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
    return sql, params

def build_sentiment_query(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Build the SQL query for sentiment data."""
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
    return sql, params

def transform_candles_data(rows: List[Tuple], columns: List[Tuple]) -> pd.DataFrame:
    """Transform raw candles data into a DataFrame."""
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

def transform_sentiment_data(rows: List[Tuple], columns: List[Tuple]) -> pd.DataFrame:
    """Transform raw sentiment data into a DataFrame."""
    if not rows:
        return pd.DataFrame()

    column_names = [c[0] for c in columns]
    df = pd.DataFrame(rows, columns=column_names)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.set_index("timestamp", inplace=True)
    return df

def make_query_executor(
    client: Client,
    query_builder: Callable[..., Tuple[str, Dict]],
    data_transformer: Callable[[List, List], pd.DataFrame],
    with_column_types: bool = False,
) -> Callable[..., pd.DataFrame]:
    """Create a function that executes a query and transforms the data."""
    def executor(*args, **kwargs) -> pd.DataFrame:
        sql, params = query_builder(*args, **kwargs)
        result = client.execute(sql, params, with_column_types=with_column_types)
        
        if with_column_types:
            rows, columns = result
        else:
            rows, columns = result, [] # No column info for candles
            
        return data_transformer(rows, columns)
    return executor

def get_candles(client: Client, **kwargs) -> pd.DataFrame:
    """Return a DataFrame with klines data."""
    return make_query_executor(client, build_candles_query, transform_candles_data)(**kwargs)

def get_sentiment(client: Client, **kwargs) -> pd.DataFrame:
    """Return a DataFrame with sentiment data."""
    return make_query_executor(client, build_sentiment_query, transform_sentiment_data, with_column_types=True)(**kwargs)
