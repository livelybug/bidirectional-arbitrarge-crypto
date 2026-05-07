# Pair Discovery Algorithm

Converts global token lists and per-chain inventories into arbitrageable routes.

**Primary mode**: Multi-chain DEX aggregator arbitrage (e.g., OKX)  
**Optional supplemental config**: Standalone native DEX venues may still be configured.

## Concept

Three data structures drive discovery:

- **symbolPair**: `{base, quote}` - Token combination (e.g., WIF/USDT)
- **swapPair**: `{base, quote, dex, chain}` - Venue for trading a pair (`dex` may be an aggregator key)
- **arbitrargePair**: Ties two venues for same `(base, quote)` → becomes `TradingPairConfig`

## Multi-Chain Aggregator Discovery Flow (Primary)

`aggregatorMultichain` is mandatory and must have at least one enabled aggregator (for example OKX). That enabled aggregator set is the source of swap-pair generation. Standalone native DEX entries in `chains.*.dexList` are optional adapter advertisements and are not currently used to generate discovered routes.

### 1. Enumerate Symbol Pairs

From `config.tokens.base` and `config.tokens.quote`, build the cartesian product of base×quote symbols.

**Example**:
```yaml
tokens:
  base:
    - WIF
    - PEPE
  quote:
    - USDT
    - USDC
```

**Result**:
```
symbolPairs = [
  { base: WIF,  quote: USDT },
  { base: WIF,  quote: USDC },
  { base: PEPE, quote: USDT },
  { base: PEPE, quote: USDC },
]
```

**Determinism**: Iterate base and quote arrays in sorted order.

### 2. Enumerate Aggregator Keys

Let `aggKeys = sorted(Object.keys(config.aggregatorMultichain).filter(k => config.aggregatorMultichain[k].enabled))`

Each aggregator key (e.g., `okx`) represents an available venue provider across multiple chains.

**Example**:
```yaml
aggregatorMultichain:
  okx:
    enabled: true
```

**Result**: `aggKeys = ['okx']`

### 3. Generate Swap Pairs Per Chain/Aggregator

For each `symbolPair = { base, quote }` and for each `chainId` in sorted `Object.keys(config.chains)`:

- Check `chains[chainId].tokenList` for both `base` and `quote` symbols
- Check `chains[chainId].nonAggr` to skip excluded aggregators (optional)
- If both tokens exist, for each `aggrKey` in `aggKeys` create a `swapPair`:

```
swapPair = {
  swapPairId: `${base}~${quote}~${aggrKey}~${chainId}`,
  base,
  quote,
  dex: aggrKey,           // Aggregator key stored in dex field
  chain: chainId,
}
```

**Example** (WIF/USDT with OKX on Arbitrum and Base):
```
swapPairs = [
  { swapPairId: 'WIF~USDT~okx~arbitrum', base: 'WIF', quote: 'USDT', dex: 'okx', chain: 'arbitrum' },
  { swapPairId: 'WIF~USDT~okx~base',     base: 'WIF', quote: 'USDT', dex: 'okx', chain: 'base' },
]
```

### 4. Derive Arbitrage Pairs

For each ordered pair of `swapPair1`, `swapPair2` in `swapPairs` where:

- `swapPair1.base === swapPair2.base` and `swapPair1.quote === swapPair2.quote`
- **Self-pairing allowed** (same `swapPairId` / same venue): aggregator may route to different underlying pools, creating price gaps

Create:

```
arbitrargePair = {
  arbitrargePairId:
    `${base}~${quote}~${swapPair1.dex}+${swapPair1.chain}~${swapPair2.dex}+${swapPair2.chain}`,
  swapPair1,
  swapPair2,
}
```

**Same-chain and cross-chain routes both allowed**:
- Same-chain: `swapPair1.chain === swapPair2.chain` (aggregator keys equal)
- Cross-chain: `swapPair1.chain !== swapPair2.chain`

**Example**:
```
arbitrargePair = {
  arbitrargePairId: 'WIF~USDT~okx+arbitrum~okx+base',
  swapPair1: { base: 'WIF', quote: 'USDT', dex: 'okx', chain: 'arbitrum' },
  swapPair2: { base: 'WIF', quote: 'USDT', dex: 'okx', chain: 'base' },
}
```

