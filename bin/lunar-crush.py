#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LunarCrush BTC Sentiment (Hourly, fixed endpoint/auth)
- Fetches hourly time-series for BTC in range 2025-07-01T00:00:00Z → 2025-07-02T00:00:00Z
- Sends Authorization: Bearer <API_KEY>
- Correct path: /api4/public/coins/{COIN}/time-series/v2
- Filters sentiment fields (and optionally: social_volume_*, social_dominance)
- Aligns exactly 24 points and saves one JSON
Dependencies: requests, pandas
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

import requests
import pandas as pd

# ============ Settings ============
API_KEY = "a5xbut8y1o5kyp38pah91lyccamebitcqofxo163k"  # Can move to ENV later
BASE_URL = "https://lunarcrush.com/api4"
COIN = "BTC"  # Can also use "bitcoin"
FROM_ISO = "2021-07-01T00:00:00Z"
TO_ISO   = "2025-07-02T00:00:00Z"
INTERVAL = "hour"   # or "1h"
INCLUDE_VOLUME_AND_DOMINANCE = True  # include social_volume_* + social_dominance

logging.basicConfig(level=logging.INFO, format="%(message)s")

# ============ Helper ============
def to_iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def parse_iso_z(s: str) -> datetime:
    # Supports "Z" as UTC
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)

# ============ Fetching ============
def fetch_lunarcrush_timeseries(coin: str, start_iso: str, end_iso: str, interval: str = "hour") -> Dict[str, Any]:
    """
    Calls the correct path with Bearer:
    GET /api4/public/coins/{COIN}/time-series/v2?interval=hour&start=...&end=...
    Expected to receive {"data": [...]} with various fields (including sentiment)
    """
    url = f"{BASE_URL}/public/coins/{coin}/time-series/v2"
    params = {
        "interval": "1h" if interval == "hour" else interval,
        "start": start_iso,
        "end": end_iso,
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}

    logging.info(f"[INFO] Fetching {coin} {params['interval']} {start_iso} → {end_iso} ...")
    r = requests.get(url, params=params, headers=headers, timeout=45)
    if r.status_code != 200:
        raise RuntimeError(f"API Error: {r.status_code} - {r.text[:300]}")
    return r.json()

# ============ Processing ============
def rows_to_df(payload: Dict[str, Any]) -> pd.DataFrame:
    rows = payload.get("data", payload)
    if not rows or not isinstance(rows, list):
        return pd.DataFrame()

    # Time field identification
    time_key = None
    probe = rows[0]
    for k in ("time", "timestamp", "datetime", "date"):
        if k in probe:
            time_key = k
            break
    if not time_key:
        for k in probe.keys():
            if "time" in k:
                time_key = k
                break
    if not time_key:
        raise ValueError("No time-like field found in response")

    df = pd.DataFrame(rows)

    # Time conversion: if numeric -> Unix seconds, otherwise ISO
    if str(df[time_key].iloc[0]).isdigit():
        df["datetime"] = pd.to_datetime(df[time_key], unit="s", utc=True)
    else:
        df["datetime"] = pd.to_datetime(df[time_key], utc=True, errors="coerce")
    df = df.set_index("datetime").sort_index()

    # Select sentiment columns + optional volume/dominance
    keep = [c for c in df.columns if "sentiment" in c.lower()]
    if INCLUDE_VOLUME_AND_DOMINANCE:
        keep += [c for c in df.columns if c.lower().startswith("social_volume")]
        keep += [c for c in df.columns if "social_dominance" in c.lower()]

    if not keep:
        # If no such fields (depends on route/endpoint) - save everything for debugging purposes
        keep = [c for c in df.columns if c != time_key]

    for c in keep:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df[sorted(set(keep))]

def save_json(df: pd.DataFrame, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_out = df.copy()
    df_out.index = df_out.index.tz_convert("UTC")
    iso_idx = df_out.index.strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {iso_idx[i]: row.dropna().to_dict() for i, (_, row) in enumerate(df_out.iterrows())}
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info(f"[INFO] Saved: {out_path}")

# ============ main ============
def main():
    start = parse_iso_z(FROM_ISO)
    end   = parse_iso_z(TO_ISO)
    if end <= start:
        raise SystemExit("TO_ISO must be after FROM_ISO")

    payload = fetch_lunarcrush_timeseries(COIN, FROM_ISO, TO_ISO, INTERVAL)
    df = rows_to_df(payload)
    if df.empty:
        raise SystemExit("No data received (empty DataFrame). Print payload to check fields.")

    # Align to full hourly grid (24 points)
    full_idx = pd.date_range(start=start, end=end, freq="H", inclusive="left", tz="UTC")
    df = df.reindex(full_idx)

    # Save to JSON
    script_dir = Path(__file__).resolve().parent
    out = script_dir / f"btc_lunarcrush_hourly_{FROM_ISO.replace(':','')}_{TO_ISO.replace(':','')}.json"
    save_json(df, out)

    logging.info(f"Range: {df.index.min()} → {df.index.max()} | Points: {len(df)}")
    logging.info(f"Columns: {list(df.columns)}")

if __name__ == "__main__":
    main()
