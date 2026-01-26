# Component Overview

Purpose: Execute bi-directional arbitrage loops for multiple configurable trading pairs across supported venues.

**Primary mode**: Multi-chain DEX aggregators (e.g., OKX)  
**Fallback mode**: Native DEX-to-DEX (only when no aggregators enabled)

Target stack: TypeScript (prod), parity with Python behavior (reference).

## Core Components

### Orchestrator (`src/orchestrator/`)
- Runs 1s loop; iterates over discovered trading pairs
- Fetches prices on both venues (same-chain or cross-chain)
- Computes forward/backward profitability
- Delegates to RiskManager for execution gating
- Selects at most one execution plan per tick
- Executes plan; handles reconciliation and fund cycling

### PriceMonitor (`src/price_monitor/`)
- Fetches prices for a given trading pair (base/quote) on DEX J (chain M) and DEX K (chain N)
- Delegates to `DexQuoteProvider` registry keyed by `(chainId, dexKey)`
- Never talks to concrete adapters directly
- Prefers API/SDK; supports fallback/sanity checks

### DEX Adapters (`src/dex/`)
- One adapter instance per (chain, dexKey): `UniswapV3Service`, `PancakeswapV3Service`, `VelodromeV2Service`, `OKXService`, etc.
- Adapters registered in `DexModule` via `DEX_*` tokens
- `DexQuoteProvider` registry uses these to resolve correct adapter for each `(chainId, dexKey)`
- **Multi-chain aggregators** (e.g., OKX) serve as primary venue providers across chains
- Native DEX adapters (Uniswap, PancakeSwap) used as fallback when no aggregators enabled
- Responsibilities:
  - Quoting: `estimateBuyQuoteToBase`, `estimateSellBaseToQuote`
  - Swapping: `swapQuoteToBase`, `swapBaseToQuote`
  - Balance queries: `getBalanceBase`, `getBalanceQuote`
- All operations respect slippage caps

### Bridge Adapter (`src/bridge/`)
- Estimate fees; bridge TokenA and USDT
- Poll settlement; provide transferId/status
- Primary implementation: Stargate

### RiskManager (`src/risk_control/`)
- Enforces thresholds (≥1.8%), total fee rate subtraction
- Stop-loss, slippage caps, position caps at global and per-pair levels
- Decides forward/backward eligibility for each pair
- Respects global stop-loss and exposure limits

### Utils
- **wallet**: Key management, RPC providers/signers per chain, nonce/gas handling
- **logger**: Structured logs + metrics hooks (JSON, opId support)
- **config**: Typed config loader, schema validation, env merge helper

## Configuration Structure

- `config.yaml`: Source of truth for runtime config
- Global token lists (`tokens.base`, `tokens.quote`)
- Per-chain inventory (`chains[chainId].tokenList`, `chains[chainId].dexList`, `chains[chainId].nonAggr`)
- `aggregatorMultichain`: Primary driver for pair discovery; when any aggregator enabled, native DEX discovery is disabled
- Bridge, risk, fees, ops, logging, wallets sections
- No static trading pairs - pairs are discovered at startup

## Data Flow

1. **Startup**: Config → PairDiscovery → `TradingPairConfig[]` (in-memory)
   - Aggregator mode: Use `aggregatorMultichain` keys as venue providers
   - Native DEX mode: Use `chains.*.dexList` (only when no aggregators enabled)
2. **Each tick** (1s): Orchestrator → PriceMonitor → Dual venue prices
3. **Evaluation**: Forward/backward profit calculation → RiskManager gating
4. **Execution**: If plan selected → Venue M → Bridge → Venue N → Reconciliation
5. **Logging**: Structured JSON logs with correlation IDs (opId) throughout

## Key Design Principles

- **Deterministic**: Same config always yields same discovery output
- **Fail-fast**: Configuration errors surface at startup, not during loop
- **Modular**: Components communicate via interfaces; easy to add new DEX/bridge/chain
- **Testable**: All adapters and logic have unit tests with mocks
