# Solution Architecture: Cross-Chain Bi-Directional Arbitrage Bot (v1.0)

## 1. Overview
- Purpose: Execute bi-directional arbitrage loops for multiple configurable trading pairs (e.g., TokenA/USDT, TokenB/USDT, TokenA/USDC, TokenB/USDC) across supported DEX/chain venues.
- Target stack: TypeScript (prod), parity with Python behavior (reference).
- Core domains: price monitoring, DEX execution, cross-chain bridging, risk control, wallets, logging/metrics.

## 2. Components & Responsibilities
-- Orchestrator (src/main.ts)
  - Runs 1s loop; iterates over all configured trading pairs and their associated route (chainM, dexJ) → (chainN, dexK); for each pair, fetches prices on both venues (same-chain or cross-chain), computes forward/backward profitability, delegates to RiskManager; chooses at most one execution plan per tick; executes the plan; handles reconciliation and fund cycling.
- PriceMonitor (src/price_monitor.ts)
  - Fetches prices for a given trading pair (base/quote) on its configured DEX J (chain M) and DEX K (chain N). DEX J and DEX K may be on the same chain (same-chain DEX-to-DEX arbitrage) or different chains (cross-chain arbitrage). Prefers API/SDK; supports fallback/sanity checks.
- DEX Adapters (src/dex/)
  - One adapter instance per (chain, dexKey), e.g. uniswap_v3 on Arbitrum, uniswap_v3 on Base, quickswap on Polygon, etc. Responsible for quoting and executing swaps (quote↔base) with slippage caps and balance queries.
- Bridge Adapter (src/bridge/stargate.ts)
  - Estimate fees; bridge TokenA and USDT; poll settlement; provide transferId/status.
-- RiskManager (src/risk_control.ts)
  - Enforce thresholds (≥1.8%), total fee rate subtraction, stop-loss, slippage caps, and position caps at both global and per-pair levels; decide forward/backward eligibility for each pair; respect global stop-loss and exposure limits across all pairs.
- Utils
  - wallet.ts: Key management, RPC providers/signers per chain, nonce/gas handling.
  - logger.ts: Structured logs + metrics hooks.
- Config (config.yaml)
  - Global lists of supported base tokens and quote tokens.
  - Chains (RPCs, tokenList, dexList), DEX/bridge params, thresholds, fee model, caps, loop interval.
  - No static trading pair list is stored in config; trading pairs and routes are discovered dynamically at startup from the global base/quote lists plus per-chain token/DEX inventory.
- Logs (/logs)
  - Execution traces, errors, bridge settlements, reconciliation summaries.

