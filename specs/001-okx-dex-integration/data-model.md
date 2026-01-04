# Data Model: OKX DEX Integration

**Feature**: 001-okx-dex-integration
**Phase**: Phase 1 - Design & Contracts
**Date**: 2026-01-02

## Overview

This document defines the data entities and their relationships for integrating OKX DEX as a multi-chain aggregator. The design extends existing types without breaking changes, following the Open/Closed Principle.

---

## Core Entities

### 1. Aggregator Swap Pair

Represents a trading venue for a token pair on a specific chain via an aggregator.

**Type**: `AggregatorSwapPair`

```typescript
interface AggregatorSwapPair {
    // Unique identifier
    swapPairId: string;           // Format: "{base}~{quote}~{aggregator}~{chainId}"
                                   // Example: "WIF~USDT~okx~arbitrum"

    // Token pair
    base: string;                  // Token symbol (e.g., "WIF")
    quote: string;                 // Token symbol (e.g., "USDT")

    // Venue identification
    aggregator: string;            // Aggregator key (e.g., "okx")
    chain: ChainId;                // Chain ID (e.g., "arbitrum", "base")

    // Token addresses (chain-specific)
    baseTokenAddress: string;      // ERC-20 contract address or zero address for native
    quoteTokenAddress: string;     // ERC-20 contract address or zero address for native

    // Metadata
    decimals: number;              // Token decimals (for amount conversion)
    enabled: boolean;              // Whether this swap pair is active
}
```

**Validation Rules**:
- `swapPairId` must be unique across all swap pairs
- `aggregator` must be registered in `aggregator-mulchain` config
- `chain` must exist in `config.chains`
- Token addresses must be valid checksum addresses (ethers.js format)

**Relationships**:
- One `AggregatorSwapPair` belongs to one `chain`
- One `AggregatorSwapPair` references one `aggregator`
- Multiple `AggregatorSwapPair` can combine to form `AggregatorArbitragePair`

---

### 2. Aggregator Arbitrage Pair

Derived from two aggregator swap pairs for the same token pair, enabling arbitrage routes.

**Type**: `AggregatorArbitragePair`

```typescript
interface AggregatorArbitragePair {
    // Unique identifier
    arbitrargePairId: string;      // Format: "{base}~{quote}~{aggJ}+{chainM}~{aggK}+{chainN}"
                                   // Example: "WIF~USDT~okx+arbitrum~okx+base"

    // Token pair (same for both legs)
    base: string;                  // Token symbol (e.g., "WIF")
    quote: string;                 // Token symbol (e.g., "USDT")

    // Entry leg (swapPair1)
    chainM: ChainId;               // Entry chain
    aggJ: string;                  // Entry aggregator key (e.g., "okx")
    swapPair1: AggregatorSwapPair;

    // Exit leg (swapPair2)
    chainN: ChainId;               // Exit chain
    aggK: string;                  // Exit aggregator key (e.g., "okx")
    swapPair2: AggregatorSwapPair;

    // Route type
    routeType: 'same-chain' | 'cross-chain';
                                   // same-chain: chainM === chainN && aggJ !== aggK
                                   // cross-chain: chainM !== chainN

    // Metadata
    enabled: boolean;              // Whether this arbitrage route is active
    discoveredAt: Date;            // When this route was discovered
}
```

**Validation Rules**:
- `base` and `quote` must match between `swapPair1` and `swapPair2`
- `swapPair1` and `swapPair2` must have different `swapPairId` (no self-pairing unless aggregator allows same-venue routes)
- `routeType` must be correctly calculated from chain/aggregator combinations

**Relationships**:
- One `AggregatorArbitragePair` references two `AggregatorSwapPair` instances
- Maps to existing `TradingPairConfig` (see below)

---

### 3. Multi-Chain Aggregator Configuration

Configuration for enabling aggregators across multiple chains.

**Type**: `AggregatorMultichainConfig`

```typescript
interface AggregatorMultichainConfig {
    [aggregatorKey: string]: {
        enabled: boolean;          // Whether this aggregator is active
        // Future extensions:
        // priority?: number;      // Priority for route selection (default: 0)
        // maxSlippageBps?: number; // Max slippage for this aggregator
    };
}

// Example in config.yaml:
// aggregator-mulchain:
//   okx:
//     enabled: true
```

**Validation Rules**:
- `aggregatorKey` must have corresponding adapter implementation
- If `enabled: true`, credentials must be configured (environment variables)
- If `enabled: false`, aggregator is excluded from pair discovery
- Aggregator is automatically supported on all chains where tokens exist, UNLESS the aggregator key is listed in `chains.{chainId}.non-aggr` exclusion list

**Relationships**:
- One configuration per aggregator (e.g., "okx")
- Referenced during pair discovery startup

---

