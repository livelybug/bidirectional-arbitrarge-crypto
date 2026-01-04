# OKX DEX Adapter Contract

**Feature**: 001-okx-dex-integration
**Phase**: Phase 1 - Design & Contracts
**Date**: 2026-01-02

## Overview

This document defines the API contract for the OKX DEX Adapter, extending the existing `DexAdapter` interface with aggregator-specific functionality.

---

## Interface: DexAdapter (Existing)

**Location**: `code/ts/src/dex/dex-adapter.interface.ts`

```typescript
export interface DexAdapter {
    readonly chain: ChainId;

    // Price estimation (buying base token with quote)
    estimateBuyQuoteToBase(
        amountQuote: string,
        baseToken: string,
        quoteToken: string,
        slippageBps: number
    ): Promise<QuoteToBaseEstimate>;

    // Price estimation (selling base token for quote)
    estimateSellBaseToQuote(
        amountBase: string,
        baseToken: string,
        quoteToken: string,
        slippageBps: number
    ): Promise<BaseToQuoteEstimate>;

    // Execute swap: quote → base
    swapQuoteToBase(
        amountQuote: string,
        baseToken: string,
        quoteToken: string,
        slippageBps: number
    ): Promise<DexSwapReceipt>;

    // Execute swap: base → quote
    swapBaseToQuote(
        amountBase: string,
        baseToken: string,
        quoteToken: string,
        slippageBps: number
    ): Promise<DexSwapReceipt>;

    // Query wallet balance (quote token)
    getBalanceQuote(quoteToken: string): Promise<string>;

    // Query wallet balance (base token)
    getBalanceBase(baseToken: string): Promise<string>;
}
```

**Implementation**: `OkxDexService` must implement all 7 methods.

---

## Interface: OkxDexAdapter (New Extension)

**Location**: `code/ts/src/dex/okx-dex.adapter.interface.ts` (NEW)

```typescript
import { DexAdapter } from './dex-adapter.interface';

/**
 * OKX DEX Aggregator Adapter
 *
 * Extends DexAdapter with aggregator-specific functionality.
 * OKX DEX routes trades across multiple DEXs internally to find
 * the best execution prices.
 */
export interface OkxDexAdapter extends DexAdapter {
    readonly aggregatorKey: 'okx';  // Fixed to 'okx' for OKX DEX

    /**
     * Initialize OKX DEX SDK client
     *
     * Loads credentials from environment variables and validates
     * that all required credentials are present.
     *
     * @throws Error if any credential is missing
     * @returns OKXDexClient instance
     */
    initializeClient(): Promise<void>;

    /**
     * Validate OKX SDK credentials
     *
     * Checks that OKX_API_KEY, OKX_SECRET_KEY, OKX_API_PASSPHRASE,
     * and OKX_PROJECT_ID are set in environment variables.
     *
     * @returns true if all credentials present
     * @throws Error with clear message if any credential missing
     */
    validateCredentials(): boolean;

    /**
     * Get supported tokens for this chain
     *
     * Queries OKX DEX for the list of tokens supported on this chain.
     * Useful for validation and debugging.
     *
     * @returns Array of token symbols and addresses
     */
    getSupportedTokens(): Promise<Array<{
        symbol: string;
        address: string;
        decimals: number;
    }>>;

    /**
     * Get available DEX liquidity sources
     *
     * Queries OKX DEX for the list of DEX protocols it aggregates
     * on this chain (e.g., Uniswap V3, Curve, Balancer).
     *
     * @returns Array of DEX protocol names
     */
    getLiquiditySources(): Promise<string[]>;

    /**
     * Health check for OKX DEX API
     *
     * Tests connectivity to OKX DEX API by calling a lightweight
     * endpoint (e.g., getSupportedTokens).
     *
     * @returns true if API is reachable
     */
    healthCheck(): Promise<boolean>;
}
```

---

## Request/Response Types

### QuoteToBaseEstimate (Existing)

```typescript
export interface QuoteToBaseEstimate {
    outBase: string;           // Expected base token output (in wei)
    price: number;             // Price as base-per-quote ratio
}
```

