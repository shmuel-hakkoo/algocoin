# test/test_data_connector.py
# -*- coding: utf-8 -*-
"""Unit tests for the DataConnector class."""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import pandas as pd
from datetime import datetime
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_connector import DataConnector

class TestDataConnector(unittest.TestCase):
    """Test suite for the DataConnector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.create_connection_patcher = patch('src.clickhouse.create_connection')
        self.mock_create_connection = self.create_connection_patcher.start()
        
        self.mock_client = MagicMock()
        self.mock_create_connection.return_value = self.mock_client
        self.connector = DataConnector()

    def tearDown(self):
        """Clean up after tests."""
        self.create_connection_patcher.stop()

    def test_get_exchanges(self):
        """Test getting exchanges from ClickHouse source."""
        with patch('src.clickhouse.EXCHANGE_NAME_TO_ID', {"BINANCE": 1, "COINBASE": 2}):
            exchanges = self.connector.get_exchanges()
            self.assertEqual(exchanges, ["BINANCE", "COINBASE"])

    def test_get_timeframes(self):
        """Test getting timeframes from ClickHouse source."""
        with patch('src.clickhouse.INTERVAL_STR_TO_CODE', {"1m": 1, "5m": 2}):
            timeframes = self.connector.get_timeframes()
            self.assertEqual(timeframes, ["1min", "5min"])

    @patch('src.clickhouse.get_candles')
    def test_load_klines(self, mock_get_candles):
        """Test loading klines from ClickHouse."""
        mock_df = pd.DataFrame({'open': [1, 2], 'close': [3, 4]})
        mock_get_candles.return_value = mock_df
        
        spec = {'symbol': 'BTCUSDT', 'timeframe': '1m'}
        df = self.connector.load_klines(spec)
        
        self.assertIs(df, mock_df)
        mock_get_candles.assert_called_once_with(self.mock_client, **spec, start=None, end=None)

    @patch('src.clickhouse.get_sentiment')
    def test_load_sentiment(self, mock_get_sentiment):
        """Test loading sentiment data from ClickHouse."""
        mock_df = pd.DataFrame({'sentiment': [0.5, -0.2]})
        mock_get_sentiment.return_value = mock_df
        
        df = self.connector.load_sentiment()
        
        self.assertIs(df, mock_df)
        mock_get_sentiment.assert_called_once_with(self.mock_client, start=None, end=None)

if __name__ == "__main__":
    unittest.main()
