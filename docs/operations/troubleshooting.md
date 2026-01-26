# Troubleshooting

Common issues and solutions for the arbitrage bot.

## Startup Issues

### Config Error: Token Not Found

**Error**:
```
Config error (Fast-fail A): token symbol "WIF" is listed in tokens.* but never appears in any chains.*.tokenList
```

**Cause**: Token in `config.yaml` `tokens.base` or `tokens.quote` not defined in any `chains.*.tokenList`

**Fix**: Add token to at least one chain's `tokenList`:
```yaml
chains:
  arbitrum:
    tokenList:
      - symbol: WIF          # ← Add here
        address: "0x..."
```

### Config Error: No Chain Advertises DEX

**Error**:
```
No chain advertises dex key pancakeswap_v3; update config.chains accordingly
```

**Cause**: `dexKey` in `dexList` but no adapter implements it

**Fix**: Add `dexList` entry to chain:
```yaml
chains:
  bsc:
    dexList:
      - key: pancakeswap_v3      # ← Ensure this key exists
        type: generic_v3
```

### Config Error: No Arbitrage Pairs

**Error**:
```
Config error (Fast-fail C): no arbitrargePairs discovered; ensure at least two venues share the same base/quote pair
```

**Cause**: Token pairs exist but never on ≥2 venues

**Fix**: Add second venue:
- Add second chain with same tokens
- Add second DEX on same chain
- Enable aggregator to provide multi-chain venue

## Runtime Issues

### Orchestrator Loop Not Starting

**Symptom**: Logs show "OrchestratorService created" but no 1s loop

**Cause**: `PairDiscoveryService` returned empty `TradingPairConfig[]`

**Fix**:
1. Check pair discovery logs: Look for `"Pair discovery complete"` message
2. If missing, verify `tokens.*` and `chains.*` alignment
3. Ensure ≥2 venues support at least one `(base, quote)` pair

### No Price Data

**Symptom**: Logs show `"priceM": 0` or `"priceN": 0`

**Cause**:
- DEX adapter returning `price: 0` (stub behavior in dry-run)
- RPC endpoint unreachable
- Token not supported on configured DEX

**Fix**:
1. Verify RPC endpoints in `.env`: `ARBITRUM_RPC`, `BASE_RPC`, etc.
2. Check adapter logs for connection errors
3. Test DEX quote endpoint manually (if API-based)
4. Verify token addresses in `config.yaml`

### Bridge Settlement Timeout

**Symptom**: Logs show `"Your bridge settlement timeout"` after 15+ minutes

**Cause**:
- Bridge provider delayed (congestion, liquidity issues)
- Transfer failed but not reported
- Chain outage

**Fix**:
1. Check bridge status page for transferId
2. Increase `ops.bridgeSettlementTimeoutMs` (if configurable)
3. Reduce trade frequency (increase `loopIntervalMs`)
4. Verify bridge provider status page

### Wallet Balance Mismatch

**Symptom**: PnL calculations don't match actual wallet balances

**Cause**:
- Bridge settlement not completed before PnL attribution
- Gas costs higher than estimated
- Slippage exceeded but trade executed

**Fix**:
1. Wait for bridge settlement before PnL calculation (see [Core Sequences](../architecture/sequences.md))
2. Check actual gas costs vs estimates
3. Review slippage logs vs thresholds

## Testing Issues

### Tests Fail with "Module not found"

**Error**:
```
Cannot find module '@/...' or 'Module './...' not found
```

**Cause**: Incorrect import path in test file

**Fix**: Use relative paths from `src/`:
```typescript
// Wrong
import { YourService } from '@/dex/your-dex.service';

// Correct
import { YourService } from '../dex/your-dex.service';
```

### Jest Timeout in CI

**Error**:
```
Jest did not exit in one second for the following reasons...
```

**Cause**: Test hanging (infinite loops, unresolved promises)

**Fix**:
1. Add `jest.setTimeout(10000)` to test file
2. Check for missing `await` keywords
3. Review async test logic for unhandled promises

### Mock Return Values Don't Match Expected

**Error**:
```
Expected: { price: 100 } but received { price: 0 }
```

