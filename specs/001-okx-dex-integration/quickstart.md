# Quickstart: OKX DEX Integration

**Feature**: 001-okx-dex-integration
**For**: Developers implementing OKX DEX adapter
**Date**: 2026-01-02

---

## Overview

This guide will help you quickly get started with implementing the OKX DEX aggregator adapter for the arbitrage bot. You'll extend the existing DEX adapter pattern to support OKX's multi-chain aggregation.

**What you'll build**:
- `OkxDexService`: A new DexAdapter implementation using the OKX DEX SDK
- Pair discovery extensions: Support aggregator-aware route discovery
- Configuration schema: Add `aggregator-mulchain` to config system
- Tests: Unit and integration tests following TDD workflow

**Time estimate**: 2-3 days for full implementation (including tests)

---

## Prerequisites

### 1. Install OKX DEX SDK

```bash
cd code/ts
pnpm add @okx-dex/okx-dex-sdk
```

### 2. Get OKX Developer Credentials

1. Visit https://web3.okx.com/build/dev-docs/wallet-api/developer-portal
2. Click "Connect Wallet" to create/login to your OKX account
3. Navigate to "API keys" and create a new API key
4. Set a passphrase (remember it!)
5. Copy your credentials:
   - API Key
   - Secret Key
   - Passphrase
   - Project ID

### 3. Set Environment Variables

Create or update `.env` file in `code/ts/`:

```bash
# OKX DEX Credentials
OKX_API_KEY=your_actual_api_key_here
OKX_SECRET_KEY=your_actual_secret_key_here
OKX_API_PASSPHRASE=your_actual_passphrase_here
OKX_PROJECT_ID=your_actual_project_id_here

# Existing variables (keep these)
ARBITRUM_RPC=https://arbitrum.infura.io/v3/YOUR_KEY
BASE_RPC=https://base.publicnode.com
# ... etc
```

**IMPORTANT**: Never commit `.env` to git (already in `.gitignore`).

---

## Step 1: Extend Configuration Schema

### 1.1 Update `config.types.ts`

**File**: `code/ts/src/utils/config/config.types.ts`

Add the new aggregator configuration type:

```typescript
// Add to existing types section

/**
 * Multi-chain aggregator configuration
 * Maps aggregator keys to their enabled state
 */
export interface AggregatorMultichainConfig {
    [aggregatorKey: string]: {
        enabled: boolean;
    };
}

/**
 * Extended chain configuration to support aggregator type
 */
export type ChainDexType =
    | 'uniswap_v3'      // Existing
    | 'velodrome_v2'    // Existing
    | 'generic_v2'      // Existing
    | 'generic_v3'      // Existing
    | 'pancakeswap_v3'  // Existing
    | 'okx_dex';        // NEW: OKX DEX aggregator
```

### 1.2 Update `config.schema.ts`

**File**: `code/ts/src/utils/config/config.schema.ts`

Add validation for `aggregator-mulchain` section:

```typescript
import { z } from 'zod';

// Add to existing schema definitions

export const aggregatorMultichainSchema = z.record(
    z.object({
        enabled: z.boolean().default(true),
    })
);

// Extend appConfigSchema to include aggregator-mulchain
export const appConfigSchema = z.object({
    // ... existing fields (tokens, chains, bridge, risk, fees, ops, logging, wallets)

    // NEW: Add aggregator-mulchain section
    aggregatorMultichain: aggregatorMultichainSchema.optional().default({}),
});
```

### 1.3 Update `config.service.ts`

**File**: `code/ts/src/utils/config/config.service.ts`

Add getter for aggregator config:

```typescript
export class ConfigService {
    // ... existing methods

    getAggregatorMultichainConfig(): AggregatorMultichainConfig {
        return this.config.aggregatorMultichain || {};
    }

    isAggregatorEnabled(aggregatorKey: string): boolean {
        const aggregatorConfig = this.getAggregatorMultichainConfig();
        return aggregatorConfig[aggregatorKey]?.enabled === true;
    }
}
```

---

## Step 2: Implement OKX DEX Adapter

### 2.1 Create Adapter File

**File**: `code/ts/src/dex/okx-dex.service.ts`

