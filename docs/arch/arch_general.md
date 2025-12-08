# Solution Architecture: Cross-Chain Bi-Directional Arbitrage Bot (v1.0)

## 1. Overview
- Purpose: Execute bi-directional cross-chain arbitrage loops for TokenA/USDT across two DEX/chain venues.
- Target stack: TypeScript (prod), parity with Python behavior (reference).
- Core domains: price monitoring, DEX execution, cross-chain bridging, risk control, wallets, logging/metrics.

## 2. Components & Responsibilities
- Orchestrator (src/main.ts)
  - Runs 1s loop; fetches dual prices; computes forward/backward profitability; delegates to RiskManager; executes plan; handles reconciliation and fund cycling.
- PriceMonitor (src/price_monitor.ts)
  - Fetches TokenA/USDT prices from DEX J (chain M) and DEX K (chain N). Prefers API/SDK; supports fallback/sanity checks.
- DEX Adapters (src/dex/)
  - uniswap_v3.ts, velodrome.ts: Quote and execute swaps (USDT↔TokenA) with slippage caps; balance queries.
- Bridge Adapter (src/bridge/stargate.ts)
  - Estimate fees; bridge TokenA and USDT; poll settlement; provide transferId/status.
- RiskManager (src/risk_control.ts)
  - Enforce thresholds (≥1.8%), total fee rate subtraction, stop-loss, slippage caps, and position caps; decide forward/backward eligibility.
- Utils
  - wallet.ts: Key management, RPC providers/signers per chain, nonce/gas handling.
  - logger.ts: Structured logs + metrics hooks.
- Config (config.yaml)
  - Chains, RPCs, tokens, DEX/bridge params, thresholds, fee model, caps, loop interval.
- Logs (/logs)
  - Execution traces, errors, bridge settlements, reconciliation summaries.

## 3. Interfaces (TypeScript, indicative)
```ts
// Types
export type ChainId = 'arbitrum' | 'base' | 'optimism' | 'ethereum' | 'bsc' | 'polygon';
export type Direction = 'forward' | 'backward';

export interface Prices {
  priceM: number; // TokenA per USDT on chain M (DEX J)
  priceN: number; // TokenA per USDT on chain N (DEX K)
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

export interface ExecutionPlan {
  direction: Direction;
  amountUSDT: string;               // entry-chain spend (post-cap)
  bridgeBackPct: number;            // e.g., 0.90–0.95
  gasReservePctOfProfit: number;    // e.g., 0.03
  slippageBps: number;              // per swap max slippage
}

export interface PriceMonitor {
  getPrice(chain: ChainId, tokenA: string, stable: string): Promise<number>;
}

export interface DexAdapter {
  readonly chain: ChainId;
  estimateBuyUsdtToToken(amountUSDT: string, tokenA: string, stable: string, slippageBps: number): Promise<{ outToken: string; price: number }>;
  estimateSellTokenToUsdt(amountToken: string, tokenA: string, stable: string, slippageBps: number): Promise<{ outUSDT: string; price: number }>;
  swapUsdtToToken(amountUSDT: string, tokenA: string, slippageBps: number): Promise<{ txHash: string }>;
  swapTokenToUsdt(amountToken: string, tokenA: string, slippageBps: number): Promise<{ txHash: string }>;
  getBalanceUSDT(): Promise<string>;
  getBalanceToken(tokenA: string): Promise<string>;
}

export interface BridgeAdapter {
  estimateBridgeToken(token: string, amount: string, from: ChainId, to: ChainId): Promise<{ feeUSD: number }>;
  bridgeToken(token: string, amount: string, from: ChainId, to: ChainId): Promise<{ txHash: string; transferId: string }>;
  waitForSettlement(transferId: string, to: ChainId, timeoutMs: number): Promise<{ settled: boolean; finalAmount: string }>;
}

export interface RiskManager {
  shouldExecute(direction: Direction, prices: Prices, fee: FeeModel, minProfitRateBps: number, ctx: { balances: Record<ChainId, { usdt: string; tokenA: string }> }): { ok: boolean; plan?: ExecutionPlan; reason?: string };
  checkSlippage(quotedBps: number, maxBps: number): boolean;
  checkStopLoss(totalPnLPct: number, stopLossPct: number): boolean;
}
```

## 4. Config Schema (config.yaml, indicative)
```yaml
chains:
  arbitrum:
    rpc: ${ARBITRUM_RPC}
    usdt: "0x..."
    tokenA: "0x..."        # per run or list
    dex: uniswap_v3
  base:
    rpc: ${BASE_RPC}
    usdt: "0x..."
    tokenA: "0x..."
    dex: uniswap_v3
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

## 5. Key Sequences

### 5.1. Price loop (1s cadence)
- Participants: Orchestrator → PriceMonitor → RiskManager → (maybe execute)
- Steps:
  1. Orchestrator concurrently fetches priceM (chain M/DEX J) and priceN (chain N/DEX K).
  2. Compute:
     - forward = (priceN / priceM − 1) − totalFeeRate
     - backward = (priceM / priceN − 1) − totalFeeRate
  3. RiskManager.shouldExecute(...) returns ok + execution plan (direction, amountUSDT, slippage, bridgeBackPct).
  4. If ok: proceed to Execute sequence; else sleep(loopIntervalMs).

### 5.2. Execute: Forward arbitrage (M → N)
- Participants: Orchestrator, Dex M, Bridge, Dex N, Wallet, Logger
- Steps:
  1. Determine amountUSDT per plan (full-amount or capped).
  2. Dex M: swap USDT→TokenA with slippageBps; wait for tx confirmation; record txHash.
  3. Bridge: bridge TokenA M→N; get transferId; waitForSettlement until settled.
  4. Dex N: swap TokenA→USDT (all or plan-specific); confirm tx.
  5. Profit realization:
     - Compute profitUSDT = (USDT on N after sell) − (amountUSDT entry + est. fees).
     - Reserve gas: retain gasReservePctOfProfit locally on N.
     - Bridge back bridgeBackPct of USDT to M; leave remainder (5%–10%) on N.
  6. Reconcile balances; log end-to-end metrics.

- Backward arbitrage mirrors chains/DEXes.

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
