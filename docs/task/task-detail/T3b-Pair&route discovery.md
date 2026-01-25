### Arbitrarge Pairs Discovery Flow

Conceptual flow using `symbolPair`, `swapPair`, and `arbitrargePair`:

> Mapping to implementation types: in code, each `arbitrargePair` will be represented as a `TradingPairConfig` where `swapPair1` provides `(chainM, dexJ)` and `swapPair2` provides `(chainN, dexK)` for a given `(baseToken, quoteToken)`.

1. **Enumerate `symbolPair` from global tokens**  
	- From `config.tokens.base` and `config.tokens.quote`, build the cartesian product of base×quote symbols. Example:

```yaml
tokens:
  base:
    - WIF
    - PEPE
  quote:
    - USDT
    - USDC
```

leads to:

```text
symbolPairs = [
  { base: WIF,  quote: USDT },
  { base: WIF,  quote: USDC },
  { base: PEPE, quote: USDT },
  { base: PEPE, quote: USDC },
]
```

	- Determinism: iterate `base` and `quote` arrays in sorted order so `symbolPairs` is always constructed in the same order for a given `config.yaml`.

2. **Generate `swapPair`s per chain/DEX for each `symbolPair`**  
	- For each `symbolPair = { base, quote }` and for each `chainId` in sorted `Object.keys(config.chains)`:  
		- Check `chains[chainId].tokenList` for both `base` and `quote` symbols.  
		- If both exist, then for each DEX in `chains[chainId].dexList` create a `swapPair`:

```text
swapPair = {
  swapPairId: `${base}~${quote}~${dexKey}~${chainId}`,
  base,
  quote,
  dex: dexKey,
  chain: chainId,
}
```

	- Example (simplified from current `config.yaml`):

```yaml
chains:
  arbitrum:
    tokenList:
      - symbol: USDT
      - symbol: WIF
    dexList:
      - key: uniswap_v3
      - key: camelot_v3
  base:
    tokenList:
      - symbol: USDT
      - symbol: WIF
      - symbol: PEPE
    dexList:
      - key: uniswap_v3
```

produces (for brevity):

```text
swapPairs = [
  { swapPairId: WIF~USDT~uniswap_v3~arbitrum, base: WIF,  quote: USDT, dex: uniswap_v3, chain: arbitrum },
  { swapPairId: WIF~USDT~camelot_v3~arbitrum, base: WIF,  quote: USDT, dex: camelot_v3, chain: arbitrum },
  { swapPairId: WIF~USDT~uniswap_v3~base,     base: WIF,  quote: USDT, dex: uniswap_v3, chain: base },
  { swapPairId: PEPE~USDT~uniswap_v3~base,    base: PEPE, quote: USDT, dex: uniswap_v3, chain: base },
]
```

	- **Fast-fail A – missing token coverage**: if any symbol in `tokens.base` or `tokens.quote` never appears in *any* `chains.*.tokenList`, throw:  
		- `Config error: token symbol "${s}" is listed in tokens.* but never appears in any chains.*.tokenList`.
	- **Fast-fail B – no `swapPair`s**: if, after processing all chains/DEXes, `swapPairs.length === 0`, throw:  
		- `Config error: no eligible swapPairs discovered; ensure tokens.* and chains.*.tokenList/dexList are configured consistently`.
	- **Adapter availability**: for each `swapPair.dex`, ensure there is a corresponding adapter/token in `src/common/tokens.ts` (or equivalent). If not, treat this as a configuration error and fail fast rather than silently skipping.

3. **Derive `arbitrargePair`s from `swapPair`s**  
	- Conceptually, an `arbitrargePair` ties together two venues (chain+DEX) for the same `(base, quote)` pair.  
	- For each ordered pair of `swapPair1`, `swapPair2` in `swapPairs` where:  
		- `swapPair1.base === swapPair2.base` and `swapPair1.quote === swapPair2.quote`, and  
		- `swapPair1.swapPairId !== swapPair2.swapPairId` (avoid self-pairing),  
	- Create:

