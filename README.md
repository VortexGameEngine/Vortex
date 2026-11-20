# Vortex Engine

Vortex is an open-source, modular C++ game engine.

Vortex is still being designed in this repository: most of this document is the target architecture, and even that may
change. Where it and the tree disagree, this document states the intent and the tree states the present.

This README holds everything humans and AI agents both need to know. `AGENTS.md` holds only instructions aimed at AI
agents; anyone is welcome to read and improve it.

## Modular architecture

The engine core is a module manager plus the primitives modules share. Everything other than the core is a module, and
`vbuild` composes a project's modules at build time: that set of modules is the engine.

## Code paradigm

Vortex mixes Data-Oriented Design (DOD) and Object-Oriented Programming (OOP):

- **DOD where performance matters.** Rendering and anything that runs per frame over many objects is built from
  Struct-of-Arrays buffers and systems, for efficient operations over many objects and efficient object pooling and
  reuse.
- **OOP elsewhere**, in code off the hot path such as startup, tooling and the editor, where it makes the code easier to
  read and maintain.

## vbuild

`vbuild` is Vortex's in-house build system; it extends CMake and drives it. It fetches and maintains Vortex module
catalogs, validates and resolves module dependencies and declared **capabilities** (a module may not consume a buffer or
capability it has not declared), and aborts on conflicting module setups. It copies the sources into `.vbuild/` and
transpiles them there with Tree-sitter and libclang: reflection macros become plain C++, OOP-looking code annotated for
DOD becomes DOD code, and, after the MVP, a module may opt in to a generated C ABI for bindings and prebuilt
distribution.

## Principles

| Commitment | In practice |
|---|---|
| **Compile-time composition** | `vbuild` assembles modules, entities and UI at build time, not at runtime. |
| **GPU-driven rendering** | The CPU writes flat command and indirect buffers; the GPU decides what to draw. |
| **Zero-cost abstractions** | APIs that make DOD code look like objects (transpiled game objects, `.cppx` UI) compile down to plain operations on contiguous buffers. |

Game developers choose per type whether a game object is DOD or plain OOP (see Game objects); the engine forces neither.

### Rules

1. **Performance-critical code is DOD**, in the core and in modules alike: no deep inheritance, per-object virtual calls
   or pointer-heavy object graphs. Per-frame code is performance-critical until a profile says otherwise. Code off the
   hot path may use OOP where DOD would cost readability. A third-party OOP library used in hot code stays at the
   boundary and converts to buffers at the edge, marked with a one-line `// RATIONALE:`.
2. **Use Struct-of-Arrays (SoA) and contiguous POD buffers by default.** Array-of-Structs only when the whole struct is
   always read together and is small, with a `// RATIONALE:`.
3. **Modules are stateless processors.** A module deterministically transforms input buffers into output buffers: no
   hidden side effects, no I/O inside the transform, no mutable state outside a declared store.
4. **Determinism is a feature.** Same inputs, same outputs, on every run and every thread count. Garbage collection,
   `std::shared_ptr` ownership graphs and output that depends on hash-map iteration order are rejected.
5. **No garbage collection in the hot path**, including third-party runtimes that bring their own.
6. **Never hand-edit generated artifacts** (`vortex.lock`, `VortexModules.cmake`, `VortexConfig.h`, generated proxies,
   transpiled `.cppx` output). Change the manifest or macro and rerun `vbuild`.
7. **When unsure, choose the more explicit, more contiguous and more deterministic option.**

## Repository layout

Today: `VortexEngine/` (core), `VortexHelloWorld/` and `VortexGoodbye/` (sample modules registered by hand in
`CMakeLists.txt`), `Sandbox/`, `Tools/vbuild/` (CLI skeleton), `cmake/` and `ThirdParty/`. Target:

```
/engine/          Core: module manager and DOD primitives (buffers, allocators, queues, phase barriers)
/modules/         Stateless processor modules, one directory each
/Tools/vbuild/    Build orchestration and transpiler, with its own docs
/tools/lsp/       LSP sidecar for .cppx
/ui/              .cppx UI runtime: UICommandBuffer, style resolution
/features/        Feature toggle client, local toggle file, server resolution
/cmake/           Hand-written CMake (generated files live in .vbuild/)
/docs/            Documentation too long for this file
/.vbuild/         vbuild output: copied and transpiled sources, VortexModules.cmake, VortexConfig.h (ignored)
```

## Building

Today the project builds with CMake 3.28 or later and C++17:

```bash
cmake -S . -B build
```

```bash
cmake --build build
```

When `clang-tidy` is installed, every engine, module and tool target runs it with warnings as errors
(`ENABLE_CLANG_TIDY`, default `ON`).

