#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_csv.py
~~~~~~~~~~~~~
Upload Binance klines CSV data to ClickHouse database.

This script reads CSV files from the Binance bulk downloader and uploads them
to the ClickHouse database using the schema defined in bin/clickhouse.py.

Usage:
    python bin/upload_csv.py --data-dir data/futures/um/monthly/klines/BTCUSDT/1m
    python bin/upload_csv.py --data-dir data/futures/um/monthly/klines/BTCUSDT/1m --batch-size 10000 --dry-run

Dependencies:
    pip install clickhouse-driver pandas python-dotenv tqdm
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

import pandas as pd
from clickhouse_driver import Client
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# ClickHouse connection settings
CH_HOST = os.getenv("CH_HOST", "localhost")
CH_USER = os.getenv("CH_USER", "default")
CH_PASSWORD = os.getenv("CH_PASSWORD", "")
CH_DATABASE = os.getenv("CH_DATABASE", "crypto")

# Constants from bin/clickhouse.py
EXCHANGE_NAME_TO_ID = {"BINANCE": 1}
INTERVAL_STR_TO_CODE = {
    "1s": 1, "1m": 2, "3m": 3, "5m": 4, "15m": 5, "30m": 6,
    "1h": 7, "2h": 8, "4h": 9, "6h": 10, "8h": 11, "12h": 12,
    "1d": 13, "3d": 14, "1w": 15, "1mo": 16,
}
MKT_ENUM = {"spot": 1, "usdm": 2, "coinm": 3}

