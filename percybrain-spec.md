# PercyBrain Language Specification

**Philosophy**: A language that makes your thinking auditable.

______________________________________________________________________

## Part I: Foundations

### 1. The Problem with Most Code

Most code lies. Not maliciously—but through omission.

- It hides assumptions in variable names nobody reads
- It scatters configuration across a dozen files
- It depends on implicit state that isn't in the function signature
- It claims to "work" without defining what that means
- It makes decisions nobody documented

PercyBrain makes these invisible things visible. Not because visibility is intrinsically good, but
because invisible bugs are the ones that ship.

### 2. Core Axioms

**Axiom 1: All values have meaning.**
A `float` is not just a number—it's a probability, a temperature, a currency amount, a ratio. The
type system should know which.

**Axiom 2: All mutations are events.**
When state changes, that change should be traceable. Implicit mutation is debugging in hard mode.

**Axiom 3: All dependencies are inputs.**
If a function depends on something, that something appears in the signature. No exceptions.

**Axiom 4: All decisions have rationale.**
Code that exists without documented reasons is code that will be changed without understanding.

**Axiom 5: All claims are testable.**
If you can't write a test for it, you can't know if it's true.

______________________________________________________________________

## Part II: The Type System

### 3. Constrained Types

Types aren't just categories—they're contracts with the compiler.

```percybrain
// A type is a name, a base type, and constraints
type Percentage = Float[0.0..100.0]
type NonEmpty<T> = List<T> @min_length(1)
type Email = String @pattern("^[^@]+@[^@]+\\.[^@]+$")
type PositiveInt = Int @min(1)
```

The constraint is part of the type. A `Percentage` is not a `Float` you happen to treat carefully—it's
a fundamentally different thing that cannot hold invalid values.

#### Stability Annotations

Some values accumulate floating-point errors over time. Mark them:

```percybrain
type Probability = Float[0.0..1.0] @stable(precision: 5)
// Values are snapped to 10^-5 grid on every assignment
```

#### Unit Annotations

Dimensional analysis catches unit errors at compile time:

```percybrain
type Distance = Float @unit(Meters)
type Time = Float @unit(Seconds)
type Speed = Float @unit(Meters / Seconds)

let d: Distance = 100
let t: Time = 10
let v: Speed = d / t  // Compiler checks units match
```

### 4. Enumerations and Sum Types

When a value can only be one of several things, say so:

```percybrain
enum Status { Pending, Active, Suspended, Closed }

enum Result<T, E> {
    Ok(T),
    Err(E)
}

// Pattern matching is exhaustive
match result {
    Ok(value) => process(value)
    Err(e) => handle(e)
}
// Compiler error if you miss a case
```

### 5. Records and Products

Records are frozen by default:

```percybrain
record User {
    id: UserID
    email: Email
    created: Timestamp
}

let user = User(id: "U001", email: "a@b.com", created: now())
user.email = "x@y.com"  // COMPILE ERROR: records are immutable

// Create modified copy instead
let updated = user.with(email: "x@y.com")
```

Explicit mutability is allowed but flagged:

```percybrain
mutable record Counter {
    value: Int
}

let c = Counter(value: 0)
c.value += 1  // Allowed because explicitly mutable
```

______________________________________________________________________

## Part III: Functions and Purity

### 6. Pure Functions

By default, functions are pure: same inputs → same outputs, no side effects.

```percybrain
fn distance(a: Point, b: Point) -> Float {
    sqrt((b.x - a.x)^2 + (b.y - a.y)^2)
}

// This function cannot:
// - Read global state
// - Write to a database
// - Generate random numbers
// - Get the current time
// - Print to console
```

### 7. Effectful Functions

When you need effects, declare them:

```percybrain
fn save_user(user: User) -> Result<Unit, DbError>
    @effect(Database)
    @effect(Logging)
{
    log.info("Saving user ${user.id}")
    db.insert(user)
}
```

The effect annotations are part of the function's type. A caller that doesn't have access to `Database` cannot call `save_user`.

### 8. Dependency Injection

Services declare their dependencies explicitly:

```percybrain
service UserService {
    inject db: Database
    inject cache: Cache
    inject clock: TimeSource

    fn create(email: Email) -> Result<User, CreateError> {
        let user = User(
            id: generate_id(),
            email: email,
            created: clock.now()
        )
        cache.set(user.id, user)
        db.insert(user)
        Ok(user)
    }
}
```

All three dependencies are visible. Testing requires providing all three—no hidden state.

______________________________________________________________________

## Part IV: Configuration

### 9. Single Source of Truth

Configuration comes from one place:

```percybrain
config App {
    source: "config.yaml"

    @section server {
        port: Int = 8080
        host: String = "localhost"
    }

    @section database {
        url: String
        pool_size: Int = 10
    }

    @section features {
        enable_beta: Bool = false
    }
}
```

