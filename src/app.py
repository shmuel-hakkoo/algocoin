# src/app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from data_connector import DataConnector

st.set_page_config(layout="wide")

st.title("Crypto Data Visualization")
st.write("Displaying klines and sentiment data from ClickHouse.")

@st.cache_data
def load_data(start_date, end_date):
    """Load data from ClickHouse using the DataConnector."""
    connector = DataConnector()
    klines_spec = {
        "exchange": "BINANCE",
        "symbol": "BTCUSDT",
        "timeframe": "1m",
    }
    klines_df = connector.load_klines("CLICKHOUSE", klines_spec, start=start_date, end=end_date)
    sentiment_df = connector.load_sentiment(start=start_date, end=end_date)
    return klines_df, sentiment_df

# Date range selector
start_date = st.date_input("Start date", datetime(2025, 3, 1).date())
end_date = st.date_input("End date", datetime(2025, 3, 31).date())

if start_date > end_date:
    st.error("Error: End date must fall after start date.")
else:
    # Load data
    klines_df, sentiment_df = load_data(
        datetime.combine(start_date, datetime.min.time()),
        datetime.combine(end_date, datetime.max.time())
    )

    if klines_df.empty and sentiment_df.empty:
        st.warning("No data available for the selected date range.")
    else:
        # Display raw data
        st.subheader("Raw Klines Data")
        st.dataframe(klines_df.head())

        st.subheader("Raw Sentiment Data")
        st.dataframe(sentiment_df.head())

        # Candlestick chart for klines
        st.subheader("Klines Candlestick Chart")
        fig_klines = go.Figure(data=[go.Candlestick(
            x=klines_df.index,
            open=klines_df['open'],
            high=klines_df['high'],
            low=klines_df['low'],
            close=klines_df['close']
        )])
        fig_klines.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_klines, use_container_width=True)

        # Sentiment balance chart
        st.subheader("Sentiment Balance Over Time")
        sentiment_cols = [col for col in sentiment_df.columns if 'sentiment_balance' in col]
        fig_sentiment = go.Figure()
        for col in sentiment_cols:
            fig_sentiment.add_trace(go.Scatter(x=sentiment_df.index, y=sentiment_df[col], mode='lines', name=col))
        st.plotly_chart(fig_sentiment, use_container_width=True)

        # Social volume chart
        st.subheader("Social Volume Over Time")
        volume_cols = [col for col in sentiment_df.columns if 'social_volume' in col]
        fig_volume = go.Figure()
        for col in volume_cols:
            fig_volume.add_trace(go.Bar(x=sentiment_df.index, y=sentiment_df[col], name=col))
        fig_volume.update_layout(barmode='stack')
        st.plotly_chart(fig_volume, use_container_width=True)
