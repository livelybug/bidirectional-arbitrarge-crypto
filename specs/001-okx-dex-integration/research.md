# Research: OKX DEX Integration

**Date**: 2026-01-02
**Feature**: OKX DEX Integration (001-okx-dex-integration)
**Phase**: Phase 0 - Research & Technology Decisions

## Executive Summary

**Decision**: Use official OKX DEX SDK (`@okx-dex/okx-dex-sdk`)

**Rationale**: The SDK is production-ready, officially maintained by OKX, provides full TypeScript support, and supports all required chains (Ethereum, Arbitrum, Base, Polygon, BSC). It offers a single aggregator interface that routes across multiple DEXs internally.

**Alternatives Considered**:
- Custom OKX API integration (rejected: more maintenance, slower development)
- Using OKX DEX as individual DEX adapters per chain (rejected: loses aggregation benefits)

---

## Research Findings

### 1. OKX DEX SDK Availability

**Status**: ✅ AVAILABLE

- **Package**: `@okx-dex/okx-dex-sdk`
- **Version**: 1.0.17 (published 3 months ago)
- **Install**: `pnpm add @okx-dex/okx-dex-sdk`
- **GitHub**: https://github.com/okx/okx-dex-sdk
- **Docs**: https://web3.okx.com/build/dev-docs/wallet-api/dex-sdk-introduction

### 2. Authentication Method

**Required Credentials** (from OKX Developer Portal):

1. `OKX_API_KEY` - API key identifier
2. `OKX_SECRET_KEY` - Secret signing key
3. `OKX_API_PASSPHRASE` - User-provided passphrase
4. `OKX_PROJECT_ID` - Project identifier

**Implementation**:
- Credentials sourced from environment variables (constitution requirement: no hardcoded keys)
- SDK handles authentication headers automatically
- Signature generation: `base64(hmac_sha256(timestamp + method + path + body, secretKey))`

### 3. Key SDK Methods

#### **Quotes** (`client.dex.getQuote`)
```typescript
const quote = await client.dex.getQuote({
    chainId: '8453',              // Base Chain
    fromTokenAddress: '0x...',   // Source token
    toTokenAddress: '0x...',     // Destination token
    amount: '1000000000000000000',  // Amount in wei
    slippage: '0.005'           // 0.5% slippage
});
```

**Response includes**:
- `toTokenAmount`: Expected output
- `priceImpactPercent`: Price impact
- `tradeFee`: Estimated network fee (USD)
- `dexRouterList`: DEXs used in aggregation

#### **Swaps** (`client.dex.executeSwap`)
```typescript
const swap = await client.dex.executeSwap({
    chainId: '8453',
    fromTokenAddress: '0x...',
    toTokenAddress: '0x...',
    amount: '100000000000000000',
    slippage: '0.005',
    userWalletAddress: '0x...'
});
```

**Response includes**:
- `transactionId`: Transaction hash
- `explorerUrl`: Block explorer link

#### **Balances**

**Critical Finding**: SDK does NOT have direct `getBalance` methods in DEX module.

**Options**:
1. **OKX Balance API** (separate from DEX SDK):
   - `GET /api/v6/dex/balance/all-token-balances-by-address`
   - `GET /api/v6/dex/balance/specific-token-balance-by-address`

2. **Use ethers.js directly** (RECOMMENDED):
   ```typescript
   const balance = await provider.getBalance(tokenAddress);
   const tokenBalance = await tokenContract.balanceOf(walletAddress);
   ```

**Decision**: Use ethers.js directly for balance queries to maintain consistency with existing DEX adapters (UniswapV3Service, etc.)

#### **Additional Methods**:
- `executeApproval`: Approve ERC-20 tokens for spending
- `getTokens`: Get supported tokens for a chain
- `getLiquidity`: Get available DEX liquidity sources
- `getChainData`: Get chain configuration

### 4. Multi-Chain Support

**Status**: ✅ ALL REQUIRED CHAINS SUPPORTED

| Chain | Chain ID | Quote | Swap | Status |
|-------|----------|-------|------|--------|
| Ethereum | `1` | ✅ | ✅ | Fully supported |
| Arbitrum | `42161` | ✅ | ✅ | Fully supported |
| Base | `8453` | ✅ | ✅ | Fully supported |
| Polygon | `137` | ✅ | ✅ | Fully supported |
| BSC | `56` | ✅ | ✅ | Fully supported |

**Additional chains supported**: Optimism, Avalanche, zkSync Era, Linea, Scroll, Mantle, Blast, Solana, Sui, TON, TRON

**Note**: Token addresses are chain-specific. Must use correct addresses per chain.

### 5. TypeScript Support

**Status**: ✅ FULL TYPESCRIPT DEFINITIONS

SDK is built with TypeScript and provides:
- Complete IntelliSense support
- Typed interfaces for all requests/responses
- Type-safe client configuration