All values live in `config.yaml`. Code references `App.server.port`, never a hardcoded `8080`.

### 10. Environment Overrides

Production needs different values:

```percybrain
config App {
    source: "config.yaml"
    env_prefix: "APP"  // APP_SERVER_PORT overrides server.port

    @section server {
        port: Int = 8080
    }
}
```

The override hierarchy is explicit: environment variables > config file > defaults.

______________________________________________________________________

## Part V: Lookup Patterns

### 11. Hierarchical Lookup

When values come from multiple sources with priorities:

```percybrain
lookup Theme {
    chain: [
        user_preference(user.id),    // Highest priority
        team_setting(user.team_id),
        org_default(user.org_id),
        system_default()              // Lowest priority
    ]
}

let theme = Theme.resolve("color_scheme", user)
// Returns first non-null value in chain
```

The chain is explicit. You can see exactly which sources are checked.

### 12. Fallback Functions

When lookup fails, provide fallbacks:

```percybrain
lookup Config {
    chain: [env_var, config_file, default]

    fn resolve(key: String) -> String? {
        for source in chain {
            if let value = source.get(key) {
                return value
            }
        }
        return null
    }

    fn resolve_or(key: String, fallback: String) -> String {
        resolve(key) ?? fallback
    }

    fn require(key: String) -> String {
        resolve(key) ?? panic("Required config missing: ${key}")
    }
}
```

______________________________________________________________________

## Part VI: Testing

### 13. Tests as Specifications

Tests aren't afterthoughts—they're the specification:

```percybrain
@spec("Distance is always non-negative")
test "distance non-negativity" {
    forall a, b: Point {
        assert distance(a, b) >= 0.0
    }
}

@spec("Distance is symmetric")
test "distance symmetry" {
    forall a, b: Point {
        assert distance(a, b) == distance(b, a)
    }
}

@spec("Triangle inequality holds")
test "triangle inequality" {
    forall a, b, c: Point {
        assert distance(a, c) <= distance(a, b) + distance(b, c)
    }
}
```

These tests document what "distance" means mathematically.

### 14. Given-When-Then

For behavior specifications:

```percybrain
test "withdrawal fails when insufficient funds" {
    given account = Account(balance: 100.00)

    when result = account.withdraw(150.00)

    then {
        assert result is Err(InsufficientFunds)
        assert account.balance == 100.00  // Unchanged
    }
}
```

### 15. Test Phases

TDD support built into the language:

```percybrain
@red  // This test is expected to fail (feature not implemented)
test "users can reset password via email" {
    // ...
}

// After implementation, remove @red
@green
test "users can reset password via email" {
    // Same test, now expected to pass
}
```

The compiler tracks test phases.

______________________________________________________________________

## Part VII: State and Events

### 16. Immutable State

State is data. It doesn't do things—things are done to it:

```percybrain
frozen record GameState {
    turn: Int
    players: List<Player>
    board: Board
}

// State never mutates. Create new versions:
fn advance_turn(state: GameState) -> GameState {
    state.with(turn: state.turn + 1)
}
```

### 17. Events as Facts

When something happens, record it as a fact:

```percybrain
event PlayerMoved {
    player_id: PlayerId
    from: Position
    to: Position
    timestamp: Timestamp
}

event ScoreChanged {
    player_id: PlayerId
    delta: Int
    reason: String
}
```

Events are immutable records of things that happened. State is derived from events, not the other way around.

### 18. Observers

Observers watch events without affecting them:

```percybrain
observer GameLogger {
    on PlayerMoved(e) {
        log.info("${e.player_id} moved from ${e.from} to ${e.to}")
    }

    on ScoreChanged(e) {
        log.info("${e.player_id} score ${e.delta}: ${e.reason}")
    }
}

observer Metrics {
    var move_count: Int = 0

    on PlayerMoved(e) {
        move_count += 1
    }

    fn get_total_moves() -> Int { move_count }
}
```

Observers are read-only. They cannot modify events or state.

______________________________________________________________________

## Part VIII: Lenses and Views

### 19. Lenses

A lens provides a derived view of data without modifying it:

```percybrain
lens TaxView over Purchase {
    computed tax_rate: Percentage =
        TaxRates.get(self.category, self.region)

    computed tax_amount: Currency =
        self.subtotal * (tax_rate / 100)

    computed total: Currency =
        self.subtotal + tax_amount
}

let purchase = Purchase(subtotal: 100, category: "electronics", region: "CA")
let view = TaxView(purchase)

view.total  // 107.25 (with CA electronics tax)
// purchase is unchanged
```

### 20. Lens Composition

Lenses can stack:

```percybrain
lens DiscountView over Purchase {
    param discount: Percentage

    computed discounted: Currency =
        self.subtotal * (1 - discount / 100)
}

let purchase = Purchase(subtotal: 100, ...)
let view = purchase
    |> DiscountView(discount: 10)  // Apply 10% discount
    |> TaxView()                    // Then calculate tax

view.total  // Tax calculated on discounted amount
```

