### How to add a new DEX

1. **Start from an existing adapter pattern.** Use `UniswapV3Service` or `PancakeswapV3Service` in `src/dex/` as the reference for logging style, deterministic pricing, slippage handling, and balance methods.
2. **Implement a new `DexAdapter` class.** Create `YourDexService` in `src/dex/` implementing `DexAdapter` from `dex-adapter.interface.ts`, including both quote methods (`estimateBuyQuoteToBase`, `estimateSellBaseToQuote`), swap methods (`swapQuoteToBase`, `swapBaseToQuote`), and `getBalanceBase` / `getBalanceQuote`.
3. **Register the adapter in `DexModule`.** Import your new service into `dex.module.ts` and expose it via a dedicated token (e.g. `DEX_YOUR_DEX`) using `useExisting`, mirroring the registrations for `DEX_UNISWAP_V3` and `DEX_PANCAKESWAP_V3`.
4. **Wire the DEX into `config.yaml`.** Add a new `dexList` entry under each relevant `chains.*` section with a unique `key` (e.g. `your_dex`) and appropriate `type`, ensuring the key matches what your adapter expects and what `TradingPairConfig.dexJ/dexK` will use.
5. **Enable discovery for the new DEX.** Update `PairDiscoveryService` so it can emit `TradingPairConfig` routes that reference your new `dexKey` on the appropriate chains, using the existing Uniswap/Pancake routes as templates.
6. **Add adapter tests following Uniswap/Pancake patterns.** Create Jest specs under `src/dex/` that construct your adapter with mocked `ConfigService` and `LoggerService`, asserting deterministic quote outputs, proper handling of bad inputs, fail-fast behavior when `config.chains` does not advertise the dex key, and a simple swap receipt shape (`txHash`).
7. **Rely on existing orchestration code.** Because `PriceMonitor` talks only to `DexQuoteProvider` and Orchestrator/RiskManager work in terms of `TradingPairConfig`, no changes are required in those modules: once your adapter is registered and the config/discovery are updated, the new DEX becomes available to the whole pipeline.