**Pair ID Format**: `base~quote~dexJ+chainM~dexK+chainN`
- `base`: Base token symbol (e.g., WIF)
- `quote`: Quote token symbol (e.g., USDT)
- `dexJ`: DEX/aggregator key for entry venue (e.g., okx)
- `chainM`: Chain ID for entry venue (e.g., arbitrum)
- `dexK`: DEX/aggregator key for exit venue (e.g., okx)
- `chainN`: Chain ID for exit venue (e.g., base)

### 5. Deterministic Ordering

Sort `arbitrargePairs` by:

```
(baseToken ASC, quoteToken ASC, chainM ASC, chainN ASC, dexJ ASC, dexK ASC)
```

**Order**: `baseToken → quoteToken → chainM → chainN → dexJ → dexK`

### 6. Aggregator Configuration

Enable aggregators in `config.yaml`:

```yaml
aggregatorMultichain:
  okx:
    enabled: true
```

Set credentials in `.env` (required for OKX):

```dotenv
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_API_PASSPHRASE=your_passphrase
OKX_PROJECT_ID=your_project_id
```

**Per-chain exclusion** (optional):
```yaml
chains:
  arbitrum:
    nonAggr: ['okx']  # Exclude OKX on this chain
```

See [Adding Aggregators](adding-dex.md) for integration details.

---

## Standalone Native DEX Config (Optional)

Standalone native DEX entries in `chains.*.dexList` are optional. They may be used by native DEX adapters, but they are not a startup prerequisite and are not currently included in discovered routes.

### 1. Enumerate Symbol Pairs

Build Cartesian product from global config:

```yaml
# config.yaml
tokens:
  base: [WIF, PEPE]
  quote: [USDT, USDC]
```

```javascript
const symbolPairs = [];
for (const base of sorted(config.tokens.base)) {
  for (const quote of sorted(config.tokens.quote)) {
    symbolPairs.push({ base, quote });
  }
}
// Result: WIF/USDT, WIF/USDC, PEPE/USDT, PEPE/USDC
```

### 2. Reference Native DEX Swap-Pair Logic

If native DEX route generation is ever re-enabled, the standalone native venue logic would look like this:

```javascript
const swapPairs = [];

for (const chainId of sorted(Object.keys(config.chains))) {
  const chain = config.chains[chainId];

  for (const symbolPair of symbolPairs) {
    const hasBase = chain.tokenList.some(t => t.symbol === symbolPair.base);
    const hasQuote = chain.tokenList.some(t => t.symbol === symbolPair.quote);

    if (hasBase && hasQuote) {
      for (const dex of chain.dexList ?? []) {
        swapPairs.push({
          swapPairId: `${symbolPair.base}~${symbolPair.quote}~${dex.key}~${chainId}`,
          base: symbolPair.base,
          quote: symbolPair.quote,
          dex: dex.key,
          chain: chainId,
        });
      }
    }
  }
}
```

**Example** (WIF/USDT on Arbitrum):
```
swapPairs = [
  { swapPairId: 'WIF~USDT~uniswap_v3~arbitrum', base: 'WIF', quote: 'USDT', dex: 'uniswap_v3', chain: 'arbitrum' },
  { swapPairId: 'WIF~USDT~camelot_v3~arbitrum', base: 'WIF', quote: 'USDT', dex: 'camelot_v3', chain: 'arbitrum' },
]
```

### 3. Derive Arbitrage Pairs

Pair venues supporting same `(base, quote)`:

```javascript
const arbitrargePairs = [];

for (let i = 0; i < swapPairs.length; i++) {
  for (let j = i + 1; j < swapPairs.length; j++) {
    const swapPair1 = swapPairs[i];
    const swapPair2 = swapPairs[j];

    // Must be same base/quote pair
    if (swapPair1.base !== swapPair2.base || swapPair1.quote !== swapPair2.quote) {
      continue;
    }

    // Avoid self-pairing (different venues)
    if (swapPair1.swapPairId === swapPair2.swapPairId) {
      continue;
    }

    arbitrargePairs.push({
      arbitrargePairId: `${swapPair1.base}~${swapPair1.quote}~${swapPair1.dex}+${swapPair1.chain}~${swapPair2.dex}+${swapPair2.chain}`,
      swapPair1,
      swapPair2,
    });
  }
}
```

**Same-chain DEX→DEX**: `chainM === chainN` but `dexJ !== dexK`
**Cross-chain**: `chainM !== chainN` (DEX keys may be equal or different)

### 4. Deterministic Sorting

Ensure same config always yields same output:

