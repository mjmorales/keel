# FRAMEWORK.md — LLM Codebase Architecture Framework

## Purpose

This framework encodes institutional memory before the institution exists. It replaces the feedback loop that human teams develop over years — where pain produces conventions, conventions produce culture, and culture protects architecture — with a contractual system that provides the same guarantees from day zero.

The framework targets **greenfield projects built with LLM assistance** in a monorepo structure. It provides microservice-grade architectural isolation through contracts rather than infrastructure.

## Core Thesis

LLMs produce locally coherent code that globally degrades architecture over sessions. They lack the feedback loop that makes human codebases clean over time: they feel no pain from past mistakes, accumulate no scar tissue, and optimize for "this works now" over "this will hold when requirements change." The solution is not documentation — it is a contractual layer that eliminates wrong options by construction.

## Design Philosophy: Boring Is Correct

The ideal codebase produced by this framework is **boring**. Predictable. Unsurprising. Every file looks like every other file in its segment. Every new feature follows the same path as the last one. There is exactly one way to do any given thing.

This is not a compromise — it is the goal. The three supreme values, in priority order:

1. **Correctness** — the code does what it claims, handles its errors, and respects its contracts.
2. **Code hygiene** — the code is clean, consistent, and structurally sound. No cleverness. No tricks. No "elegant" solutions that require context to understand.
3. **LLM-friendliness** — the code is maximally parseable by a cold-start LLM session. Any session, reading any file, can immediately understand where it is, what this code does, and where to put the next thing.

These values trump performance, expressiveness, conciseness, and developer ergonomics. A boring codebase that any LLM session can navigate correctly is worth more than a clever codebase that requires institutional knowledge to modify safely.

**What "boring" means concretely:**

- **One way to do each thing.** If the framework assigns the Strategy pattern for rule dispatch, every rule-like dispatch in that segment uses Strategy. No "this one is simpler so I'll use a switch." No "this case is special." The pattern is the path; there are no shortcuts.
- **Explicit over implicit.** No metaprogramming, no reflection, no convention-over-configuration magic, no "auto" anything. If behavior exists, it is visible in the source code at the call site.
- **Flat over nested.** Deep nesting (of directories, of control flow, of abstractions) requires more context to understand. Prefer flat structures that can be read linearly.
- **Local readability.** Every file should be understandable without reading 10 other files. Imports declare dependencies. Types declare shapes. Functions declare behavior. Nothing is hidden.
- **Uniform structure within segments.** All files in a segment follow the same layout. If handlers are structured as validate → execute → respond, every handler follows that shape. If adapters are structured as interface → implementation → constructor, every adapter follows that shape.
- **No cleverness.** A "clever" solution is one where the reader must reconstruct the author's reasoning to understand it. LLMs cannot reliably reconstruct reasoning across sessions. Write the obvious thing.

---

## 1. Axioms

Axioms are architectural truths that every large codebase eventually learns the hard way. They are organized as a directed dependency graph: derived axioms are only safe when their foundational dependencies are satisfied.

### 1.1 Foundational (no dependencies)

#### A1: Single Concept Ownership

Every domain concept has exactly one owning segment. No concept is defined in two places. No segment extends or wraps another segment's types.

**Scar**: The same concept gets three representations across a codebase. Developers spend more time translating between representations than building features. Changes to the concept require synchronized updates across all representations.

**Enforcement**: The owning segment is declared at inception. Import analysis verifies no other segment defines types that overlap with owned concepts.

#### A2: Frozen Vocabulary

Domain vocabulary — the names of concepts, operations, states, and relationships — is established during inception and changed only by explicit decision. Naming reflects the problem domain, not implementation details.

