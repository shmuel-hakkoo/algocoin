#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_json.py
~~~~~~~~~~~~~~
Upload sentiment and social volume JSON data to ClickHouse database.

This script reads a JSON file with timestamped sentiment data and uploads it
to the ClickHouse database.

Usage:
    python bin/upload_json.py --file /path/to/your/file.json
    python bin/upload_json.py --file data/bitcoin_sentiment_volume_2025-03-01T180000Z_2025-07-01T190000Z.json --batch-size 1000 --dry-run

Dependencies:
    pip install clickhouse-driver pandas python-dotenv tqdm
"""

import argparse
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime

import pandas as pd
from clickhouse_driver import Client
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# ClickHouse connection settings from environment variables
CH_HOST = os.getenv("CH_HOST", "localhost")
CH_USER = os.getenv("CH_USER", "default")
CH_PASSWORD = os.getenv("CH_PASSWORD")
CH_DATABASE = os.getenv("CH_DATABASE", "crypto")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload_json.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Validate required environment variables
if not CH_PASSWORD:
    logger.warning("⚠️  CH_PASSWORD not set in environment variables. Connection may fail.")
    logger.info("💡 Create a .env file with your ClickHouse credentials (see .env.example)")


class ClickHouseJsonUploader:
    """Upload JSON sentiment data to ClickHouse database."""

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
                secure=True
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
        logger.info("🔧 Creating database schema for sentiment data...")

        # Create database if it doesn't exist
        self.client.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
        logger.info(f"✓ Database {self.database} created/verified")

        # Create sentiment table
        try:
            self.client.execute(f"DROP TABLE IF EXISTS {self.database}.sentiment")
        except:
            pass

        create_sql = f"""CREATE TABLE {self.database}.sentiment (
            timestamp DateTime,
            sentiment_balance_reddit Float64,
            sentiment_balance_twitter Float64,
            sentiment_balance_telegram Float64,
            sentiment_balance_bitcointalk Float64,
            sentiment_balance_youtube_videos Float64,
            sentiment_balance_4chan Float64,
            sentiment_balance_total Float64,
            social_volume_reddit UInt32,
            social_volume_twitter UInt32,
            social_volume_telegram UInt32,
            social_volume_bitcointalk UInt32,
            social_volume_youtube_videos UInt32,
            social_volume_4chan UInt32,
            social_volume_total UInt32,
            window_id UInt32
        ) ENGINE = MergeTree()
        ORDER BY timestamp"""

        self.client.execute(create_sql)
        logger.info("✓ Sentiment table created/verified")

        logger.info("🎉 Database schema setup complete!")

    def upload_json_file(self, json_path: Path, batch_size: int = 5000, dry_run: bool = False) -> Dict[str, Any]:
        """Upload a single JSON file to ClickHouse."""
        logger.info(f"📂 Processing {json_path.name}")

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            records = []
            for timestamp, values in data.items():
                record = {
                    'timestamp': timestamp,
                    **values
                }
                records.append(record)

            df = pd.DataFrame(records)
            logger.info(f"  📊 Loaded {len(df)} records from {json_path.name}")

        except Exception as e:
            logger.error(f"  ❌ Failed to read or parse {json_path}: {e}")
            return {"file": json_path.name, "status": "error", "error": str(e)}

        if df.empty:
            logger.warning(f"  ⚠️  No data found in: {json_path.name}")
            return {"file": json_path.name, "status": "skipped", "reason": "empty"}

        # Convert timestamp from string to datetime
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
            df = df.dropna(subset=['timestamp'])
        except Exception as e:
            logger.error(f"  ❌ Failed to convert timestamps: {e}")
            return {"file": json_path.name, "status": "error", "error": f"Timestamp conversion error: {e}"}

        # Reorder columns to match ClickHouse schema
        df = df[[
            'timestamp', 'sentiment_balance_reddit', 'sentiment_balance_twitter',
            'sentiment_balance_telegram', 'sentiment_balance_bitcointalk',
            'sentiment_balance_youtube_videos', 'sentiment_balance_4chan',
            'sentiment_balance_total', 'social_volume_reddit', 'social_volume_twitter',
            'social_volume_telegram', 'social_volume_bitcointalk',
            'social_volume_youtube_videos', 'social_volume_4chan',
            'social_volume_total', 'window_id'
        ]]

        if dry_run:
            logger.info(f"  🔍 DRY RUN: Would upload {len(df)} rows to sentiment table")
            logger.info(f"  📋 Sample data:\n{df.head(3)}")
            return {"file": json_path.name, "status": "dry_run", "rows": len(df)}

        # Upload in batches
        total_uploaded = 0
        try:
            for start_idx in tqdm(range(0, len(df), batch_size),
                                desc=f"Uploading {json_path.name}"):
                batch = df[start_idx:start_idx + batch_size]
                data_to_insert = [tuple(row) for row in batch.itertuples(index=False)]

                self.client.execute(f"""
                    INSERT INTO {self.database}.sentiment
                    (timestamp, sentiment_balance_reddit, sentiment_balance_twitter,
                     sentiment_balance_telegram, sentiment_balance_bitcointalk,
                     sentiment_balance_youtube_videos, sentiment_balance_4chan,
                     sentiment_balance_total, social_volume_reddit, social_volume_twitter,
                     social_volume_telegram, social_volume_bitcointalk,
                     social_volume_youtube_videos, social_volume_4chan,
                     social_volume_total, window_id)
                    VALUES
                """, data_to_insert)

                total_uploaded += len(batch)

            logger.info(f"  ✅ Successfully uploaded {total_uploaded} rows from {json_path.name}")
            return {"file": json_path.name, "status": "success", "rows": total_uploaded}

        except Exception as e:
            logger.error(f"  ❌ Failed to upload {json_path}: {e}")
            return {"file": json_path.name, "status": "error", "error": str(e), "rows_uploaded": total_uploaded}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Upload sentiment JSON data to ClickHouse")
    parser.add_argument("--file", type=str, required=True,
                       help="Path to the JSON file")
    parser.add_argument("--batch-size", type=int, default=5000,
                       help="Batch size for uploads (default: 5000)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview upload without actually inserting data")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    parser.add_argument("--create-schema", action="store_true",
                       help="Create database schema before uploading")

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    json_file = Path(args.file)
    if not json_file.exists():
        logger.error(f"❌ JSON file does not exist: {json_file}")
        sys.exit(1)

    logger.info(f"🎯 Starting JSON upload from {json_file}")
    logger.info(f"📦 Batch size: {args.batch_size}")
    logger.info(f"🔍 Dry run: {args.dry_run}")

    try:
        uploader = ClickHouseJsonUploader()

        if args.create_schema:
            uploader.create_database_schema()

        result = uploader.upload_json_file(
            json_path=json_file,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )

        if result["status"] == "success":
            logger.info(f"✅ Successfully processed {result['file']} ({result.get('rows', 0):,} rows)")
        elif result["status"] == "error":
            logger.error(f"❌ Error processing {result['file']}: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
