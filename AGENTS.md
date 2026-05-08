# AGENTS.md

## Code Style Guidelines

### General
- Use `unknown` instead of `any` (strict type safety)
- No `async` keyword on functions without `await` expressions

### Formatting (Prettier)
- 2 spaces indentation
- Trailing commas (all)
- Semicolons required
- LF line endings

### TypeScript
- Explicit types on complex interfaces and returns
- Inferred types where obvious
- `readonly` on immutable class fields
- Strict null checks enabled
- Decorator metadata enabled

### NestJS Patterns
- `@Injectable()` on all services
- `@Inject(CUSTOM_TOKEN)` for DI tokens (not classes)
- Implement `OnModuleInit` for startup logic
- Dependency injection via constructor params

### Logging
- Use `LoggerService` (not console)
- Methods: `debug`, `info`, `warn`, `error`
- Context via optional meta object: `logger.info('message', { key: value })`
- Operation-scoped: `logger.withOpId(opId).info('message')`

### Immutability
- Immutable data objects (`TradingPairConfig`, `Prices`)

## Testing Conventions

### File Locations
- Unit tests: `src/**/*.spec.ts` (co-located)
- Integration: `test/**/*.integration.spec.ts`
- E2E: `test/**/*.e2e-spec.ts`
- Slow/integration: `test/slow/**/*.integration.spec.ts`


## Project Structure

- `src/orchestrator/` - Main trading loop
- `src/dex/` - DEX adapters (Uniswap V3, PancakeSwap V3, Velodrome V2)
- `src/bridge/` - Bridge adapters
- `src/price_monitor/` - Price fetching
- `src/risk_control/` - Risk management
- `src/utils/` - Shared utilities (config, wallet, logger)
- `src/common/` - Shared types and DI tokens

## Key Constraints

- TypeScript strict mode (some options relaxed)
- Ethers.js v6 for blockchain interactions