______________________________________________________________________

## Part IX: Documentation

### 21. Decision Records

Architectural decisions are first-class:

```percybrain
decision ADR001 "Use PostgreSQL over MongoDB" {
    status: accepted
    date: 2024-01-15

    context: |
        We need a database. Team has experience with both
        relational and document stores.

    options: [
        "PostgreSQL" -> {
            pros: ["ACID", "Team familiarity", "Mature tooling"]
            cons: ["Schema migrations", "Horizontal scaling harder"]
        },
        "MongoDB" -> {
            pros: ["Flexible schema", "Easy horizontal scaling"]
            cons: ["Eventual consistency", "Less team experience"]
        }
    ]

    decision: "PostgreSQL"

    rationale: |
        Our data is inherently relational. The team knows SQL.
        We don't anticipate needing horizontal scaling for
        at least 2 years.
}
```

### 22. Specification Links

Code can reference external specs:

```percybrain
@implements("RFC-7231 Section 6.5.1")
fn handle_bad_request() -> Response {
    Response(status: 400, body: "Bad Request")
}

@requirement("JIRA-1234")
fn calculate_discount(order: Order) -> Percentage {
    // Implementation of discount logic from ticket
}
```

### 23. Anti-Patterns

Document what NOT to do:

```percybrain
@antipattern("Don't catch generic exceptions")
// BAD:
try { risky() } catch { log("something failed") }

// GOOD:
try { risky() }
catch NetworkError(e) { retry() }
catch ValidationError(e) { report(e) }
```

______________________________________________________________________

## Part X: Project Organization

### 24. Modules

Code is organized into modules:

```percybrain
module user {
    export User, UserService, CreateError

    record User { ... }
    service UserService { ... }
    enum CreateError { ... }

    // Private helper, not exported
    fn validate_email(email: String) -> Bool { ... }
}
```

### 25. Slices

Work is organized into vertical slices:

```percybrain
slice "Password Reset" {
    status: in_progress

    components: [
        endpoint("POST /reset-password"),
        service(PasswordResetService),
        email(PasswordResetEmail),
        storage(reset_tokens_table)
    ]

    tests: {
        unit: 8,
        integration: 3
    }

    dependencies: [
        "User Authentication",  // Must be complete first
        "Email Service"
    ]
}
```

### 26. Epochs and Milestones

Long-term work has structure:

```percybrain
epoch "V1 Launch" {
    target: 2024-Q2

    milestones: [
        "Core Authentication" -> complete,
        "User Management" -> complete,
        "Billing Integration" -> in_progress,
        "Admin Dashboard" -> planned
    ]
}
```

______________________________________________________________________

## Part XI: Error Handling

### 27. Result Types

Functions that can fail return `Result`:

```percybrain
fn parse_int(s: String) -> Result<Int, ParseError> {
    // ...
}

// Caller must handle both cases
match parse_int("42") {
    Ok(n) => use(n)
    Err(e) => handle(e)
}
```

### 28. Error Hierarchies

Errors have structure:

```percybrain
error DataError {
    message: String
}

error ValidationError extends DataError {
    field: String
    value: Any
}

error NotFoundError extends DataError {
    entity: String
    id: String
}
```

### 29. No Generic Catches

You cannot catch "any error":

```percybrain
// COMPILE ERROR: must specify error type
try { risky() } catch { ... }

// VALID: specific error types
try { risky() }
catch ValidationError(e) { fix(e.field) }
catch NotFoundError(e) { create(e.id) }
// Other errors propagate
```

______________________________________________________________________

## Part XII: The Compiler

### 30. What the Compiler Checks

- Type constraints are satisfied
- All dependencies are injected
- No implicit mutation
- All pattern matches are exhaustive
- All decisions have rationale
- All tests have specifications
- No hardcoded configuration values
- Effect annotations are accurate

### 31. What the Compiler Generates

- Runtime constraint validators
- Dependency injection wiring
- Test harnesses
- Documentation from doc comments
- Decision record index
- Deprecation warnings

______________________________________________________________________

## Appendix: Design Principles

### Why These Choices?

**Immutability by default**: Bugs from unexpected mutation are subtle and hard to find. Making
mutation explicit makes it auditable.

**Explicit dependencies**: "It works on my machine" usually means "my machine has hidden state yours
doesn't."

**Constrained types**: A `Percentage` that can be 150% isn't a percentage. The type system should prevent invalid states.

**Tests as specs**: A test without a specification is just "code that happens to pass." Specs make intent explicit.

**Decision records**: Code archaeology is expensive. Future maintainers deserve context.

**No magic**: If you can't see how something works, you can't know when it breaks.

______________________________________________________________________

> "The goal is not to write clever code. The goal is to write code that a tired person at 3 AM can
> understand, debug, and trust."
