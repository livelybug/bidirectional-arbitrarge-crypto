# Config Reference

Complete `config.yaml` structure with inline comments.

```yaml
# Multi-chain aggregator configuration (MANDATORY primary venue provider)
# Must define at least one aggregator and at least one enabled aggregator.
# Standalone native DEXes are optional supplemental venues configured via chains.*.dexList.
aggregatorMultichain:
  okx:
    enabled: true                      # Enable OKX aggregator
  # Add more aggregators here as needed
  # Example:
  # kyber:
  #   enabled: false

# Global token symbols used to build trading pairs
tokens:
  base:
    - WIF      # dogwifhat
    - PEPE     # pepe token
    - BRETT    # Brett token
  quote:
    - USDT     # Tether USD
    # - USDC   # Future: USD Coin

# Per-chain configuration
chains:
  # Arbitrum
  arbitrum:
    rpc: ${ARBITRUM_RPC}              # JSON-RPC endpoint (inject from .env)
    tokenList:
      - symbol: USDT
        address: "0x..."              # Contract address on Arbitrum
      - symbol: WIF
        address: "0x..."
    dexList:                             # Optional standalone native DEXes on this chain
      - key: uniswap_v3               # Unique DEX key
        type: uniswap_v3              # Adapter type
      - key: camelot_v3
        type: generic_v3
    # Optional: Exclude specific aggregators on this chain
    # nonAggr: ['okx']               # Example: exclude OKX on Arbitrum

  # Base
  base:
    rpc: ${BASE_RPC}
    tokenList:
      - symbol: USDT
        address: "0x..."
      - symbol: WIF
        address: "0x..."
    dexList:                             # Optional standalone native DEXes on this chain
      - key: uniswap_v3
        type: uniswap_v3

  # Ethereum (mainnet)
  ethereum:
    rpc: ${ETHEREUM_RPC}
    tokenList:
      - symbol: USDC
        address: "0x..."              # USDC on Ethereum
      - symbol: PEPE
        address: "0x..."
    dexList:                             # Optional standalone native DEXes on this chain
      - key: uniswap_v3
        type: uniswap_v3

  # Polygon
  polygon:
    rpc: ${POLYGON_RPC}
    tokenList:
      - symbol: USDC
        address: "0x..."
      - symbol: PEPE
        address: "0x..."
    dexList:                             # Optional standalone native DEXes on this chain
      - key: quickswap                 # QuickSwap on Polygon
        type: generic_v2

  # Binance Smart Chain
  bsc:
    rpc: ${BSC_RPC}
    tokenList:
      - symbol: USDT
        address: "0x..."
      - symbol: WIF
        address: "0x..."
    dexList:                             # Optional standalone native DEXes on this chain
      - key: pancakeswap_v3             # PancakeSwap V3
        type: generic_v3

# Bridge provider configuration
bridge:
  provider: stargate                     # Currently only stargate supported
  stargate:
    router: "0x..."                   # Stargate router address
    lzEndpoint: "0x..."                # LayerZero endpoint

# Risk management parameters
risk:
  minProfitRateBps: 180                  # 1.8% = minimum profit to execute
  stopLossPct: 0.20                      # 20% loss triggers global pause
  slippageBps: 300                      # 3% = maximum slippage per swap
  positionCaps:
    fullAmountMode: true                # Use full available amount (subject to caps)
    singleTxCapPct: 1.0                 # 35% = no single-tx cap (can set 0.05–1.0)
    maxExposurePct: 0.95               # 95% = maximum total exposure

# Fee model (all costs subtracted from profit)
fees:
  dexFeeBpsPerSwap: 30                 # 0.3% per DEX swap (2 swaps = 0.6%)
  bridgeFlatUSD: 1.5                    # $1.50 flat bridge fee
  bridgePctBps: 30                      # 0.3% percentage bridge fee
  gasUSD: 0.6                            # $0.60 estimated gas per operation
  slippageReserveBps: 50                # 0.5% safety reserve for execution
  totalFeeRateBps: 180                  # 1.8% = total fee rate (used in profit calc)

# Operational parameters
ops:
  loopIntervalMs: 1000                    # 1 second orchestrator tick
  bridgeBackPct: 0.92                    # 92% = bridge back to originating chain
  gasReservePctOfProfit: 0.03            # 3% = retain as gas buffer
  dryRun: true                             # true = simulation only (no on-chain tx)
  # Max time to wait for single price request
  priceRequestTimeoutMs: 5000              # 5 seconds

# Logging configuration
logging:
  level: info                            # debug | info | warn | error
  json: true                             # Structured JSON logs
  # includeCaller: false                    # Optional: include source file/line in logs

# Wallet configuration
wallets:
  keystorePath: ./wallets/             # Path to encrypted keystores (no keys in YAML)
  address: "0x..."                       # Trading wallet public address
  # Private key loading via env/keystore only (never commit!)
```

## Environment Variables for Injection

Inject into `.env` (see `.env.example` for template):

### RPC Endpoints
- `ARBITRUM_RPC`, `BASE_RPC`, `OPTIMISM_RPC`, `ETHEREUM_RPC`, `POLYGON_RPC`, `BSC_RPC`, `MONAD_RPC`

### Risk & Ops Overrides
- `MIN_PROFIT_RATE_BPS`, `STOP_LOSS_PCT`, `SLIPPAGE_BPS`, `LOOP_INTERVAL_MS`
- `BRIDGE_BACK_PCT`, `GAS_RESERVE_PCT_OF_PROFIT`, `SINGLE_TX_CAP_PCT`, `MAX_EXPOSURE_PCT`

### Logging
- `LOG_LEVEL`, `LOG_JSON`

### Secrets
- `PRIVATE_KEY` or `WALLET_PRIVATE_KEY` (dev only, never commit)
- `STARGATE_API_KEY`, `LZ_API_KEY` (bridge providers)
- `OKX_API_KEY`, `OKX_SECRET_KEY`, `OKX_API_PASSPHRASE`, `OKX_PROJECT_ID` (OKX aggregator)

## Environment Overlays

For environment-specific configs, place alongside `config.yaml`:

- `config.dev.yaml` – Development (testnets, verbose logs)
- `config.test.yaml` – Test/CI (quiet logs, short intervals)
- `config.prd.yaml` – Production (production RPCs, real wallet)

Active via `APP_ENV` env var: `dev` (default), `test`, `prd`.

## Fail-Fast Triggers

Startup fails immediately if:

- `tokens.base` or `tokens.quote` is empty
- Fewer than 2 chains configured
- `aggregatorMultichain` is missing, empty, or has no enabled aggregators
- Optional DEX key in `dexList` has no adapter
- Token in `tokens.*` never appears in any `chains.*.tokenList`
