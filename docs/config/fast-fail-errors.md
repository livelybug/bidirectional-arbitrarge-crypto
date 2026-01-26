# Fast-Fail Errors Reference

All configuration errors that abort startup with clear messages and fixes.

## Error List

| Error Code | Full Message | Meaning | Fix |
|-------------|---------------|----------|------|
| **Fast-fail A** | `Config error (Fast-fail A): token symbol "${s}" is listed in tokens.* but never appears in any chains.*.tokenList` | Token in `tokens.base` or `tokens.quote` not found on any chain | Add the token to at least one `chains.*.tokenList` array, or remove it from `tokens.*` |
| **Fast-fail B** | `Config error (Fast-fail B): no eligible swapPairs discovered; ensure tokens.* and chains.*.tokenList/dexList are configured consistently` | No chain has both base and quote tokens together | Ensure at least one chain includes both tokens in its `tokenList` and a DEX in `dexList` |
| **Fast-fail C** | `Config error (Fast-fail C): no arbitrargePairs discovered; ensure at least two venues share the same base/quote pair` | Pairs exist but never on ≥2 venues | Add a second chain/DEX combination that supports the same `(base, quote)` pair |
| **Fast-fail D** | `Config error (Fast-fail D): aggregator '${aggKey}' is enabled but missing required credentials: ${missingKeys.join(', ')}` | Aggregator enabled but environment credentials missing | Add missing env vars (e.g., `OKX_API_KEY`, `OKX_SECRET_KEY`, `OKX_API_PASSPHRASE`, `OKX_PROJECT_ID`) to `.env` |
| **No chain advertises DEX** | `No chain advertises dex key ${dexKey}; update config.chains accordingly` | DEX adapter exists but no chain lists it in `dexList` | Add the `dexKey` to at least one `chains[chainId].dexList` entry |
| **No chains configured** | `No chains configured; unable to initialize adapter for ${dexKey}` | `chains` object is empty or missing | Add at least one chain configuration with `rpc`, `tokenList`, `dexList` to `config.yaml` |

## Common Scenarios

### Scenario 1: Adding a new token (e.g., APU)

**Error**: Fast-fail A for token `APU`

**Fix**:
```yaml
# config.yaml
tokens:
  base:
    - WIF
    - PEPE
    - APU    # ← Add here
```

**AND** add token address to at least one chain:
```yaml
chains:
  arbitrum:
    tokenList:
      - symbol: USDT
        address: "0x..."
      - symbol: APU    # ← Add address here
        address: "0x..."
```

### Scenario 2: Missing DEX reference

**Error**: `No chain advertises dex key pancakeswap_v3`

**Fix**:
```yaml
chains:
  bsc:
    dexList:
      - key: pancakeswap_v3           # ← Ensure this key exists
        type: generic_v3
```

### Scenario 3: Adding OKX aggregator without credentials

**Error**: Fast-fail D for aggregator `okx`

**Fix**:
```bash
# .env
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_API_PASSPHRASE=your_passphrase
OKX_PROJECT_ID=your_project_id
```

```yaml
# config.yaml
aggregatorMultichain:
  okx:
    enabled: true    # ← Ensure enabled if using OKX
```

### Scenario 4: Per-chain aggregator exclusion (nonAggr)

**Warning**: `Aggregator 'okx' in chains.arbitrum.non-aggr is not defined in aggregator-mulchain config`

**Note**: This is a non-fatal warning logged at startup. The chain will skip the excluded aggregator.

**Fix**: Either:
1. Remove `nonAggr` entry if aggregator is not intended to be excluded
2. Add the aggregator to `aggregatorMultichain` if it should be available

**Example**:
```yaml
# config.yaml
chains:
  arbitrum:
    nonAggr: ['okx']  # Exclude OKX on this chain

aggregatorMultichain:
  okx:
    enabled: true  # OKX is defined, warning won't trigger
```

### Scenario 4: Removing a token that's the only one on a chain

**Error**: Fast-fail C (no arbitrage pairs possible)

**Fix**: Either:
1. Keep the token and add a second venue for the same pair
2. Or remove the token from `tokens.base` if it's only on one chain

## Validation in Code

**Pair Discovery** (`src/orchestrator/pair-discovery/`):
- Checks token coverage across all chains
- Validates each `swapPair` has both base/quote in `tokenList`
- Ensures ≥2 venues per `(base, quote)` before building routes
- Validates aggregator credentials (Fast-fail D)
- Warns on `chains.*.nonAggr` references to undefined aggregators (non-fatal)

**ConfigService** (`src/utils/config/`):
- Runs `appConfigSchema.parse(raw)` on bootstrap
- Throws Zod error if any field violates schema rules
- Does NOT catch errors - Nest bootstrap fails immediately

**DEX Adapters** (`src/dex/`):
- Each adapter throws if `config.chains` does not advertise its `dexKey`
- Example: `UniswapV3Service` scans `chains` for `uniswap_v3` in `dexList`

## Debugging Tips

1. **Check exact error message** - Copy-paste from logs to match above table
2. **Verify chain/DEX keys** - Ensure keys in `dexList` match adapter expectations
3. **Check token coverage** - Run `pnpm config:print` and verify all `tokens.*` symbols appear in `chains.*.tokenList`
4. **Review aggregator config** - If using OKX/other aggregators, verify enabled flag AND credentials
5. **Check for typos** - Common: `pancakeswap_v3` vs `pancakeswap_v3`, `uniswap_v3` vs `uniswapV3`

## Related Documentation

- [Schema Validation](config/schema.md) - Zod rules and constraints
- [Config Reference](config/reference.md) - Full config example
- [Pair Discovery](implementation/pair-discovery.md) - Algorithm details