**Scar**: Naming that doesn't reflect the domain creates a permanent translation layer in every developer's (and every LLM session's) understanding. Inconsistent naming produces inconsistent architecture because names guide where code is placed.

**Enforcement**: The vocabulary is recorded in the project CLAUDE.md. New terms require an ADR.

#### A3: Singular Error Strategy

Error handling strategy is decided once at inception: how errors are created, how they propagate across segment boundaries, how they are reported to users. One strategy, consistently applied.

**Scar**: Error handling that isn't decided upfront becomes inconsistent and stays that way. Some segments use error codes, some use exceptions/panics, some swallow errors silently. Debugging becomes archaeology.

**Enforcement**: The error strategy is declared per-language in the project CLAUDE.md. The friction protocol fires if a segment handles errors inconsistently with the declared strategy.

#### A4: I/O Boundary at Inception

The boundary between code that performs I/O (network, disk, database, external APIs) and code that performs pure logic is established at project start. This is the most important structural decision in any codebase.

**Scar**: The I/O boundary is always violated first and always costs the most. Once logic code acquires an I/O dependency, testability degrades, coupling increases, and the violation spreads because "the precedent is already there."

**Enforcement**: Segments are tagged `pure-logic` or `io-boundary` at inception. Import analysis enforces that `pure-logic` segments have zero I/O imports.

#### A5: One Canonical Path

For every operation, there is exactly one sanctioned way to accomplish it. Not "the best" way, not "the recommended" way — the **only** way. If the framework assigns the Adapter pattern for wrapping external APIs, every external API in that segment gets an Adapter. No exceptions for "simple" cases. No shortcuts for "obvious" calls. The pattern is the path.

**Scar**: Human codebases accumulate multiple approaches to the same problem because different developers (or the same developer at different times) make different local decisions. In a human team this stabilizes over years as the team converges on conventions. In an LLM-driven codebase, convergence never happens — each session is equally likely to pick any valid approach, so the codebase accumulates every valid approach simultaneously.

**Why this matters for LLMs specifically**: When an LLM encounters a codebase with two ways to do something, it has no basis for choosing between them. It may match whichever it reads first, whichever is closest in context, or whichever its training data prefers. Across sessions, this produces every permutation. One canonical path eliminates the choice entirely.

**Enforcement**:

- Constraint-to-pattern mapping assigns patterns, not suggests them. Every "When Active" condition in the pattern registry that is satisfied produces a mandatory pattern.
- The session-end audit flags alternative approaches to the same operation within a segment.
- New patterns or approaches require friction protocol approval — they cannot be introduced silently.
- Within a segment, all files of the same kind follow an identical internal structure (layout, ordering, naming conventions).

### 1.2 Derived (require foundational axioms)

#### A6: Abstractions Are Foundational, Not Premature

_Depends on: A1 (concept ownership), A2 (vocabulary)_

For LLM-driven development, abstractions defined at project start are foundational infrastructure, not premature optimization. LLMs will not independently discover the need for an abstraction, will not feel the pain of its absence, and will not refactor toward it. Duplication created by an LLM is permanent.

**Inversion**: This contradicts the common advice "prefer duplication over premature abstraction." That heuristic assumes a human developer who will feel the pain of duplication and refactor when the right abstraction reveals itself. LLMs do not have this feedback loop. Abstractions must be designed upfront.

**Enforcement**: The constraint-to-pattern mapping provides abstractions for each segment at inception. The friction protocol fires if a segment lacks the expected abstractions.

#### A7: Boundaries Are Binary

_Depends on: A4 (I/O boundary), A1 (concept ownership)_

A boundary between segments either exists and is enforced, or it does not exist. There is no "soft boundary" or "guideline boundary." Unenforced boundaries erode to nothing within a few sessions.

**Scar**: Teams declare boundaries in documentation but don't enforce them in CI. Within months, the boundaries exist only on paper. With LLMs, "months" becomes "sessions."

**Enforcement**: Every segment boundary has a corresponding import restriction that is checked at pre-commit. If a boundary cannot be enforced by tooling, it is not a real boundary.

#### A8: Testability Is Design Feedback

_Depends on: A7 (boundaries), A4 (I/O boundary)_

If code is hard to test, the design is wrong. Testability is not a feature to be added — it is a proxy signal for architectural correctness. `pure-logic` segments should be trivially testable with no setup. `io-boundary` segments should be testable with interface mocks at their adapter layer.

**Scar**: Code that wasn't designed for testability gets tested through integration tests that are slow, flaky, and test too many things at once. Eventually, tests are skipped or removed.

**Enforcement**: Test structure mirrors segment structure. Each segment has a test strategy derived from its constraints.

#### A9: Clean Breaks Over Backwards Compatibility

_Depends on: A7 (boundaries), A8 (testability), A6 (abstractions)_

LLM-driven codebases should always take the architecturally correct solution, not the one that minimizes churn. Backwards compatibility is a cognitive load management tool for human developers who can only hold limited context. LLMs do not share this constraint.

**Inversion**: This contradicts the instinct to preserve backwards compatibility for safety. The safety comes not from compatibility shims but from enforced boundaries (A7) and tests (A8). If those are satisfied, a clean break is always preferable to accumulated compatibility layers.

**Dependency warning**: This axiom is only safe when A7 and A8 are fully satisfied. Without enforced boundaries and tests, clean breaks become destructive.

**Enforcement**: When a design change is needed, the framework directs Claude to implement the new design fully and remove the old one. No shim layers, no deprecation periods, no `_old` suffixes.

### 1.3 Emergent (become relevant at scale)

#### A10: Responsibility Follows Activity

The files that change most frequently are the files that matter most. They accumulate the most assumptions, the most implicit coupling, and the most risk. Scrutinize active files more than stable ones.

**Enforcement**: Session-end drift reports weight findings by file change frequency.

#### A11: Boolean Flags Are Deferred Design Decisions

A boolean parameter that changes behavior is a design decision that wasn't made. It will attract more booleans until the function signature is a configuration language. Replace with Strategy or explicit types.

**Enforcement**: The session-end audit flags boolean parameters that control branching logic.

#### A12: State Ownership Is Explicit

Shared mutable state starts as a shortcut and ends as an architecture. Every piece of mutable state must have exactly one owning segment, one owning type within that segment, and a defined lifetime.

**Enforcement**: The `stateful` constraint requires declaring the single mutable structure. The pre-commit hook verifies no other segment mutates state it doesn't own.

---

## 2. Segments

### 2.1 Definition

A **segment** is an architecturally independent unit within a monorepo. It is the contractual equivalent of a microservice: it owns a specific responsibility, communicates with other segments only through declared interfaces, and can evolve independently as long as its contracts hold.

Every segment has:

- A **path** in the monorepo (e.g., `services/evaluator/`)
- A **language** (e.g., Go, TypeScript, Python)
- A **set of constraints** (from the constraint registry)
- **Inward contracts** (derived from constraints — what the segment must/must not do)
- **Outward contracts** (derived from constraints — obligations imposed on neighbors)
- **Owned concepts** (from the vocabulary — what domain concepts this segment is authoritative for)

### 2.2 Segment Isolation Rules

These rules apply universally to all segments, regardless of constraints:

1. **No internal imports across segments.** Segments may only depend on each other through declared interfaces or shared schema segments. Direct imports of another segment's internal packages are forbidden.

2. **Communication is typed.** All data crossing a segment boundary must use types from a `schema-owning` segment or interfaces defined at the boundary. No `interface{}`, no `any`, no untyped maps crossing boundaries.

3. **No circular dependencies.** The segment dependency graph must be a DAG. If segment A depends on segment B, B must not depend on A, directly or transitively.

4. **Fault isolation.** A failure (panic, crash, timeout) in one segment must not propagate to another segment unless explicitly declared as a fault line.

5. **One segment, one language.** A segment is implemented in exactly one language. Polyglot projects achieve language diversity through multiple segments, not multilingual segments.

---

## 3. Constraint Registry

Constraints are binary properties declared on segments at inception. Each constraint carries a **contract** — obligations that propagate inward (on the segment itself) and outward (on every segment that interacts with it).

### 3.1 Constraints

#### `pure-logic`

The segment performs no I/O and has no side effects.

| Direction | Obligation |
|-----------|-----------|
| **Inward** | No imports of I/O packages (network, filesystem, database, OS). No side effects. Given the same inputs + state, produces the same outputs. |
| **Outward (on callers)** | Callers must handle all I/O before invoking this segment. No I/O handles (readers, writers, connections, HTTP requests) may be passed as arguments. |
| **Outward (on dependents)** | Segments that depend on this segment's output receive value types only. |

#### `io-boundary`

The segment interfaces with external systems.

| Direction | Obligation |
|-----------|-----------|
| **Inward** | All external calls go through adapter interfaces (not concrete implementations). Adapters must be replaceable for testing. Owns retry/timeout/circuit-breaking logic. |
| **Outward (on callers)** | Callers must handle this segment's errors — no swallowing. |
| **Outward (on pure-logic segments)** | `pure-logic` segments must not depend on this segment directly. They depend on interfaces that this segment implements. |

#### `user-facing`

The segment is a public API surface (HTTP API, CLI, UI).

| Direction | Obligation |
|-----------|-----------|
| **Inward** | Owns all display formatting, error presentation, and user interaction. Provides a single entry facade. |
| **Outward (on internal segments)** | Internal segments must not format output for display. They return structured data; the `user-facing` segment decides presentation. |

#### `stateful`

The segment manages mutable state.

| Direction | Obligation |
|-----------|-----------|
| **Inward** | Declares exactly one primary mutable structure (e.g., `AlertState`, `SessionStore`). All state mutations are methods on this structure. State has a defined lifecycle (creation, update, teardown). |
| **Outward (on callers)** | Callers do not manage state on behalf of this segment. They call methods; they do not directly read/write state. |
| **Outward (on other stateful segments)** | Two `stateful` segments must not share mutable structures. Each owns its state exclusively. |

#### `event-producing`

The segment emits events consumed by other segments.

| Direction | Obligation |
|-----------|-----------|
| **Inward** | Events are typed (defined in a `schema-owning` segment), versioned, and immutable once emitted. |
| **Outward (on consumers)** | Consumers must use the declared event types. They must not require the producer to know about consumer-specific needs. |
| **Outward (on the dependency graph)** | The producer does not import consumers. Data flows one direction. |

#### `event-consuming`

The segment reacts to events from other segments.

| Direction | Obligation |
|-----------|-----------|
| **Inward** | Handles events idempotently. Does not assume ordering unless explicitly declared. Owns its own failure handling — a failed consumer does not block the producer. |
| **Outward (on producers)** | Producers must not assume consumer behavior, timing, or success. Fire-and-forget semantics unless the contract explicitly declares otherwise. |

#### `schema-owning`

The segment defines shared data types used across segment boundaries.

| Direction | Obligation |
|-----------|-----------|
| **Inward** | Types are immutable value objects. This segment has zero dependencies on other segments. Breaking changes require a new type or version, not mutation of existing types. |
| **Outward (on all consumers)** | Consumers use types exactly as defined. No wrapping in local types. No extending with additional fields. No aliasing to different names. If a consumer needs a different shape, it defines a local mapping function, not a new type. |

#### `concurrent`

The segment handles parallel execution.

| Direction | Obligation |
|-----------|-----------|
| **Inward** | All synchronization is explicit. No implicit shared state. Race conditions are prevented by construction (channels, mutexes with clear ownership), not by convention. |
| **Outward (on callers)** | Callers must respect the concurrency contract — e.g., if the segment exposes a channel-based API, callers use channels, not callbacks. |

### 3.2 Constraint Combinations

Some constraint combinations have additional implications beyond the sum of individual constraints:

| Combination | Additional Obligation |
|-------------|----------------------|
| `io-boundary` + `event-consuming` | The segment is a **sink** — it receives events and performs I/O actions. It must own retry logic, circuit breaking, and idempotency. Failure must not propagate upstream. |
| `io-boundary` + `event-producing` | The segment is a **source** — it receives external input and produces domain events. It must validate/transform external data into schema types before emitting. |
| `user-facing` + `io-boundary` | The segment is a **gateway** — it owns the full request lifecycle from external input to response. It delegates to internal segments but owns error formatting and response shaping. |

### 3.3 Forbidden Combinations

| Combination | Reason |
|-------------|--------|
| `pure-logic` + `io-boundary` | Contradictory. A segment cannot be both free of I/O and responsible for I/O. Split into two segments. |
| `pure-logic` + `stateful` | Contradictory. `pure-logic` means no side effects; `stateful` means state mutations are the primary operation. A segment that manages state is `stateful`. A segment that transforms data without mutation is `pure-logic`. If you need both, split into two segments: a `stateful` segment that owns the state and a `pure-logic` segment that computes transformations on values extracted from that state. |
| `schema-owning` + `stateful` | Schema segments are passive definitions. They must not hold state. If schemas need runtime behavior, that belongs in a separate segment that consumes the schemas. |
| `schema-owning` + `io-boundary` | Schema segments must have zero external dependencies. |
| `schema-owning` + `user-facing` | Schema segments are internal contracts, not user interfaces. |
| `schema-owning` + `concurrent` | Schema segments are passive type definitions with no runtime behavior. Concurrency is a runtime concern. |

---

## 4. Pattern Registry

Patterns are structural solutions to anticipated pressures. The framework does not suggest patterns — it **assigns** them based on constraints. Claude fills in the pattern; it does not choose whether to use it.

### 4.1 Constraint → Pattern Mapping

#### `pure-logic`

| Pattern | Purpose | When Active |
|---------|---------|-------------|
| **Strategy** | Swappable algorithms behind a stable interface. | When the segment handles multiple variants of the same operation. |
| **Visitor** | Operations over a type hierarchy without modifying the types. | When the segment defines a tree or graph structure that multiple operations traverse. |
| **Composite** | Uniform treatment of individual and compound elements. | When the segment has recursive or hierarchical data. |
| **Pipeline** | Sequential transformation stages. | When the segment transforms data through multiple steps. |
| **Value Objects** | Immutable types that are compared by value, not identity. | Always. All types in a `pure-logic` segment should be value types unless explicitly tagged `stateful`. |

#### `io-boundary`

| Pattern | Purpose | When Active |
|---------|---------|-------------|
| **Adapter** | Wraps external systems behind internal interfaces. | Always. Every external dependency gets an adapter. |
| **Repository** | Abstracts data storage behind a domain-oriented interface. | When the segment persists data. |
| **Circuit Breaker** | Prevents cascading failure from external system outages. | When the segment calls external APIs or services that can fail/timeout. |

#### `user-facing`

| Pattern | Purpose | When Active |
|---------|---------|-------------|
| **Facade** | Single entry point that hides internal complexity. | Always. The user-facing segment exposes one surface. |
| **Chain of Responsibility** | Middleware/pipeline for request processing. | When requests pass through multiple processing stages (auth, validation, logging, etc). |
| **Command** | Encapsulates a user action as an object. | When the segment handles discrete user operations (CLI commands, API endpoints). |

#### `stateful`

| Pattern | Purpose | When Active |
|---------|---------|-------------|
| **Explicit State Ownership** | One type owns all mutable state. All mutations are methods on that type. | Always. This is the defining pattern of `stateful` segments. |
| **Repository** | Abstracts state persistence. | When state survives process restarts. |
| **Unit of Work** | Groups related state mutations into atomic operations. | When multiple state changes must succeed or fail together. |

#### `event-producing`

| Pattern | Purpose | When Active |
|---------|---------|-------------|
| **Observer** | Decoupled notification of state changes. | Always. The producer emits; it does not direct. |
| **Registry** | Table-driven dispatch for event routing. | When events are dispatched to different handlers by type. |

#### `event-consuming`

| Pattern | Purpose | When Active |
|---------|---------|-------------|
| **Observer** | Subscribe to events from producers. | Always. |
| **Strategy** | Per-event-type handling logic. | When different event types require different processing. |
| **Idempotency Key** | Deduplication of processed events. | When at-least-once delivery is possible. |

#### `schema-owning`

| Pattern | Purpose | When Active |
|---------|---------|-------------|
| **Value Objects** | All types are immutable and compared by value. | Always. |
| **Builder** | Complex type construction with validation. | When types have invariants that must hold at construction time. |
| **Factory** | Creation of types from external representations. | When types are constructed from serialized data (JSON, protobuf, etc). |

#### `concurrent`

| Pattern | Purpose | When Active |
|---------|---------|-------------|
| **Explicit Ownership** | Every piece of shared data has one owning goroutine/thread. | Always. |
| **Channel/Message Passing** | Communication through typed channels, not shared memory. | When concurrent components need to coordinate. Prefer over mutexes. |

---

## 5. Inter-Segment Contract Rules

### 5.1 Dependency Direction

Segments form a directed acyclic graph. Dependencies flow in one direction. The allowed dependency patterns:

**Note: Arrows below represent call-flow (A → B means "A calls B"), not import direction.** Under dependency inversion (Section 5.2), the actual import direction is often reversed — the caller defines the interface, the implementer imports and satisfies it. The pre-commit import checker must use the import rules in Section 5.2, not these arrows.

Allowed call-flow:

```
schema-owning ← (all other segments may import schemas)
user-facing → pure-logic (gateway delegates to logic)
user-facing → io-boundary (gateway delegates to adapters)
io-boundary → pure-logic (adapters call logic through interfaces)
event-producing → schema-owning (events use schema types)
event-consuming → schema-owning (handlers use schema types)
```

Forbidden call-flow:

```
pure-logic → io-boundary (logic must not know about I/O)
pure-logic → user-facing (logic must not know about presentation)
event-consuming → event-producing (no bidirectional event flow without explicit declaration)
any segment → user-facing (only users call the gateway, not other segments)
```

**`stateful` segments** are not positioned in the generic DAG above because their placement is project-specific. During inception (Q&A), the human declares where each `stateful` segment sits in the dependency graph — which segments may call it, and which segments it may call. This positioning is recorded in the project CLAUDE.md and enforced like any other dependency rule.

### 5.2 Interface Ownership

When segment A needs to call segment B, the interface is defined by the **caller**, not the implementer. This inverts the typical pattern and is deliberate:

- A defines the interface it needs (dependency inversion)
- B implements that interface
- A never imports B's package — only B imports A's interface (or both import from schemas)

This ensures that the caller controls the contract and the implementer adapts to it. **Concretely: the pre-commit import checker verifies that no segment directly imports another non-schema segment's package.** Cross-segment communication happens through interfaces defined by the caller or types defined in schema-owning segments.

### 5.3 Data Crossing Boundaries

All data crossing segment boundaries must be:

1. **Typed** — using types from a `schema-owning` segment or interfaces
2. **Immutable** — the receiver must not mutate data received from another segment
3. **Self-contained** — no pointers to internal structures, no handles that require the sender to stay alive, no lazy-loading references back into the sender

---

## 6. Friction Protocol

Friction is the signal that the current task doesn't fit the declared architecture. It is diagnostic, not obstructive. The framework defines both a **response protocol** (what to do when friction is felt) and a **detection mechanism** (how to find friction that wasn't self-reported).