### 4. TradingPairConfig Extension

**Note**: This is an **EXISTING** type being extended to support aggregators.

**Current Definition** (from `config.types.ts`):

```typescript
interface TradingPairConfig {
    id: PairId;                   // Unique pair identifier
    baseToken: TokenSymbol;       // "WIF", "PEPE"
    quoteToken: StableSymbol;     // "USDT", "USDC"
    chainM: ChainId;              // Entry chain (DEX J)
    dexJ: string;                 // Entry DEX key (NOW SUPPORTS AGGREGATOR KEYS)
    chainN: ChainId;              // Exit chain (DEX K)
    dexK: string;                 // Exit DEX key (NOW SUPPORTS AGGREGATOR KEYS)
    // ... optional fields (minProfitRateBps, slippageBps, positionCaps)
}
```

**Extension for Aggregators**:

**No type changes required!** The existing `dexJ` and `dexK` fields now accept:
- Traditional DEX keys: `"uniswap_v3"`, `"pancakeswap_v3"`, `"velodrome_v2"`
- **Aggregator keys**: `"okx"` (NEW)

**Interpretation**:
- `(chainId, dexKey)` is now a generic "venue key"
- Can represent either a native DEX or a multi-chain aggregator
- Pair discovery treats both uniformly

**Example IDs**:
- Traditional: `WIF~USDT~uniswap_v3+arbitrum~pancakeswap_v3+base`
- Aggregator: `WIF~USDT~okx+arbitrum~okx+base`
- Mixed: `WIF~USDT~uniswap_v3+ethereum~okx+base`

---

## Configuration Data Structures

### config.yaml Extensions

#### New Section: `aggregator-mulchain`

```yaml
aggregator-mulchain:
  okx:
    enabled: true
  # Future aggregators:
  # 1inch:
  #   enabled: false
  # paraswap:
  #   enabled: false
```

#### Existing Section: `chains.{chainId}` (with `non-aggr` exclusion)

**IMPORTANT**: Aggregators are NOT added to `dexList`. They are enabled globally via `aggregator-mulchain` and supported on all chains by default. To exclude an aggregator from a specific chain, use the `non-aggr` list:

```yaml
chains:
  arbitrum:
    rpc: ${ARBITRUM_RPC}
    tokenList:
      - symbol: USDT
        address: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69CCbb"
      - symbol: WIF
        address: "0x..."  # actual address
    dexList:
      - key: uniswap_v3    # Existing DEX (native)
        type: uniswap_v3
      - key: pancakeswap_v3  # Existing DEX (native)
        type: pancakeswap_v3
    # NO okx entry here - aggregators are managed globally
    non-aggr: []  # Empty = all enabled aggregators supported
                  # To exclude OKX: non-aggr: ['okx']

  # Example: Chain that excludes OKX aggregator
  polygon:
    rpc: ${POLYGON_RPC}
    tokenList:
      - symbol: USDT
        address: "0x..."
      - symbol: PEPE
        address: "0x..."
    dexList:
      - key: quickswap
        type: generic_v2
    non-aggr: ['okx']  # OKX aggregator explicitly excluded
```

**Configuration Model**: Opt-out pattern
- Global aggregator enable: `aggregator-mulchain.okx.enabled: true`
- Per-chain aggregator exclude: `chains.{chainId}.non-aggr: ['okx']`
- Default (empty `non-aggr`): All globally enabled aggregators are supported
- Aggregator keys are NOT added to `chains.{chainId}.dexList`

### Environment Variables

```bash
# OKX DEX Credentials (required if okx.enabled: true)
OKX_API_KEY=your_api_key_here
OKX_SECRET_KEY=your_secret_key_here
OKX_API_PASSPHRASE=your_passphrase_here
OKX_PROJECT_ID=your_project_id_here
```

---

## Enums and Constants

### Aggregator Keys

```typescript
// New aggregator keys (extensible)
const AGGREGATOR_KEYS = {
    OKX: 'okx',
    // Future: ONE_INCH: '1inch',
    // Future: PARASWAP: 'paraswap',
} as const;

type AggregatorKey = typeof AGGREGATOR_KEYS[keyof typeof AGGREGATOR_KEYS];
```

### DEX Types

```typescript
// Extended to support aggregators
type DexType =
    | 'uniswap_v3'        // Existing
    | 'velodrome_v2'      // Existing
    | 'generic_v2'        // Existing
    | 'generic_v3'        // Existing
    | 'pancakeswap_v3'    // Existing
    | 'okx_dex';          // NEW: OKX DEX aggregator
```

### Chain IDs

```typescript
// Already exists in config.types.ts
type ChainId =
    | 'ethereum'
    | 'arbitrum'
    | 'base'
    | 'polygon'
    | 'bsc';
```

---

## State Transitions