```text
arbitrargePair = {
  arbitrargePairId:
    `${base}~${quote}~${swapPair1.dex}+${swapPair1.chain}~${swapPair2.dex}+${swapPair2.chain}`,
  swapPair1,
  swapPair2,
}
```

	- Same-chain and cross-chain routes are both allowed:  
		- Same-chain DEX↔DEX: `swapPair1.chain === swapPair2.chain` but `swapPair1.dex !== swapPair2.dex`.  
		- Cross-chain: `swapPair1.chain !== swapPair2.chain` (DEX keys may be equal or different).
	- In implementation, each `arbitrargePair` becomes a `TradingPairConfig` with:  
		- `baseToken = base`, `quoteToken = quote`.  
		- `chainM = swapPair1.chain`, `dexJ = swapPair1.dex`.  
		- `chainN = swapPair2.chain`, `dexK = swapPair2.dex`.  
		- `id = arbitrargePairId` (or a similar deterministic encoding).
	- **Fast-fail C – no `arbitrargePair`s**: if `arbitrargePairs.length === 0`, throw:  
		- `Config error: no arbitrargePairs discovered; ensure at least two venues share the same base/quote pair`.

4. **Deterministic ordering and stability**  
	- Construct `symbolPairs`, `swapPairs`, and `arbitrargePairs` using sorted iterations over:  
		- Base symbols, then quote symbols.  
		- Chain ids (`chainId` strings).  
		- DEX keys within each chain.
	- After building `arbitrargePairs` (or the derived `TradingPairConfig[]` list), apply a final sort by:

```text
(baseToken ASC, quoteToken ASC, chainM ASC, chainN ASC, dexJ ASC, dexK ASC)
```

	- This ensures the exact same `config.yaml` always yields the same ordered discovery output, simplifying testing and debugging.

Error modes summary (aligned with the flow):

- **Missing token coverage** – any symbol in `tokens.base` or `tokens.quote` not present in any `chains.*.tokenList` must fail discovery with a clear config error (Fast-fail A).  
- **No swapPairs** – if no venues support any `(base, quote)` from `tokens`, discovery must fail (Fast-fail B).  
- **No arbitrargePairs** – if `swapPairs` exist but there is never more than one venue per `(base, quote)`, discovery must fail (Fast-fail C).  
- **Unsupported DEX keys** – any DEX key present in `chains.*.dexList` but lacking a corresponding adapter/token mapping should be treated as a hard configuration error rather than silently skipped.  
- **Non-deterministic iteration (to avoid)** – unsorted iteration over tokens, chains, or DEX lists can lead to unstable output; sorting at each step is required.

These rules apply whether the algorithm is coded as a pure helper or wrapped in a Nest discovery service. The key behavior is that configuration gaps or drifts are surfaced early and loudly, and the final `TradingPairConfig[]` universe of arbitrageable pairs is deterministic for a given config.

### Multi-Chain Dex Aggregator Arbitrarge Pairs Discovery Flow

Conceptual flow using `symbolPair`, `swapPair`, and `arbitrargePair` for a multi-chain DEX aggregator (e.g., OKX DEX aggregator).

> Mapping to implementation types: in code, each `arbitrargePair` will still be represented as a `TradingPairConfig` where `swapPair1` provides `(chainM, aggJ)` and `swapPair2` provides `(chainN, aggK)` for a given `(baseToken, quoteToken)`.
>
> Note: for minimal churn, this can reuse existing `TradingPairConfig` fields (`dexJ`, `dexK`) to store aggregator keys (e.g. `'okx'`). In that case, interpret `(chainId, dexKey)` as a generic “venue key” that may be either a native DEX key or an aggregator key.

New fields in config changes:

```yaml
aggregator-mulchain:
  okx:
    enabled: true
```

New field sin .env file
```dotenv
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_API_PASSPHRASE=your_passphrase
OKX_PROJECT_ID=your_project_id
```

1. **Enumerate `symbolPair` from global tokens**
	- From `config.tokens.base` and `config.tokens.quote`, build the cartesian product of base×quote symbols. Example:

```yaml
tokens:
  base:
    - WIF
    - PEPE
  quote:
    - USDT
    - USDC
```

leads to:

```text
symbolPairs = [
  { base: WIF,  quote: USDT },
  { base: WIF,  quote: USDC },
  { base: PEPE, quote: USDT },
  { base: PEPE, quote: USDC },
]
```

	- Determinism: iterate base then quote arrays in sorted order.

2. **Enumerate aggregator keys**
	- Let `aggKeys = sorted(Object.keys(config['aggregator-mulchain'] ?? {}))`.
	- Each aggregator key (e.g. `okx`) represents an available “venue provider” across multiple chains.
	- Credentials, like OKX_SECRET_KEY and OKX_API_PASSPHRASE are treated as secrets and should be env-backed; discovery should not log credential values.

