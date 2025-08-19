* [bias-codex](https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Cognitive_bias_codex_en.svg/2560px-Cognitive_bias_codex_en.svg.png)

---

## ❌ Why “3 years backtest → live trading” is wrong

1. **Overfitting risk**

   * If you optimize parameters on 3 years of data, you are tuning your model to past *noise* and idiosyncrasies.
   * Markets are non-stationary: what worked in 2021 may break in 2022 because volatility regimes, liquidity, microstructure, and even exchange mechanics change.

2. **False confidence**

   * A beautiful equity curve on 3 years can be just curve-fitting.
   * Without out-of-sample testing, you don’t know if your strategy has predictive power or if you just mined lucky patterns.

3. **No robustness across regimes**

   * In 3 years you may have missed important environments (bull run, crash, sideways chop, low/high volatility).
   * A single contiguous test period might not expose you to enough market states.

4. **Look-ahead bias**

   * By fitting once on a long dataset and then looking at results, you are implicitly peeking into the future (because parameters are optimized using the *whole* history).

---

## ✅ The correct way: Window-based testing (Walk-Forward / Rolling windows)

Instead of **train once → test once**, you use **multiple training and testing windows**:

1. **Split data into rolling windows**

   * Example: Train (optimize parameters) on 1 year of data, then test on the *next* 3 months.
   * Slide forward by 3 months and repeat.
   * This simulates the real-world process of re-optimizing periodically.

2. **Generate multiple sets of parameters**

   * Each window produces its own best parameters.
   * This prevents a single “perfect-fit” parameter set from fooling you.
   * You can analyze parameter stability: do the same ranges keep showing up, or does the system require constant retuning?

3. **Forward performance evaluation**

   * Each out-of-sample test (the “future” unseen data) shows how the strategy would have performed if deployed then.
   * Combining them gives you a **realistic picture of live robustness**.

4. **Parameter robustness testing**

   * Instead of just taking the single “best” parameter, test neighborhoods around it.
   * If performance collapses when parameters shift slightly, it’s likely curve-fit.

5. **Market regime sensitivity**

   * Walk-forward testing naturally covers different volatility and liquidity conditions.
   * You’ll learn whether the strategy survives regime shifts or needs adaptive logic.

---

## 🔑 Bottom Line

* **3-year backtest only** = fooling yourself with hindsight + curve fit.
* **Window-based testing (walk-forward / rolling validation)** = closest simulation of real-life trading, exposes overfitting, tests robustness, and shows if parameters generalize.

This is why top quant firms never trust a single static backtest. They demand **walk-forward validation** across multiple windows before risking live capital.

---

