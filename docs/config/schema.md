# Configuration Schema Validation

Zod-based validation rules for `config.yaml` and `.env` overrides.

## Schema Structure

### Granular Schemas

**tokensConfigSchema**
```typescript
z.object({
  base: z.array(z.string().min(1)).min(1),
  quote: z.array(z.string().min(1)).min(1),
})
```
- `base`: Non-empty array of non-empty strings (WIF, PEPE, etc.)
- `quote`: Non-empty array of non-empty strings (USDT, USDC)

**chainConfigSchema**
```typescript
z.object({
  rpc: z.string().min(1),
  tokenList: z.array(z.object({
    symbol: z.string().min(1),
    address: z.string().regex(/^0x/),
  })),
  dexList: z.array(z.object({
    key: z.string().min(1),
    type: z.string().min(1),
  })).optional(),
  nonAggr: z.array(z.string()).optional(), // Aggregator exclusion list
})
```
- `rpc`: Non-empty string (RPC endpoint URL)
- `tokenList`: Array of `{symbol, address}` where address starts with `0x`
- `dexList`: Optional array of `{key, type}` for native DEXes. Aggregator-first mode does not require it.
- `nonAggr`: Optional array of aggregator keys to exclude on this chain (e.g., `['okx']`)

**chainsConfigSchema**
```typescript
z.record(z.enum(ChainIds), chainConfigSchema)
```
- Keys must be valid `ChainId`: arbitrum, base, optimism, ethereum, polygon, bsc

**bridgeStargateSchema**
```typescript
z.object({
  router: z.string().regex(/^0x/),
  lzEndpoint: z.string().regex(/^0x/),
})
```
- Both fields must be valid hex addresses starting with `0x`

**bridgeConfigSchema**
```typescript
z.object({
  provider: z.literal('stargate'),
  stargate: bridgeStargateSchema,
})
```
- Currently only supports `stargate` provider
- **To add a new bridge**: Modify `bridgeConfigSchema` to include the new bridge type (see [Adding a Bridge](../implementation/adding-bridge.md) for complete steps)

**positionCapsSchema**
```typescript
z.object({
  fullAmountMode: z.boolean().default(true),
  singleTxCapPct: z.number().min(0).max(1).default(1.0),
  maxExposurePct: z.number().min(0).max(1).default(0.95),
})
```
- `fullAmountMode`: Default true
- `singleTxCapPct`: 0–1 (0–100%), default 1.0 (no cap)
- `maxExposurePct`: 0–1, default 0.95 (95%); must be ≥ `singleTxCapPct`

**riskConfigSchema**
```typescript
z.object({
  minProfitRateBps: z.number().int().min(120).max(10000),
  stopLossPct: z.number().min(0).max(0.5),
  slippageBps: z.number().int().min(0).max(1000),
  positionCaps: positionCapsSchema,
})
```
- `minProfitRateBps`: 120–10000 (1.2%–100%)
- `stopLossPct`: 0–0.5 (0–50%)
- `slippageBps`: 0–1000 (0–10%)

**feesConfigSchema**
```typescript
z.object({
  dexFeeBpsPerSwap: z.number().int().min(0).max(300),
  bridgeFlatUSD: z.number().min(0),
  bridgePctBps: z.number().int().min(0).max(1000),
  gasUSD: z.number().min(0),
  slippageReserveBps: z.number().int().min(0).max(1000),
  totalFeeRateBps: z.number().int().min(0).max(5000).refine(
    (val, ctx) => (val >= (ctx.data.dexFeeBpsPerSwap * 2) ?
      val :
      { message: 'totalFeeRateBps must be ≥ 2 * dexFeeBpsPerSwap (2 swaps per arbitrage)' }),
  ),
})
```
- `dexFeeBpsPerSwap`: 0–300 (0–3%)
- `bridgeFlatUSD`: ≥0 (USD flat fee)
- `bridgePctBps`: 0–1000 (0–10%)
- `gasUSD`: ≥0 (estimated gas cost)
- `slippageReserveBps`: 0–1000 (0–10%)
- `totalFeeRateBps`: 0–5000; must be ≥ 2× `dexFeeBpsPerSwap` (accounting for 2 swaps per arbitrage: buy on venue M, sell on venue N)