### 6.1 Response Protocol

When implementation cannot fit the existing segment structure, constraint declarations, or pattern assignments without modification:

**Step 1: STOP.** Do not adapt the architecture to fit the implementation. Do not add an import that violates a boundary. Do not create a type that duplicates a schema. Do not bypass a constraint.

**Step 2: DIAGNOSE.** Identify which specific contract is preventing the implementation. Name the segment, the constraint, and the obligation being violated.

**Step 3: PROPOSE.** Write a friction report:

```
FRICTION DETECTED

Task:       [what was being implemented]
Conflict:   [segment] [constraint] cannot [action]
Contract:   [quote the specific obligation]
Root cause: [why the current architecture doesn't accommodate this]

PROPOSED RESOLUTION:

Option A: [solution that respects existing contracts]
          Contract impact: [what changes, what doesn't]

Option B: [solution that modifies contracts]
          Contract impact: [which contracts change, full downstream consequences]

Recommendation: [which option and why]

AWAITING APPROVAL.
```

**Step 4: WAIT.** Do not proceed until the human approves a resolution. If Option B (contract modification) is approved, update CLAUDE.md to reflect the new contracts before implementing.

### 6.2 Detection: Pre-Commit (Hard Violations)

The pre-commit hook checks for violations that are always wrong, regardless of context:

| Check | Violation |
|-------|-----------|
| **Cross-segment imports** | Segment A imports segment B's internal package |
| **I/O in pure-logic** | `pure-logic` segment imports I/O packages |
| **Schema wrapping** | Non-schema segment defines types that wrap or extend schema types |
| **Circular dependency** | Segment A imports B and B imports A (direct or transitive) |
| **State outside owner** | Mutable state declared outside the segment's declared state type |

Hard violations **block the commit**. No override without an approved ADR.

### 6.3 Detection: Session-End (Soft Drift)

The session-end audit checks for drift that isn't necessarily wrong but indicates erosion:

| Check | Finding |
|-------|---------|
| **Missing patterns** | A constraint calls for a pattern that doesn't exist in the segment |
| **Alternative approaches** | Two or more implementations of the same operation using different patterns or idioms within a segment. Violates A5 (One Canonical Path). |
| **Switch sprawl** | A switch/case statement that should be a Strategy or Registry |
| **Boolean parameters** | Functions with boolean flags that control behavior branching |
| **Error inconsistency** | Error handling that deviates from the declared strategy |
| **Naming drift** | New identifiers that don't match the declared vocabulary |
| **Structural non-uniformity** | Files of the same kind within a segment that follow different internal layouts (e.g., one handler validates-then-executes, another executes-then-validates) |
| **Hot file concentration** | High change frequency in a single file suggests it has too many responsibilities |

