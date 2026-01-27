# Adding a New Chain

Configure a new blockchain network for arbitrage operations.

## Overview

A "chain" represents a blockchain network (e.g., Arbitrum, Base, Ethereum) with:
- JSON-RPC endpoint
- List of supported tokens with contract addresses
- List of available DEXes on that chain

## Configuration Steps

### 1. Add Chain to Types

**Location**: `src/common/types.ts`

```typescript
export type ChainId =
  | 'arbitrum'
  | 'base'
  | 'optimism'
  | 'ethereum'
  | 'polygon'
  | 'bsc'
  | 'monad'
  | 'your_new_chain';                      // ← Add your chain here
```

### 2. Add Chain to Config

**Location**: `config.yaml`

```yaml
chains:
  # ... existing chains ...

  your_new_chain:                    # ← Add new chain section
    rpc: ${YOUR_NEW_CHAIN_RPC}       # ← Reference env var
    tokenList:
      - symbol: USDT                  # ← Stablecoin on this chain
        address: "0x..."            # ← USDT contract address
      - symbol: WIF                   # ← Base token on this chain
        address: "0x..."            # ← Base token address
      - symbol: PEPE
        address: "0x..."
    dexList:
      - key: uniswap_v3              # ← DEX on this chain
        type: uniswap_v3
      - key: your_custom_dex            # ← Additional DEXes
        type: generic_v3
```

### 3. Add Environment Variables

**Location**: `.env`

```bash
YOUR_NEW_CHAIN_RPC=https://your-rpc-provider.com
```

**RPC Endpoints Should**:
- Be public or privately operated
- Support standard JSON-RPC methods
- Provide reasonable latency (<500ms for eth_call)
- Include chain ID verification

### 4. Verify Token Addresses

For each token in `tokenList`:

1. **Deploy or find contract** on the new chain
2. **Verify ABI** supports standard ERC-20 methods (`balanceOf`, `transfer`, `approve`)
3. **Test small amount**:
   ```bash
   # Using ethers.js or similar
   await contract.balanceOf(walletAddress);
   ```

### 5. Add Token to Global Lists (Optional)

If you want this chain to participate in arbitrage:

**Location**: `config.yaml` → `tokens`

```yaml
tokens:
  base:
    - WIF
    - PEPE
    - your_new_token           # ← Add if token should be base in arbitrage
  quote:
    - USDT
```

**No change required** if token is only traded, not used as base/quote in pairs.

### 6. Test Configuration

```bash
cd code/ts
pnpm config:print | grep your_new_chain
```

Verify output shows your chain configuration with correct RPC URL and token addresses.

## Adding DEX to New Chain

After adding the chain, integrate DEXes:

1. **See [Adding a DEX](adding-dex.md)** for DEX integration steps
2. **Register DEX** in `your_new_chain.dexList` with appropriate `key` and `type`
3. **Add DEX adapter** implementation if not existing

## Validation

Run these checks after configuration:

### Config Validation

```bash
pnpm test src/utils/config/config.schema.spec.ts
```

Should pass without errors.

### Discovery Validation

```bash
pnpm test src/orchestrator/pair-discovery/pair-discovery.service.spec.ts
```

Should include your chain in:
- Swap pair generation
- Arbitrage pair derivation

### Runtime Check

```bash
APP_ENV=dev pnpm start:dev
```

Verify logs show:
- Chain initialization for `your_new_chain`
- DEX registration
- Pair discovery includes routes on/from `your_new_chain`

## Common Issues

| Issue | Symptoms | Fix |
|--------|-----------|------|
| RPC connection fails | `Error: could not detect network` | Verify RPC URL is correct and reachable; check API rate limits |
| Token not found | `Error: call revert exception` | Verify contract address is correct for chain; token may not be deployed |
| DEX not found | `No chain advertises dex key uniswap_v3` | Ensure `dexList` entry matches adapter's `dexKey` |
| Chain ID mismatch | `Error: chainId mismatch` | Verify RPC returns correct chain ID (e.g., 42161 for Arbitrum) |

## Example: Adding Optimism

```yaml
# types.ts
export type ChainId = ... | 'optimism';

# config.yaml
chains:
  optimism:
    rpc: ${OPTIMISM_RPC}
    tokenList:
      - symbol: USDT
        address: "0x94b008aA0056156727158846102e9433cF8e81"
      - symbol: PEPE
        address: "0x..."
    dexList:
      - key: velodrome_v2
        type: velodrome_v2

# .env
OPTIMISM_RPC=https://mainnet.optimism.io
```

## Related Documentation

- [Config Reference](../config/reference.md) - Full config structure
- [Adding a DEX](adding-dex.md) - DEX integration guide
- [Fast-Fail Errors](../config/fast-fail-errors.md) - Configuration error messages
- [Architecture Interfaces](../architecture/interfaces.md) - TypeScript type definitions
