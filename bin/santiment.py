#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path
import requests
import pandas as pd
from datetime import datetime, timedelta

# ===================== Parameters =====================
API_KEY = "27qv3oh5anhvl4zm_o5xgs4u2njr4u43c"
BASE_URL = "https://api.santiment.net/graphql"

SLUG = "bitcoin"
FROM = "2025-03-01T18:00:00Z"
TO   = "2025-07-01T19:00:00Z"
INTERVAL = "5m"  # 5 minutes

# Batch size for metrics to avoid complexity limits
BATCH_SIZE = 2  # Number of metrics per request
TIME_BATCH_DAYS = 30  # Number of days per time batch

# ===================== Metrics Lists =====================
# Supported social sources (based on common experience; farcaster sometimes unavailable)
SOURCES = [
    "reddit",
    "twitter",
    "telegram",
    "bitcointalk",
    "youtube_videos",
    "4chan",
    # "farcaster",  # Can be enabled, and if it fails – the auto-filter will remove it
]

# Sentiment (positive-negative balance)
SENTIMENT_METRICS = [f"sentiment_balance_{s}" for s in SOURCES] + ["sentiment_balance_total"]

# Social volume = how many documents/posts were mentioned (counts)
VOLUME_METRICS = [f"social_volume_{s}" for s in SOURCES] + ["social_volume_total"]

ALL_METRICS = SENTIMENT_METRICS + VOLUME_METRICS

# ===================== Helper =====================
def build_query(metrics, slug, t_from, t_to, interval, use_json=True):
    """Builds GraphQL query with aliases for each metric."""
    parts = []
    for i, m in enumerate(metrics):
        alias = f"m{i}"
        if use_json:
            part = f'''
            {alias}: getMetric(metric: "{m}") {{
              timeseriesDataJson(
                selector: {{ slug: "{slug}" }}
                from: "{t_from}"
                to: "{t_to}"
                interval: "{interval}"
              )
            }}
            '''
        else:
            part = f'''
            {alias}: getMetric(metric: "{m}") {{
              timeseriesData(
                selector: {{ slug: "{slug}" }}
                from: "{t_from}"
                to: "{t_to}"
                interval: "{interval}"
              ) {{
                datetime
                value
              }}
            }}
            '''
        parts.append(part)
    return "{\n" + "\n".join(parts) + "\n}"

