#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_inspector.py
~~~~~~~~~~~~~~~
A utility to inspect the ClickHouse database schema and sample data.

This script connects to the database, lists tables, and for specified tables,
it prints the schema and a sample of the data.

Usage:
    python bin/db_inspector.py
"""

import os
import sys
import logging
import pandas as pd
from dotenv import load_dotenv
from clickhouse_driver import Client

# Load environment variables
load_dotenv()

# ClickHouse connection settings
CH_HOST = os.getenv("CH_HOST", "localhost")
CH_USER = os.getenv("CH_USER", "default")
CH_PASSWORD = os.getenv("CH_PASSWORD")
CH_DATABASE = os.getenv("CH_DATABASE", "crypto")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class DbInspector:
    """Inspects the ClickHouse database schema and data."""

    def __init__(self):
        """Initialize ClickHouse connection."""
        try:
            self.client = Client(
                host=CH_HOST,
                user=CH_USER,
                password=CH_PASSWORD,
                database=CH_DATABASE,
                secure=True
            )
            self.client.execute("SELECT 1")
            logger.info(f"✓ Connected to ClickHouse at {CH_HOST}/{CH_DATABASE}")
        except Exception as exc:
            logger.error(f"Failed to connect to ClickHouse: {exc}")
            sys.exit(1)

    def list_tables(self):
        """Lists all tables in the database."""
        logger.info("Listing tables...")
        tables = self.client.execute("SHOW TABLES")
        print("Tables found:", [table[0] for table in tables])
        return [table[0] for table in tables]

    def inspect_table(self, table_name: str):
        """Prints the schema and sample data for a given table."""
        logger.info(f"\n--- Inspecting table: {table_name} ---")

        # Get schema
        try:
            schema = self.client.execute(f"DESCRIBE TABLE {table_name}")
            print(f"\nSchema for {table_name}:")
            df_schema = pd.DataFrame(schema, columns=['name', 'type', 'default_type', 'default_expression', 'comment', 'codec_expression', 'ttl_expression'])
            print(df_schema[['name', 'type']])
        except Exception as e:
            logger.error(f"Could not get schema for {table_name}: {e}")
            return

        # Get sample data
        try:
            data, columns = self.client.execute(f"SELECT * FROM {table_name} LIMIT 5", with_column_types=True)
            print(f"\nSample data from {table_name}:")
            if data:
                df_data = pd.DataFrame(data, columns=[c[0] for c in columns])
                print(df_data)
            else:
                print("No data found in table.")
        except Exception as e:
            logger.error(f"Could not get sample data for {table_name}: {e}")

def main():
    """Main entry point."""
    inspector = DbInspector()
    tables = inspector.list_tables()
    
    tables_to_inspect = ['klines', 'sentiment']
    for table in tables_to_inspect:
        if table in tables:
            inspector.inspect_table(table)
        else:
            logger.warning(f"Table '{table}' not found in the database.")

if __name__ == "__main__":
    main()