**opsConfigSchema**
```typescript
z.object({
  loopIntervalMs: z.number().int().min(1).max(60000),
  bridgeBackPct: z.number().min(0).max(1),
  gasReservePctOfProfit: z.number().min(0).max(1),
})
```
- `loopIntervalMs`: 1–60000 (1ms–60s), default 1000
- `bridgeBackPct`: 0–1, default 0.92 (92%)
- `gasReservePctOfProfit`: 0–1, default 0.03 (3%)

**loggingConfigSchema**
```typescript
z.object({
  level: z.enum(['debug', 'info', 'warn', 'error']),
  json: z.boolean(),
})
```
- `level`: One of debug/info/warn/error
- `json`: Boolean flag for structured output

**walletsConfigSchema**
```typescript
z.object({
  keystorePath: z.string().min(1),
  address: z.string().regex(/^0x[a-fA-F0-9]{40}$/),
})
```
- `keystorePath`: Non-empty path to encrypted keystore
- `address`: Valid EVM address (42 hex chars starting with `0x`)

### Root Schema

**appConfigSchema**
```typescript
z.object({
  tokens: tokensConfigSchema,
  chains: chainsConfigSchema,
  aggregatorMultichain: aggregatorMultichainSchema,
  bridge: bridgeConfigSchema,
  risk: riskConfigSchema,
  fees: feesConfigSchema,
  ops: opsConfigSchema,
  logging: loggingConfigSchema,
  wallets: walletsConfigSchema,
}).superRefine(/* cross-field: at least one aggregator must be enabled */)
```

**Cross-field rules:**

| Rule | Requirement |
|---|---|
| `aggregatorMultichain` presence | **required** |
| `aggregatorMultichain` size | must define **at least one** aggregator |
| `aggregatorMultichain` enablement | must have **at least one** `enabled: true` aggregator |
| `chains.*.dexList` | optional |

This is enforced via `aggregatorMultichainSchema` plus `appConfigSchema.superRefine`. Violating the enablement rule produces a Zod error at path `aggregatorMultichain`.

## Environment Variable Preprocessing

For env overrides (e.g., `MIN_PROFIT_RATE_BPS`, `LOOP_INTERVAL_MS`):

```typescript
const numericPreprocessor = (v: unknown) => {
  if (typeof v === 'string') {
    const num = Number(v);
    if (Number.isFinite(num)) return num;
  }
  return v;
};

z.preprocess(numericPreprocessor, z.number().int().min(0))
```

## Validation Behavior

### Startup Fail-Fast

On validation failure:
- `ConfigService` throws Zod error
- Nest bootstrap does NOT catch-and-continue
- Process exits with clear error message and stack
- No partial configs allowed

### Error Messages

Zod errors provide:
- Path to invalid field (e.g., `risk.minProfitRateBps`)
- Expected type and constraints
- Actual received value
- Human-readable message

## Type Safety

Export inferred type:
```typescript
export type AppConfig = z.infer<typeof appConfigSchema>;
```

Optional compile-time check to sync with `config.types.ts`:
```typescript
type _ConfigCheck = AssertEqual<AppConfig, ConfigFromTypes>;
```

## Implementation Location

File: `src/utils/config/config.schema.ts`
Co-located with: `config.types.ts`

Usage in `ConfigService`:
```typescript
import { appConfigSchema } from './config.schema';
import { AppConfig } from './config.types';

export class ConfigService {
  parseConfig(raw: unknown): AppConfig {
    return appConfigSchema.parse(raw);  // Throws on validation error
  }
}
```