# CSV column mapping based on Binance klines format
KLINES_COLUMNS = [
    "open_time",      # 0: Open time (Unix timestamp in milliseconds)
    "open",           # 1: Open price
    "high",           # 2: High price
    "low",            # 3: Low price
    "close",          # 4: Close price
    "volume",         # 5: Volume
    "close_time",     # 6: Close time (Unix timestamp in milliseconds)
    "quote_vol",      # 7: Quote asset volume
    "trades",         # 8: Number of trades
    "taker_base",     # 9: Taker buy base asset volume
    "taker_quote",    # 10: Taker buy quote asset volume
    "ignore"          # 11: Unused field (always 0)
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload_csv.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ClickHouseUploader:
    """Upload CSV klines data to ClickHouse database."""

    def __init__(self, host: str = CH_HOST, user: str = CH_USER,
                 password: str = CH_PASSWORD, database: str = CH_DATABASE):
        """Initialize ClickHouse connection."""
        self.database = database
        try:
            self.client = Client(
                host=host,
                user=user,
                password=password,
                database=database,
            )
            # Test connection
            self.client.execute("SELECT 1")
            logger.info(f"✓ Connected to ClickHouse at {host}/{database}")
        except Exception as exc:
            raise ConnectionError(
                f"Failed to connect to ClickHouse (host={host}, db={database}): {exc}"
            ) from exc
    
    def create_database_schema(self):
        """Create the required database schema if it doesn't exist."""
        logger.info("🔧 Creating database schema...")
        
        # Create database if it doesn't exist
        self.client.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
        logger.info(f"✓ Database {self.database} created/verified")
        
        # Create single klines table with all data - split into steps
        try:
            # Drop and recreate to avoid issues
            self.client.execute(f"DROP TABLE IF EXISTS {self.database}.klines")
        except:
            pass
        
        # Create table step by step
        create_sql = f"""CREATE TABLE {self.database}.klines (
            symbol String,
            interval String,  
            open_time DateTime,
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume Float64,
            close_time DateTime,
            quote_vol Float64,
            trades UInt32,
            taker_base Float64,
            taker_quote Float64
        ) ENGINE MergeTree ORDER BY open_time"""
        
        self.client.execute(create_sql)
        logger.info("✓ Klines table created/verified")
        
        logger.info("🎉 Database schema setup complete!")


    def upload_csv_file(self, csv_path: Path, symbol: str, interval: str,
                       batch_size: int = 5000, dry_run: bool = False) -> Dict[str, Any]:
        """Upload a single CSV file to ClickHouse."""
        logger.info(f"📂 Processing {csv_path.name}")

        # Read CSV file with pandas auto-detection, then standardize
        try:
            # Try reading normally - pandas will auto-detect headers
            df = pd.read_csv(csv_path)
            
            # Always ensure we have the right column names
            if len(df.columns) == len(KLINES_COLUMNS):
                df.columns = KLINES_COLUMNS
            else:
                raise ValueError(f"Expected {len(KLINES_COLUMNS)} columns, got {len(df.columns)}")
                
            logger.info(f"  📊 Loaded {len(df)} rows from {csv_path.name}")
                
        except Exception as e:
            logger.error(f"  ❌ Failed to read {csv_path}: {e}")
            return {"file": csv_path.name, "status": "error", "error": str(e)}

        if df.empty:
            logger.warning(f"  ⚠️  Empty file: {csv_path.name}")
            return {"file": csv_path.name, "status": "skipped", "reason": "empty"}

        # Convert timestamps from milliseconds to datetime with error handling
        try:
            # Check for invalid timestamp values
            invalid_open = df['open_time'].isna() | (df['open_time'] <= 0) | (df['open_time'] > 2**63-1)
            invalid_close = df['close_time'].isna() | (df['close_time'] <= 0) | (df['close_time'] > 2**63-1)
            
            if invalid_open.any() or invalid_close.any():
                logger.warning(f"  ⚠️  Found {invalid_open.sum()} invalid open_time and {invalid_close.sum()} invalid close_time values")
                # Remove rows with invalid timestamps
                df = df[~(invalid_open | invalid_close)]
                logger.info(f"  📊 After cleaning: {len(df)} rows remaining")
            
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True, errors='coerce')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True, errors='coerce')
            
            # Remove any rows where conversion failed
            before_clean = len(df)
            df = df.dropna(subset=['open_time', 'close_time'])
            after_clean = len(df)
            
            if before_clean != after_clean:
                logger.warning(f"  ⚠️  Removed {before_clean - after_clean} rows with invalid timestamps")
                
        except Exception as e:
            logger.error(f"  ❌ Failed to convert timestamps: {e}")
            return {"file": csv_path.name, "status": "error", "error": f"Timestamp conversion error: {e}"}

        # Drop the ignore column
        df = df.drop('ignore', axis=1)

        # Add symbol and interval columns
        df['symbol'] = symbol
        df['interval'] = interval

        # Reorder columns to match ClickHouse schema
        df = df[[
            'symbol', 'interval', 'open_time', 'open', 'high', 'low', 'close',
            'volume', 'close_time', 'quote_vol', 'trades', 'taker_base', 'taker_quote'
        ]]

        if dry_run:
            logger.info(f"  🔍 DRY RUN: Would upload {len(df)} rows to klines table")
            logger.info(f"  📋 Sample data:\n{df.head(3)}")
            return {"file": csv_path.name, "status": "dry_run", "rows": len(df)}

        # Upload in batches
        total_uploaded = 0
        try:
            for start_idx in tqdm(range(0, len(df), batch_size),
                                desc=f"Uploading {csv_path.name}"):
                batch = df[start_idx:start_idx + batch_size]

                # Convert to list of tuples for ClickHouse
                data = [tuple(row) for row in batch.values]

                # Insert batch
                self.client.execute(f"""
                    INSERT INTO {self.database}.klines
                    (symbol, interval, open_time, open, high, low, close,
                     volume, close_time, quote_vol, trades, taker_base, taker_quote)
                    VALUES
                """, data)

                total_uploaded += len(batch)

            logger.info(f"  ✅ Successfully uploaded {total_uploaded} rows from {csv_path.name}")
            return {"file": csv_path.name, "status": "success", "rows": total_uploaded}

        except Exception as e:
            logger.error(f"  ❌ Failed to upload {csv_path}: {e}")
            return {"file": csv_path.name, "status": "error", "error": str(e), "rows_uploaded": total_uploaded}

    def upload_directory(self, data_dir: Path, batch_size: int = 5000,
                        dry_run: bool = False, file_pattern: str = "*.csv") -> List[Dict[str, Any]]:
        """Upload all CSV files from a directory."""
        csv_files = list(data_dir.glob(file_pattern))

        if not csv_files:
            logger.warning(f"⚠️  No CSV files found in {data_dir}")
            return []

        logger.info(f"🚀 Found {len(csv_files)} CSV files to process")

        # Parse directory structure to extract symbol and interval
        # Assuming path: .../SYMBOL/INTERVAL/*.csv
        path_parts = data_dir.parts
        symbol = path_parts[-2]  # BTCUSDT
        interval = path_parts[-1]  # 1m

        logger.info(f"📈 Symbol: {symbol}, Interval: {interval}")

        results = []
        total_success = 0
        total_errors = 0

        for csv_file in sorted(csv_files):
            result = self.upload_csv_file(csv_file, symbol, interval, batch_size, dry_run)
            results.append(result)

            if result["status"] == "success":
                total_success += 1
            elif result["status"] == "error":
                total_errors += 1

        logger.info(f"🏁 Upload complete: {total_success} successful, {total_errors} errors")
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Upload Binance klines CSV data to ClickHouse")
    parser.add_argument("--data-dir", type=str, required=True,
                       help="Directory containing CSV files")
    parser.add_argument("--batch-size", type=int, default=5000,
                       help="Batch size for uploads (default: 5000)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview upload without actually inserting data")
    parser.add_argument("--pattern", type=str, default="*.csv",
                       help="File pattern to match (default: *.csv)")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    parser.add_argument("--create-schema", action="store_true",
                       help="Create database schema before uploading")

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"❌ Data directory does not exist: {data_dir}")
        sys.exit(1)

    logger.info(f"🎯 Starting CSV upload from {data_dir}")
    logger.info(f"📦 Batch size: {args.batch_size}")
    logger.info(f"🔍 Dry run: {args.dry_run}")

    try:
        uploader = ClickHouseUploader()
        
        # Create schema if requested
        if args.create_schema:
            uploader.create_database_schema()
        
        results = uploader.upload_directory(
            data_dir=data_dir,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            file_pattern=args.pattern
        )

        # Summary report
        successful = [r for r in results if r["status"] == "success"]
        errors = [r for r in results if r["status"] == "error"]

        if successful:
            total_rows = sum(r.get("rows", 0) for r in successful)
            logger.info(f"✅ Successfully processed {len(successful)} files ({total_rows:,} total rows)")

        if errors:
            logger.error(f"❌ {len(errors)} files had errors:")
            for error in errors:
                logger.error(f"  - {error['file']}: {error.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
