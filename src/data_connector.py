# data_connector.py
# -*- coding: utf-8 -*-
"""Unified interface for loading OHLCV data from CSV files or ClickHouse."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import re

import pandas as pd

from . import clickhouse as ch
from clickhouse_driver import Client

__all__ = ["DataConnector"]


class DataConnector:
    """Load OHLCV data and expose available sources."""

    def __init__(
        self,
        clickhouse_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._ch_params = clickhouse_params or {}
        self._ch: Optional[Client] = None

    # ------------------------------------------------------------------
    def _get_ch(self) -> Client:
        if self._ch is None:
            self._ch = ch.create_connection(**self._ch_params)
        return self._ch

    # ------------------------------------------------------------------
    def get_exchanges(self) -> List[str]:
        return sorted(ch.EXCHANGE_NAME_TO_ID.keys())

    def get_symbols(self, exchange: str | None = None) -> List[str]:
        return []  # symbol list not implemented

    def get_timeframes(self) -> List[str]:
        def _conv(tf: str) -> str:
            if tf.endswith("m"):
                return tf[:-1] + "min"
            return tf

        return sorted(_conv(tf) for tf in ch.INTERVAL_STR_TO_CODE)

    def load_klines(
        self,
        spec: Any,
        *,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Return a DataFrame with OHLCV data for the given source."""
        client = self._get_ch()
        if not isinstance(spec, dict):
            raise TypeError("spec must be dict for ClickHouse")
        return ch.get_candles(client, **spec, start=start, end=end)

    def load_sentiment(
        self,
        *,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Return a DataFrame with sentiment data from ClickHouse."""
        client = self._get_ch()
        return ch.get_sentiment(client, start=start, end=end)
