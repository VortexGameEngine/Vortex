# AGENTS.md — Vortex Engine

Guidance for AI coding agents (and humans) contributing to the Vortex Engine. Read this fully before writing or
modifying code. When a rule here conflicts with your instinct or with a "usual C++ pattern", **the rule wins** — every
rule below exists to protect determinism, cache locality, or zero-cost abstraction.

Vortex is being designed in this repository: most of what follows is the target architecture, not shipped code. Where
this document and the tree disagree, the document states the intent and the tree states the present (§3 lists both).

`vbuild` has its own `AGENTS.md` and a detailed architecture document under `/Tools/vbuild/`. Read those before touching
the transpiler or build tooling.

---

## 1. What is Vortex

At its root, Vortex Engine is three things: a **Data-Oriented Design (DOD) core**, an **OOP façade** over that core, and
a **module manager**. When coupled with a specific configuration of modules, Vortex *is* the engine.

Everything else follows from three commitments:

| Commitment | Meaning in practice |
|---|---|
| **Compile-time composition** | Modules, entities and UI are assembled at build time by `vbuild`, not wired up at runtime. |
| **GPU-driven rendering** | The CPU produces flat command/indirect buffers; the GPU decides what to draw. |
| **Zero-cost abstractions** | Any ergonomic API (OOP proxies, `.cppx` UI, scripting) must compile down to raw contiguous-buffer operations with no runtime overhead. |

**Expose both OOP and DOD; implement DOD internally.** Game developers get two public APIs over the same engine: a DOD
API (systems over SoA buffers) and an OOP API. OOP game code may stay actual OOP, or be annotated with `VGAMEOBJECT()`
so that `vbuild` transpiles it into DOD C++ calling the DOD API at zero runtime cost (§6). Inside the engine, everything
performance-critical is DOD and the OOP API is a lightweight façade over it; plain OOP is acceptable internally only
where performance is not critical and DOD would make the code harder to read or maintain, or where a third-party library
imposes it — each such place carries a `// RATIONALE:` (§2.1).

---

## 2. Non-negotiable rules (read twice)

1. **No deep inheritance, no per-object virtual calls, no pointer-heavy object graphs in any performance-critical
   path.** Core and modules alike; there is no privileged layer. Two exceptions, each marked with a one-line
   `// RATIONALE:`: (a) wrapping a third-party library that is OOP by design — keep its objects at the boundary and
   convert to buffers at the edge; (b) code off the hot path (startup, editor tooling, one-off setup — anything not run
   per frame) where DOD would cost readability or maintainability; per-frame code is on the hot path until a profile
   says otherwise. Anywhere else, if you feel the need for a `virtual`, you are modelling something that should be a
   buffer + a system. These rules bind the engine and its modules; game code may use the OOP API with or without
   transpilation (§6).
2. **Struct-of-Arrays (SoA) and contiguous POD buffers by default.** Array-of-Structs is only acceptable when the whole
   struct is always read together and is small enough to keep cache-line density high — and you must say so in a
   one-line `// RATIONALE:` comment.
3. **Modules are stateless processors.** A module deterministically transforms input buffers into output buffers. No
   hidden side effects, no I/O inside the transform, and no mutable state outside a declared store (§5).
4. **Determinism is a feature.** Same inputs → same outputs, every run, every thread count. Anything that breaks this
   (GC, `std::shared_ptr` ownership graphs, output that depends on hash-map iteration order) is rejected.
5. **No garbage collection anywhere in the hot path.** This includes third-party transpilers or runtimes that bring
   their own GC.
6. **Never hand-edit generated artifacts** (`vortex.lock`, `VortexModules.cmake`, `VortexConfig.h`, generated proxy
   structs, transpiled `.cppx` output). Change the source manifest/macro and rerun `vbuild`.
7. **Code explains itself; comments are a last resort.** Readable names and small, well-named functions over prose.
   Public interfaces get a short doc comment; nothing else does unless the code cannot be made clearer (see §12).

---

## 3. Repository layout