```typescript
import { Injectable } from '@nestjs/common';
import { OKXDexClient } from '@okx-dex/okx-dex-sdk';
import type {
    BaseToQuoteEstimate,
    DexAdapter,
    DexSwapReceipt,
    QuoteToBaseEstimate,
} from './dex-adapter.interface';
import { ConfigService } from '../utils/config/config.service';
import { ChainId } from '../utils/config/config.types';
import { LoggerService } from '../utils/logger/logger.service';
import { WalletService } from '../wallet/wallet.service';

@Injectable()
export class OkxDexService implements DexAdapter {
    public readonly chain: ChainId;
    public readonly aggregatorKey = 'okx';
    private client: OKXDexClient | null = null;

    constructor(
        chain: ChainId,
        private readonly configService: ConfigService,
        private readonly logger: LoggerService,
        private readonly walletService: WalletService,
    ) {
        this.chain = chain;
        this.initializeClient();
    }

    async estimateBuyQuoteToBase(
        amountQuote: string,
        baseToken: string,
        quoteToken: string,
        slippageBps: number,
    ): Promise<QuoteToBaseEstimate> {
        const slippage = (slippageBps / 10000).toString();

        try {
            const response = await this.client!.dex.getQuote({
                chainId: this.mapChainId(this.chain),
                fromTokenAddress: quoteToken,
                toTokenAddress: baseToken,
                amount: amountQuote,
                slippage,
            });

            const outBase = response.data[0].toTokenAmount;
            const price = parseFloat(amountQuote) / parseFloat(outBase);

            this.logger.debug('okx-buy-quote', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                amountQuote,
                outBase,
                price,
                slippageBps,
            });

            return { outBase, price };
        } catch (error: any) {
            this.logger.error('okx-quote-error', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                error: error.message,
            });
            throw error;
        }
    }

    async estimateSellBaseToQuote(
        amountBase: string,
        baseToken: string,
        quoteToken: string,
        slippageBps: number,
    ): Promise<BaseToQuoteEstimate> {
        const slippage = (slippageBps / 10000).toString();

        try {
            const response = await this.client!.dex.getQuote({
                chainId: this.mapChainId(this.chain),
                fromTokenAddress: baseToken,
                toTokenAddress: quoteToken,
                amount: amountBase,
                slippage,
            });

            const outQuote = response.data[0].toTokenAmount;
            const price = parseFloat(outQuote) / parseFloat(amountBase);

            this.logger.debug('okx-sell-quote', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                amountBase,
                outQuote,
                price,
                slippageBps,
            });

            return { outQuote, price };
        } catch (error: any) {
            this.logger.error('okx-quote-error', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                error: error.message,
            });
            throw error;
        }
    }

    async swapQuoteToBase(
        amountQuote: string,
        baseToken: string,
        quoteToken: string,
        slippageBps: number,
    ): Promise<DexSwapReceipt> {
        if (this.walletService.isDryRun()) {
            this.logger.info('okx-swap-dry-run', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                amountQuote,
                slippageBps,
            });

            await this.simulateAsyncLatency();
            return { txHash: `0xdryrun-okx-${this.chain}-${Date.now().toString(16)}` };
        }

        const slippage = (slippageBps / 10000).toString();

        try {
            const swap = await this.client!.dex.executeSwap({
                chainId: this.mapChainId(this.chain),
                fromTokenAddress: quoteToken,
                toTokenAddress: baseToken,
                amount: amountQuote,
                slippage,
                userWalletAddress: this.walletService.getAddress(),
            });

            this.logger.info('okx-swap-success', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                amountQuote,
                txHash: swap.transactionId,
                explorerUrl: swap.explorerUrl,
            });

            return { txHash: swap.transactionId };
        } catch (error: any) {
            this.logger.error('okx-swap-error', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                error: error.message,
            });
            throw error;
        }
    }

    async swapBaseToQuote(
        amountBase: string,
        baseToken: string,
        quoteToken: string,
        slippageBps: number,
    ): Promise<DexSwapReceipt> {
        if (this.walletService.isDryRun()) {
            this.logger.info('okx-swap-dry-run', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                amountBase,
                slippageBps,
            });

            await this.simulateAsyncLatency();
            return { txHash: `0xdryrun-okx-${this.chain}-${Date.now().toString(16)}` };
        }

        const slippage = (slippageBps / 10000).toString();

        try {
            const swap = await this.client!.dex.executeSwap({
                chainId: this.mapChainId(this.chain),
                fromTokenAddress: baseToken,
                toTokenAddress: quoteToken,
                amount: amountBase,
                slippage,
                userWalletAddress: this.walletService.getAddress(),
            });

            this.logger.info('okx-swap-success', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                amountBase,
                txHash: swap.transactionId,
                explorerUrl: swap.explorerUrl,
            });

            return { txHash: swap.transactionId };
        } catch (error: any) {
            this.logger.error('okx-swap-error', {
                aggregator: 'okx',
                chain: this.chain,
                baseToken,
                quoteToken,
                error: error.message,
            });
            throw error;
        }
    }

    async getBalanceQuote(quoteToken: string): Promise<string> {
        return this.getBalance(quoteToken, 'quote');
    }

    async getBalanceBase(baseToken: string): Promise<string> {
        return this.getBalance(baseToken, 'base');
    }

    /**
     * Unified balance query method
     * Consolidates duplicate logic for base and quote token balance queries
     */
    private async getBalance(tokenAddress: string, tokenType: 'base' | 'quote'): Promise<string> {
        const provider = this.walletService.getProvider(this.chain);
        const address = this.walletService.getAddress();

        try {
            // Native token (ETH, BNB, MATIC, etc.)
            if (tokenAddress === '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE') {
                const balance = await provider.getBalance(address);
                this.logger.debug(`okx-balance-${tokenType}-native`, {
                    aggregator: 'okx',
                    chain: this.chain,
                    tokenAddress,
                    balance: balance.toString(),
                });
                return balance.toString();
            }

            // ERC-20 token
            const tokenContract = new ethers.Contract(
                tokenAddress,
                ['function balanceOf(address) view returns (uint256)'],
                provider,
            );
            const balance = await tokenContract.balanceOf(address);

            this.logger.debug(`okx-balance-${tokenType}-erc20`, {
                aggregator: 'okx',
                chain: this.chain,
                tokenAddress,
                balance: balance.toString(),
            });

            return balance.toString();
        } catch (error: any) {
            this.logger.error('okx-balance-error', {
                aggregator: 'okx',
                chain: this.chain,
                tokenAddress,
                tokenType,
                error: error.message,
            });
            return '0';  // Safe default on error
        }
    }

    private initializeClient(): void {
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

        this.client = new OKXDexClient({
            apiKey,
            secretKey,
            apiPassphrase,
            projectId,
            evm: {
                wallet: this.walletService.getEVMWallet(this.chain),
            },
        });

        this.logger.info('okx-client-initialized', {
            aggregator: 'okx',
            chain: this.chain,
        });
    }

    private mapChainId(chainId: ChainId): string {
        const chainMap: Record<ChainId, string> = {
            ethereum: '1',
            arbitrum: '42161',
            base: '8453',
            polygon: '137',
            bsc: '56',
        };

        const mapped = chainMap[chainId];
        if (!mapped) {
            throw new Error(`Unsupported chain: ${chainId}`);
        }

        return mapped;
    }

    private async simulateAsyncLatency(): Promise<void> {
        await new Promise((resolve) => setTimeout(resolve, 50));
    }
}
```

