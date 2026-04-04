# Keel

Architectural contract enforcement for LLM-driven codebases.

LLM-generated code degrades over sessions. Each new session cold-starts with no actual memory of past decisions, no awareness o ffriction  accumulated from earlier mistakes, and no reason to prefer the pattern established three weeks ago over the pattern that looks reasonable right now. The result is architectural drift via locally coherent code that globally erodes structure.

Keel solves this by encoding institutional memory as contractual constraints before the first line of code is written. It conducts a structured interview at project inception, derives a full contract graph from your answers, and generates a per-project enforcement toolkit under `.keel/`. Every subsequent LLM session loads those contracts on start. Pre-commit hooks enforce hard violations. The CLI surfaces drift and compliance status at any point.

The goal is not a clever codebase, but  a **boring** one instead. Prefering to be predictable, uniform, and navigable by any LLM session without institutional context.

## Quick Start

Install the CLI:

```bash
pipx install git+https://github.com/mjmorales/keel.git#subdirectory=cli
```

Install the inception skill into Claude Code:

```bash
keel install-skill /path/to/keel-repo
```

Start a new project (inside Claude Code, in an empty project directory):

```
/keel-inception
```

Claude will conduct the  interview, derive your contract graph, and generate the full `.keel/` toolkit. From that point forward, every session loads contracts automatically and every commit is checked against them.

Verify contract compliance at any time:

```bash
keel check
keel status
```

## Philosophy: Boring Is Correct

Keel is built on the ideal that an LLM-driven codebase should be boring.

Human teams accumulate architectural knowledge through pain. Whenever a pattern gets violated, or something breaks, a human team adds a rule or a constraint somewhere. Amongst humasn that rule becomes culture, and over years that culture protects the architecture. LLMs have none of this. They don't feel the pressure from past sessions, accumulate no scar tissue, and optimize for "this works now" over "this will hold when requirements change."

Documentation doesn't _truly_ fix this since documentation is advisory. Keel replaces the feedback loop with a contractual layer: a system where wrong options are eliminated by construction rather than by convention.

What "boring" means in practice:

- One way to do each thing. If the contract assigns the Strategy pattern for a given dispatch, every dispatch in that segment uses Strategy. No shortcuts for "simpler" cases.
- Explicit over implicit. No metaprogramming, no reflection, no auto-anything. If behavior exists, it's visible at the call site.
- Flat over nested. Deep nesting — of directories, control flow, or abstractions — requires context to understand. Prefer structures readable linearly.
- Local readability. Every file should be understandable without reading 10 others. Imports declare dependencies. Types declare shapes. Nothing is hidden.
- Uniform structure within segments. All files of the same kind in a segment follow the same internal layout.
- No cleverness. A clever solution is one where the reader must reconstruct the author's reasoning. LLMs can't reliably do this across sessions.

These values take priority over performance, conciseness, and developer ergonomics.

## How It Works

Keel has two components: a Claude Code skill (the inception engine) and a CLI (non-LLM enforcement).

### Inception (run once per project)

The inception skill conducts a 9-question structured interview:

| # | Question | Purpose |
|---|----------|---------|
| Q1 | What does this project do? | Establishes domain and primary action |
| Q2 | What are the distinct responsibilities? | Defines segments (3-7 recommended) |
| Q3 | What language for each segment? | One segment, one language — enforced |
| Q4 | Which constraints apply to each segment? | Derives the constraint set |
| Q5 | How do segments communicate? | Builds the dependency DAG and data flow map |
| Q6 | Which segment failures must be isolated? | Maps fault boundaries |
| Q7 | How should errors work? | Sets per-language error strategy |
| Q8 | What are the core domain nouns and verbs? | Freezes vocabulary |
| Q9 | What file templates should each segment use? | Defines mandatory internal file layouts |

After the interview, Keel derives the full contract graph and presents it for review before generating anything.

### The Generated Toolkit

Everything Keel generates lives under `.keel/`:

```
.keel/
├── .gitignore                        # Keel-managed
├── CLAUDE.md                         # Architectural authority
├── FRAMEWORK.md                      # The 12-axiom framework
├── ledger.json                       # Decision index
├── skills/
│   ├── keel-frame/                   # Loads contracts at session start
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── contracts.json        # Compiled contract graph
│   ├── keel-audit/                   # Guides LLM drift analysis
│   │   └── SKILL.md
│   ├── keel-gen/                     # Generates files from templates
│   │   ├── SKILL.md
│   │   └── templates/
│   │       └── <segment>_<kind>.j2
│   ├── keel-decide/                  # Friction protocol; records decisions
│   │   └── SKILL.md
│   └── keel-map/                     # Source map maintenance
│       └── SKILL.md
├── commands/
│   ├── keel-check.md
│   ├── keel-new.md
│   ├── keel-status.md
│   ├── keel-map.md
│   ├── keel-tree.md
│   └── keel-decisions.md
├── decisions/
│   └── 000-inception.json            # Immutable inception record
└── map.json                          # Living source map (local, regenerated)
```