3. **Generate `swapPair`s per chain/aggregator for each `symbolPair`**
	- Replace native DEX venue enumeration with aggregator venue enumeration.
	- For each `symbolPair = { base, quote }`, for each `chainId` in sorted `Object.keys(config.chains)`:
		- Check `chains[chainId].tokenList` for both `base` and `quote` symbols.
		- If both exist, then for each `aggrKey` in `aggKeys` create a `swapPair`:

```text
swapPair = {
  swapPairId: `${base}~${quote}~${aggrKey}~${chainId}`,
  base,
  quote,
  aggregator: aggrKey,
  chain: chainId,
}
```

	- **Fast-fail A – missing token coverage (unchanged)**: if any symbol in `tokens.base` or `tokens.quote` never appears in *any* `chains.*.tokenList`, throw:
		- `Config error: token symbol "${s}" is listed in tokens.* but never appears in any chains.*.tokenList`.
	- **Fast-fail B – no `swapPair`s (unchanged)**: if `swapPairs.length === 0`, throw:
		- `Config error: no eligible swapPairs discovered; ensure tokens.* and chains.*.tokenList/dexList are configured consistently`.
		- (In aggregator mode, interpret this as: tokens.* and chains.*.tokenList are inconsistent, or `aggregator-mulchain` is missing/empty.)
	- **Adapter availability (aggregator)**: for each `swapPair.aggregator`, ensure there is a corresponding aggregator adapter/token mapping (equivalent of the DEX adapter registry). If not, treat this as a configuration error and fail fast rather than silently skipping.

4. **Derive `arbitrargePair`s from `swapPair`s (same-venue allowed)**
	- Conceptually, an `arbitrargePair` ties together two legs (entry and exit) for the same `(base, quote)`.
	- For each ordered pair of `swapPair1`, `swapPair2` in `swapPairs` where:
		- `swapPair1.base === swapPair2.base` and `swapPair1.quote === swapPair2.quote`,
		- **Self-pairing is allowed** (same `swapPairId` / same venue): this models “buy” and “sell” that both go through the same aggregator on the same chain, where the aggregator may route to different underlying DEX pools and produce a price gap.
	- Create:

```text
arbitrargePair = {
  arbitrargePairId:
    `${base}~${quote}~${swapPair1.aggregator}+${swapPair1.chain}~${swapPair2.aggregator}+${swapPair2.chain}`,
  swapPair1,
  swapPair2,
}
```

	- Same-chain and cross-chain routes are both allowed:
		- Same-chain: `swapPair1.chain === swapPair2.chain` (aggregator keys may be equal or different).
		- Cross-chain: `swapPair1.chain !== swapPair2.chain`.
	- In implementation, each `arbitrargePair` becomes a `TradingPairConfig` with:
		- `baseToken = base`, `quoteToken = quote`.
		- `chainM = swapPair1.chain`, `aggJ = swapPair1.aggregator`.
		- `chainN = swapPair2.chain`, `aggK = swapPair2.aggregator`.
		- `id = arbitrargePairId` (or a similar deterministic encoding).

5. **Deterministic ordering and stability (extend ordering to aggregator keys)**
	- Construct `symbolPairs`, `swapPairs`, and `arbitrargePairs` using sorted iterations over:
		- Base symbols, then quote symbols.
		- Chain ids (`chainId` strings).
		- Aggregator keys (`aggKeys`).
	- After building `arbitrargePairs` (or the derived `TradingPairConfig[]` list), apply a final sort by:

```text
(baseToken ASC, quoteToken ASC, chainM ASC, chainN ASC, aggJ ASC, aggK ASC)
```

6. Error modes summary (aligned with the flow, aggregator edition):

- **Missing token coverage** – any symbol in `tokens.base` or `tokens.quote` not present in any `chains.*.tokenList` must fail discovery (Fast-fail A).
- **No swapPairs** – if no chain supports any `(base, quote)` from `tokens` (or no aggregators are configured), discovery must fail (Fast-fail B).
- **Unsupported aggregator keys** – any aggregator key referenced by `aggregator-mulchain` but lacking a corresponding adapter/registry mapping should be treated as a hard configuration error rather than silently skipped.
- **Non-deterministic iteration (to avoid)** – unsorted iteration over tokens, chains, or aggregator keys can lead to unstable output; sorting at each step is required.