**OKX DEX Implementation Details**:
- Calls `client.dex.getQuote()` with `fromTokenAddress = quoteToken`, `toTokenAddress = baseToken`
- Converts `toTokenAmount` from OKX response to `outBase`
- Calculates `price = amountQuote / outBase`
- Applies slippage tolerance to minimum output

### BaseToQuoteEstimate (Existing)

```typescript
export interface BaseToQuoteEstimate {
    outQuote: string;          // Expected quote token output (in wei)
    price: number;             // Price as quote-per-base ratio
}
```

**OKX DEX Implementation Details**:
- Calls `client.dex.getQuote()` with `fromTokenAddress = baseToken`, `toTokenAddress = quoteToken`
- Converts `toTokenAmount` from OKX response to `outQuote`
- Calculates `price = outQuote / amountBase`
- Applies slippage tolerance to minimum output

### DexSwapReceipt (Existing)

```typescript
export interface DexSwapReceipt {
    txHash: string;            // Transaction hash
}
```

**OKX DEX Implementation Details**:
- In dry-run mode: Returns mock `txHash = "0xdryrun-${timestamp}"`
- In live mode: Returns actual transaction hash from `client.dex.executeSwap()`
- Includes block explorer URL in logs

---

## Error Contract

### Error Codes

| Error Code | Description | HTTP Status | Retry Strategy |
|------------|-------------|-------------|----------------|
| `OKX_MISSING_CREDENTIALS` | One or more OKX credentials not configured | N/A | Do not retry (configuration error) |
| `OKX_AUTHENTICATION_FAILED` | Invalid OKX credentials | 401 | Do not retry (credentials error) |
| `OKX_RATE_LIMITED` | API rate limit exceeded | 429 | Retry with exponential backoff |
| `OKX_QUOTE_TIMEOUT` | Quote request timed out (>5s) | 408 | Retry once, then skip |
| `OKX_INSUFFICIENT_LIQUIDITY` | Not enough liquidity for trade | 400 | Do not retry (market condition) |
| `OKX_INSUFFICIENT_BALANCE` | Wallet balance too low | 400 | Do not retry (fund shortage) |
| `OKX_SLIPPAGE_TOO_HIGH` | Price impact exceeds slippage tolerance | 400 | Do not retry (market condition) |
| `OKX_UNSUPPORTED_PAIR` | Token pair not supported on this chain | 400 | Do not retry (configuration) |
| `OKX_NETWORK_ERROR` | Network connectivity issue | 503 | Retry with exponential backoff |
| `OKX_INVALID_RESPONSE` | Malformed API response | 502 | Log and skip |

### Error Response Format

```typescript
interface OkxDexError extends Error {
    code: string;              // Error code from table above
    aggregator: 'okx';         // Always 'okx'
    chain: ChainId;            // Chain where error occurred
    timestamp: Date;           // When error occurred
    retryable: boolean;        // Whether to retry this operation
    details?: {                // Additional error context
        tokenPair?: string;    // e.g., "WIF/USDT"
        requestedAmount?: string;
        reason?: string;       // Human-readable explanation
    };
}
```

### Error Handling Examples

```typescript
// Example 1: Missing credentials
throw new OkxDexError({
    code: 'OKX_MISSING_CREDENTIALS',
    aggregator: 'okx',
    chain: 'arbitrum',
    timestamp: new Date(),
    retryable: false,
    details: {
        reason: 'OKX_API_KEY not set in environment variables'
    }
});

// Example 2: Rate limited
throw new OkxDexError({
    code: 'OKX_RATE_LIMITED',
    aggregator: 'okx',
    chain: 'ethereum',
    timestamp: new Date(),
    retryable: true,
    details: {
        tokenPair: 'WIF/USDT',
        reason: 'HTTP 429: Too many requests. Retry after 1s.'
    }
});

// Example 3: Insufficient liquidity
throw new OkxDexError({
    code: 'OKX_INSUFFICIENT_LIQUIDITY',
    aggregator: 'okx',
    chain: 'base',
    timestamp: new Date(),
    retryable: false,
    details: {
        tokenPair: 'PEPE/USDC',
        requestedAmount: '1000000000000000000000', // 1000 PEPE
        reason: 'Not enough liquidity across aggregated DEXs'
    }
});
```

