# Core Sequences

Key operational flows for the arbitrage system.

## Pair & Route Discovery (Startup)

**Participants**: ConfigService → DexModule provider factories → PairDiscovery → Logger

**Config-first DEX initialization flow**:
1. Nest bootstraps modules declared in code
2. `ConfigService` loads `config.yaml` and optional `config.{APP_ENV}.yaml`
3. `DexModule` provider factories read the merged config to decide which DEX adapters to instantiate
4. Only configured DEX adapters are created; unconfigured DEX tokens resolve to `null`
5. `PriceMonitorModule` builds its quote-provider registry from the adapters that were actually instantiated

**Flow** (aggregator-first):
1. Discovery reads global token lists: `config.tokens.{base,quote}`
2. If `aggregatorMultichain` has any enabled aggregators:
    - **Aggregator mode** (primary): Uses aggregator keys as venue providers
    - Enumerates enabled aggregators (e.g., `okx`)
    - Builds `swapPair`s using aggregator keys instead of native DEXes
    - Respects `chains.*.nonAggr` to exclude specific aggregators per chain
3. If no aggregators enabled:
    - **Native DEX mode** (fallback): Uses `chains.*.dexList` entries
    - For each chain in `config.chains`:
      - Builds `swapPair`s for every `(base,quote)` where both tokens exist in `tokenList`
      - Each DEX in `dexList` generates a `swapPair` entry
4. For each `(base,quote)` pair appearing on ≥2 venues:
    - Creates `TradingPairConfig` routes `(chainM, dexJ) → (chainN, dexK)`
    - Assigns deterministic ID: `WIF~USDT~okx+arbitrum~okx+base` (aggregator mode) or `WIF~USDT~uniswap_v3+arbitrum~uniswap_v3+base` (native mode)
5. Applies deterministic sort: `baseToken → quoteToken → chainM → chainN → dexJ → dexK`

**Behavior**:
- **Aggregator enabled**: Native DEX discovery is **disabled** (`includeNativeDex: false`)
- **No aggregators**: Native DEX discovery runs, aggregator mode is skipped

**Fast-Fail Rules** (aborts startup):
- **Fast-fail A**: Token in `tokens.*` never appears in any `chains.*.tokenList`
- **Fast-fail B**: No `swapPair`s discovered (no chain supports any pair)
- **Fast-fail C**: No `arbitrargePairs` (never ≥2 venues per pair)
- **Fast-fail D**: Aggregator enabled but missing credentials (e.g., OKX env vars)

**Output**: In-memory `TradingPairConfig[]` consumed by Orchestrator, PriceMonitor, RiskManager.

---

## Price Loop (1s Cadence)

**Participants**: Orchestrator → PriceMonitor → RiskManager → (execute)

**Per Tick**:
1. Iterate over all discovered `TradingPairConfig[]`
2. For each pair, call `PriceMonitor.getPairPrices(pair)`:
   - Concurrently fetches `priceM` (chainM/dexJ) and `priceN` (chainN/dexK)
3. Compute profitability:
   ```
   forward = (priceN / priceM - 1) - totalFeeRate
   backward = (priceM / priceN - 1) - totalFeeRate
   ```
4. Build runtime context: `PairRuntimeState`, global PnL/paused flags
5. Call `RiskManager.shouldExecute()` for both directions
6. Collect all valid `ExecutionPlan`s
7. Select at most one plan (e.g., highest expected profit)
8. Execute if plan exists; else sleep until next tick

**Latency Budget**: Full tick should complete within ~1s to allow next cycle.

---

## Execute: Forward Arbitrage (M → N)

**Participants**: Orchestrator, Dex M, Bridge, Dex N, Wallet, Logger

**Steps**:
1. Determine `amountQuote` per plan (full-amount or capped)
2. **Dex M** (swap quote→base):
   - Call `swapQuoteToBase` with `slippageBps`
   - Wait for tx confirmation; record txHash
3. **Bridge** (bridge base token):
   - Call `bridgeToken` from chain M to chain N
   - Get `transferId`; call `waitForSettlement`
   - Retries: exponential backoff (base 250ms, max 5s)
4. **Dex N** (swap base→quote):
   - Call `swapBaseToQuote` (all or plan-specified)
   - Confirm tx
5. **Profit realization**:
   - Compute profit = `(quote on N after sell) - (amountQuote + fees)`
   - Retain `gasReservePctOfProfit` locally on N (e.g., 3%)
   - Bridge back `bridgeBackPct` of quote to M (e.g., 92%)
   - Leave remainder (5-10%) on N as realized profit
6. **Update state**: Per-pair and global PnL; reconcile balances
7. **Log**: End-to-end metrics including `pair.id`, direction, tx hashes, transferId

**Backward arbitrage** mirrors chains/DEXes in reverse order.

---

## Bridge Settlement & Reconciliation

**Flow**:
1. Poll settlement status by `transferId` with bounded retries (5 attempts, exponential backoff)
2. **On success**:
   - Log start_ts/end_ts, from/to, amounts, feeUSD
   - Resume normal execution (sell step)
3. **On timeout**:
   - Mark pending; skip sell step
   - Resume/repair in next loop via reconciliation job
4. **Always log**:
   - transferId, from, to, token, amount_in, amount_out, settled flag

---

## Stop-Loss & Pause

**Flow**:
1. Maintain rolling PnL vs initial capital
2. After each execution, check: `totalPnLPct >= stopLossPct`
3. **If triggered**:
   - Set global `paused = true`
   - Stop all new executions
   - Log alert with current loss percentage
4. Operator manually resets after review

---

## Fail-Fast Validation (Bootstrap)

**When**: Orchestrator bootstraps all components

**Checks**:
1. **ConfigService**: At least one base token, one quote token, ≥2 chains
2. **DexModule provider factories**: Decide which adapter providers to instantiate from merged runtime config
   - Native DEX adapters instantiate only when some `chains.*.dexList` advertises their `dexKey`
   - Aggregator adapters instantiate only when `aggregatorMultichain.*.enabled = true`
3. **Configured DEX Adapters**: Each instantiated adapter resolves target chain from config and fast-fails on invalid config
   - If a configured adapter cannot resolve its runtime chain or credentials, it throws immediately
4. **PairDiscovery**: Runs discovery flow; throws on fast-fail A/B/C

**Result**: If any check fails, process exits with clear error before loop starts.