Target layout. Today the tree holds `VortexEngine/` (core), `VortexHelloWorld/` and `VortexGoodbye/` (sample modules
registered by hand in `CMakeLists.txt`), `Sandbox/`, `Tools/vbuild/` (CLI skeleton), `cmake/` and `ThirdParty/`; confirm
against the tree before relying on a path.

```
/engine/          Core: DOD primitives (buffers, allocators, queues, phase barriers),
                  OOP façade generation targets, module manager
/modules/         Stateless processor modules (one directory per module)
/Tools/vbuild/    Build orchestration + transpiler — has its own AGENTS.md
/tools/lsp/       LSP sidecar / Volar-based proxy for .cppx
/ui/              .cppx UI runtime: UICommandBuffer, style resolution
/scripting/       Wasm host, buffer marshalling, TypeScript toolchain
/features/        Feature Toggle (FT) client, local FT file, server resolution
/cmake/           Hand-written CMake (generated files live in .vbuild/)
/docs/            Design docs and ADRs — check here before proposing new patterns
/.vbuild/         vbuild output: copied + transpiled sources, VortexModules.cmake, VortexConfig.h (ignored)
```

---

## 4. Build system: `vbuild` + CMake

`vbuild` is the **only** supported entry point. It reads declarative YAML project manifests and drives CMake.

### What `vbuild` does
- **Resolves dependencies** between modules and verifies declared **capabilities** (a module may not consume a
  buffer/capability it has not declared).
- **Transpiles**: copies the sources into `.vbuild/` and, with embedded `Tree-sitter` and `libclang`, parses the C++ and
  HTML there to emit zero-cost boilerplate (entity proxies, UI command emitters, style tables).
- **Produces deterministic artifacts**:
  - `vortex.lock` — pinned, reproducible dependency/module resolution; lives at the project root and is tracked.
  - `.vbuild/VortexModules.cmake` — generated module registration consumed by CMake.
  - `.vbuild/VortexConfig.h` — compile-time configuration and feature-toggle defaults.

### Agent workflow
Planned commands — the tool is under active development, so verify against `/Tools/vbuild/AGENTS.md` first.

```bash
vbuild configure        # parse manifests, resolve deps, emit generated files
vbuild build            # invoke CMake/ninja with the generated configuration
vbuild test             # run unit + determinism tests
```

Rules:
- If you add a module, a capability, an entity type, or a `.cppx` file, **update the YAML manifest** — do not touch
  `VortexModules.cmake` directly.
- Commit `vortex.lock` changes only when you intentionally changed dependencies, and explain the change in the commit
  message.
- A build that emits a non-deterministic artifact (diff on rebuild with no source change) is a bug. Report/fix it; do
  not work around it.

---

## 5. Data-Oriented Design conventions

### Memory layout
```cpp
/// Entity positions as SoA: a system reading only `x` streams one contiguous array.
struct PositionBuffer {
    float* x;        ///< `count` elements.
    float* y;        ///< `count` elements.
    float* z;        ///< `count` elements.
    uint32_t count;
};
```

- Prefer fixed-capacity, arena- or chunk-allocated buffers over `std::vector` growth in the frame loop.
- Use handles/indices (`uint32_t`) instead of pointers for cross-buffer references.
- Keep POD types trivially copyable; `static_assert(std::is_trivially_copyable_v<T>)` on any type that goes into a
  buffer, queue, or the Wasm boundary.

### Modules as stateless processors
```cpp
/// Pure transform; `out.count` must equal `in.count`. `dt` is the fixed timestep.
struct GravityModule {
    static void process(const VelocityBuffer& in, VelocityBuffer& out, float dt);
};
```

The signature says the rest: `const` input, caller-provided output, no members. That is the documentation.

### State: stores and the event bus
- Mutable state lives in **stores**. A store is a declared state container: SoA buffers owned by the engine, or the
  objects of an OOP library. Several isolated stores may coexist; a system declares which stores it reads and writes.