---

## Logging Contract

### Log Levels and Contexts

All OKX DEX operations MUST use `LoggerService` with operation-scoped contexts (constitution requirement).

### Log Format

```typescript
// Info level: Successful operations
logger.info('operation-name', {
    aggregator: 'okx',
    chain: 'arbitrum',
    operation: 'quote',  // or 'swap', 'balance', 'approval'
    baseToken: 'WIF',
    quoteToken: 'USDT',
    amountQuote: '1000000000',
    outBase: '523456789',
    price: 0.000523,
    slippageBps: 300,
    durationMs: 1234
});

// Warn level: Recoverable errors
logger.warn('okx-quote-retry', {
    aggregator: 'okx',
    chain: 'base',
    baseToken: 'PEPE',
    quoteToken: 'USDC',
    reason: 'HTTP 429 rate limited, retrying in 1s',
    retryAttempt: 1,
    maxRetries: 3
});

// Error level: Failed operations
logger.error('okx-swap-failed', {
    aggregator: 'okx',
    chain: 'ethereum',
    baseToken: 'WIF',
    quoteToken: 'USDT',
    amountBase: '100000000000000000',
    reason: 'Insufficient liquidity',
    errorCode: 'OKX_INSUFFICIENT_LIQUIDITY',
    slippageBps: 500
});

// Debug level: Detailed diagnostics
logger.debug('okx-sdk-response', {
    aggregator: 'okx',
    chain: 'arbitrum',
    method: 'getQuote',
    requestParams: { /* ... */ },
    responseSummary: {
        toTokenAmount: '523456789',
        priceImpactPercent: '0.05',
        dexRouterList: ['Uniswap V3', 'Curve']
    }
});
```

### Required Log Fields

Every log entry MUST include:
- `aggregator`: Always `'okx'`
- `chain`: Chain ID (e.g., `'arbitrum'`)
- `operation`: Type of operation (`'quote'`, `'swap'`, `'balance'`)
- `timestamp`: ISO 8601 timestamp (added by LoggerService)

Conditionally included:
- `baseToken`, `quoteToken`: For swap/quote operations
- `amount*`: Amounts being queried/swapped
- `txHash`: For successful swap executions
- `reason`: For errors/warnings
- `errorCode`: For errors
- `durationMs`: For operation timing
- `retryAttempt`, `maxRetries`: For retry logic

---

## Performance Contract

### Response Time SLAs

| Operation | Target SLA | Max Timeout | Action on Timeout |
|-----------|------------|--------------|-------------------|
| Quote estimation | <3 seconds | 5 seconds | Log error, return failure, skip this tick |
| Balance query | <2 seconds | 3 seconds | Log error, return "0", skip swap |
| Swap execution | <10 seconds | 30 seconds | Log error, may need manual reconciliation |

### Throughput Limits

- **Max concurrent requests**: 5 (to avoid overwhelming OKX API)
- **Rate limit handling**: Exponential backoff starting at 1s, max 10s
- **Circuit breaker**: Open after 5 consecutive failures, half-open after 30s cooldown

---

## Security Contract

### Credential Management (Constitution Requirement)

**Rule**: Private keys and API credentials MUST NEVER be hardcoded or committed to git.

**Implementation**:
```typescript
// ✅ CORRECT: Load from environment
const apiKey = process.env.OKX_API_KEY;
const secretKey = process.env.OKX_SECRET_KEY;
const apiPassphrase = process.env.OKX_API_PASSPHRASE;
const projectId = process.env.OKX_PROJECT_ID;

if (!apiKey || !secretKey || !apiPassphrase || !projectId) {
    throw new Error(
        'OKX DEX credentials not configured. ' +
        'Set OKX_API_KEY, OKX_SECRET_KEY, OKX_API_PASSPHRASE, OKX_PROJECT_ID environment variables.'
    );
}

// ❌ FORBIDDEN: Hardcoded credentials
const apiKey = '0x1234567890abcdef';  // NEVER DO THIS
```

### Input Validation (Constitution Requirement)

