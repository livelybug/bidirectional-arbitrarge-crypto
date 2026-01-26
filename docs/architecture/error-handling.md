# Error Handling & Resilience

Strategy for handling failures, retries, and maintaining system stability.

## Retry Strategy

**Exponential Backoff with Jitter**:
- Base: 250ms
- Max: 5s
- Attempts: 5
- Jitter: ±20% random variation

**Applied to**:
- Price fetch failures
- DEX quote/tx submission failures
- Bridge estimate/submit/settlement polling failures

**Example**:
```typescript
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  context: string,
): Promise<T> {
  let attempt = 0;
  while (attempt < 5) {
    try {
      return await fn();
    } catch (e) {
      attempt++;
      if (attempt === 5) throw e;
      const delay = Math.min(250 * Math.pow(2, attempt), 5000);
      await sleep(delay + Math.random() * delay * 0.2);
      logger.warn(`${context} retry ${attempt}/${5}`, { error: e.message });
    }
  }
  throw new Error(`${context} failed after 5 attempts`);
}
```

## Timeouts

| Operation | Timeout | Rationale |
|-----------|----------|------------|
| Price fetch | 5-10s | Per external call; skip cycle on timeout |
| DEX quote | 5s | Prevent indefinite blocking |
| Swap tx confirmation | Chain-dependent (e.g., 30s) | Wait for on-chain finality |
| Bridge estimate | 5s | Quick fee calculation |
| Bridge settlement | 60-900s | Varies by route; monitor longer |
| Config load | 2s | Fast-fail on slow/blocking loads |

## Circuit Breakers

**Per-Adapter Circuit Breaker**:
- **Open** after: 5 consecutive failures
- **Cooldown**: 60s before testing recovery
- **Half-open**: Send 1 test request; success = close, failure = reopen
- **Closed**: Normal operation

**State Machine**:
```
Closed (normal) → (5 failures) → Open (blocking)
Open (60s) → Half-open (test request)
Half-open → success → Closed (normal)
Half-open → failure → Open (blocking)
```

**Implementation Example**:
```typescript
class CircuitBreaker {
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  private failures = 0;
  private lastFailureTime?: number;

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      const cooldownExpired = Date.now() - (this.lastFailureTime ?? 0) > 60000;
      if (!cooldownExpired) throw new Error('Circuit breaker open');
      this.state = 'half-open';
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (e) {
      this.onFailure();
      throw e;
    }
  }

  private onSuccess() {
    this.failures = 0;
    this.state = this.state === 'half-open' ? 'closed' : 'closed';
  }

  private onFailure() {
    this.failures++;
    this.lastFailureTime = Date.now();
    if (this.failures >= 5) this.state = 'open';
  }
}
```

## Idempotency

**Operation Tagging**:
- Every operation tagged with unique `opId` (correlation ID)
- Persist in-memory ledger: `{ opId, status, txHash }`
- On retry, check ledger: skip if already completed

**Prevents**:
- Duplicate DEX swaps
- Duplicate bridge transfers
- Double-charging for same operation

## Fallback Behavior

| Scenario | Action | Reason |
|----------|--------|--------|
| Price API fails | Skip current cycle | Don't execute with stale data |
| All price APIs fail | Log error, continue next tick | System resilience |
| Bridge delayed | Reconcile asynchronously | Don't block orchestrator |
| RPC provider unresponsive | Switch to backup RPC | Redundancy (future) |
| DEX slippage > configured cap | Abort trade | Risk control |

## Error Categories

### Expected Transient Errors (Retry)
- Network timeouts
- Rate limit exceeded (429)
- Temporary RPC provider unavailability
- Bridge pending status (not settled yet)

### Permanent Errors (No Retry)
- Invalid private key
- Insufficient funds (genuine, not gas-related)
- Token/DEX not supported
- Configuration errors (fail-fast A/B/C)

### Business Logic Errors (Log + Skip)
- Profit below threshold
- Slippage cap exceeded
- Position cap exceeded
- Stop-loss triggered

## Logging for Debugging

**Structured Error Logs**:
```json
{
  "ts": "2025-01-25T12:34:56.789Z",
  "level": "error",
  "msg": "Bridge settlement timeout",
  "opId": "op_abc123",
  "context": {
    "transferId": "0x123...",
    "toChain": "base",
    "elapsedMs": 900000
  },
  "error": {
    "name": "TimeoutError",
    "message": "Settlement not received within 15 minutes"
  }
}
```

**Always Include**:
- `opId` for correlation
- Context (operation details)
- Original error object (name, message, stack)
- Retry attempt count (if applicable)