- Modules own no state: they receive `const` slices of a store and write caller-provided output slices.
- A store changes only in response to **events on the engine bus**, reduced at a barrier (§9): emitting is a queue push,
  and the handler that applies the change runs at the declared barrier in a fixed order. DOD and OOP stores alike follow
  this, so both stay deterministic.

---

## 6. Game objects: DOD API and OOP façade

Game developers choose per type:

- **DOD API.** Write systems that iterate the buffers directly (§5). Use it wherever you are writing a system.
- **OOP API (transpiled).** Declare the type with `VGAMEOBJECT()`; `vbuild` lowers the OOP-looking declaration into SoA
  storage plus a proxy that calls the DOD API. Same runtime cost as hand-written DOD. Use it for anything that exists in
  quantity or is touched every frame and that you would rather write as objects.
- **Actual OOP (untranspiled).** Ordinary C++ objects, virtuals and all, living outside the SoA chunks. Fully supported;
  the developer trades cache locality for familiarity. Not iterated by systems; integrates through the event bus (§9).

For `VGAMEOBJECT()` types:

- `vbuild` generates a **Typed Proxy Handle** struct per entity type.
- A proxy holds a chunk index + slot index, **never** a pointer to an object.
- Accessors like `p.health() -= 10` compile to `chunk.health[p.slot] -= 10`.

```cpp
/// Single source of truth for the Player layout; vbuild generates `PlayerProxy`.
VGAMEOBJECT(Player,
    (float,  health),
    (Vec3,   position)
);

void apply_damage(PlayerProxy p, float amount) {
    p.health() -= amount;   // -> chunk.health[p.slot] -= amount;
}
```

Rules:
- Never add virtual methods, base classes, or heap-owned members to entity declarations; the proxy generator will (and
  should) reject them.
- Never store a proxy across frames without revalidating — slots may be compacted. Store the stable entity ID instead.
- If you need behaviour, write a **system** that iterates buffers; do not put logic "inside" the entity.

---

## 7. `.cppx` — React-like UI in C++

UI is written declaratively inside C++ using the `REACT(<HTML>)` macro.

```cpp
/// Builds the HUD for one player. Zero allocation.
auto render_hud(const HudState& s) {
    return REACT(
        <div class="hud">
            <span class="hp">{s.health}</span>
            <ul>
                REACT_MAP(s.buffs, buff, <li class="buff">{buff.name}</li>)
            </ul>
        </div>
    );
}
```

`{expr}` interpolates C++ values; `REACT_MAP` expands a list. `vbuild` unrolls the block into straight-line C++ that
emits `UICommand`s into the frame's `UICommandBuffer`; what `REACT()` evaluates to is not yet fixed.

Key facts to respect:
- **No Virtual DOM diffing.** The raw POD UI state is hashed each frame; if the hash changes, the contiguous command
  buffer is rebuilt in full. Do not add per-node dirty flags or retained trees.
- **Zero allocation.** Anything that would allocate inside `REACT()` (e.g. `std::string` concatenation) is a bug; use
  fixed buffers or pre-formatted state.
- **Scoped styles.** `<style scoped>` blocks are transpiled into compile-time hashed integer IDs and bitmasks resolved
  on the CPU. Never introduce runtime CSS parsing or string-based selector matching.
- Generated output contains `#line` directives pointing back at the `.cppx` source; keep them intact when touching the
  transpiler.

---

## 8. Tooling: LSP sidecar for `.cppx`

- Standard IDEs (VS Code, CLion) are supported through an LSP middleware proxy built on Volar.
- The proxy builds **Shadow Documents**: HTML regions replaced with whitespace (preserving line/column positions) so
  `clangd` sees valid C++; HTML/CSS queries are routed to their own language services.
- Compiler diagnostics map back to `.cppx` lines via injected `#line` directives.

If you change `.cppx` syntax in the transpiler, you **must** update the shadow document generator in the same change,
and verify that positions still line up.

---

## 9. Events, messaging and callbacks

Systems communicate only through the **event bus**: a set of lock-free queues, each drained at a declared phase barrier.