**Rule**: ALL external inputs (API responses, RPC results, configs) MUST be validated.

**Validation Checklist**:
1. **SDK Response Structure**: Verify response has expected `data` array
2. **Token Addresses**: Validate checksum format using `ethers.isAddress()`
3. **Amounts**: Validate non-negative, parseable as BigInt
4. **Chain IDs**: Validate against allowed chains list
5. **Slippage**: Validate 0 <= slippageBps <= 10000 (100%)

**Example**:
```typescript
function validateQuoteResponse(response: unknown): QuoteResponse {
    if (!response || typeof response !== 'object') {
        throw new Error('Invalid quote response: not an object');
    }

    const quote = response as QuoteResponse;
    if (!quote.data || !Array.isArray(quote.data)) {
        throw new Error('Invalid quote response: missing data array');
    }

    if (quote.data.length === 0) {
        throw new Error('Invalid quote response: empty data array');
    }

    const firstQuote = quote.data[0];
    if (!firstQuote.toTokenAmount || !firstQuote.priceImpactPercent) {
        throw new Error('Invalid quote response: missing required fields');
    }

    return quote;
}
```

### Dry-Run Mode (Constitution Requirement)

**Rule**: ALL features MUST work correctly in dry-run mode before live execution.

**Implementation**:
```typescript
async swapQuoteToBase(...): Promise<DexSwapReceipt> {
    if (this.walletService.isDryRun()) {
        this.logger.info('okx-swap-dry-run', {
            aggregator: 'okx',
            chain: this.chain,
            baseToken,
            quoteToken,
            amountQuote,
            slippageBps
        });

        // Simulate delay
        await this.simulateAsyncLatency();

        // Return mock receipt
        return {
            txHash: `0xdryrun-okx-${this.chain}-${Date.now().toString(16)}`
        };
    }

    // Live execution
    const swap = await this.client.dex.executeSwap({...});
    return { txHash: swap.transactionId };
}
```

---

## Testing Contract

### Unit Test Coverage

**Requirement**: >80% code coverage (FR-020)

**Test File**: `code/ts/src/dex/okx-dex.service.spec.ts`

**Must Cover**:
1. Client initialization (valid/missing credentials)
2. Quote estimation (normal, high slippage, unsupported pair)
3. Balance queries (native token, ERC-20, zero balance)
4. Swap execution (dry-run mode, live mode with mocked SDK)
5. Error handling (rate limits, timeouts, insufficient liquidity)
6. Input validation (invalid addresses, negative amounts)
7. Logging (all operations emit structured logs)

### Integration Test Coverage

**Test File**: `code/ts/test/dex/okx-dex.integration.spec.ts`

**Must Cover**:
1. End-to-end quote → balance → swap flow (with mocked SDK)
2. Pair discovery includes OKX aggregator routes
3. Multi-chain quotes (same pair across Ethereum, Arbitrum, Base)
4. Error recovery (SDK failure, graceful degradation)
5. Dry-run vs live mode behavior

**Constraint**: Integration tests use mocked OKX SDK (no live API calls).

---

## Version Contract

### API Versioning

- **OKX DEX SDK Version**: `^1.0.17` (locked to minor version)
- **Node.js Version**: `>=24.0.0` (per constitution)
- **TypeScript Version**: `^5.0.0` (strict mode enabled)

### Backward Compatibility

- ✅ Existing `DexAdapter` interface unchanged
- ✅ Existing `TradingPairConfig` unchanged (interprets `dexJ/dexK` as venue keys)
- ✅ Existing DEX adapters unaffected
- ✅ Pair discovery extended (additive only)

---

## Summary

This contract defines:
1. **Interface**: `OkxDexAdapter` extends `DexAdapter`
2. **Types**: Quote/swap/balance request/response formats
3. **Errors**: 10 error codes with retry strategies
4. **Logging**: Structured logging with operation contexts
5. **Performance**: 3-5 second SLAs for quotes/balances
6. **Security**: Environment-based credentials, input validation
7. **Testing**: >80% unit coverage, integration tests with mocks

**Next**: Generate quickstart.md for developer onboarding