## 3. Interfaces (TypeScript, indicative)
```ts
chains:
  arbitrum:
    rpc: ${ARBITRUM_RPC}
    tokenList:
      - symbol: USDT
        address: "0x..."
      - symbol: WIF
        address: "0x..."
    dexList:
      - key: uniswap_v3
        type: uniswap_v3
      - key: camelot_v3
        type: generic_v3
  base:
    rpc: ${BASE_RPC}
    tokenList:
      - symbol: USDT
        address: "0x..."
      - symbol: WIF
        address: "0x..."
    dexList:
      - key: uniswap_v3
        type: uniswap_v3
  ethereum:
    rpc: ${ETHEREUM_RPC}
    tokenList:
      - symbol: USDC
        address: "0x..."
      - symbol: PEPE
        address: "0x..."
    dexList:
      - key: uniswap_v3
        type: uniswap_v3
  polygon:
    rpc: ${POLYGON_RPC}
    tokenList:
      - symbol: USDC
        address: "0x..."
      - symbol: PEPE
        address: "0x..."
    dexList:
      - key: quickswap
        type: generic_v2

export interface ChainDexConfig {
  key: string;         // e.g., 'uniswap_v3', 'quickswap', 'velodrome_v2'
  type: 'uniswap_v3' | 'velodrome_v2' | 'generic_v2' | 'generic_v3';
}

export interface ChainConfig {
  rpc: string;
  tokenList: ChainTokenConfig[]; // available tokens on this chain
  dexList: ChainDexConfig[];     // available DEXes on this chain
}

export type ChainsConfig = Record<ChainId, ChainConfig>;

export interface Prices {
  priceM: number; // base per quote on chain M (DEX J)
  priceN: number; // base per quote on chain N (DEX K)
}

export interface FeeModel {
  dexFeeBpsPerSwap: number;         // e.g., 5–30 bps
  bridgeFlatUSD?: number;           // e.g., 1–2 USDT
  bridgePctBps?: number;            // e.g., 30–50 bps (Hop/Synapse)
  gasUSD?: number;                  // e.g., 0.3–0.6
  slippageReserveBps?: number;      // e.g., 30–50 bps
  totalFeeRateBps: number;          // e.g., 120–180 bps (used in profit calc)
}

export interface PositionCaps {
  singleTxCapPct?: number;          // e.g., 0.05–1.0 of total funds
  maxExposurePct?: number;          // e.g., 0.90–1.0 of total funds
  fullAmountMode?: boolean;         // default true
}

export interface TradingPairConfig {
  id: PairId;
  baseToken: TokenSymbol;           // e.g., 'WIF', 'PEPE'
  quoteToken: StableSymbol;         // 'USDT' or 'USDC'
  chainM: ChainId;                  // entry chain (DEX J)
  dexJ: string;                     // key from chains[chainM].dexList
  chainN: ChainId;                  // exit chain (DEX K)
  dexK: string;                     // key from chains[chainN].dexList
  // Optional per-pair overrides (fall back to global risk/fees/ops)
  minProfitRateBps?: number;
  slippageBps?: number;
  positionCaps?: PositionCaps;
}

export interface PairRuntimeState {
  balances: Record<ChainId, { base: string; quote: string }>;
  pnlPct?: number;
  paused?: boolean;
}

export interface ExecutionPlan {
  direction: Direction;
  pairId: PairId;                   // which trading pair this plan is for
  amountQuote: string;              // entry-chain spend in quote (e.g. USDT/USDC) post-cap
  bridgeBackPct: number;            // e.g., 0.90–0.95
  gasReservePctOfProfit: number;    // e.g., 0.03
  slippageBps: number;              // per swap max slippage
}

export interface PriceMonitor {
  // Fetch price for a specific pair on one side (M or N), or both at once.
  getPairPrices(pair: TradingPairConfig): Promise<Prices>;
}

export interface DexAdapter {
  readonly chain: ChainId;
  estimateBuyQuoteToBase(amountQuote: string, baseToken: string, quoteToken: string, slippageBps: number): Promise<{ outBase: string; price: number }>;
  estimateSellBaseToQuote(amountBase: string, baseToken: string, quoteToken: string, slippageBps: number): Promise<{ outQuote: string; price: number }>;
  swapQuoteToBase(amountQuote: string, baseToken: string, quoteToken: string, slippageBps: number): Promise<{ txHash: string }>;
  swapBaseToQuote(amountBase: string, baseToken: string, quoteToken: string, slippageBps: number): Promise<{ txHash: string }>;
  getBalanceQuote(quoteToken: string): Promise<string>;
  getBalanceBase(baseToken: string): Promise<string>;
}

export interface BridgeAdapter {
  estimateBridgeToken(token: string, amount: string, from: ChainId, to: ChainId): Promise<{ feeUSD: number }>;
  bridgeToken(token: string, amount: string, from: ChainId, to: ChainId): Promise<{ txHash: string; transferId: string }>;
  waitForSettlement(transferId: string, to: ChainId, timeoutMs: number): Promise<{ settled: boolean; finalAmount: string }>;
}

export interface RiskManager {
  shouldExecute(
    pair: TradingPairConfig,
    direction: Direction,
    prices: Prices,
    fee: FeeModel,
    minProfitRateBps: number,
    ctx: {
      pairState: PairRuntimeState;
      globalState: { totalPnLPct: number; paused: boolean };
    },
  ): { ok: boolean; plan?: ExecutionPlan; reason?: string };
  checkSlippage(quotedBps: number, maxBps: number): boolean;
  checkStopLoss(totalPnLPct: number, stopLossPct: number): boolean;
}
```

## 4. Config Schema (config.yaml, indicative)
```yaml
tokens:
  base:
    - WIF
    - PEPE
  quote:
    - USDT
    - USDC

chains:
  arbitrum:
    rpc: ${ARBITRUM_RPC}
    tokenList:
      - symbol: USDT
        address: "0x..."
      - symbol: WIF
        address: "0x..."
    dexList:
      - key: uniswap_v3
        type: uniswap_v3
      - key: camelot_v3
        type: generic_v3
  base:
    rpc: ${BASE_RPC}
    tokenList:
      - symbol: USDT
        address: "0x..."
      - symbol: WIF
        address: "0x..."
    dexList:
      - key: uniswap_v3
        type: uniswap_v3
  ethereum:
    rpc: ${ETHEREUM_RPC}
    tokenList:
      - symbol: USDC
        address: "0x..."
      - symbol: PEPE
        address: "0x..."
    dexList:
      - key: uniswap_v3
        type: uniswap_v3
  polygon:
    rpc: ${POLYGON_RPC}
    tokenList:
      - symbol: USDC
        address: "0x..."
      - symbol: PEPE
        address: "0x..."
    dexList:
      - key: quickswap
        type: generic_v2
bridge:
  provider: stargate
  stargate:
    router: "0x..."
    lzEndpoint: "0x..."
risk:
  minProfitRateBps: 180
  stopLossPct: 0.20
  slippageBps: 300
  positionCaps:
    fullAmountMode: true
    singleTxCapPct: 1.0    # 100% = cap disabled effect in full-amount mode
    maxExposurePct: 0.95
fees:
  dexFeeBpsPerSwap: 30
  bridgeFlatUSD: 1.5
  gasUSD: 0.6
  slippageReserveBps: 50
  totalFeeRateBps: 180
ops:
  loopIntervalMs: 1000
  bridgeBackPct: 0.92
  gasReservePctOfProfit: 0.03
logging:
  level: info
  json: true
wallets:
  keystorePath: ./wallets/...
  address: "0x..."
  # private key loading via env/keystore only
```