Soft drift produces a **drift report** with findings and recommendations. It does not block work.

---

## 7. Monorepo Conventions

### 7.1 Directory Structure

```
project-root/
├── CLAUDE.md              # Layer 3 — project-bound contracts (generated)
├── schemas/               # schema-owning segment(s)
│   ├── go/                # Go type definitions
│   └── ts/                # Generated TypeScript types
├── services/              # backend segments
│   ├── <segment-name>/
│   │   ├── <segment>.go   # entry point
│   │   └── *_test.go      # tests mirror segment structure
│   └── ...
├── web/                   # frontend segment(s)
├── tools/                 # developer tooling segments
├── infra/                 # infrastructure-as-code segment
└── scripts/               # build, CI, code generation (not a segment)
```

### 7.2 Naming

- Segment directories are lowercase, singular nouns matching the domain vocabulary
- Package names match directory names
- No `common/`, `shared/`, `utils/`, `helpers/` directories — these are concept ownership failures. Every function belongs to the segment that owns its concept.

### 7.3 Language-Specific Conventions

The framework is language-agnostic in its axioms and constraints but language-specific in enforcement:

**Go**: Package boundaries are segment boundaries. Unexported symbols are segment-internal by construction. Interfaces at package boundaries enforce contracts. `internal/` directories provide additional scoping where needed.