### 2.2 Create Test File (TDD First!)

**File**: `code/ts/src/dex/okx-dex.service.spec.ts`

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { OkxDexService } from './okx-dex.service';
import { ConfigService } from '../utils/config/config.service';
import { LoggerService } from '../utils/logger/logger.service';
import { WalletService } from '../wallet/wallet.service';

describe('OkxDexService', () => {
    let service: OkxDexService;
    let configService: jest.Mocked<ConfigService>;
    let loggerService: jest.Mocked<LoggerService>;
    let walletService: jest.Mocked<WalletService>;

    beforeEach(async () => {
        const module: TestingModule = await Test.createTestingModule({
            providers: [
                OkxDexService,
                {
                    provide: ConfigService,
                    useValue: {
                        getChainsConfig: jest.fn().returnValue({
                            arbitrum: {
                                rpc: 'https://arbitrum.infura.io/v3/test',
                                tokenList: [
                                    { symbol: 'USDT', address: '0x...' },
                                    { symbol: 'WIF', address: '0x...' },
                                ],
                                dexList: [
                                    { key: 'uniswap_v3', type: 'uniswap_v3' },
                                    { key: 'pancakeswap_v3', type: 'pancakeswap_v3' },
                                ],
                                non-aggr: [],  // OKX supported by default (empty exclusion list)
                            },
                        }),
                        getAggregatorMultichainConfig: jest.fn().returnValue({
                            okx: { enabled: true },
                        }),
                        isAggregatorEnabled: jest.fn().returnValue(true),
                    },
                },
                {
                    provide: LoggerService,
                    useValue: {
                        info: jest.fn(),
                        debug: jest.fn(),
                        warn: jest.fn(),
                        error: jest.fn(),
                    },
                },
                {
                    provide: WalletService,
                    useValue: {
                        getProvider: jest.fn(),
                        getAddress: jest.fn().returnValue('0x1234567890123456789012345678901234567890'),
                        isDryRun: jest.fn().ReturnValue(false),
                        getEVMWallet: jest.fn(),
                    },
                },
            ],
        }).compile();

        service = module.get<OkxDexService>(OkxDexService);
        configService = module.get(ConfigService);
        loggerService = module.get(LoggerService);
        walletService = module.get(WalletService);
    });

    it('should be defined', () => {
        expect(service).toBeDefined();
    });

    it('should have correct chain', () => {
        expect(service.chain).toBe('arbitrum');
    });

    it('should have correct aggregator key', () => {
        expect(service.aggregatorKey).toBe('okx');
    });

    // TODO: Add more tests following TDD workflow
    // - estimateBuyQuoteToBase
    // - estimateSellBaseToQuote
    // - swapQuoteToBase (dry-run and live)
    // - swapBaseToQuote (dry-run and live)
    // - getBalanceQuote (native and ERC-20)
    // - getBalanceBase (native and ERC-20)
    // - Error handling (rate limits, timeouts, etc.)
});
```

---

## Step 3: Register OKX Adapter in DexModule

### 3.1 Update `dex.module.ts`

**File**: `code/ts/src/dex/dex.module.ts`

Add OKX DEX provider:

```typescript
import { Module } from '@nestjs/common';
import { ConfigService } from '../utils/config/config.service';
import { LoggerService } from '../utils/logger/logger.service';
import { WalletService } from '../wallet/wallet.service';
import { UniswapV3Service } from './uniswap-v3.service';
import { PancakeswapV3Service } from './pancakeswap-v3.service';
import { VelodromeV2Service } from './velodrome-v2.service';
import { OkxDexService } from './okx-dex.service';  // NEW