### Fail-Fast Defaults
- Bootstrapping enforces sane defaults by throwing when critical config slices are missing. `OrchestratorService` requires at least one base token, one quote token, and a minimum of two chains, with the first two chains each exposing at least one `dexList` entry. Any violation aborts startup before the loop begins.
- Each concrete DEX adapter (for example `UniswapV3Service` and `VelodromeV2Service`) resolves its target chain by scanning `chains.*.dexList` for its `dexKey`. If no chain advertises the key—or if `chains` is empty—the adapter throws instead of silently defaulting to a placeholder chain like `arbitrum`.
- `config.yaml` must therefore continue to list every DEX key for which an adapter exists and keep the token arrays populated. This configuration drift immediately in both runtime bootstrapping and the config unit tests.

## 5. Key Sequences

### 5.1. Price loop (1s cadence, dynamic multi-pair discovery)
- Participants: Orchestrator → ConfigService → PriceMonitor → RiskManager → (maybe execute)
- Steps:
  1. At startup, Orchestrator (or a dedicated discovery component) asks ConfigService for:
     - Global base token list and quote token list.
     - Per-chain `tokenList` and `dexList`.
     - It then:
       - Computes the Cartesian product of `base × quote` into candidate token pairs.
       - For each token pair, scans all chains/DEXes to find venues where both tokens exist and the DEX is listed in `dexList`.
       - For any token pair that appears on fewer than 2 venues, drops it (no arbitrage possible).
       - For remaining token pairs, builds `TradingPairConfig`+route entries `(chainM, dexJ) → (chainN, dexK)` across same-chain and cross-chain combinations.
       - Applies any deterministic sorting (e.g., `baseToken`, then `quoteToken`, then `(chainM,dexJ,chainN,dexK)`) for reproducible ordering.
       - If any global base/quote token is not present on at least one chain’s `tokenList`, fails fast with a clear config error.
  2. On each tick (every `ops.loopIntervalMs`, default 1000ms), Orchestrator iterates over the in-memory list of discovered `TradingPairConfig`+route entries (evaluated sequentially within the tick):
     - For each pair `p`, Orchestrator calls `PriceMonitor.getPairPrices(p)` to concurrently fetch priceM (chainM/dexJ) and priceN (chainN/dexK).
     - Compute candidate profitability for `p`:
       - forward = (priceN / priceM − 1) − totalFeeRate
       - backward = (priceM / priceN − 1) − totalFeeRate
     - Build an effective `FeeModel` and risk parameters for `p` from global config (`risk`, `fees`, `ops`) (per-pair overrides can be added in a later version if needed).
     - Construct a per-pair runtime context (`PairRuntimeState` and global PnL/paused flags).
     - Call `RiskManager.shouldExecute(p, direction, prices, feeModel, effectiveMinProfitRateBps, ctx)` for each direction and collect any returned `ExecutionPlan`s.
  3. From all candidate plans produced in this tick, Orchestrator selects at most one plan to execute (e.g., the highest expected profit that passes all risk checks) to simplify concurrency and exposure management.
  4. If a plan is selected: proceed to the Execute sequence for that pair; else sleep until the next tick.

### 5.2. Execute: Forward arbitrage (M → N, per pair)
- Participants: Orchestrator, Dex M, Bridge, Dex N, Wallet, Logger
- Steps (for a selected `ExecutionPlan` and its `TradingPairConfig`):
  1. Determine `amountQuote` per plan (full-amount or capped) in the quote token of the pair (USDT or USDC).
  2. Dex M (on `pair.chainM` / `pair.dexJ`): swap quote→base with `slippageBps`; wait for tx confirmation; record txHash.
  3. Bridge: bridge the base token from chain M to chain N via BridgeAdapter; get transferId; waitForSettlement until settled.
  4. Dex N (on `pair.chainN` / `pair.dexK`): swap base→quote (all or plan-specific); confirm tx.
  5. Profit realization:
     - Compute profit in quote units = (quote on N after sell) − (amountQuote entry + est. fees).
     - Reserve gas: retain `gasReservePctOfProfit` locally on N.
     - Bridge back `bridgeBackPct` of quote to M; leave remainder (5%–10%) on N as realized profit and local liquidity.
  6. Update per-pair and global PnL; reconcile balances; log end-to-end metrics including `pair.id` and direction.