**Key Types**:
```typescript
interface GetQuoteParams {
    chainId: string;
    fromTokenAddress: string;
    toTokenAddress: string;
    amount: string;
    slippage: string;
    dexIds?: string;
    directRoute?: boolean;
}

interface QuoteResponse {
    data: Array<{
        chainIndex: string;
        fromTokenAmount: string;
        toTokenAmount: string;
        tradeFee: string;
        estimateGasFee: string;
        priceImpactPercent: string;
        // ... full token and routing info
    }>;
}
```

### 6. Error Handling

**Common Errors**:
- HTTP 429: Rate limited (retry with backoff)
- "Insufficient liquidity": Not enough DEX liquidity
- "Insufficient balance": Wallet balance too low
- "Slippage too high": Price impact exceeds tolerance

**Constitution Alignment**:
- Must validate all SDK responses (requirement: input validation)
- Must implement exponential backoff for 429 errors (requirement: RPC reliability)
- Must provide actionable error messages (requirement: error handling)

---

## Architecture Decisions

### Decision 1: Adapter Implementation Pattern

**Choice**: Follow existing DexAdapter interface pattern (UniswapV3Service, PancakeswapV3Service, VelodromeV2Service)

**Rationale**:
- Maintains consistency with existing codebase
- Requires minimal changes to DexModule and pair discovery
- Easy to test alongside existing adapters

**Implementation**:
```typescript
@Injectable()
export class OkxDexService implements DexAdapter {
    public readonly chain: ChainId;
    private readonly dexKey = 'okx';
    private client: OKXDexClient;

    constructor(
        chain: ChainId,
        private readonly configService: ConfigService,
        private readonly logger: LoggerService,
        private readonly walletService: WalletService,
    ) {
        this.chain = chain;
        this.client = this.initializeClient();
    }

    async estimateBuyQuoteToBase(...) { /* implement */ }
    async estimateSellBaseToQuote(...) { /* implement */ }
    async swapQuoteToBase(...) { /* implement */ }
    async swapBaseToQuote(...) { /* implement */ }
    async getBalanceQuote(...) { /* use ethers.js */ }
    async getBalanceBase(...) { /* use ethers.js */ }
}
```

### Decision 2: Balance Query Strategy

**Choice**: Use ethers.js directly instead of OKX Balance API

**Rationale**:
- Consistent with existing DEX adapters (they use ethers.js for balances)
- OKX Balance API is separate from DEX SDK (additional dependency)
- ethers.js already integrated in project for blockchain interactions
- Direct RPC calls faster than going through OKX servers

**Implementation**:
```typescript
async getBalanceQuote(quoteToken: string): Promise<string> {
    const provider = this.walletService.getProvider(this.chain);
    const balance = quoteToken === NATIVE_TOKEN
        ? await provider.getBalance(this.walletService.getAddress())
        : await this.erc20Balance(quoteToken);
    return balance.toString();
}
```

### Decision 3: OKX Client Lifecycle

**Choice**: Initialize OKX client once in constructor, validate credentials early

**Rationale**:
- Fail-fast if credentials missing (FR-017)
- Avoid re-initializing on every request (performance)
- Credentials loaded from environment variables (security)

**Implementation**:
```typescript
private initializeClient(): OKXDexClient {
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

    return new OKXDexClient({
        apiKey,
        secretKey,
        apiPassphrase,
        projectId,
        evm: {
            wallet: this.walletService.getEVMWallet(this.chain)
        }
    });
}
```

### Decision 4: Dry-Run Mode Support

**Choice**: Respect existing dry-run flag in WalletService

**Rationale**:
- Constitution requirement: dry-run mode mandatory
- Prevents accidental live transactions during testing
- Consistent with existing DEX adapters

**Implementation**:
```typescript
async swapQuoteToBase(...): Promise<DexSwapReceipt> {
    if (this.walletService.isDryRun()) {
        this.logger.info('OKX DEX quote→base swap (dry-run)', {...});
        return { txHash: `0xdryrun-${Date.now()}` };
    }

    // Live execution
    const swap = await this.client.dex.executeSwap({...});
    return { txHash: swap.transactionId };
}
```

---

## Configuration Schema

### New Environment Variables

```bash
# OKX DEX Credentials
OKX_API_KEY=your_api_key_here
OKX_SECRET_KEY=your_secret_key_here
OKX_API_PASSPHRASE=your_passphrase_here
OKX_PROJECT_ID=your_project_id_here
```

### New config.yaml Section

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

### Chain-Level Exclusion (non-aggr)

**IMPORTANT**: Aggregators are supported on ALL chains by default when enabled globally. To exclude an aggregator from a specific chain, use the `non-aggr` list:

```yaml
chains:
  arbitrum:
    rpc: ${ARBITRUM_RPC}
    tokenList:
      - symbol: USDT
        address: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69CCbb"
      - symbol: WIF
        address: "0x..."
    dexList:
      - key: uniswap_v3
        type: uniswap_v3
      - key: pancakeswap_v3
        type: pancakeswap_v3
    non-aggr: []  # Empty array = all enabled aggregators supported

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
    non-aggr: []  # Empty array = all enabled aggregators supported

  # Example: Exclude OKX from specific chain
  # polygon:
  #   rpc: ${POLYGON_RPC}
  #   tokenList: [...]
  #   dexList: [...]
  #   non-aggr: ['okx']  # OKX aggregator excluded from this chain
```

