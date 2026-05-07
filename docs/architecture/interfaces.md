# TypeScript Interfaces

Core type definitions for the arbitrage system.

## Core Types

```typescript
export type PairId = string;  // Format: `${baseToken}~${quoteToken}~${dexJ}+${chainM}~${dexK}+${chainN}`
export type Direction = 'forward' | 'backward';
export type ChainId = 'arbitrum' | 'base' | 'optimism' | 'ethereum' | 'polygon' | 'bsc' | 'monad';
```

## Trading Pair Configuration

```typescript
export interface TradingPairConfig {
  id: PairId;                    // Deterministic route identifier
  baseToken: string;              // e.g., 'WIF', 'PEPE'
  quoteToken: string;             // e.g., 'USDT', 'USDC'
  chainM: ChainId;                // Entry chain (DEX J)
  dexJ: string;                   // Venue key for M (typically aggregator key such as 'okx'; standalone DEX keys optional)
  chainN: ChainId;                // Exit chain (DEX K)
  dexK: string;                   // Venue key for N (typically aggregator key such as 'okx'; standalone DEX keys optional)
  minProfitRateBps?: number;      // Per-pair profit threshold override
  slippageBps?: number;           // Per-pair slippage cap override
  positionCaps?: Partial<PositionCaps>;  // Per-pair position cap override
}
```

## Price & Execution Data

```typescript
export interface Prices {
  priceM: number;  // Price on venue M (base per quote)
  priceN: number;  // Price on venue N (base per quote)
}

export interface ExecutionPlan {
  direction: Direction;
  pairId: PairId;
  amountQuote: string;              // Entry-chain spend in quote token
  bridgeBackPct: number;           // 0.90–0.95, fraction to bridge back
  gasReservePctOfProfit: number;  // e.g., 0.03 (3%)
  slippageBps: number;              // Per swap max slippage
}
```

## Fee & Risk Models

```typescript
export interface FeeModel {
  dexFeeBpsPerSwap: number;       // 5–30 bps per swap
  bridgeFlatUSD?: number;           // 1–2 USDT flat fee
  bridgePctBps?: number;          // 30–50 bps (Hop/Synapse)
  gasUSD?: number;                  // 0.3–0.6 USDT gas
  slippageReserveBps?: number;      // 30–50 bps reserve
  totalFeeRateBps: number;          // 120–180 bps (used in profit calc)
}

export interface PositionCaps {
  singleTxCapPct?: number;   // 0.05–1.0 (5–100% of total funds)
  maxExposurePct?: number;    // 0.90–1.0 (90–100% of total funds)
  fullAmountMode?: boolean;      // Default true
}
```

## Runtime State

```typescript
export interface PairRuntimeState {
  balances: Record<ChainId, { base: string; quote: string }>;
  pnlPct?: number;
  paused?: boolean;
}

export interface GlobalRuntimeState {
  totalPnLPct: number;
  paused: boolean;
}
```

## Adapter Interfaces

### DEX Adapter
```typescript
export interface DexAdapter {
  readonly chain: ChainId;
  estimateBuyQuoteToBase(
    amountQuote: string,
    baseToken: string,
    quoteToken: string,
    slippageBps: number,
  ): Promise<{ outBase: string; price: number }>;
  estimateSellBaseToQuote(
    amountBase: string,
    baseToken: string,
    quoteToken: string,
    slippageBps: number,
  ): Promise<{ outQuote: string; price: number }>;
  swapQuoteToBase(
    amountQuote: string,
    baseToken: string,
    quoteToken: string,
    slippageBps: number,
  ): Promise<{ txHash: string }>;
  swapBaseToQuote(
    amountBase: string,
    baseToken: string,
    quoteToken: string,
    slippageBps: number,
  ): Promise<{ txHash: string }>;
  getBalanceQuote(quoteToken: string): Promise<string>;
  getBalanceBase(baseToken: string): Promise<string>;
}
```

### Bridge Adapter
```typescript
export interface BridgeAdapter {
  estimateBridgeToken(
    token: string,
    amount: string,
    from: ChainId,
    to: ChainId,
  ): Promise<{ feeUSD: number }>;
  bridgeToken(
    token: string,
    amount: string,
    from: ChainId,
    to: ChainId,
  ): Promise<{ txHash: string; transferId: string }>;
  waitForSettlement(
    transferId: string,
    to: ChainId,
    timeoutMs: number,
  ): Promise<{ settled: boolean; finalAmount: string }>;
}
```

### Price Monitor
```typescript
export interface PriceMonitor {
  getPairPrices(pair: TradingPairConfig): Promise<Prices>;
}
```

### Risk Manager
```typescript
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

## Quote Provider (Registry)
```typescript
export interface DexQuoteRequest {
  chainId: ChainId;
  dexKey: string;        // e.g., 'uniswap_v3', 'pancakeswap_v3'
  baseToken: string;
  quoteToken: string;
}

export interface DexQuoteProvider {
  getQuote(request: DexQuoteRequest): Promise<number>;
}
```

All interfaces defined in `src/common/types.ts` and referenced across all modules.