- Backward arbitrage mirrors chains/DEXes for the same `TradingPairConfig` (swap/bridge/swap in reverse order).

### 5.3. Bridge settlement & reconciliation
- Poll settlement status by transferId with bounded retries/backoff.
- On timeout: mark pending, skip sell step; resume/repair in next loop via reconciliation job.
- Always log:
  - start_ts/end_ts, transferId, from/to, token, amount_in/out, feeUSD, settled flag.

### 5.4. Stop-loss & pause
- Maintain rolling PnL vs initial capital.
- If loss ≥ stopLossPct: set global “paused=true”, stop new executions, alert.

## 6. Error Handling, Retries, Circuit-Breakers
- Retries: Exponential backoff with jitter (e.g., base 250ms, max 5s, 5 attempts) for:
  - Price fetch, DEX quote/tx submit, bridge estimate/submit/settlement polling.
- Timeouts: Per external call (e.g., 5–10s for quotes; 60–900s for settlement).
- Circuit-breakers per adapter:
  - Open after consecutive failures (e.g., 5), half-open test after cooldown.
- Idempotency:
  - Tag operations with opId; persist in-memory ledger/log to avoid duplicate actions on retries.
- Fallbacks:
  - If price API fails, skip cycle; do not execute with stale data.
  - If bridge delayed, reconcile asynchronously.

## 7. Observability (Logging & Metrics)
- Structured logs (JSON):
  - price_sample, profit_estimates, decision(reason,plan), dex_swap(submit/confirm), bridge(init/settle), sell, pnl, reserves, caps_applied, errors.
- Metrics (optional):
  - loop_latency_ms, price_fetch_ms, swap_latency_ms, bridge_settlement_sec, execs_count, success_rate, avg_profit_bps, gas_reserve_total.
- Correlation IDs:
  - opId across the full cycle, include tx hashes and transferId.

## 8. Security
- Secrets: Load from env/keystore; never hardcode. Support encrypted keystore files in ./wallets.
- RPC/API keys: env-injected; scoped least privileges.
- Address allowlists per chain; sanity-check token addresses.
- Transaction simulation (where available) before execution.
- Optional: Alerting on unusual slippage, bridge delays, or large position usage.

## 9. Performance Considerations
- Concurrency: Parallel price fetches; serialize per-cycle execution to avoid balance races.
- Rate limits: Respect provider quotas; add token bucket for DEX/bridge APIs.
- Gas: Dynamic estimation; preflight “gas affordability” checks; auto-reserve 3% profit for gas.
- Latency budgets:
  - price fetch <300ms/chain; swap confirmation configurable; bridge settlement tracked asynchronously.

## 10. Deployment & Environments
- Config-driven: No code changes across envs.
- Packaging: Node runtime; optional container with minimal base image.
- Run modes:
  - Dry-run/simulate: execute quotes only, no on-chain tx.
  - Live: full execution.
- Health checks: Loop heartbeat logs; optional /status endpoint (future).

## 11. Risks & Mitigations
- Slippage/MEV: Use conservative slippage caps; simulate routes; consider private tx relays.
- Bridge risk: Prefer reliable providers; monitor status; pause on anomalies.
- Liquidity risk: Pre-check pool liquidity/price impact; cap amounts dynamically.
- Market risk: Enforce minProfitRate; stop-loss; pause on volatility spikes.
- Infra risk: Redundant RPCs; automatic failover; exponential backoff.

## 12. Module-to-FRD Traceability
- 1s loop → Orchestrator + PriceMonitor (Sections 2.1.1, 4.1).
- Profit calc with total fee rate → RiskManager (2.1.2–2.1.3).
- Execution threshold ≥1.8% → RiskManager gating (2.1.4).
- Full-amount execution + caps → RiskManager + Orchestrator (2.4.2).
- Bridge back 90–95%, retain 3% gas → Orchestrator (execution plan).
- Stop-loss, slippage ≤3% → RiskManager (2.4.1–2.4.3).
- Logging & settlement reconciliation → Logger + BridgeAdapter (4.4, 4.2).

## 13. Open Decisions (to confirm)
- Exact DEX price source priority (pool reads vs. quote APIs vs. TWAP).
- Bridge settlement SLA thresholds per route.
- PnL attribution timing (on sell vs. after bridge-back).