### Ongoing Enforcement

Four mechanisms maintain contracts after inception:

- Pre-commit hook — runs `keel check --staged` on every commit. Hard violations block.
- keel-frame skill — loads contracts at session start so every LLM response is framed against them.
- `keel check` — on-demand contract validation from the CLI.
- `keel audit` — deeper drift analysis, suitable for CI integration.

## Installation

### CLI

Requires Python 3.11+.

```bash
pipx install git+https://github.com/mjmorales/keel.git#subdirectory=cli
keel --version
```

### Docker

```bash
docker run --rm -v "$(pwd):/project" ghcr.io/mjmorales/keel <command>
```

### Inception Skill

```bash
# Via CLI (recommended)
keel install-skill /path/to/keel-repo

# Via task (from the keel repo)
task install        # copy to ~/.claude/skills/project-inception/
task link           # symlink (dev mode)

# Dev mode via CLI
keel install-skill /path/to/keel-repo --link
```

## CLI Reference

All commands accept `-p <path>` to target a different project directory.

| Command | Description |
|---------|-------------|
| `keel check` | Check all tracked files against contracts |
| `keel check --staged` | Check staged files only (pre-commit hook) |
| `keel audit` | Static drift analysis on recent changes |
| `keel map` | Display the current source map |
| `keel map --rebuild` | Rebuild `map.json` from project state |
| `keel map --json-output` | Raw JSON output |
| `keel tree` | Full segment dependency tree |
| `keel tree <segment>` | Single segment's dependencies |
| `keel tree --dot` | Graphviz DOT format |
| `keel status` | Compliance overview |
| `keel decisions` | List decision ledger |
| `keel decisions --type <type>` | Filter by type |
| `keel decisions --since <date>` | Filter by date |
| `keel decisions --detail <id>` | Full detail for one decision |
| `keel decide <type> "<summary>"` | Record a decision |
| `keel install-skill [source]` | Install inception skill |

### Violation Types (`keel check`)

| Code | Trigger |
|------|---------|
| `forbidden-import` | Segment imports a package declared off-limits |
| `io-in-pure-logic` | `pure-logic` segment imports an I/O package |
| `cross-segment` | Segment imports from another non-schema segment |

### Finding Types (`keel audit`)

| Code | Trigger |
|------|---------|
| `boolean-param` | Function takes a bare `bool` parameter |
| `switch-sprawl` | `switch`/`match` with more than 4 cases |
| `naming-drift` | Identifier contains no frozen vocabulary terms |
| `hot-file` | File changed 10+ times in 30 days |

### Decision Types (`keel decide`)

| Type | When to use |
|------|-------------|
| `friction` | A constraint is being intentionally violated |
| `amendment` | A contract is being changed |
| `vocabulary` | A new domain term is being added |
| `pattern` | A new structural pattern is being adopted |
| `segment` | A segment is being added, removed, or restructured |

## The Friction Protocol

When a constraint needs to be violated or a contract needs to change, Keel requires explicit documentation before the change is made.

```bash
# Record a friction exception
keel decide friction "Allow direct DB access in reporting — read-only queries bypass stateful layer"

# Amend a contract permanently
keel decide amendment "Split auth into auth-core and auth-adapter"
```

Edit the generated `.keel/decisions/<id>.json` to add full context, then update `.keel/CLAUDE.md` to reflect the new contracts.

## Requirements

| Component | Requirement |
|-----------|-------------|
| `keel` CLI | Python 3.11+ |
| Docker image | Docker |
| Inception skill | Claude Code |
| Contract checking | Git |

The CLI has one runtime dependency: [Click](https://click.palletsprojects.com/) 8.0+.

## A Note on How This Was Built

This project was built with significant help from LLMs. But Keel was refined by a human who cares deeply about the craft of software and the people who practice it. Behind every architectural decision and every constrain should be a person that thought hard about what can help their codebases sustainable for real team members. LLMs should act as your hands; with the intent staying sincerely human.

## License

MIT

[github.com/mjmorales/keel](https://github.com/mjmorales/keel)

Built with love for the community that will use it <3