`vbuild` will become the only supported entry point; see `Tools/vbuild/`. Planned commands: `vbuild configure`,
`vbuild build`, `vbuild test`. Its artifacts are deterministic: `vortex.lock` (pinned resolution, tracked at the project
root), `.vbuild/VortexModules.cmake` (module registration) and `.vbuild/VortexConfig.h` (compile-time configuration and
toggle defaults).

- **Adding a module, capability, entity type or `.cppx` file means updating its YAML manifest.**
- **Commit `vortex.lock` changes only when you changed dependencies on purpose**, and say why in the commit message.
- **An artifact that changes on rebuild without a source change is a bug.** Fix or report it; never work around it.

## Modules

- **Each module has its own export macro.** Its CMake target generates `<Module>Export.h` with `GenerateExportHeader`,
  defining `<MODULE>_API`; the core has its own. Windows needs each shared library to export its own symbols.
- **Linkage is chosen per module in the manifest.** `vbuild` rejects a static module linked into more than one shared
  binary, since that duplicates its global state.
- **The core links no module.** The application (the Sandbox or a game) links the core and the modules.
- **Modules are registered by generated code.** One `vbuild`-generated source file, compiled into the application, calls
  each module's entry point in dependency order. Static initializers are not used: their order across translation units
  is unspecified and they force whole-archive linking.
- **`cmake/Vortex.cmake` provides a hand-written, target-based CMake API.** A module's `CMakeLists.txt` declares its
  target through it, and the generated `VortexModules.cmake` calls it once per module, so plain CMake still works.
- **Code tests for a module only through `VORTEX_HAS_<MODULE>`** in `VortexConfig.h`.

The current `add_vortex_module`, `register_vortex_module` and shared `VE_EXPORT` macro predate this design.

## Data-oriented design

```cpp
/// Entity positions as SoA: a system reading only `x` streams one contiguous array.
struct PositionBuffer {
    float* x;        ///< `count` elements.
    float* y;        ///< `count` elements.
    float* z;        ///< `count` elements.
    uint32_t count;
};

/// Pure transform; `out.count` must equal `in.count`. `dt` is the fixed timestep.
struct GravityModule {
    static void Process(const VelocityBuffer& in, VelocityBuffer& out, float dt);
};
```

- **Prefer fixed-capacity, arena- or chunk-allocated buffers** to `std::vector` growth in the frame loop.
- **Reference across buffers with handles or indices** (`uint32_t`), not pointers.
- **`static_assert(std::is_trivially_copyable_v<T>)`** on every type that goes into a buffer or queue.
- **Mutable state lives in stores.** A store is a declared state container: SoA buffers owned by the engine, or the
  objects of an OOP library. Several stores may coexist; a system declares which it reads and writes. Modules receive
  `const` slices of a store and write caller-provided output slices.
- **A store changes only through events on the engine bus**, applied by handlers at a declared barrier in a fixed order.
  DOD and OOP stores alike.

## Game objects

Game developers choose per type:

- **DOD API:** systems that iterate buffers directly.
- **OOP API, transpiled:** a type declared with `VGAMEOBJECT()` is lowered by `vbuild` into SoA storage plus a proxy
  that calls the DOD API, at the cost of hand-written DOD. For types that exist in quantity or are touched every frame.
- **Plain OOP, untranspiled:** ordinary C++ objects outside the SoA chunks, virtuals and all, not wrappers over DOD
  code. Not iterated by systems; they integrate through the event bus.

```cpp
/// Single source of truth for the Player layout; vbuild generates `PlayerProxy`.
VGAMEOBJECT(Player,
    (float,  health),
    (Vec3,   position)
);

void ApplyDamage(PlayerProxy p, float amount) {
    p.health() -= amount;   // -> chunk.health[p.slot] -= amount;
}
```

- **A proxy holds a chunk index and a slot index, never a pointer.**
- **Entity declarations have no virtual methods, base classes or heap-owned members**; the generator rejects them.
- **Never keep a proxy across frames without revalidating it**; slots may be compacted. Keep the stable entity ID.
- **Behaviour lives in systems**, never inside the entity.

### Proposed: DOD classes and `VRef`

Not yet adopted. When adopted, it replaces `VGAMEOBJECT()` and the proxies above.

- **An empty marker macro before a class** (placeholder name `VE_DOD_CLASS()`) makes `vbuild` generate its SoA store and
  member access. A marked class has no base classes, no virtual functions and only trivially copyable members.
- **Game objects always refer to each other through `VRef<T>`**, DOD and OOP alike, never by value, pointer or C++
  reference. It is an 8-byte, trivially copyable handle passed by value: slot, generation (how often the slot was
  reused) and store id. A type can switch paradigm without changing call sites.