**TypeScript**: Module boundaries are segment boundaries. Barrel exports (`index.ts`) define the public contract. ESLint import restrictions enforce cross-segment rules.

**Python**: Package boundaries are segment boundaries. `__init__.py` exports define the public contract. Import linting enforces cross-segment rules.

---

## 8. Inception Q&A Schema

Layer 2 (SKILL.md) uses this schema to interview the human and produce Layer 3 (project CLAUDE.md). The Q&A is conducted at project inception — before any code is written.

### 8.1 Required Questions

**Q1: Project Purpose**
What does this project do? (One sentence. This becomes the vocabulary seed.)

**Q2: Segments**
What are the distinct responsibilities in this system? (Each becomes a segment.)

**Q3: Language Per Segment**
What language will each segment be written in?

**Q4: Constraints Per Segment**
For each segment, the interviewer proposes constraints based on the described responsibility. The human confirms or adjusts.

**Q5: Communication Map**
How do segments communicate? What data flows between them? (This defines the dependency graph and identifies which types belong in schema-owning segments.)

**Q6: Fault Lines**
Which segment failures must be isolated from which other segments? (This defines fault isolation contracts.)

**Q7: Error Strategy**
How should errors be represented, propagated, and reported? (One answer per language in the project.)

**Q8: Domain Vocabulary**
What are the core nouns and verbs of the domain? (These become the frozen vocabulary in A2.)

