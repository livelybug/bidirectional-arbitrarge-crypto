# Adding a DEX Adapter

Integrate new decentralized exchange into the arbitrage system.

## Overview

DEX adapters are modular components that implement `DexAdapter` interface. Each adapter:
- Provides quote estimates for buying/selling base/quote tokens
- Executes swaps with slippage caps
- Queries wallet balances
- Registered via DI tokens for dependency injection

## Implementation Checklist

### 1. Create Adapter Service

**Location**: `src/dex/your-dex.service.ts`

**Template** (copy from `uniswap-v3.service.ts`):

```typescript
import { Injectable } from '@nestjs/common';
import { ConfigService } from '../utils/config/config.service';
import { LoggerService } from '../utils/logger/logger.service';
import type {
  BaseToQuoteEstimate,
  DexAdapter,
  DexSwapReceipt,
  QuoteToBaseEstimate,
} from './dex-adapter.interface';

@Injectable()
export class YourDexService implements DexAdapter {
  public readonly chain: string;
  private readonly dexKey = 'your_dex';  // Unique key (matches config.chains.*.dexList[].key)

  constructor(
    private readonly configService: ConfigService,
    private readonly logger: LoggerService,
  ) {
    this.chain = this.resolveChain('your_dex');
  }

  // Required methods from DexAdapter interface
  async estimateBuyQuoteToBase(
    amountQuote: string,
    baseToken: string,
    quoteToken: string,
    slippageBps: number,
  ): Promise<QuoteToBaseEstimate> {
    // TODO: Implement quote calculation
    return { outBase: '0', price: 1.0 };
  }

  async estimateSellBaseToQuote(
    amountBase: string,
    baseToken: string,
    quoteToken: string,
    slippageBps: number,
  ): Promise<BaseToQuoteEstimate> {
    // TODO: Implement quote calculation
    return { outQuote: '0', price: 1.0 };
  }

  async swapQuoteToBase(
    amountQuote: string,
    baseToken: string,
    quoteToken: string,
    slippageBps: number,
  ): Promise<DexSwapReceipt> {
    this.logger.info('Your DEX quote→base swap', {
      chain: this.chain,
      dexKey: this.dexKey,
      amountQuote,
      baseToken,
      quoteToken,
      slippageBps,
    });
    // TODO: Execute actual swap
    return { txHash: `0x${Date.now().toString(16)}` };
  }

  async swapBaseToQuote(
    amountBase: string,
    baseToken: string,
    quoteToken: string,
    slippageBps: number,
  ): Promise<DexSwapReceipt> {
    this.logger.info('Your DEX base→quote swap', {
      chain: this.chain,
      dexKey: this.dexKey,
      amountBase,
      baseToken,
      quoteToken,
      slippageBps,
    });
    // TODO: Execute actual swap
    return { txHash: `0x${Date.now().toString(16)}` };
  }

  async getBalanceQuote(quoteToken: string): Promise<string> {
    // TODO: Query wallet balance
    return '0';
  }

  async getBalanceBase(baseToken: string): Promise<string> {
    // TODO: Query wallet balance
    return '0';
  }

  // Resolve target chain from config
  private resolveChain(dexKey: string): string {
    const entries = Object.entries(this.configService.getChainsConfig());
    if (!entries.length) {
      throw new Error(`No chains configured; unable to initialize adapter for ${dexKey}`);
    }

    const match = entries.find(([, cfg]) => cfg.dexList.some((dex) => dex.key === dexKey));
    if (!match) {
      throw new Error(`No chain advertises dex key ${dexKey}; update config.chains accordingly`);
    }

    return match[0];  // Returns chainId (e.g., 'arbitrum', 'base')
  }
}
```

**Key Points**:
- Implement all 6 interface methods
- Resolve chain from config (fail-fast if DEX not advertised)
- Log all operations with `chain` and `dexKey` context
- Normalize invalid inputs (NaN, negative numbers) to safe defaults

### 2. Register in DexModule

**Location**: `src/dex/dex.module.ts`

```typescript
import { Module } from '@nestjs/common';
import { YourDexService } from './your-dex.service';

// Create unique token constant
export const DEX_YOUR_DEX = Symbol('DEX_YOUR_DEX');

@Module({
  providers: [
    {
      provide: DEX_YOUR_DEX,
      useExisting: YourDexService,  // Register existing instance for DI
    },
    // ... existing DEX registrations
  ],
  exports: [DEX_YOUR_DEX],  // Export for injection in other modules
})
export class DexModule {}
```

### 3. Add to Config

**Location**: `config.yaml`

```yaml
chains:
  your_chain:                          # Add chain section
    rpc: ${YOUR_CHAIN_RPC}          # Add RPC URL to .env
    tokenList:
      - symbol: USDT
        address: "0x..."            # Token address on this chain
      - symbol: WIF
        address: "0x..."
    dexList:
      - key: your_dex                    # Must match yourDexService.dexKey
        type: your_dex_type            # Type identifier (any string)
```

**Environment Variables** (add to `.env`):
```bash
YOUR_CHAIN_RPC=https://your-rpc-endpoint.com
```

