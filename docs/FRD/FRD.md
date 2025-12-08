# Functional Requirement Document: Cross-Chain Bi-Directional Arbitrage Bot (v1.0)

## 1. Introduction

### 1.1. Product Overview
The Cross-Chain Bi-Directional Arbitrage Bot is an automated trading system designed to capitalize on price discrepancies of specific crypto assets across different decentralized exchanges (DEXs) on various blockchain networks. It performs bi-directional arbitrage by monitoring prices, calculating potential profits, and executing trades when profitable opportunities are identified, while incorporating risk management features.

## 2. Functional Requirements

### 2.1. Core Arbitrage Logic

#### 2.1.1. Price Monitoring
- The system must continuously monitor and fetch the prices of specified token pairs (`TokenA/USDT`) from two different DEXs (DEX J and DEX K) on their respective blockchains.
- Price fetching should be near real-time to ensure accuracy.

#### 2.1.2. Profit Calculation
- The system must calculate the potential profit for both forward and backward arbitrage loops.
- **Forward Arbitrage (DEX J to DEX K):**
  - `profit_forward (%) = (price_K / price_J - 1) * 100 - Cross_Chain_Fees`
- **Backward Arbitrage (DEX K to DEX J):**
  - `profit_backward (%) = (price_J / price_K - 1) * 100 - Cross_Chain_Fees`

#### 2.1.3. Fee Calculation
- The system must account for all associated transaction costs when calculating profitability. The total estimated cross-chain fees are between **1.2% and 1.8%**.
- This includes:
    - **DEX Transaction Fees:** 0.05% - 0.3% per trade (total of 2 trades for a round trip).
    - **Cross-Chain Bridge Fees:**
        - Stargate: 1-2 USDT
        - Hop / Synapse: 0.3% - 0.5%
    - **Gas Fees:** Approximately 0.3-0.6 USDT for transactions on Arbitrum and Base.

#### 2.1.4. Trade Execution
- The system shall trigger an arbitrage trade only if the calculated profit margin meets or exceeds a predefined threshold.
- **Execution Threshold:** `profit_forward` or `profit_backward` >= **1.8%**.
- The execution process for a forward arbitrage (M -> N) is as follows:
    1. Buy Token A with USDT on DEX J.
    2. Bridge Token A from its native chain to the chain of DEX K.
    3. Sell Token A for USDT on DEX K.
    4. Bridge USDT back to the original chain.

### 2.2. Supported Platforms

| Chain 1 (M) | DEX J          | Chain 2 (N) | DEX K          | Cross-Chain Bridge      | Status      |
|-------------|----------------|-------------|----------------|-------------------------|-------------|
| Arbitrum    | Uniswap V3     | Base        | Uniswap V3     | Stargate / LayerZero    | Supported   |
| Arbitrum    | Camelot V3     | Optimism    | Velodrome V2   | Hop / Synapse           | To be added |
| Ethereum    | Uniswap V3     | Polygon     | QuickSwap      | Stargate                | Supported   |
| BSC         | PancakeSwap V3 | Arbitrum    | SushiSwap      | Multichain / Celer      | To be added |

### 2.3. Supported Assets

#### 2.3.1. Meme Tokens (Token A)
- The bot must support arbitrage trading for the following meme tokens:
    - WIF (dogwifhat)
    - PEPE
    - BRETT
    - MOG
    - APU

#### 2.3.2. Stablecoins
- The bot will use USDT as the primary stablecoin for quoting and trading.
- USDC support may be added in future versions.

### 2.4. Risk Management

#### 2.4.1. Stop-Loss
- The system must implement a global stop-loss mechanism.
- If the total loss of all positions reaches a configurable threshold of **15% - 30%** of the initial capital, the bot must cease all trading activities and alert the user.

#### 2.4.2. Position Sizing
- **Single Transaction Limit:** The value of any single arbitrage trade must not exceed **5% - 10%** of the total available funds.
- **Maximum Position Limit:** The total value of all open positions at any given time must not exceed **90% - 95%** of the total funds.

#### 2.4.3. Slippage Control
- The system must allow for a configurable maximum slippage percentage for each DEX trade.
- The default maximum slippage for a single transaction is capped at **3%**. If a trade is predicted to exceed this, it should not be executed.

## 3. System Architecture & Implementation

### 3.1. High-Level Structure
- The system will be developed in TypeScript, converting the logic from an existing Python simulation.
- The project will be structured into modular components as outlined below.

### 3.2. Project File Structure
```
cross_chain_arb/
├── config.yaml                 # Configuration file for chains, tokens, API keys, etc.
├── wallets/                    # Directory for wallet private keys
├── src/
│   ├── main.ts                 # Main entry point for the arbitrage bot
│   ├── dex/
│   │   ├── uniswap_v3.ts       # Uniswap V3 interaction logic
│   │   └── velodrome.ts        # Velodrome interaction logic
│   ├── bridge/
│   │   └── stargate.ts         # Stargate bridge interaction logic
│   ├── price_monitor.ts        # Price fetching and monitoring module
│   ├── risk_control.ts         # Risk management logic
│   └── utils/
│       ├── wallet.ts
│       └── logger.ts
├── logs/
└── package.json
```

## 4. Non-Functional Requirements

### 4.1. Performance
- The bot must be able to fetch prices and execute trades with minimal latency to effectively capture arbitrage opportunities.

### 4.2. Reliability
- The bot should run continuously with high availability. It must handle network errors and API failures gracefully, with appropriate retry mechanisms.

### 4.3. Security
- Private keys and sensitive API keys must be stored securely and not exposed in the codebase.

### 4.4. Logging
- The bot must produce detailed logs for all major events, including:
    - Price checks and identified opportunities.
    - Executed trades (buys, sells, bridges).
    - Errors and exceptions.
    - Risk management triggers (e.g., stop-loss activation).
