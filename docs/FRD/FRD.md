# Functional Requirement Document: Cross-Chain Bi-Directional Arbitrage Bot (v1.0)

## 1. Introduction

### 1.1. Product Overview
The Cross-Chain Bi-Directional Arbitrage Bot is an automated trading system designed to capitalize on price discrepancies of specific crypto assets across different decentralized exchanges (DEXs) on various blockchain networks. It performs bi-directional arbitrage by monitoring prices, calculating potential profits, and executing trades when profitable opportunities are identified, while incorporating risk management features.
- The arbitrage loop executes on a 1-second cadence to capture near real-time price discrepancies.

## 2. Functional Requirements

### 2.1. Core Arbitrage Logic

#### 2.1.1. Price Monitoring
- The system must continuously monitor and fetch the prices of specified token pairs (e.g., `TokenA/USDT`, `TokenB/USDT`, `TokenA/USDC`, `TokenB/USDC`) from configured trade venues. The primary venue model is multi-chain aggregators (for example OKX via `aggregatorMultichain`). Standalone native DEX venues remain optional and secondary.
- The set of token pairs and arbitrage routes must be derived from configuration rather than hard-coded, using:
    - A global list of base tokens (e.g., meme tokens like WIF, PEPE, BRETT),
    - A global list of quote tokens (e.g., USDT, USDC), and
    - Per-chain availability for those tokens, plus optional standalone DEX listings when native DEX venues are enabled.
- Price monitoring must remain near real-time to preserve opportunity detection accuracy, with a 1-second loop cadence by default (configurable).
- `aggregatorMultichain` must remain the mandatory primary venue model, with optional native DEX support as a secondary route source.
- Route discovery for this requirement is specified in [Core Sequences](../architecture/sequences.md).

#### 2.1.2. Profit Calculation
- The system must calculate the potential profit for both forward and backward arbitrage loops.
- **Forward Arbitrage (DEX J to DEX K):**
  - `profit_forward (%) = (price_K / price_J - 1) * 100 - Cross_Chain_Fees`
- **Backward Arbitrage (DEX K to DEX J):**
  - `profit_backward (%) = (price_J / price_K - 1) * 100 - Cross_Chain_Fees`
- Profit calculations must subtract the configured total fee rate (see 2.1.3) before threshold comparison.

#### 2.1.3. Fee Calculation
- The system must account for all associated transaction costs when calculating profitability. The total estimated cross-chain fees are between **1.2% and 1.8%**.
- This includes:
    - **DEX Transaction Fees:** 0.05% - 0.3% per trade (total of 2 trades for a round trip).
    - **Cross-Chain Bridge Fees:**
        - Stargate: 1-2 USDT
        - Hop / Synapse: 0.3% - 0.5%
    - **Gas Fees:** Approximately 0.3-0.6 USDT for transactions on Arbitrum and Base.
- A configurable “total fee rate” parameter must be used in profit calculations. Recommended effective threshold range: 1.2%–1.8%.

#### 2.1.4. Trade Execution
- The system shall trigger an arbitrage trade only if the calculated profit margin meets or exceeds a predefined threshold.
- **Execution Threshold:** `profit_forward` or `profit_backward` >= **1.8%**.
- The execution sequence for forward arbitrage (M -> N) must include entry, bridging, exit, and capital return in that order; detailed flow is defined in [Core Sequences](../architecture/sequences.md#execute-forward-arbitrage-m--n).
- Execution amount:
    - Default: use the chain’s current available USDT, subject to configured caps.
    - Configurable caps:
        - Optional single-transaction cap (% of total funds).
        - Optional maximum total exposure cap (% of total funds).
    - Post-trade fund cycling:
        - Bridge back 90%–95% of USDT to the originating chain to maintain bilateral balance.
        - Retain 5%–10% locally as realized profit.
    - Gas reserve: retain 3% of each trade’s profit on the destination chain as gas buffer for subsequent operations.

### 2.2. Supported Platforms

- Each supported chain (e.g., Arbitrum, Base, Ethereum, Polygon) participates in the mandatory multi-chain aggregator venue set and may also host optional standalone DEX adapters (e.g., Uniswap V3, Camelot V3, Velodrome V2, QuickSwap, SushiSwap).
- Arbitrage routes are defined as ordered pairs of venues `(Chain 1 (M), DEX J) → (Chain 2 (N), DEX K)`, where `Chain 1` and `Chain 2` may be the same or different. In the current aggregator-first design, `DEX J` / `DEX K` are typically aggregator keys such as `okx`.

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
- Position sizing must support full-amount execution mode. When enabled:
    - The bot may use all available USDT on the entry chain, subject to optional configurable caps:
        - **Single Transaction Cap (optional):** e.g., 5%–100% of total funds.
        - **Maximum Exposure Cap (optional):** e.g., 90%–100% of total funds.

#### 2.4.3. Slippage Control
- The system must allow for a configurable maximum slippage percentage for each DEX trade.
- The default maximum slippage for a single transaction is capped at **3%**. If a trade is predicted to exceed this, it should not be executed.
- Default slippage for swaps should also include a reserve (e.g., 1%) for execution safety within quotes.

#### 2.4.4. Operational Reserves
- The system must retain **3%** of realized profit per cycle on the destination chain for future gas needs.
- The system must log and reconcile bridge fees and final settled balances post-bridge to ensure accurate PnL.

## 3. System Architecture & Implementation

### 3.1. High-Level Structure
- The system will be developed in TypeScript, converting the logic from an existing Python simulation.
- The project will be structured into modular components as outlined below.
- Reference implementation exists in Python; TypeScript is the target production language. Behavioral parity with the Python logic is required.
- NestJS module composition remains code-defined, but DEX adapter provider instantiation and collection exposure are configuration-driven at startup.
- The PriceMonitor quote registry must be built from the active adapter collection exposed by DexModule.

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
- Respect API rate limits; prefer DEX quote APIs over scraping. Implement batching and concurrency control where applicable.

### 4.2. Reliability
- The bot should run continuously with high availability. It must handle network errors and API failures gracefully, with appropriate retry mechanisms.
- Add retries and backoff for bridge operations; detect and log bridge settlement completion before PnL attribution.

### 4.3. Security
- Private keys and sensitive API keys must be stored securely and not exposed in the codebase.

### 4.4. Logging
- The bot must produce detailed logs for all major events, including:
    - Price checks and identified opportunities.
    - Executed trades (buys, sells, bridges).
    - Errors and exceptions.
    - Risk management triggers (e.g., stop-loss activation).
    - Include bridge initiation/completion, amounts bridged back (90%–95%), and retained gas reserve (3% of profit).
