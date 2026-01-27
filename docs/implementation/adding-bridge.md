# Adding a Bridge Adapter

Integrate new cross-chain bridge for asset transfers.

## Overview

Bridge adapters implement `BridgeAdapter` interface to:
- Estimate bridge fees in USD
- Execute token transfers between chains
- Poll settlement status with timeout handling
- Provide transferId for correlation and reconciliation

## Implementation Checklist

### 1. Create Bridge Service

**Location**: `src/bridge/your-bridge.service.ts`

**Template** (copy from `stargate.service.ts`):

```typescript
import { Injectable } from '@nestjs/common';
import { ConfigService } from '../utils/config/config.service';
import { LoggerService } from '../utils/logger/logger.service';
import type { BridgeAdapter } from '../bridge/bridge.interface';
import type { ChainId } from '../common/types';

@Injectable()
export class YourBridgeService implements BridgeAdapter {
  private readonly bridgeKey = 'your_bridge';  // Unique identifier
  private readonly chainM: ChainId;
  private readonly chainN: ChainId;

  constructor(
    private readonly configService: ConfigService,
    private readonly logger: LoggerService,
  ) {
    // Resolve which chains this bridge connects
    // Typically hardcoded per bridge implementation
    this.chainM = 'arbitrum';  // Example: from chain
    this.chainN = 'base';      // Example: to chain
  }

  // Required methods from BridgeAdapter interface
  async estimateBridgeToken(
    token: string,
    amount: string,
    from: ChainId,
    to: ChainId,
  ): Promise<{ feeUSD: number }> {
    // TODO: Calculate estimated fee
    const feeUSD = 2.5;  // Example: $2.50 flat fee
    this.logger.debug('Your bridge fee estimate', {
      bridgeKey: this.bridgeKey,
      token,
      amount,
      from,
      to,
      feeUSD,
    });
    return { feeUSD };
  }

  async bridgeToken(
    token: string,
    amount: string,
    from: ChainId,
    to: ChainId,
  ): Promise<{ txHash: string; transferId: string }> {
    this.logger.info('Your bridge initiate', {
      bridgeKey: this.bridgeKey,
      token,
      amount,
      from,
      to,
    });

    // TODO: Execute actual bridge transaction
    const txHash = `0x${Date.now().toString(16)}`;
    const transferId = `transfer_${Date.now()}`;

    return { txHash, transferId };
  }

  async waitForSettlement(
    transferId: string,
    to: ChainId,
    timeoutMs: number,
  ): Promise<{ settled: boolean; finalAmount: string }> {
    this.logger.debug('Your bridge settlement poll', {
      bridgeKey: this.bridgeKey,
      transferId,
      to,
      timeoutMs,
    });

    const startTime = Date.now();
    const maxAttempts = 20;  // Example: poll 20 times
    const intervalMs = Math.min(timeoutMs / maxAttempts, 30000);  // Max 30s between polls

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const elapsed = Date.now() - startTime;
      if (elapsed > timeoutMs) {
        this.logger.warn('Your bridge settlement timeout', {
          bridgeKey: this.bridgeKey,
          transferId,
          to,
          elapsedMs,
          attempts,
        });
        return { settled: false, finalAmount: '0' };
      }

      // TODO: Poll bridge status
      const settled = await this.checkSettlementStatus(transferId);

      if (settled) {
        const finalAmount = await this.getFinalAmount(transferId);
        this.logger.info('Your bridge settlement complete', {
          bridgeKey: this.bridgeKey,
          transferId,
          to,
          finalAmount,
          elapsedMs,
        });
        return { settled: true, finalAmount };
      }

      await sleep(intervalMs);
    }

    return { settled: false, finalAmount: '0' };
  }

  private async checkSettlementStatus(transferId: string): Promise<boolean> {
    // TODO: Query bridge API or on-chain for transfer status
    return false;  // Placeholder
  }

  private async getFinalAmount(transferId: string): Promise<string> {
    // TODO: Query destination chain balance or bridge API for final amount
    return '0';  // Placeholder
  }
}

async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

**Key Points**:
- Implement all 3 interface methods
- Log all operations with context
- Poll settlement with exponential backoff or fixed interval
- Return `settled: false` on timeout
- Include transferId in all logs for correlation

### 2. Register in BridgeModule

**Location**: `src/bridge/bridge.module.ts`

```typescript
import { Module } from '@nestjs/common';
import { YourBridgeService } from './your-bridge.service';
import { StargateService } from './stargate.service';

// Create unique token constant
export const BRIDGE_YOUR_BRIDGE = Symbol('BRIDGE_YOUR_BRIDGE');

@Module({
  providers: [
    {
      provide: BRIDGE_YOUR_BRIDGE,
      useExisting: YourBridgeService,
    },
    StargateService,  // Keep existing bridges
  ],
  exports: [BRIDGE_YOUR_BRIDGE],
})
export class BridgeModule {}
```

### 3. Update Config

**Location**: `config.yaml`

```yaml
bridge:
  provider: your_bridge                    # ← Update bridge provider
  your_bridge:
    router: "0x..."                    # ← Router contract address
    endpoint: "https://your-bridge-api.com"  # ← API endpoint (if applicable)
```

**⚠️ Important**: When adding a new bridge, you must also update the schema validation:

**Location**: `src/utils/config/config.schema.ts`

```typescript
// Add new bridge configuration type
const bridgeYourBridgeSchema: z.ZodType<YourBridgeConfig> = z.object({
  router: z.string().startsWith('0x'),
  // ... other bridge-specific fields
});

