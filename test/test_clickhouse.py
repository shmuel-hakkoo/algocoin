# tests/test_clickhouse.py
# -*- coding: utf-8 -*-
"""Unit tests for the ClickHouseConnector class."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pandas as pd
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.clickhouse import ClickHouseConnector, parse_symbol

class TestClickHouse(unittest.TestCase):
    """Test suite for the ClickHouseConnector and utility functions."""

    def test_parse_symbol(self):
        """Test the parse_symbol function."""
        self.assertEqual(parse_symbol("BTCUSDT"), ("BTC", "USDT"))
        self.assertEqual(parse_symbol("ETHBTC"), ("ETH", "BTC"))
        self.assertEqual(parse_symbol("ADABNB"), ("ADA", "BNB"))
        self.assertEqual(parse_symbol("XRPBUSD"), ("XRP", "BUSD"))

    @patch('src.clickhouse.Client')
    def test_connection_success(self, mock_client):
        """Test successful connection to ClickHouse."""
        mock_instance = mock_client.return_value
        mock_instance.execute.return_value = [(1,)]
        connector = ClickHouseConnector()
        self.assertIsNotNone(connector.cli)
        mock_instance.execute.assert_called_once_with("SELECT 1")

    @patch('src.clickhouse.Client')
    def test_connection_failure(self, mock_client):
        """Test failed connection to ClickHouse."""
        mock_client.side_effect = Exception("Connection failed")
        with self.assertRaises(ConnectionError):
            ClickHouseConnector()

    @patch('src.clickhouse.Client')
    def test_candles(self, mock_client):
        """Test the candles method."""
        mock_instance = mock_client.return_value
        mock_rows = [
            (datetime(2023, 1, 1, 0, 0), 100, 102, 99, 101, 1000, 101000, 10, 500, 50500),
            (datetime(2023, 1, 1, 0, 1), 101, 102, 100, 101, 1200, 121200, 12, 600, 60600),
        ]
        mock_instance.execute.return_value = mock_rows
        
        connector = ClickHouseConnector()
        df = connector.candles(exchange="BINANCE", symbol="BTCUSDT", timeframe="1m")
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn("open", df.columns)

    @patch('src.clickhouse.Client')
    def test_sentiment(self, mock_client):
        """Test the sentiment method."""
        mock_instance = mock_client.return_value
        mock_rows = [
            (datetime(2023, 1, 1, 0, 0), 0.5, 0.1),
            (datetime(2023, 1, 1, 0, 1), -0.2, 0.8),
        ]
        mock_columns = [('timestamp', 'DateTime'), ('sentiment', 'Float64'), ('confidence', 'Float64')]
        mock_instance.execute.return_value = (mock_rows, mock_columns)

        connector = ClickHouseConnector()
        df = connector.sentiment()

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn("sentiment", df.columns)

if __name__ == "__main__":
    unittest.main()