### Pair Discovery State Machine

```
[Startup: Orchestrator initialized]
    ↓
[Load aggregator config] → [Check credentials]
    ↓
[Enumerate aggregators] → [For each enabled aggregator]
    ↓
[Generate swap pairs] → [For each chain × token pair]
    ↓
[Derive arbitrage pairs] → [Combine swap pairs]
    ↓
[Validate] → [Fast-fail if no pairs discovered]
    ↓
[Return TradingPairConfig[]] → [Cached in PairDiscoveryService]
```

### Aggregator Swap Pair Lifecycle

```
[Created during pair discovery]
    ↓
[Enabled: true] ← (default if aggregator enabled in config)
    ↓
[Quote requested] → [Quote returned] OR [Error: rate limit/timeout]
    ↓
[Balance queried] → [Balance returned] OR [Error: insufficient funds]
    ↓
[Swap executed] → [Success: txHash] OR [Failed: slippage/liquidity]
    ↓
[Disabled: false] ← (if persistent failures or manual disable)
```

---

## Data Validation

### Input Validation (Constitution Requirement)

All external data MUST be validated before use:

#### 1. Token Address Validation

```typescript
function isValidTokenAddress(address: string): boolean {
    // Checksum validation using ethers.js
    try {
        return ethers.isAddress(address);
    } catch {
        return false;
    }
}
```

#### 2. Amount Validation

```typescript
function isValidAmount(amount: string): boolean {
    try {
        const value = BigInt(amount);
        return value >= 0n;
    } catch {
        return false;
    }
}
```

#### 3. Chain ID Validation

```typescript
// Import valid chains from config to maintain single source of truth
function isValidChain(chainId: string): chainId is ChainId {
    const chainsConfig = configService.getChainsConfig();
    const validChains = Object.keys(chainsConfig) as ChainId[];
    return validChains.includes(chainId);
}
```

#### 4. SDK Response Validation

```typescript
function validateQuoteResponse(response: unknown): QuoteResponse {
    if (!response || typeof response !== 'object') {
        throw new Error('Invalid quote response: not an object');
    }

    const quote = response as QuoteResponse;
    if (!quote.data || !Array.isArray(quote.data) || quote.data.length === 0) {
        throw new Error('Invalid quote response: missing or empty data array');
    }

    const firstQuote = quote.data[0];
    if (!firstQuote.toTokenAmount || !firstQuote.priceImpactPercent) {
        throw new Error('Invalid quote response: missing required fields');
    }

    return quote;
}
```

---

## Schema Migrations

### Migration 1: Add Aggregator Support

**Files to Modify**:
1. `config.schema.ts` - Add `aggregator-mulchain` schema
2. `config.types.ts` - Add `AggregatorMultichainConfig` type
3. `pair-discovery.helper.ts` - Extend discovery algorithm for aggregators

**Backward Compatibility**: ✅ FULL
- Existing `TradingPairConfig` unchanged
- Existing DEX adapters unaffected
- New aggregators are additive only

**Migration Script**: Not required (additive change)

---

## Testing Data

### Test Fixtures

```typescript
// Test configuration
const MOCK_AGGREGATOR_CONFIG: AggregatorMultichainConfig = {
    okx: { enabled: true }
};

// Test swap pair
const MOCK_OKX_SWAP_PAIR: AggregatorSwapPair = {
    swapPairId: 'WIF~USDT~okx~arbitrum',
    base: 'WIF',
    quote: 'USDT',
    aggregator: 'okx',
    chain: 'arbitrum',
    baseTokenAddress: '0x...',
    quoteTokenAddress: '0x...',
    decimals: 18,
    enabled: true
};

// Test arbitrage pair
const MOCK_OKX_ARBITRAGE_PAIR: AggregatorArbitragePair = {
    arbitrargePairId: 'WIF~USDT~okx+arbitrum~okx+base',
    base: 'WIF',
    quote: 'USDT',
    chainM: 'arbitrum',
    aggJ: 'okx',
    swapPair1: MOCK_OKX_SWAP_PAIR,
    chainN: 'base',
    aggK: 'okx',
    swapPair2: { /* similar to swapPair1 but for base */ },
    routeType: 'cross-chain',
    enabled: true,
    discoveredAt: new Date('2026-01-02')
};
```

---

## Summary

**Key Design Decisions**:

1. **Reuse Existing Types**: `TradingPairConfig` extended without breaking changes
2. **Generic Venue Keys**: `(chainId, dexKey)` now supports both DEX and aggregator keys
3. **Additive Only**: No migrations required, backward compatible
4. **Type Safety**: Full TypeScript definitions, validated at runtime
5. **Constitution Aligned**: Input validation, structured logging, dry-run mode support

**Next**: Generate API contracts in `contracts/` directory