// Update bridgeConfigSchema to support the new provider
export const bridgeConfigSchema: z.ZodType<BridgeConfig> = z.union([
  z.object({
    provider: z.literal('stargate'),
    stargate: bridgeStargateSchema,
  }),
  z.object({
    provider: z.literal('your_bridge'),  // ← Add your bridge provider
    your_bridge: bridgeYourBridgeSchema,    // ← Add your bridge config schema
  }),
]);
```

This ensures the config validates correctly with your new bridge provider.

**Environment Variables** (add to `.env` if needed):
```bash
YOUR_BRIDGE_API_KEY=your_api_key
YOUR_BRIDGE_ENDPOINT=https://your-bridge.com
```

### 4. Update Orchestrator

**Location**: `src/orchestrator/orchestrator.service.ts`

Bridge selection is based on route chains:

```typescript
// This code already works generically:
// If pair.chainM === 'arbitrum' && pair.chainN === 'base',
// system uses configured bridge provider (e.g., stargate)

// If your bridge connects different chains, no code changes needed.
// Just ensure config bridge.provider matches your new bridge.
```

### 5. Add Unit Tests

**Location**: `test/bridge/your-bridge.service.spec.ts`

**Test Coverage Required**:
1. **Fee estimation**: Returns USD amount for given token/amount/chain pair
2. **Bridge initiation**: Returns `txHash` and `transferId`
3. **Settlement polling**:
   - Returns `settled: true` on successful completion
   - Returns `settled: false` on timeout
   - Logs warnings for retries
4. **Error handling**: Throws on invalid inputs or configuration errors

**Example Test**:
```typescript
it('estimates bridge fee and executes transfer', async () => {
  const moduleRef = await Test.createTestingModule({
    providers: [
      YourBridgeService,
      { provide: ConfigService, useValue: mockConfig },
      { provide: LoggerService, useValue: mockLogger },
    ],
  }).compile();

  const service = moduleRef.get<YourBridgeService>(YourBridgeService);

  const fee = await service.estimateBridgeToken('WIF', '100', 'arbitrum', 'base');
  expect(fee.feeUSD).toBeGreaterThan(0);

  const result = await service.bridgeToken('WIF', '100', 'arbitrum', 'base');
  expect(result.txHash).toMatch(/^0x[a-f0-9]+$/);
  expect(result.transferId).toBeTruthy();
});
```

## Bridge Configuration Patterns

### Stargate Pattern (Current)

```yaml
bridge:
  provider: stargate
  stargate:
    router: "0x..."          # Router contract
    lzEndpoint: "0x..."       # LayerZero endpoint
```

### Hop/Synapse Pattern (Future)

```yaml
bridge:
  provider: hop  # or synapse
  hop:
    apiEndpoint: "https://api.hop.exchange/v1"
    contractMap:
      arbitrum: "0x..."
      base: "0x..."
```

## Common Implementation Patterns

### Settlement Polling

```typescript
async waitForSettlement(transferId: string, to: ChainId, timeoutMs: number) {
  const maxAttempts = Math.ceil(timeoutMs / 30000);  // Poll every 30s
  const startTime = Date.now();

  for (let i = 0; i < maxAttempts; i++) {
    const status = await this.getStatus(transferId);

    if (status === 'settled') {
      return { settled: true, finalAmount: await this.getAmount(transferId) };
    }

    if (Date.now() - startTime > timeoutMs) {
      return { settled: false, finalAmount: '0' };
    }

    await sleep(30000);  // 30s backoff
  }

  return { settled: false, finalAmount: '0' };
}
```

### Fee Estimation

Bridges typically charge:
- **Flat USD fee**: Fixed amount per transfer (e.g., Stargate $1.50)
- **Percentage fee**: % of transferred amount (e.g., Hop 0.3%)
- **Dynamic gas**: Variable based on network congestion

Calculate total: `flatUSD + (amount * percentage) + estimatedGas`

### Error Handling

| Error Type | Handling Strategy |
|-------------|-------------------|
| Network timeout | Log warning, continue to next tick |
| Insufficient balance | Throw error; Orchestrator handles pause |
| Invalid token address | Fast-fail at startup; require config fix |
| Bridge not supported between chains | Log error, skip route in discovery |
| Transfer failed (on-chain) | Log error with txHash; do not retry |

## Verification Checklist

After implementation, verify:

- [ ] All 3 `BridgeAdapter` methods implemented
- [ ] `bridgeKey` constant matches `config.yaml` `bridge.provider`
- [ ] Settlement polling includes timeout logic
- [ ] All logs include `bridgeKey` and `transferId`
- [ ] Unit tests cover success, timeout, and error cases
- [ ] `BridgeModule` exports `BRIDGE_YOUR_BRIDGE` token
- [ ] Config includes bridge-specific settings (router, endpoint, etc.)
- [ ] Test suite passes: `pnpm test test/bridge/your-bridge.service.spec.ts`

## Related Documentation

- [BridgeAdapter Interface](../architecture/interfaces.md#bridge-adapter) - Interface specification
- [Config Reference](../config/reference.md) - Bridge configuration format
- [Error Handling](../architecture/error-handling.md) - Retry and timeout strategies
- [Core Sequences](../architecture/sequences.md#bridge-settlement--reconciliation) - Settlement flow