**Q9: File Templates**
For each segment, after constraints and patterns are assigned, the interviewer proposes a canonical file structure — the internal layout that every file of a given kind will follow. The human confirms or adjusts. This becomes the mandatory template for that file kind. (Enforces A5: One Canonical Path — every handler looks like every other handler, every adapter looks like every other adapter.)

### 8.2 Output

The Q&A produces a project CLAUDE.md containing:

1. **Segment map** — each segment with path, language, constraints, owned concepts
2. **Contract graph** — all inward and outward obligations, fully derived from constraints
3. **Pattern assignments** — per segment, derived from constraint-to-pattern mapping
4. **File templates** — per segment, the canonical internal structure for each file kind (handlers, adapters, strategies, etc.). Every file of a given kind follows the same template. No variation.
5. **Dependency graph** — allowed and forbidden import paths
6. **Fault isolation map** — which failures are contained where
7. **Error strategy** — per language
8. **Vocabulary** — frozen domain terms

This CLAUDE.md is the **sole architectural authority** for the project. Claude reads it at the start of every session. It is updated only through the friction protocol (Section 6).

---

## Appendix A: Why These Axioms

Each axiom exists because of a specific, repeatedly observed failure mode in LLM-driven codebases. This appendix preserves the reasoning so that future sessions understand the _why_, not just the _what_.

