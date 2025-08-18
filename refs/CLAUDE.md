# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is an algorithmic trading repository built on top of NautilusTrader, focusing on cryptocurrency and financial markets trading strategies. The codebase contains backtesting examples, live trading implementations, and comprehensive documentation for various trading strategies and market integrations.

## Development Commands

### Environment Setup
```bash
# Install UV package manager first (prerequisite)
# https://docs.astral.sh/uv/#installation

# Activate virtual environment (if using home directory setup)
make activate

# Install NautilusTrader package
make install-nautilus

# Run Jupyter environment in Docker
make jupyter
```

### Core Dependencies
- **NautilusTrader**: Main trading framework (`nautilus_trader`)
- **UV**: Python package manager for dependency management
- **Python 3.x**: Primary development language

## Architecture

### Core Framework Structure (NautilusTrader)
The repository is built on NautilusTrader's event-driven architecture with these key components:

- **NautilusKernel**: Central orchestration system managing all components
- **MessageBus**: Pub/Sub messaging backbone for inter-component communication
- **DataEngine**: Processes and routes market data (quotes, trades, bars, order books)
- **ExecutionEngine**: Manages order lifecycle and execution routing
- **RiskEngine**: Provides pre-trade risk checks and position monitoring
- **Cache**: High-performance in-memory storage for instruments, orders, positions

### Environment Contexts
- **Backtest**: Historical data with simulated venues
- **Sandbox**: Real-time data with simulated venues  
- **Live**: Real-time data with live venues (paper/real trading)

### Design Patterns
- Domain Driven Design (DDD)
- Event-driven architecture
- Messaging patterns (Pub/Sub, Req/Rep)
- Ports and adapters (Hexagonal architecture)
- Single-threaded design for optimal performance

## Repository Structure

### `/backtest/` - Backtesting Examples
Contains various backtesting strategies and examples:
- EMA crossover strategies for crypto (ETHUSDT, BTCUSDT)
- FX trading strategies (AUDUSD, GBPUSD)
- Market maker implementations
- Integration examples with Binance, Databento, Betfair

### `/live/` - Live Trading Implementations
Live trading examples organized by exchange:
- `binance/`: Binance Futures and Spot trading
- `bybit/`, `bitmex/`, `okx/`: Other crypto exchanges
- `interactive_brokers/`: Traditional market connectivity
- `databento/`: Professional market data integration

### `/concepts/` - Documentation
Core concept documentation covering:
- Architecture, actors, adapters, strategies
- Data handling, execution, portfolio management
- Message bus, caching, logging systems

### `/tutorials/` - Learning Resources
Jupyter notebooks and tutorials for:
- Backtesting with orderbook data
- Data catalog usage and external data loading
- Databento integration examples

## Common Development Workflows

### Running Backtests
Backtest files are executable Python scripts. Navigate to `/backtest/` and run:
```bash
python crypto_ema_cross_with_binance_provider.py
python fx_ema_cross_audusd_bars_from_ticks.py
```

### Strategy Development
1. Examine existing strategies in `/backtest/` for patterns
2. Use NautilusTrader's strategy base classes
3. Implement `on_start()`, `on_data()`, `on_stop()` methods
4. Test with backtesting before live deployment

### Data Integration
- Use instrument providers for exchange-specific data
- Leverage data wranglers for format conversion
- Implement custom data clients for new sources

## Key Patterns to Follow

### Strategy Implementation
- Inherit from NautilusTrader strategy classes
- Use proper typing with NautilusTrader model objects
- Implement event-driven handlers (on_bar, on_quote_tick, etc.)
- Follow finite state machine patterns for component lifecycle

### Configuration Management
- Use NautilusTrader's config classes for strategy parameters
- Environment-specific configurations for backtest vs live
- Proper instrument and venue configuration

### Risk Management
- Implement position sizing and risk limits
- Use stop-loss and take-profit mechanisms
- Pre-trade risk validation through RiskEngine

## Trading Strategy Examples

The repository includes comprehensive examples for:
- **EMA Cross**: Trend-following strategies with exponential moving averages
- **Market Making**: Liquidity provision strategies
- **Bracket Orders**: Advanced order management with stops and targets
- **Trail Stops**: Dynamic stop-loss management
- **Multi-asset**: Cross-instrument trading strategies