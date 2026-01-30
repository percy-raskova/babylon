# PercyBrain: A Programming Language for Rigorous Minds

## What Is This?

PercyBrain is a programming language designed for people who:

- Refuse to write code without understanding *why* it should exist
- Believe types should encode meaning, not just prevent crashes
- Treat tests as executable specifications of truth claims
- Document decisions because future-you deserves to know what past-you was thinking
- Would rather spend an hour designing than a day debugging
- Get viscerally uncomfortable when they see magic numbers

This is not a language for moving fast and breaking things. It's a language for building systems you can trust.

______________________________________________________________________

## Core Beliefs

### 1. Code Without Theory Is Just Typing

Every system encodes assumptions about how the world works. Most languages let you hide those
assumptions in implementation details. PercyBrain forces you to name them.

```percybrain
@grounded("Kahneman & Tversky, Prospect Theory")
principle LossAversion {
    // Humans weight losses ~2.25x more than equivalent gains
    const LOSS_WEIGHT: Float = 2.25
}
```

If you can't cite why something is true, maybe it isn't.

### 2. Types Are Contracts, Not Labels

A type that says "this is a float" tells you nothing useful. A type that says "this is a probability
between 0 and 1, quantized to prevent drift" tells you everything.

```percybrain
type Probability = Float[0.0..1.0] @stable
type Temperature = Float @unit(Kelvin) @min(0.0)
type UserID = String @pattern("[A-Z]{3}[0-9]{6}")
```

When types carry meaning, entire categories of bugs become impossible.

### 3. Mutation Is Lying About the Past

When you mutate state, you destroy information. PercyBrain defaults to immutability—not because
mutation is always wrong, but because it should be a conscious choice.

```percybrain
frozen record Point(x: Float, y: Float)

let p1 = Point(0, 0)
let p2 = p1.with(x: 5)  // p1 unchanged, p2 is new

// If you need mutation, declare it explicitly
mutable var counter = 0
counter += 1  // Allowed because you asked for it
```

### 4. Configuration Belongs in One Place

Scattering constants across files is technical debt with compound interest. PercyBrain enforces single-source-of-truth configuration.

```percybrain
config Settings {
    source: "settings.yaml"  // One file, all values

    @section network {
        timeout_ms: Int = 5000
        retry_count: Int = 3
    }

    @section limits {
        max_connections: Int = 100
    }
}

// Everywhere else references Settings, never hardcodes
let timeout = Settings.network.timeout_ms
```

### 5. Dependencies Should Be Visible

If a function secretly depends on global state, database connections, or the current time, it's lying
about its inputs. PercyBrain requires explicit injection.

```percybrain
service OrderProcessor {
    inject db: Database
    inject clock: TimeSource
    inject logger: Logger

    fn process(order: Order) -> Result {
        // All dependencies visible in signature
    }
}

// Testing becomes trivial
let processor = OrderProcessor(
    db: MockDatabase(),
    clock: FrozenClock(2024-01-15),
    logger: NullLogger()
)
```

### 6. Tests Are Specifications, Not Afterthoughts

A test that says "it works" is useless. A test that says "given these conditions, this invariant
holds" is documentation that runs.

```percybrain
@specification
test "triangle inequality holds for all distances" {
    forall a, b, c: Point {
        let d_ab = distance(a, b)
        let d_bc = distance(b, c)
        let d_ac = distance(a, c)

        assert d_ac <= d_ab + d_bc
    }
}

@requirement("SPEC-042")
test "user cannot withdraw more than balance" {
    given account = Account(balance: 100)
    when result = account.withdraw(150)
    then assert result is InsufficientFunds
}
```

### 7. Fallbacks Should Be Explicit Chains

When you need to look something up, the fallback logic is usually scattered across conditionals.
PercyBrain makes lookup chains first-class.

```percybrain
lookup UserPreferences {
    chain: [
        user_override(user_id),      // Check user-specific setting
        team_default(user.team_id),  // Then team default
        org_policy(user.org_id),     // Then org policy
        system_default()             // Finally system default
    ]
}

let theme = UserPreferences.get("theme", user)
// Clear which sources were checked, in what order
```

### 8. Views Shouldn't Require Modification

When you need a new perspective on data, you shouldn't have to change the original structure. Lenses
let you add views without touching internals.

```percybrain
lens TaxView over Transaction {
    computed tax_amount: Currency =
        self.amount * TaxRates.get(self.category)

    computed after_tax: Currency =
        self.amount - self.tax_amount
}

// Original Transaction unchanged
let tx = Transaction(amount: 100, category: "software")
let view = TaxView(tx)
let tax = view.tax_amount  // 7.00
```

### 9. Decisions Deserve Documentation

Six months from now, you won't remember why you chose approach A over B. PercyBrain has first-class
support for decision records.

```percybrain
decision "Use event sourcing for audit trail" {
    status: accepted
    date: 2024-01-15

    context: |
        We need complete audit history. Traditional CRUD
        overwrites previous state.

    alternatives: [
        "Soft deletes with history table",
        "Change data capture",
        "Event sourcing"
    ]

    choice: "Event sourcing"

    rationale: |
        Events are the source of truth. State is derived.
        Natural fit for our domain where "what happened"
        matters more than "what is."

    consequences: {
        positive: ["Complete audit trail", "Time travel queries"]
        negative: ["Eventual consistency complexity", "Storage growth"]
    }
}
```

### 10. Work in Vertical Slices

Features aren't done until they're deployed and working. PercyBrain organizes work into deliverable
slices, not horizontal layers.

```percybrain
slice "User Registration" {
    deliverables: [
        endpoint("/api/register"),
        model(User),
        validation(email, password),
        storage(users_table),
        notification(welcome_email)
    ]

    tests: 12
    status: complete
}
```

______________________________________________________________________

## What PercyBrain Is Not

- **Not a rapid prototyping language**: Design time is not wasted time
- **Not a "move fast" language**: Speed without direction is just thrashing
- **Not a dynamic scripting language**: Types are mandatory, not optional
- **Not a language for lone wolves**: It assumes others will read your code

______________________________________________________________________

## Who Should Use This?

PercyBrain is for developers who:

1. Have been burned by "temporary" solutions that became permanent
1. Spend time understanding before coding
1. Value clarity over cleverness
1. Believe documentation is part of the work, not overhead
1. Want to trust their systems, not just hope they work

______________________________________________________________________

## The Mantra

> "If you can't explain why it works, you don't know that it does."

PercyBrain doesn't make you a better programmer. It makes your thinking visible—so you can see when it's wrong.