@Module({
    providers: [
        UniswapV3Service,
        PancakeswapV3Service,
        VelodromeV2Service,
        OkxDexService,  // NEW
        ConfigService,
        LoggerService,
        WalletService,
    ],
    exports: [
        UniswapV3Service,
        PancakeswapV3Service,
        VelodromeV2Service,
        OkxDexService,  // NEW
    ],
})
export class DexModule {}
```

---

## Step 4: Extend Pair Discovery for Aggregators

### 4.1 Update `pair-discovery.helper.ts`

**File**: `code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.ts`

Add aggregator enumeration logic (refer to docs/task/task-detail/T3b-Pair&route discovery.md for full implementation).

---

## Step 4: Extend Pair Discovery for Aggregators (HIGH PRIORITY)

**Priority**: This step MUST be completed before adapter testing to ensure aggregator routes are discovered correctly.

### 4.1 Update `pair-discovery.helper.ts`

**File**: `code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.ts`

Add aggregator enumeration logic (refer to docs/task/task-detail/T3b-Pair&route discovery.md for full implementation).

**Key Changes**:
- Enumerate enabled aggregators from `config['aggregator-mulchain']`
- Generate swap pairs for each aggregator on each chain where tokens exist
- Check `chains.{chainId}.non-aggr` exclusion list before generating pairs
- Support self-pairing for same-aggregator routes
- Derive aggregator arbitrage pairs

---

## Step 5: Update config.yaml

Add OKX DEX aggregator to your configuration:

```yaml
aggregator-mulchain:
  okx:
    enabled: true

chains:
  arbitrum:
    rpc: ${ARBITRUM_RPC}
    tokenList:
      - symbol: USDT
        address: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69CCbb"
      - symbol: WIF
        address: "0x..."  # actual WIF address
    dexList:
      - key: uniswap_v3
        type: uniswap_v3
      - key: pancakeswap_v3
        type: pancakeswap_v3
    # NO okx entry here - aggregators are managed globally
    non-aggr: []  # Empty = all enabled aggregators supported
                  # To exclude OKX: non-aggr: ['okx']

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
    non-aggr: []  # OKX aggregator supported by default

  ethereum:
    rpc: ${ETHEREUM_RPC}
    tokenList: [...]
    dexList: [...]
    non-aggr: []

  polygon:
    rpc: ${POLYGON_RPC}
    tokenList: [...]
    dexList: [...]
    non-aggr: []

  bsc:
    rpc: ${BSC_RPC}
    tokenList: [...]
    dexList: [...]
    non-aggr: []
