# test/test_db.py
# -*- coding: utf-8 -*-
"""Unit tests for the db module."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pandas as pd
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db import create_connection, get_candles, get_sentiment, parse_symbol

class TestDB(unittest.TestCase):
    """Test suite for the db module and utility functions."""

    def test_parse_symbol(self):
        """Test the parse_symbol function."""
        self.assertEqual(parse_symbol("BTCUSDT"), ("BTC", "USDT"))
        self.assertEqual(parse_symbol("ETHBTC"), ("ETH", "BTC"))
        self.assertEqual(parse_symbol("ADABNB"), ("ADA", "BNB"))
        self.assertEqual(parse_symbol("XRPBUSD"), ("XRP", "BUSD"))

    @patch('src.db.Client')
    def test_connection_success(self, mock_client):
        """Test successful connection to ClickHouse."""
        mock_instance = mock_client.return_value
        mock_instance.execute.return_value = [(1,)]
        client = create_connection()
        self.assertIsNotNone(client)
        mock_instance.execute.assert_called_once_with("SELECT 1")

    @patch('src.db.Client')
    def test_connection_failure(self, mock_client):
        """Test failed connection to ClickHouse."""
        mock_client.side_effect = Exception("Connection failed")
        with self.assertRaises(ConnectionError):
            create_connection()

    @patch('src.db.Client')
    def test_get_candles(self, mock_client):
        """Test the get_candles function."""
        mock_instance = mock_client.return_value
        mock_rows = [
            (datetime(2023, 1, 1, 0, 0), 100, 102, 99, 101, 1000, 101000, 10, 500, 50500),
            (datetime(2023, 1, 1, 0, 1), 101, 102, 100, 101, 1200, 121200, 12, 600, 60600),
        ]
        mock_instance.execute.return_value = mock_rows
        
        client = create_connection()
        df = get_candles(client, symbol="BTCUSDT", timeframe="1m")
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn("open", df.columns)

    @patch('src.db.Client')
    def test_get_sentiment(self, mock_client):
        """Test the get_sentiment function."""
        mock_instance = mock_client.return_value
        mock_rows = [
            (datetime(2023, 1, 1, 0, 0), 0.5, 0.1),
            (datetime(2023, 1, 1, 0, 1), -0.2, 0.8),
        ]
        mock_columns = [('timestamp', 'DateTime'), ('sentiment', 'Float64'), ('confidence', 'Float64')]
        mock_instance.execute.return_value = (mock_rows, mock_columns)

        client = create_connection()
        df = get_sentiment(client)

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn("sentiment", df.columns)

if __name__ == "__main__":
    unittest.main()
