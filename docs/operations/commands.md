# Command Reference

All `pnpm` commands for building, testing, and running the project.

## Install Dependencies

```bash
cd code/ts
pnpm install
```

## Linting

```bash
# Auto-fix linting errors
pnpm lint

# Lint test files only
pnpm lint:test

# Lint and auto-fix (recommended)
pnpm lint --fix
```

## Building

```bash
# Type-check and compile TypeScript
pnpm build

# Build with watch mode (development)
pnpm start:dev      # Includes build + watch

# Build for production
pnpm start:prod     # Uses optimized build output
```

**Output**: Compiled files in `dist/` directory.

## Testing

```bash
# Unit tests (excludes test/slow/)
pnpm test

# All tests including slow/integration
pnpm test:all

# Test in watch mode (interactive development)
pnpm test:watch

# Generate coverage report
pnpm test:cov

# Single test file (full path from project root)
## unit tests: (or just pnpm test, it'll match properly since it's under src/)
pnpm run test src/path/to/service.spec.ts
## integration tests:  (because the test script ignores test/slow/ on purpose)
pnpm exec jest test/slow/dex/okx-dex.integration.spec.ts --runInBand

# E2E tests only
pnpm test:e2e

# Test in debug mode
pnpm test:debug
```

**Test Options**:
- `--watch`: Re-run tests on file changes
- `--runInBand`: Run tests sequentially (for CI)
- `--coverage`: Generate coverage report

## Running the Application

```bash
# One-off start (honors config.yaml + .env)
pnpm start

# Development mode with watch + rebuild on changes
pnpm start:dev

# Production mode from compiled output
pnpm build
pnpm start:prod
```

## Configuration Inspection

```bash
# Print effective merged config for current environment
pnpm config:print

# Print specific environment
APP_ENV=test pnpm config:print
APP_ENV=prd pnpm config:print

# Check specific setting (uses jq if available)
pnpm config:print | jq '.risk.minProfitRateBps'
```

Output is JSON with:
- `appEnv`: Active environment (dev/test/prd)
- `config`: Merged configuration with redacted secrets

## Wallet Operations

```bash
# Check wallet balance on a chain (helper script)
pnpm wallet:dev-balance

# Generate new encrypted keystore (future feature)
pnpm wallet:create-keystore
```

## Formatting

```bash
# Format all TypeScript files with Prettier
pnpm format

# Format specific files
pnpm format src/**/*.ts test/**/*.ts
```

## Cleanup

```bash
# Remove build artifacts
rm -rf dist/

# Remove dependencies (start fresh)
rm -rf node_modules
pnpm install

# Remove coverage reports
rm -rf coverage/
```

## Pre-Commit Validation

```bash
# Equivalent to CI gates (run locally before committing)
pnpm lint && pnpm build && pnpm test

# Lint + build + test with coverage
pnpm lint && pnpm build && pnpm test:cov
```

## Useful Aliases

Add to `~/.bashrc` or `.zshrc`:

```bash
# From project root
alias arb-dev='cd ~/path/to/project/code/ts && pnpm start:dev'
alias arb-test='cd ~/path/to/project/code/ts && pnpm test'
alias arb-build='cd ~/path/to/project/code/ts && pnpm build && pnpm lint'
```

## Troubleshooting Commands

```bash
# Check Node version
node --version        # Should be ≥24

# Check pnpm version
pnpm --version

# Verify config syntax (before running)
pnpm config:print   # If this errors, config.yaml is invalid

# Run with verbose logging
APP_ENV=dev LOG_LEVEL=debug pnpm start:dev

# Check TypeScript version
npx tsc --version   # Should match package.json

# Check for lint errors only (no auto-fix)
pnpm lint --no-fix
```

## Common Error Messages

| Error | Meaning | Fix |
|-------|----------|------|
| `Cannot find module` | Dependency not installed | Run `pnpm install` |
| `Type 'X' is not assignable to type 'Y'` | Type error in code | Check type definitions; fix compilation error |
| `Module not found` | Import path incorrect | Verify import path matches file location |
| `Config error (Fast-fail *)` | Configuration invalid | See [Fast-Fail Errors](../config/fast-fail-errors.md) |
| `ENOSPC` | System limit (open files) | Close unused terminals or increase ulimit |

## Performance Profiling (Optional)

```bash
# Run tests with CPU profiling
NODE_ENV=production pnpm test

# Generate flamegraph (future)
pnpm test:profile
```

## Related Documentation

- [Deployment](deployment.md) - Environment setup and CI pipeline
- [Quick Start](../getting-started/quickstart.md) - Initial setup
- [Config Reference](../config/reference.md) - Config structure
