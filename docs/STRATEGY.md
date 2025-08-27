
- add more lead leg indicators
- add a 'movimento de lado' filter, so we know that 80% of the time we are out
- so we use all of ours indicators, for the positive signal and negative
- get more macro indicators,


* https://www.coinglass.com/BitcoinOpenInterest
* https://www.coinglass.com/exchanges
* https://www.coinglass.com/LiquidationData
* https://www.coinglass.com/CryptoApi
* https://www.coinglass.com/whale-alert
* https://www.coinglass.com/bitcoin-etf



## CMC Fear / Greed

** Charts **

* https://coinmarketcap.com/charts/fear-and-greed-index/#fear-and-greed-index-faq
* https://www.augmento.ai/bitcoin-sentiment/
* https://milkroad.com/fear-greed/

Observe rate of change and stationary values

* high volatility represents a change on trend
* high levels sustain an uptrend
* low levels sustain a downtrend




---

## 1. Core Inputs

1. **News & Macro Events**

   * Track announcements from the Fed, SEC, ETFs, global regulation, BTC halving cycles.
   * Flag "market-moving" events (ETF approvals, major exchange hacks, halving date approaches).
   * Scoring:

     * **Bullish = +1** (ETF inflows, adoption news, halving)
     * **Bearish = -1** (bans, exchange collapse, hacks)

2. **Fundamentals (On-chain & macro)**

   * On-chain: active addresses, miner flows, exchange inflows/outflows, hash rate.
   * Macro: USD strength, inflation numbers.
   * Simple check:

     * More coins leaving exchanges = bullish.
     * More coins entering exchanges = bearish.

3. **Price Action (TA)**

   * Use a **trend filter**: 50-day vs 200-day moving average.

     * Above 200D MA = only look for longs.
     * Below 200D MA = only look for shorts/hedges.
   * Momentum: RSI / MACD for entry timing.

4. **Investor Sentiment**

   * Use **Crypto Fear & Greed Index (FGI)**.

     * Extreme Fear (<25) = contrarian long.
     * Extreme Greed (>75) = caution / take profit.
   * Also track funding rates (if perpetual swaps overheated).

---

## 2. Strategy Logic (Example)

* **Step 1: Trend filter** → Only trade in direction of major trend (200D MA).
* **Step 2: Sentiment overlay** → Extreme readings trigger entry/exit zones.
* **Step 3: News/Fundamental catalyst** → Confirm bias.
* **Step 4: Entry** → Use price action (breakout or retest with RSI confirmation).
* **Step 5: Risk management**

  * 1–2% of portfolio per trade.
  * Stop-loss under last swing low (long) or above swing high (short).
  * Take profit at 2R (2x risk).

---

## 3. Example Scenarios

1. **ETF inflows strong + BTC above 200D MA + Fear Index = 30 (fear but recovering)**
   → Enter long after breakout.
   → Hold until FGI > 70 or RSI overheated.

2. **Regulation ban + BTC under 200D MA + Greed Index = 80**
   → Avoid longs, maybe short if breakdown confirmed.

---

## 4. Tools & Implementation

* **News**: Twitter (X), CoinDesk, CoinTelegraph, Santiment alerts.
* **Fundamentals**: Glassnode, CryptoQuant (exchange flows).
* **Price action**: TradingView with MAs, RSI, MACD.
* **Sentiment**: CMC Fear & Greed, Alternative.me.

---


