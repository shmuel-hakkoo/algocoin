# test/test_data_connector.py
# -*- coding: utf-8 -*-
"""Unit tests for the DataConnector class."""

import unittest
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
        self.csv_dir = Path("test/test_data")
        self.csv_dir.mkdir(exist_ok=True)
        self.create_dummy_csv()
        self.connector = DataConnector(csv_dir=self.csv_dir)

    def create_dummy_csv(self):
        """Create a dummy CSV file for testing."""
        data = {
            "timestamp": pd.to_datetime(["2023-01-01 00:00:00", "2023-01-01 00:01:00"]),
            "open": [100, 101],
            "high": [102, 102],
            "low": [99, 100],
            "close": [101, 101],
            "volume": [1000, 1200],
        }
        df = pd.DataFrame(data).set_index("timestamp")
        df.to_csv(self.csv_dir / "TEST_SYM, 1.csv")

    def test_scan_csv(self):
        """Test scanning of CSV files."""
        csv_info = self.connector._scan_csv()
        self.assertEqual(len(csv_info), 1)
        self.assertEqual(csv_info[0]["exchange"], "TEST")
        self.assertEqual(csv_info[0]["symbol"], "SYM")
        self.assertEqual(csv_info[0]["timeframe"], "1min")

    def test_get_exchanges_csv(self):
        """Test getting exchanges from CSV source."""
        exchanges = self.connector.get_exchanges("CSV")
        self.assertEqual(exchanges, ["TEST"])

    def test_get_symbols_csv(self):
        """Test getting symbols from CSV source."""
        symbols = self.connector.get_symbols("CSV", "TEST")
        self.assertEqual(symbols, ["SYM"])

    def test_get_timeframes_csv(self):
        """Test getting timeframes from CSV source."""
        timeframes = self.connector.get_timeframes("CSV")
        self.assertEqual(timeframes, ["1min"])

    def test_get_csv_path(self):
        """Test getting the path of a CSV file."""
        path = self.connector.get_csv_path("TEST", "SYM", "1min")
        self.assertEqual(path, str(self.csv_dir / "TEST_SYM, 1.csv"))

    def test_load_klines_csv(self):
        """Test loading klines from a CSV file."""
        path = self.connector.get_csv_path("TEST", "SYM", "1min")
        df = self.connector.load_klines("CSV", path)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)

    def tearDown(self):
        """Tear down test fixtures."""
        for f in self.csv_dir.glob("*.csv"):
            f.unlink()
        self.csv_dir.rmdir()

if __name__ == "__main__":
    unittest.main()
