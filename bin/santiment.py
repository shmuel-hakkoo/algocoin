#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path
import requests
import pandas as pd

# ===================== Parameters =====================
API_KEY = "27qv3oh5anhvl4zm_o5xgs4u2njr4u43c"
BASE_URL = "https://api.santiment.net/graphql"

SLUG = "bitcoin"
FROM = "2021-07-01T18:00:00Z"
TO   = "2025-07-01T19:00:00Z"
INTERVAL = "5m"  # 5 minutes

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
    for err in payload["errors"]:
        m = re.search(r"The metric '([^']+)' is not supported", err.get("message", ""))
        if m:
            bad.add(m.group(1))

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
    print("-> Fetching data from Santiment (with auto-filtering if needed)...")
    payload, used_metrics = try_fetch_with_autofilter(ALL_METRICS, SLUG, FROM, TO, INTERVAL, API_KEY)

    print("-> Converting to DataFrame...")
    df = payload_to_wide_df(payload, used_metrics, FROM, TO, INTERVAL)

    print("-> Quality check total (sentiment)...")
    validate_total(df)

    # Save to regular JSON in script directory
    script_dir = Path(__file__).resolve().parent
    out_file = script_dir / f"{SLUG}_sentiment_volume_{FROM.replace(':','')}_{TO.replace(':','')}.json"
    save_json(df, out_file)

    print("Time range:", df.index.min(), "→", df.index.max(), "| Rows:", len(df))
    print("Columns:", list(df.columns))
    print("Metrics actually used:", used_metrics)

if __name__ == "__main__":
    main()