- **Lock-free queues**: SPSC, MPSC, MPMC — choose the narrowest that fits (SPSC is cheapest; MPMC only when truly
  required). Name the producer and consumer phases in a one-line comment on every queue declaration.
- **Deterministic phase barriers**: systems run in fixed phases; a queue is drained only at its declared barrier, so
  ordering is reproducible.

```cpp
struct EventBus {
    /// Physics phase -> Gameplay phase; drained at the PostPhysics barrier.
    SpscQueue<CollisionEvent, 4096> collisions;
};
```

### Callbacks

Callbacks are allowed. The indirect call is cheap; what is expensive is **firing a handler synchronously from inside a
system's transform** at the moment an event is emitted. That runs arbitrary code on an arbitrary worker thread, pulls
unrelated data into cache mid-loop, makes ordering depend on scheduling, and can re-enter the buffer being iterated. So:

- **Never dispatch at emit time.** Emitting an event is a queue push, nothing more.
- **Dispatch at a barrier**, on a known thread, in a deterministic order (registration order or sorted by entity ID —
  never hash-map order).
- **Batch where possible.** A handler that receives a slice of events is cheaper and easier to reason about than one
  invoked per event.
- **Hybrid model:**
  - Plain OOP game objects register **individual callbacks** and unsubscribe in their destructor (RAII — no dangling
    subscriptions).
  - DOD systems use **one global subscription with predicate filtering** — they scan the event stream and select by
    predicate rather than registering many handlers.
- In hot paths prefer a function pointer + context handle over `std::function` with captures (which may heap-allocate).
  If thousands of indirect calls run per frame, sort them by target to keep branch prediction stable.

---

## 10. Scripting boundary (TypeScript → Wasm)

- **Do not use C++ transpilers** such as `compilets`. They depend on garbage collection (`cppgc`) and `std::shared_ptr`,
  which break determinism and cache locality.
- TypeScript is compiled to **WebAssembly** and treated as an **isolated, stateless processor**, exactly like a native
  module.
- The host passes **contiguous memory buffers** into the sandbox and reads output buffers back. Scripts never hold
  references into engine memory, and the engine never calls back into scripts mid-transform. This preserves lock-free
  execution.

Rules for agents:
- Marshal only trivially-copyable POD across the boundary; version the layout.
- No host imports that perform I/O or allocation on behalf of the script inside the frame loop.

---

## 11. Feature Toggles (FTs)

Feature toggles are resolved in a strict override chain (later wins):

1. **Local FT file** in the project — the baseline, always present.
2. **Vortex Engine official FT server** — may override local values.
3. **Custom game-developer-run FT server** — may override both of the above.

Rules:
- Every new toggle gets a default in the local file and a one-line description.
- Toggle evaluation must be **resolved once at a defined point** (startup or a phase barrier), never read live from the
  network inside a system's transform — that would break determinism.
- Compile-time toggles surface through `VortexConfig.h`; runtime toggles through the FT client API. Do not read the file
  or servers directly from module code.

---

## 12. Documentation standard

The goal is code that needs no explanation. In priority order:

1. **Make the code say it.** Choose names that state intent. If a block needs a comment to be understood, extract it
   into a function whose name *is* the comment. Refactoring internals for readability is preferred over annotating them.
2. **Document public interfaces — briefly.** Every public type, function, macro, queue and buffer gets a `///` comment
   of one to three lines: what it does and any invariant the caller must respect (thread ownership, buffer size
   contracts, phase). Do not restate what the signature already says.
3. **Mark rule deviations.** Any departure from a rule or convention in this document carries a one-line `// RATIONALE:`
   comment. That is the only place justification belongs in code.
4. **No walls of text.** Comments are tech debt: every line must be kept in sync with the code or it becomes a lie. If
   you change behaviour, update or delete the comment in the same change.
5. **Docs describe the repository, nothing else.** Comments, doc blocks and `/docs/` describe the code as it currently
   exists. They must never reference design conversations, chat history, prompts, alternatives that were discussed, or
   how a decision was reached. Alternatives that matter go in an ADR under `/docs/`, written as a standalone record —
   not as a transcript.