**Configuration Model**: Opt-out pattern
- Global enable: `aggregator-mulchain.{aggregatorKey}.enabled: true`
- Per-chain exclude: `chains.{chainId}.non-aggr: ['okx']`
- Default: All enabled aggregators supported on all chains

---

## Testing Strategy

### Unit Tests (TDD)

**File**: `code/ts/src/dex/okx-dex.service.spec.ts`

**Coverage** (>80% required by FR-020):
1. **Client initialization**: Valid credentials, missing credentials (should throw)
2. **Quote estimation**: Normal case, slippage calculation, error responses
3. **Balance queries**: Native token, ERC-20 token, zero balance
4. **Swap execution**: Dry-run mode, live mode (mocked SDK)
5. **Error handling**: Rate limits, timeouts, insufficient liquidity

### Integration Tests

**File**: `code/ts/test/dex/okx-dex.integration.spec.ts`

**Scenarios**:
1. **End-to-end quote → balance → swap flow** (with mocked SDK)
2. **Pair discovery integration**: OKX aggregator included in discovered pairs
3. **Multi-chain quotes**: Same token pair across Ethereum, Arbitrum, Base
4. **Error recovery**: SDK failure gracefully handled

**Note**: Integration tests use mocked OKX SDK responses (no live API calls).

---

## Performance Considerations

### SDK Call SLAs

- **Quotes**: <5 seconds per call (SC-001)
- **Balances**: <3 seconds per query (SC-002)
- **Pair discovery**: <10 seconds total at startup

### Rate Limiting

**OKX API Limits** (from docs):
- Unauthenticated: 10 requests/second
- Authenticated: 20 requests/second

**Mitigation**:
- Implement exponential backoff for HTTP 429 errors
- Cache quotes for duration of trading tick (1 second)
- Use circuit breaker pattern for sustained failures

### Memory Management

**Constitution requirement**: Avoid memory leaks in long-running processes

**Strategy**:
- OKX client is singleton (one instance per chain)
- No circular references in adapter
- Providers obtained from WalletService (already managed)

---

## Security Considerations

### Credential Management

✅ Constitution compliant:
- Credentials from environment variables only (not in config.yaml)
- Never log credential values
- Validate credentials at startup (fail-fast)

### Input Validation

**Constitution requirement**: Validate all external inputs

**Validations**:
1. **SDK responses**: Check for expected structure before parsing
2. **Token addresses**: Validate checksum format (ethers.js)
3. **Amounts**: Validate non-negative, reasonable bounds
4. **Chain IDs**: Validate against supported chains list

### Transaction Safety

**Constitution requirements**:
- Verify all parameters before live execution
- Double-check chain IDs (prevent mainnet/testnet confusion)
- Validate gas estimates are reasonable

**Implementation**:
```typescript
async swapQuoteToBase(...): Promise<DexSwapReceipt> {
    // Validate token addresses
    if (!this.isValidTokenAddress(baseToken)) {
        throw new Error(`Invalid base token address: ${baseToken}`);
    }

    // Validate amount
    const amountNum = BigInt(amountQuote);
    if (amountNum <= 0n) {
        throw new Error(`Amount must be positive: ${amountQuote}`);
    }

    // Gas estimation (via SDK quote)
    const quote = await this.client.dex.getQuote({...});
    const estimatedFee = parseFloat(quote.data[0].estimateGasFee);
    if (estimatedFee > 1.0) {  // $1 USD threshold
        this.logger.warn('High gas fee estimated', { estimatedFee, chain: this.chain });
    }

    // Execute swap
    const swap = await this.client.dex.executeSwap({...});
    return { txHash: swap.transactionId };
}
```

---

## Open Questions (Resolved)

All "NEEDS CLARIFICATION" items from Technical Context have been resolved:

- [x] SDK availability: ✅ `@okx-dex/okx-dex-sdk` v1.0.17
- [x] API structure: ✅ `OKXDexClient` with `dex.getQuote`, `dex.executeSwap`
- [x] Authentication method: ✅ 4 environment variables (API key, secret, passphrase, project ID)
- [x] Multi-chain support: ✅ All 5 required chains supported
- [x] TypeScript definitions: ✅ Full TypeScript support with types
- [x] Balance queries: ✅ Use ethers.js directly (consistent with existing adapters)

---

## Next Steps: Phase 1

With research complete, proceed to Phase 1 to generate:
1. **data-model.md** - Define Aggregator Swap Pair, TradingPairConfig extensions
2. **contracts/** - OKX DEX adapter interface contract
3. **quickstart.md** - Developer onboarding guide

**Gate Check**: ✅ Constitution satisfied, no blockers identified