**Cause**: Mock implementation incorrect

**Fix**:
```typescript
const mockFn = jest.fn().mockReturnValue({ price: 100 });  // Correct
const mockFn = jest.fn().mockImplementation(() => ({ price: 100 }));  // Also correct

// Wrong
const mockFn = jest.fn().mockReturnValue({ price: 0 });
```

## Performance Issues

### High Memory Usage

**Symptom**: Node process uses >1GB RAM

**Cause**:
- Accumulating large in-memory datasets
- Not cleaning up after operations
- Circular references in data structures

**Fix**:
1. Profile with `node --inspect --heap-prof`
2. Limit in-memory history (keep only last N entries)
3. Ensure event listeners are removed when not needed

### Slow Loop Execution

**Symptom**: Orchestrator tick takes >1s, loop accumulates delay

**Cause**:
- Synchronous operations blocking loop
- Network latency > expected (500ms+ per price fetch)
- Too many pairs evaluated per tick

**Fix**:
1. Use parallel price fetching (`Promise.all`)
2. Increase `ops.loopIntervalMs` if latency is expected
3. Reduce number of evaluated pairs
4. Optimize expensive operations (caching, batching)

## Environment-Specific Issues

### Dev Environment: "Cannot connect to RPC"

**Error**:
```
Error: could not detect network (request=0)
```

**Cause**: Wrong `ARBITRUM_RPC` URL or testnet vs mainnet mismatch

**Fix**:
1. Verify RPC URL is correct and reachable
2. Check chain ID matches network (e.g., 42161 for Arbitrum)
3. Ensure wallet has balance on testnet before trying trades

### Production: "Keystore password incorrect"

**Error**:
```
Error: Incorrect keystore password
```

**Cause**: Wrong password in env var or failed decryption

**Fix**:
1. Verify `KEYSTORE_PASSWORD` env var
2. Regenerate keystore with known password
3. Check keystore file integrity

## Debugging Tips

### Enable Verbose Logging

```bash
# From code/ts
APP_ENV=dev LOG_LEVEL=debug pnpm start:dev
```

Logs will include:
- `includeCaller: true` (source file/line)
- All debug-level messages
- Full context objects

### Check Configuration

```bash
# Print effective config
pnpm config:print | jq '.'
```

Look for:
- Missing RPC URLs
- Empty token lists
- Disabled DEXes
- Suspicious numeric values

### Test Single Component

```bash
# Run only pair discovery tests
pnpm test src/orchestrator/pair-discovery/pair-discovery.service.spec.ts

# Run only config tests
pnpm test src/utils/config/config.schema.spec.ts
```

### Isolate with Dry-Run

```yaml
# config.yaml
ops:
  dryRun: true  # Prevents on-chain transactions
```

Use to test:
- Price monitoring logic
- Risk manager thresholds
- Orchestrator decision-making

Without risking real funds.

## Getting Help

If issue persists:

1. **Check logs**: Look for error messages with context (`opId`, `chain`, `dexKey`)
2. **Review documentation**:
   - [Fast-Fail Errors](../config/fast-fail-errors.md) - Startup errors
   - [Error Handling](../architecture/error-handling.md) - Retry patterns
   - [Command Reference](commands.md) - Build/test/run commands
3. **Verify environment**: Run `pnpm config:print` and check values
4. **Check CI status**: Review `.github/workflows/ci.yml` output for failures

## Common Gotchas

- **Forgot to run tests**: `pnpm build` succeeds but tests fail → deployment breaks
- **Environment mismatch**: Code expecting `test` config but running in `dev`
- **Aggregator enabled without credentials**: Fast-fail D prevents startup
- **Wrong RPC for chain**: Arbitrum config but Base RPC used
- **Pair ID typos**: `WIF~USDT~uniswap_v3+arbitrum~uniswap_v3+base` (correct) vs `WIF~USDT~uniswap_v3+base~uniswap_v3+base` (wrong - same chain twice)

## Related Documentation

- [Architecture Error Handling](../architecture/error-handling.md) - Retry strategies
- [Core Sequences](../architecture/sequences.md) - Operational flows
- [Deployment Guide](deployment.md) - Environment setup