```

**Configuration Model**: Opt-out pattern
- Global enable: `aggregator-mulchain.okx.enabled: true`
- Per-chain exclude: `chains.{chainId}.non-aggr: ['okx']`
- Default: All enabled aggregators supported on all chains
- **DO NOT** add `okx` to `chains.{chainId}.dexList`

---

## Step 6: Register OKX Adapter in DexModule

### 6.1 Update `dex.module.ts`

**File**: `code/ts/src/dex/dex.module.ts`

Add OKX DEX provider:

```typescript
import { Module } from '@nestjs/common';
import { ConfigService } from '../utils/config/config.service';
import { LoggerService } from '../utils/logger/logger.service';
import { WalletService } from '../wallet/wallet.service';
import { UniswapV3Service } from './uniswap-v3.service';
import { PancakeswapV3Service } from './pancakeswap-v3.service';
import { VelodromeV2Service } from './velodrome-v2.service';
import { OkxDexService } from './okx-dex.service';  // NEW

@Module({
    providers: [
        UniswapV3Service,
        PancakeswapV3Service,
        VelodromeV2Service,
        OkxDexService,  // NEW
        ConfigService,
        LoggerService,
        WalletService,
    ],
    exports: [
        UniswapV3Service,
        PancakeswapV3Service,
        VelodromeV2Service,
        OkxDexService,  // NEW
    ],
})
export class DexModule {}
```

---

## Step 7: Run Tests

### 7.1 Run Unit Tests

```bash
cd code/ts
pnpm test src/dex/okx-dex.service.spec.ts
```

### 7.2 Run All Tests

```bash
pnpm test
```

### 7.3 Run Integration Tests

```bash
pnpm test:test/dex/okx-dex.integration.spec.ts
```

---

## Step 8: Test in Dry-Run Mode

### 8.1 Start Bot in Dry-Run

```bash
cd code/ts
APP_ENV=dev pnpm run start:dev
```

### 8.2 Verify Logs

Look for OKX DEX logs:

```json
{
  "level": "info",
  "message": "okx-client-initialized",
  "aggregator": "okx",
  "chain": "arbitrum"
}

{
  "level": "info",
  "message": "Pair discovery complete",
  "aggregators": ["okx"],
  "okxPairs": 12
}
```

---

## Troubleshooting

### Error: "OKX DEX credentials not configured"

**Solution**: Set all 4 environment variables in `.env`:
```bash
OKX_API_KEY=...
OKX_SECRET_KEY=...
OKX_API_PASSPHRASE=...
OKX_PROJECT_ID=...
```

### Error: "No chain advertises dex key okx"

**Solution**: This error should not occur with the opt-out configuration model. Ensure:
1. `aggregator-mulchain.okx.enabled: true` in config.yaml
2. `chains.{chainId}.non-aggr` does NOT contain `'okx'` for the chains you want to support
3. OKX adapter is correctly registered in DexModule

**Correct Configuration**:
```yaml
aggregator-mulchain:
  okx:
    enabled: true

chains:
  arbitrum:
    dexList: [...]
    non-aggr: []  # NOT ['okx'] - empty means OKX is supported
```

### Error: "Rate limited" (HTTP 429)

**Solution**: This is expected behavior. The adapter will retry with exponential backoff. If persistent, consider reducing trading frequency.

### Error: "Insufficient liquidity"

**Solution**: OKX DEX doesn't have enough liquidity for this token pair on this chain. The bot will skip this opportunity and try other pairs/chains.

---

## Next Steps

1. **Implement remaining adapter methods**: Complete all 7 DexAdapter methods
2. **Write comprehensive tests**: Achieve >80% code coverage
3. **Extend pair discovery**: Implement aggregator-aware discovery (refer to T3b task detail)
4. **Test on testnet**: Before mainnet, test on Sepolia/Goerli if OKX supports it
5. **Deploy to mainnet**: Only after successful dry-run testing

---

## Additional Resources

- **OKX DEX SDK Docs**: https://web3.okx.com/build/dev-docs/wallet-api/dex-sdk-introduction
- **OKX Developer Portal**: https://web3.okx.com/build/dev-docs/wallet-api/developer-portal
- **Architecture Doc**: [arch_general.md](../../../docs/arch/arch_general.md)
- **Pair Discovery Task**: [T3b-Pair&route discovery.md](../../../docs/task/task-detail/T3b-Pair&route discovery.md)
- **Constitution**: [.specify/memory/constitution.md](../../../.specify/memory/constitution.md)

---

## Support

If you encounter issues:
1. Check logs for structured error messages with `errorCode` field
2. Verify OKX credentials are correctly set in environment
3. Ensure `aggregator-mulchain.okx.enabled: true` in config.yaml
4. Confirm OKX is NOT listed in `chains.{chainId}.non-aggr` for chains you want to support
5. Review research.md for detailed SDK usage examples

**Good luck with your implementation!** 🚀