def fetch_payload(query, api_key):
    headers = {"Authorization": f"Apikey {api_key}"}
    resp = requests.post(BASE_URL, json={"query": query}, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()

def _node_to_rows(node):
    """Returns [{datetime, value}, ...] from node, supports timeseriesDataJson/list."""
    if not node:
        return []
    tsj = node.get("timeseriesDataJson")
    if tsj is not None:
        if isinstance(tsj, str):
            try:
                return json.loads(tsj)
            except json.JSONDecodeError:
                pass
        elif isinstance(tsj, list):
            return tsj
    ts = node.get("timeseriesData")
    if ts is not None:
        if isinstance(ts, list):
            return ts
        elif isinstance(ts, str):
            try:
                return json.loads(ts)
            except json.JSONDecodeError:
                pass
    return []

def payload_to_wide_df(payload, metrics, t_from, t_to, interval):
    """Converts payload to wide DataFrame and aligns to full interval grid."""
    series_map = {}
    for i, metric in enumerate(metrics):
        node = payload.get("data", {}).get(f"m{i}", {})
        rows = _node_to_rows(node)
        if rows:
            s = (
                pd.DataFrame(rows)
                .assign(datetime=lambda d: pd.to_datetime(d["datetime"], utc=True))
                .set_index("datetime")["value"]
            )
        else:
            s = pd.Series(dtype="float64")
        series_map[metric] = s

    df = pd.concat(series_map, axis=1)
    pandas_freq = "5min" if interval.lower() in ("5m", "5min") else interval
    full_idx = pd.date_range(start=t_from, end=t_to, freq=pandas_freq, tz="UTC", inclusive="left")
    df = df.reindex(full_idx)

    # Type conversion
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def batch_metrics(metrics, batch_size):
    """Split metrics into batches to avoid complexity limits."""
    for i in range(0, len(metrics), batch_size):
        yield metrics[i:i + batch_size]

def batch_time_periods(start_time, end_time, days_per_batch):
    """Split time range into batches to avoid complexity limits."""
    start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

    current = start
    while current < end:
        batch_end = min(current + timedelta(days=days_per_batch), end)
        yield (
            current.strftime('%Y-%m-%dT%H:%M:%SZ'),
            batch_end.strftime('%Y-%m-%dT%H:%M:%SZ')
        )
        current = batch_end

def try_fetch_with_autofilter(metrics, slug, t_from, t_to, interval, api_key):
    """
    Attempts to fetch payload; if there are errors about unsupported metrics,
    filters them out and tries again (once).
    """
    def _fetch(ms):
        q = build_query(ms, slug, t_from, t_to, interval, use_json=True)
        pl = fetch_payload(q, api_key)
        return pl, ms

    payload, used_metrics = _fetch(metrics)
    if "errors" not in payload:
        return payload, used_metrics

    bad = set()
    complexity_errors = []
    for err in payload["errors"]:
        err_msg = err.get("message", "")
        m = re.search(r"The metric '([^']+)' is not supported", err_msg)
        if m:
            bad.add(m.group(1))
        elif "too complex" in err_msg.lower() or "complexity" in err_msg.lower():
            complexity_errors.append(err_msg)

    if complexity_errors and not bad:
        raise RuntimeError(f"Query complexity exceeded. Try reducing batch size or time range. Errors: {complexity_errors}")

    if not bad:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")

    filtered = [m for m in metrics if m not in bad]
    print("Warning: Filtered out unsupported metrics:", sorted(bad))
    if not filtered:
        raise RuntimeError("All metrics filtered out; nothing to fetch.")

    payload2, used2 = _fetch(filtered)
    if "errors" in payload2:
        raise RuntimeError(f"GraphQL errors after filtering: {payload2['errors']}")
    return payload2, used2

def fetch_metrics_in_batches(metrics, slug, t_from, t_to, interval, api_key, batch_size, time_batch_days):
    """Fetch metrics in batches (both metrics and time) and merge results."""
    all_dataframes = []
    all_used_metrics = set()

    print(f"Fetching {len(metrics)} metrics in batches of {batch_size} metrics and {time_batch_days} day periods...")

    # Get time periods
    time_periods = list(batch_time_periods(t_from, t_to, time_batch_days))
    print(f"Split into {len(time_periods)} time periods")

    # For each time period, fetch all metrics in batches
    time_dataframes = []

    for time_idx, (period_start, period_end) in enumerate(time_periods, 1):
        print(f"\nTime Period {time_idx}/{len(time_periods)}: {period_start} to {period_end}")
        period_dataframes = []

        for batch_num, batch_metric_list in enumerate(batch_metrics(metrics, batch_size), 1):
            print(f"  Batch {batch_num}: Fetching {len(batch_metric_list)} metrics...")

            try:
                payload, used_metrics = try_fetch_with_autofilter(
                    batch_metric_list, slug, period_start, period_end, interval, api_key
                )

                df = payload_to_wide_df(payload, used_metrics, period_start, period_end, interval)
                period_dataframes.append(df)
                all_used_metrics.update(used_metrics)

                print(f"    Completed: {len(used_metrics)} metrics retrieved")

            except RuntimeError as e:
                if "complexity" in str(e).lower():
                    print(f"    Batch {batch_num} failed due to complexity. Consider reducing BATCH_SIZE or TIME_BATCH_DAYS.")
                    raise
                else:
                    print(f"    Batch {batch_num} failed: {e}")
                    continue

        # Combine metrics for this time period
        if period_dataframes:
            period_combined = pd.concat(period_dataframes, axis=1)
            time_dataframes.append(period_combined)

    if not time_dataframes:
        raise RuntimeError("No data retrieved from any batch")

    # Combine all time periods
    final_df = pd.concat(time_dataframes, axis=0).sort_index()

    # Remove duplicates and align to full time grid
    pandas_freq = "5min" if interval.lower() in ("5m", "5min") else interval
    full_idx = pd.date_range(start=t_from, end=t_to, freq=pandas_freq, tz="UTC", inclusive="left")
    final_df = final_df.reindex(full_idx)

    return final_df, list(all_used_metrics)

def validate_total(df):
    """Quality check for sentiment: total ≈ sum of all social sources (small tolerance)."""
    if "sentiment_balance_total" not in df.columns:
        print("Warning: No sentiment_balance_total column for validation.")
        return
    parts = [c for c in df.columns if c.startswith("sentiment_balance_") and c != "sentiment_balance_total"]
    if not parts:
        print("Warning: No social components for sum validation.")
        return
    social_sum = df[parts].sum(axis=1)
    mismatch = (df["sentiment_balance_total"] - social_sum).abs() > 1e-6
    if mismatch.any():
        print("Warning: total ≠ sum of components in some rows (total", mismatch.sum(), ")")
    else:
        print("Total validation (sentiment): OK")

def to_int_safe(s):
    """Converts series to integer values (counts) while preserving NaN as NaN."""
    return s.round().astype("Int64")

def save_json(df, out_path):
    """
    Save to JSON in format:
    {
      "YYYY-MM-DDTHH:MM:SSZ": {
        "window_id": <int>,
        "sentiment_balance_reddit": ...,
        "social_volume_reddit": <int>,
        ...
      }, ...
    }
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Add window_id (running counter by time)
    df_out = df.copy()
    df_out["window_id"] = range(1, len(df_out) + 1)

    # Convert volume columns to integers
    vol_cols = [c for c in df_out.columns if c.startswith("social_volume_")]
    for c in vol_cols:
        df_out[c] = to_int_safe(df_out[c])

    # Index to ISO8601 format with Z
    df_out.index = df_out.index.tz_convert("UTC")
    iso_index = df_out.index.strftime("%Y-%m-%dT%H:%M:%SZ")

    data_dict = {iso_index[i]: row.dropna().to_dict() for i, (_, row) in enumerate(df_out.iterrows())}

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=2)

    print("Saved:", out_path)

# ===================== main =====================
def main():
    print("-> Fetching data from Santiment using batched requests...")

    # Fetch all metrics (sentiment + volume) in batches
    df, used_metrics = fetch_metrics_in_batches(
        ALL_METRICS, SLUG, FROM, TO, INTERVAL, API_KEY, BATCH_SIZE, TIME_BATCH_DAYS
    )

    print("-> Quality check total (sentiment)...")
    validate_total(df)

    # Save to data directory
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "data"
    data_dir.mkdir(exist_ok=True)
    out_file = data_dir / f"{SLUG}_sentiment_volume_{FROM.replace(':','')}_{TO.replace(':','')}.json"
    save_json(df, out_file)

    print("Time range:", df.index.min(), "→", df.index.max(), "| Rows:", len(df))
    print("Columns:", list(df.columns))
    print("Metrics actually used:", used_metrics)
    print(f"Total metrics retrieved: {len(used_metrics)}")

    # Summary by metric type
    sentiment_count = sum(1 for m in used_metrics if m.startswith("sentiment_"))
    volume_count = sum(1 for m in used_metrics if m.startswith("social_volume_"))
    print(f"Sentiment metrics: {sentiment_count}, Volume metrics: {volume_count}")

if __name__ == "__main__":
    main()