### 4. Update Type Definitions

**Location**: `src/common/types.ts`

```typescript
export type ChainId =
  | 'arbitrum'
  | 'base'
  | 'optimism'
  | 'ethereum'
  | 'polygon'
  | 'bsc'
  | 'your_chain';                      // ← Add your chain here
```

### 5. Add Unit Tests

**Location**: `src/dex/your-dex.service.spec.ts`

**Test Coverage Required**:
1. **Deterministic pricing**: Quote estimates return consistent values for same inputs
2. **Input normalization**: Invalid amounts/slippage return safe defaults
3. **Fail-fast on missing config**: Throws when `your_dex` not in `dexList`
4. **Receipt structure**: Swap methods return objects with `txHash` field
5. **Balance queries**: Return valid string representations

**Example Test**:
```typescript
it('provides deterministic price and quote estimates', async () => {
  const moduleRef = await Test.createTestingModule({
    providers: [
      YourDexService,
      {
        provide: ConfigService,
        useValue: {
          getChainsConfig: () => ({
            your_chain: {
              rpc: 'http://example',
              tokenList: [],
              dexList: [{ key: 'your_dex', type: 'your_dex_type' }],
            },
          }),
        },
      },
      { provide: LoggerService, useValue: mockLogger },
    ],
  }).compile();

  const service = moduleRef.get<YourDexService>(YourDexService);
  expect(service.chain).toBe('your_chain');

  const estimate = await service.estimateSellBaseToQuote('1', 'WIF', 'USDT', 0);
  expect(estimate.price).toBeGreaterThan(0);
});
```

### 6. Add Orchestrator Integration

**No code changes required** in:
- `OrchestratorService`: Uses `TradingPairConfig[]` with `dexJ`/`dexK` keys
- `PriceMonitorService`: Uses `DexQuoteProvider` registry, not direct adapter references

**Your DEX becomes available when**:
1. `DexModule` registers it with `DEX_YOUR_DEX` token
2. `config.yaml` includes `your_dex` key in at least one chain's `dexList`
3. `PairDiscoveryService` generates routes with `dexJ` or `dexK` = `'your_dex'`

## Aggregator DEXs

For multi-chain aggregators (e.g., OKX, Binance):

Same pattern applies:
- Create service with `dexKey = 'okx'` (or other aggregator key)
- Add aggregator to `config.aggregatorMultichain`:
  ```yaml
  aggregatorMultichain:
    okx:
      enabled: true
  ```
- Add credentials to `.env` (see [Fast-Fail Errors](../config/fast-fail-errors.md))
- Pair discovery treats aggregator keys as valid `dexJ`/`dexK` values

## Common Patterns

### Logging Style

```typescript
this.logger.debug('Your DEX buy estimate', {
  chain: this.chain,
  dexKey: this.dexKey,
  baseToken,
  quoteToken,
  price: calculatedPrice,
  outBase,
});

this.logger.info('Your DEX base→quote swap', {
  chain: this.chain,
  dexKey: this.dexKey,
  amountBase,
  slippageBps,
  txHash: receipt.txHash,
});
```

### Input Normalization

```typescript
private parseAmount(amount: string): number {
  const numeric = Number(amount);
  if (!Number.isFinite(numeric) || numeric < 0) {
    this.logger.warn('Your DEX received invalid amount, normalizing to 0', {
      chain: this.chain,
      dexKey: this.dexKey,
      rawAmount: amount,
    });
    return 0;
  }
  return numeric;
}

private normalizeSlippage(slippageBps: number): number {
  if (!Number.isFinite(slippageBps)) {
    this.logger.warn('Your DEX received non-finite slippage, normalizing to 0 bps', {
      chain: this.chain,
      dexKey: this.dexKey,
      rawSlippageBps: slippageBps,
    });
    return 0;
  }
  if (slippageBps < 0) {
    this.logger.warn('Your DEX received negative slippage, clamping to 0 bps', {
      chain: this.chain,
      dexKey: this.dexKey,
      rawSlippageBps: slippageBps,
    });
    return 0;
  }
  return slippageBps;
}
```

## Verification Checklist

After implementation, verify:

- [ ] All 6 `DexAdapter` methods implemented
- [ ] `dexKey` constant matches `config.yaml` `dexList[].key`
- [ ] Chain resolution throws on missing DEX key
- [ ] Unit tests cover deterministic behavior, error handling
- [ ] `DexModule` exports `DEX_YOUR_DEX` token
- [ ] Config includes chain with `your_dex` in `dexList`
- [ ] `src/common/types.ts` includes new `ChainId`
- [ ] Logs include `chain` and `dexKey` context
- [ ] Test suite passes: `pnpm test src/dex/your-dex.service.spec.ts`

## Related Documentation

- [DexAdapter Interface](../architecture/interfaces.md#dex-adapter) - Interface specification
- [Config Reference](../config/reference.md) - Chain and DEX configuration format
- [Pair Discovery](pair-discovery.md) - How routes include new DEX
- [Error Handling](../architecture/error-handling.md) - Retry patterns and circuit breakers