**A1 (Single Concept Ownership)**: LLMs naturally create duplicate representations when they can't see or don't read the existing one. Without explicit ownership, the same concept accumulates representations across sessions until no one knows which is canonical.

**A2 (Frozen Vocabulary)**: LLMs are inconsistent namers across sessions. The same concept gets called `user`, `account`, `profile`, and `member` in different sessions. Each name suggests a different module, creating phantom architectural divisions.

**A3 (Singular Error Strategy)**: LLMs match the error style of whatever code is closest in context. If the first file uses error codes and the second uses exceptions, the third file is a coin flip. Error strategy diverges within the first few sessions.

**A4 (I/O Boundary)**: LLMs treat I/O as a local implementation detail rather than an architectural seam. They'll add `http.Get` inside a pure calculation function because it solves the immediate problem, destroying testability and coupling in one line.

**A5 (One Canonical Path)**: LLMs given a choice between two valid approaches will pick differently across sessions. Session 1 uses a switch statement. Session 3 uses a map lookup. Session 7 uses a method dispatch. All are "correct." The codebase now has three patterns for the same operation, and Session 10 has no basis for choosing among them. One canonical path means the choice was made at inception and every session follows it without deliberation.

**A6 (Foundational Abstractions)**: The "prefer duplication" heuristic assumes humans will feel duplication pain and refactor. LLMs don't feel pain. They'll duplicate a pattern 15 times across 15 sessions and never notice.

**A7 (Binary Boundaries)**: LLMs respect boundaries they can see (compilation errors, import restrictions) and ignore boundaries they're told about (documentation, comments, conventions). If the boundary isn't enforced by tooling, it doesn't exist.

**A8 (Testability as Design)**: LLMs will write tests that work around bad design rather than flagging the design as wrong. An untestable function gets an integration test with 50 lines of setup instead of being split into testable units.

**A9 (Clean Breaks)**: LLMs default to backwards-compatible changes because their training data is full of backwards-compatible changes. They'll add a `V2` function alongside `V1`, a compatibility shim, and a migration layer when the right answer is to delete `V1` and update all call sites.

**A10 (Activity-Based Scrutiny)**: LLMs don't have a sense of which files are "hot." They treat a file that changes every session the same as a file that hasn't changed in months. Hot files need more scrutiny because they accumulate assumptions faster.

**A11 (Boolean Flags)**: LLMs love boolean parameters because they're the lowest-effort way to add a behavioral branch. Each boolean defers a design decision, and LLMs never revisit deferred decisions.

**A12 (State Ownership)**: LLMs take the shortest path to making state accessible, which usually means making it globally accessible. Shared mutable state starts as a convenience in Session 1 and becomes load-bearing architecture by Session 5.