```javascript
arbitrargePairs.sort((a, b) => {
  const byBase = a.baseToken.localeCompare(b.baseToken);
  if (byBase !== 0) return byBase;

  const byQuote = a.quoteToken.localeCompare(b.quoteToken);
  if (byQuote !== 0) return byQuote;

  const byChainM = a.chainM.localeCompare(b.chainM);
  if (byChainM !== 0) return byChainM;

  const byChainN = a.chainN.localeCompare(b.chainN);
  if (byChainN !== 0) return byChainN;

  const byDexJ = a.dexJ.localeCompare(b.dexJ);
  if (byDexJ !== 0) return byDexJ;

  return a.dexK.localeCompare(b.dexK);
});
```

**Order**: `baseToken → quoteToken → chainM → chainN → dexJ → dexK`

## Fast-Fail Rules

Discovery throws on startup if:

| Rule | Error | Fix |
|-------|--------|------|
| **Fast-fail A** | Token in `tokens.*` never appears in any `chains.*.tokenList` | Add token to at least one chain's `tokenList` or remove from `tokens.*` |
| **Fast-fail B** | No `swapPairs` discovered | Ensure at least one chain has both tokens in `tokenList` and at least one enabled aggregator can serve that pair; standalone `dexList` entries are optional supplemental venues |
| **Fast-fail C** | No `arbitrargePairs` discovered | Ensure at least two venues support the same `(base, quote)` pair |
| **Fast-fail D** | Aggregator enabled but missing credentials | Add required env vars (e.g., `OKX_API_KEY`, `OKX_SECRET_KEY`, `OKX_API_PASSPHRASE`, `OKX_PROJECT_ID`) |
| **Unsupported DEX** | DEX key in optional `dexList` but no adapter exists | Add adapter or remove DEX key from config |

## Output

In-memory `TradingPairConfig[]` array:

```typescript
export interface TradingPairConfig {
  id: string;         // Format: `base~quote~dexJ+chainM~dexK+chainN`
  baseToken: string;   // e.g., WIF
  quoteToken: string;  // e.g., USDT
  chainM: string;      // e.g., arbitrum
  dexJ: string;        // e.g., uniswap_v3
  chainN: string;      // e.g., base
  dexK: string;        // e.g., uniswap_v3
}
```

**Aggregator mode example**:
```
[
  { id: 'WIF~USDT~okx+arbitrum~okx+base', baseToken: 'WIF', quoteToken: 'USDT', chainM: 'arbitrum', dexJ: 'okx', chainN: 'base', dexK: 'okx' },
  { id: 'PEPE~USDT~okx+arbitrum~okx+base', baseToken: 'PEPE', quoteToken: 'USDT', chainM: 'arbitrum', dexJ: 'okx', chainN: 'base', dexK: 'okx' },
]
```

**Standalone native DEX reference example**:
```
[
  { id: 'WIF~USDT~uniswap_v3+arbitrum~uniswap_v3+base', baseToken: 'WIF', quoteToken: 'USDT', chainM: 'arbitrum', dexJ: 'uniswap_v3', chainN: 'base', dexK: 'uniswap_v3' },
  { id: 'PEPE~USDT~uniswap_v3+arbitrum~uniswap_v3+base', baseToken: 'PEPE', quoteToken: 'USDT', chainM: 'arbitrum', dexJ: 'uniswap_v3', chainN: 'base', dexK: 'uniswap_v3' },
]
```

## Implementation

**File**: `src/orchestrator/pair-discovery/pair-discovery.service.ts`

**Service Method**: `getAllPairs(): TradingPairConfig[]`

**Called by**:
- Orchestrator at startup (`onModuleInit`)
- Tests (directly accessing in-memory array)

**Logging**: On success, logs structured summary:

```json
{
  "level": "info",
  "msg": "Pair discovery complete",
  "data": {
    "uniqueBaseSymbols": 2,
    "uniqueQuoteSymbols": 1,
    "chainsScanned": 2,
    "arbitrargePairs": 2,
    "swapPairs": 4,
    "symbolPairsEvaluated": 2,
    "baseTokens": ["WIF", "PEPE"],
    "quoteTokens": ["USDT"],
    "chains": ["arbitrum", "base"],
    "dexKeys": ["uniswap_v3"],
    "pairIdsSample": ["WIF~USDT~uniswap_v3+arbitrum~uniswap_v3+base"]
  }
}
```

## Aggregator Implementation

For details on adding new aggregators, see [Adding a DEX](adding-dex.md).