6. **Markdown wraps at 120 columns**, the same limit `.clang-format` applies to C++. `.githooks/scripts/mdwrap.py`
   rewraps prose and list items; headings, tables, code blocks and hard line breaks are left exactly as written.

---

## 13. Contribution workflow

Vortex Engine is **open source**. Work is tracked as GitHub **Issues** and lands through **Pull Requests**; contributors
and users may suggest or implement features.

**Contribution over forking.** Maintainers have the final say on whether a PR is accepted, but the project strives for
consensus so that people build together rather than fork. When a fork is unavoidable, prefer an alternative module to a
fork of the engine: the module system exists so that competing implementations can coexist.

- **One Issue, one PR.** Reference the Issue before starting and scope the change to it; if you discover adjacent work,
  open a new Issue rather than expanding the PR.
- **Suggestions are proposals.** A feature request from a user or contributor is not an instruction to build it. It is
  filed as an Issue (templates under `.github/ISSUE_TEMPLATE/`) and is accepted or declined by maintainers before
  implementation begins.
- **Keep PRs small and reviewable.** Prefer several focused PRs over one large one. A PR that mixes a refactor with a
  behaviour change will be sent back.
- **PR description = what and why, in the repository's terms.** State the change, the Issue it closes, and the
  verification you ran (§14). The same rule as §12 applies: no references to conversations, prompts or discussion
  history.
- **Never push to protected branches.** Everything, including maintainer work and generated-artifact updates, goes
  through review.
- **Keep the Issue current** as work progresses.
- **Repository hooks install themselves** the first time you configure CMake, controlled by `VORTEX_INSTALL_GIT_HOOKS`
  (default ON); an existing `core.hooksPath` is never overwritten. If you never configure a build, run
  `cmake -P cmake/GitHooks.cmake` once instead. The pre-commit hook rewraps the staged copy of each Markdown file to 120
  columns (§12) and re-stages it. The working copy is updated to match only when it has no unstaged edits; otherwise it
  is left alone and reported.

---

## 14. Testing and verification

Before considering a change done:

- `vbuild build` succeeds from a clean tree with no warnings introduced.
- Generated artifacts are byte-identical across two consecutive builds.
- Determinism tests pass: identical inputs produce identical output buffers, including under different worker-thread
  counts.
- No new `virtual`, `std::shared_ptr`, RTTI, or frame-loop heap allocation in a performance-critical path without a
  `// RATIONALE:` (grep is a fair first check).
- No callback is invoked at emit time; every handler runs at a barrier.
- `.cppx` changes: shadow-document positions and `#line` mapping verified.
- New toggles, modules, entities, or capabilities are reflected in the YAML manifest and the lockfile diff is
  intentional.
- Public interfaces documented per §12; no comment references anything outside the repository.

Exact test targets are defined by `vbuild`; see `/Tools/vbuild/AGENTS.md`.

---

## 15. Quick "do / don't"

| Do | Don't |
|---|---|
| Write systems that iterate SoA buffers | Put behaviour inside entity structs |
| Use indices/handles for references | Use raw or smart pointers between entities |
| Declare queues with producer/consumer/barrier | Fire callbacks synchronously from inside a transform |
| Keep third-party OOP at the boundary, convert to buffers at the edge | Let library object graphs leak into hot loops |
| Change YAML manifests and rerun `vbuild` | Edit generated CMake/headers/lockfile by hand |
| Keep `REACT()` blocks allocation-free | Introduce retained UI trees or VDOM diffing |
| Marshal POD buffers into Wasm | Share engine memory or callbacks with scripts |
| Resolve FTs at a defined point | Query toggles inside a transform |
| Rename/extract until the code is clear | Explain unclear code with a paragraph |
| Scope each PR to one Issue | Implement a suggestion before its Issue is accepted |

When unsure, prefer the option that is **more explicit, more contiguous, and more deterministic**.
