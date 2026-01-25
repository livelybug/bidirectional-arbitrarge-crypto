# AGENTS.md

## Code Style Guidelines

### General
- **Be very concise and terse** - explicit requirement
- Use `unknown` instead of `any` (strict type safety)
- No `async` keyword on functions without `await` expressions

### Formatting (Prettier)
- 2 spaces indentation
- Single quotes
- 100 char line width
- Trailing commas (all)
- Semicolons required
- LF line endings

### Imports
- Group loosely by functionality (local → external)
- No strict alphabetical ordering enforced
- Clean, minimal imports

### Naming Conventions
- Services: `PascalCaseService` (e.g., `UniswapV3Service`)
- Interfaces/Types: `PascalCase` (e.g., `DexAdapter`, `PairId`)
- Methods/Functions: `camelCase`
- Private methods: `camelCase`
- Constants: `UPPER_SNAKE_CASE` for static const
- No "I" prefix on interfaces

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

### Error Handling
- Throw `Error` directly (not custom classes typically)
- Fast-fail on config errors
- Validate inputs, log warnings, return safe defaults
- No empty catch blocks

### Logging
- Use `LoggerService` (not console)
- Methods: `debug`, `info`, `warn`, `error`
- Context via optional meta object: `logger.info('message', { key: value })`
- Operation-scoped: `logger.withOpId(opId).info('message')`

### Immutability
- Immutable data objects (`TradingPairConfig`, `Prices`)
- No mutation of returned objects
- Copy or create new instances when modifying

## Testing Conventions

### File Locations
- Unit tests: `src/**/*.spec.ts` (co-located)
- Integration: `test/**/*.integration.spec.ts`
- E2E: `test/**/*.e2e-spec.ts`
- Slow/integration: `test/slow/**/*.integration.spec.ts`

### Test Structure
- Use `describe`/`it` from Jest
- Mock dependencies with `jest.fn()`
- Create helper functions for test setup
- `beforeEach` for cleanup: `jest.clearAllMocks()`

### Mock Pattern
```typescript
const loggerMock: jest.Mocked<LoggerService> = {
  info: jest.fn(),
  warn: jest.fn(),
  debug: jest.fn(),
  error: jest.fn(),
  // ... include all interface methods
} as unknown as jest.Mocked<LoggerService>;
```

### Module Testing
```typescript
const moduleRef = await Test.createTestingModule({
  providers: [
    ServiceUnderTest,
    { provide: Dependency, useValue: mockValue },
  ],
}).compile();
const service = moduleRef.get<ServiceUnderTest>(ServiceUnderTest);
```

## Project Structure

- `src/orchestrator/` - Main trading loop
- `src/dex/` - DEX adapters (Uniswap V3, PancakeSwap V3, Velodrome V2)
- `src/bridge/` - Bridge adapters
- `src/price_monitor/` - Price fetching
- `src/risk_control/` - Risk management
- `src/utils/` - Shared utilities (config, wallet, logger)
- `src/common/` - Shared types and DI tokens

## Key Constraints

- Node.js >= 24 required
- TypeScript strict mode (some options relaxed)
- Ethers.js v6 for blockchain interactions
- Zod for config validation
- All operations must be deterministic and testable