- **A store holds one layout:** SoA columns for a DOD class, or an array of object pointers for an OOP type, with one
  generation per slot. A reference resolves a DOD class straight to its columns and an OOP type through the slot's
  pointer, chosen at compile time, so only OOP pays the extra lookup.
- **It has pointer-like syntax without being a pointer.** `ref->member` reaches members (for a DOD class, through a
  temporary struct of member references that optimized builds remove), `explicit operator bool` says whether the object
  still exists, and references compare with `==` and against `nullptr`. No conversion to `T*` and no `operator*`.
- **Several stores per type.** `store.Create<T>(args...)`, `store.Destroy(ref)`, and `store.Adopt(...)` to make an
  existing OOP object referable. Other threads push these as requests that the owning thread applies at the barrier.
- **Each game object type has a default store**, generated by `vbuild`, created at startup and owned by the simulation
  thread; `Create<T>(args...)` without a store uses it. Explicit stores are for several stores of a type, or for
  fixed-size ones.
- **A store may declare indices:** a filter on a pure predicate (one that reads only the object's own members) or a key.
  The barrier updates an index whenever a write changes a member it reads, so `FindMany` on an indexed predicate returns
  the cached result. Indices are never automatic, since every write to a member pays for each index on it; key indices
  iterate in slot order.
- **After the MVP, a store may be bound to one thread.** Its writes apply immediately, with no request queue, and access
  from any other thread is rejected: by `vbuild` where the engine's job and system APIs make it visible, and by a thread
  check on every resolve, release builds included.
- **Stores grow by doubling at a barrier.** A store created as fixed-size never grows or moves, so its owning thread may
  also create objects during a phase; `Create` on a full one returns an invalid reference.
- **Destroying an object bumps its slot's generation at the barrier**, so stale references fail their check before the
  slot can be reused. Anything that outlives a phase, such as an event, carries the `VRef`; a request whose generation
  no longer matches is dropped, like a request for a destroyed object.
- **Writes through a `VRef` become requests.** `vbuild` lowers `ref->member = value` and compound assignments (`-=`,
  `+=`, ...) into requests applied at the barrier in a fixed order (system order, then entity ID). Reads in the same
  phase see the old value.
- **`VRefSet<T>` applies one operation to many objects.** `store.FindMany(predicate)` returns the matching objects,
  always iterated in slot order; for each method `Foo` of a DOD class, `vbuild` generates `FooAll` on the set. A call
  becomes one request, applied at the barrier as a loop over the SoA columns in slot order, which the compiler can
  vectorize; slots whose generation no longer matches are skipped.
- **Never keep what `->` returns past the current phase**; keep the `VRef`. At the barrier, the object may be destroyed,
  its slot reused or its store grown.
- **`vbuild` rejects `Player*` and `Player&` to DOD classes**, naming `VRef<Player>` in the diagnostic.
- **`VRef<Derived>` converts to `VRef<Base>`**; downcasts check the object's concrete type without RTTI.
- **`vbuild` generates LLDB and Visual Studio formatters** that show the referenced object, not the handle.

## `.cppx` UI

UI is declared in C++ with the `REACT(<HTML>)` macro. `{expr}` interpolates C++ values and `REACT_MAP` expands a list.
`vbuild` unrolls the block into straight-line C++ that emits `UICommand`s into the frame's `UICommandBuffer`; what
`REACT()` evaluates to is not fixed yet.

```cpp
/// Builds the HUD for one player. Zero allocation.
auto RenderHud(const HudState& s) {
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

- **No virtual DOM.** The POD UI state is hashed each frame; when the hash changes, the command buffer is rebuilt in
  full. No per-node dirty flags or retained trees.
- **Zero allocation inside `REACT()`.** Use fixed buffers or pre-formatted state, never `std::string` concatenation.
- **Scoped styles compile to hashed integer IDs and bitmasks** resolved on the CPU. No runtime CSS parsing or
  string-based selector matching.
- **Generated output keeps `#line` directives** pointing at the `.cppx` source.
- **IDE support comes from an LSP proxy built on Volar.** It builds shadow documents, with HTML regions replaced by
  whitespace that preserves line and column positions, so `clangd` sees valid C++; HTML and CSS queries go to their own
  language services. **A change to `.cppx` syntax updates the shadow document generator in the same change**, with
  positions verified.

## Events and callbacks

Systems communicate only through the **event bus**: lock-free queues, each drained at a declared phase barrier, so
ordering is reproducible.

```cpp
struct EventBus {
    /// Physics phase -> Gameplay phase; drained at the PostPhysics barrier.
    SpscQueue<CollisionEvent, 4096> collisions;
};
```

- **Use the narrowest queue that fits:** SPSC, then MPSC, then MPMC. Name the producer and consumer phases on every
  queue declaration.
- **Emitting is a queue push, nothing more.** A handler fired inside a transform runs arbitrary code on an arbitrary
  thread, pollutes the cache, makes ordering depend on scheduling and can re-enter the buffer being iterated.
- **Handlers run at a barrier**, on a known thread, in registration order or sorted by entity ID, never hash-map order.
  Prefer handlers that take a slice of events.
- **Plain OOP objects register individual callbacks** and unsubscribe in their destructor. **DOD systems use one
  subscription** and filter the event stream by predicate.
- **In hot paths, use a function pointer and a context handle** rather than a capturing `std::function`, which may
  allocate. Sort thousands of indirect calls per frame by target.

## Feature toggles

Toggles resolve through an override chain, later wins: the project's local toggle file, then the official Vortex toggle
server, then a server the game developer runs.

- **Every toggle has a default and a one-line description in the local file.**
- **Toggles resolve once, at startup or a phase barrier**, never from the network inside a transform.
- **Compile-time toggles come from `VortexConfig.h`, runtime toggles from the toggle client API.** Module code never
  reads the file or the servers.

## Naming

- **PascalCase** for types, functions and methods. **snake_case** for variables, parameters and data members; private
  members end in `_` and globals start with `g_`. **UPPER_SNAKE_CASE** for constants (`constexpr`, and `const` at
  namespace or class scope); `const` locals and parameters stay snake_case.
- **Names the language or the standard library require stay lowercase:** `begin`, `end`, `size`, `data`, `empty`, `get`,
  `swap` and their variants.
- **Every third-party API sits behind a façade** that follows this convention, so libraries stay replaceable.
- `.clang-tidy` enforces the convention. The macro prefix is not unified yet: code uses `VE_`, `vbuild` documents
  `VORTEX_`.

## Documentation

1. **Make the code say it.** If a block needs a comment, extract it into a function whose name is the comment.
2. **Document public interfaces in one to three `///` lines:** what it does and any invariant the caller must respect
   (thread ownership, buffer sizes, phase). Don't restate the signature.
3. **Mark every deviation from these rules with a one-line `// RATIONALE:`**, the only place justification belongs in
   code.
4. **Keep comments in sync.** A change in behaviour updates or deletes its comment in the same change.
5. **Docs describe the repository as it is.** Design decisions live in this file, or in `docs/` when too long, each with
   a one-line reason where it isn't obvious.
6. **Markdown wraps at 120 columns**, like `.clang-format` for C++. The pre-commit hook rewraps prose and list items
   with `.githooks/scripts/mdwrap.py`; headings, tables, code blocks and hard line breaks stay as written.

## Contributing

Work is tracked as GitHub Issues and lands through Pull Requests. Maintainers decide what is accepted, but the project
seeks consensus so people build together rather than fork; when a fork is unavoidable, prefer an alternative module,
since the module system lets competing implementations coexist.

- **A suggestion is a proposal.** File it as an Issue from `.github/ISSUE_TEMPLATE/`; it is built only once maintainers
  accept it.
- **One Issue, one PR.** Scope the PR to its Issue and file adjacent work as a new Issue. Keep the Issue current.
- **Keep PRs small:** one kind of change (feature, behaviour change, refactor, or tooling), never a refactor mixed with
  a behaviour change.
- **A PR description states the change, the Issue it closes and the verification you ran.**
- **Never push to protected branches.** Everything goes through review, maintainer work and generated artifacts
  included.
- **Git hooks install themselves** the first time CMake configures (`VORTEX_INSTALL_GIT_HOOKS`, default `ON`) and never
  overwrite an existing `core.hooksPath`. Without a build, run `cmake -P cmake/GitHooks.cmake` once. The pre-commit hook
  rewraps staged Markdown and re-stages it; the working copy is updated only when it has no unstaged edits.

### Before a change is done

- The build succeeds from a clean tree with no new warnings.
- Generated artifacts are byte-identical across two consecutive builds.
- Determinism tests pass: identical inputs give identical output buffers under any worker-thread count.
- No new `virtual`, `std::shared_ptr`, RTTI or frame-loop heap allocation in performance-critical code without a
  `// RATIONALE:`; grep is a fair first check.
- Every handler runs at a barrier, none at emit time.
- `.cppx` changes keep shadow-document positions and `#line` mapping correct.
- New toggles, modules, entities and capabilities are in the YAML manifest, and the lockfile diff is intentional.
- Public interfaces are documented, and no comment refers to anything outside the repository.

## License

Apache License 2.0; see `LICENSE`.
