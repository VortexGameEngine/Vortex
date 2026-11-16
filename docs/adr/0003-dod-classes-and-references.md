# 0003. DOD classes, `VReference` and stores

**Status:** Proposed

## Context

Game developers write classes; the engine wants Struct-of-Arrays (SoA) storage, where each data member of a type lives
in its own contiguous array. A raw pointer cannot refer to an object whose members are spread across arrays, and a
pointer to a destroyed object dangles silently. A **store** is an engine-owned container of objects of one type; a
**handle** identifies one object in a store by its slot and generation, where the **generation** counts how often the
slot has been reused.

## Decision

- **Mark a DOD class with an empty marker macro** placed before the class. Compilers see nothing; `vbuild` reads the
  marker and generates the SoA store and member access for that class.

  ```cpp
  VE_DOD_CLASS()
  class Player {
  public:
      float health;
      Vec3 position;
  };
  ```

- **Keep DOD classes plain.** A DOD class has no base classes, no virtual functions and only trivially copyable data
  members; `vbuild` rejects anything else.
- **Refer to objects through `VReference<T>`**, for DOD classes and for OOP objects alike. The handle holds a slot, a
  generation and a store id, and is trivially copyable.
- **Give `VReference` pointer-like syntax.** `ref->member` reaches the object's members, `explicit operator bool`
  reports whether the object still exists, and references compare with `==` and against `nullptr`. There is no
  conversion to `T*` and no `operator*`.
- **Allow several stores per type.** Objects are created and destroyed through a store: `store.Create<T>(args...)` and
  `store.Destroy(ref)`. For an OOP type, the store owns the objects at stable addresses.
- **Reject raw pointers and references to DOD classes** (`Player*`, `Player&`) in transpiled code, with a diagnostic
  that names `VReference<Player>`.
- **Convert OOP references along inheritance.** `VReference<Derived>` converts implicitly to `VReference<Base>`.
  Converting down is checked against the concrete type the store recorded for the slot, without RTTI.

## Consequences

- A type can move between DOD and OOP without changing its call sites, since both are reached through `VReference<T>`
  and `->`.
- An OOP object is referable only if a store created it; objects on the stack, from plain `new`, or held as members of
  other objects are not.
- For a DOD class, `->` builds a temporary set of references to the members. Optimized builds remove the unused ones;
  unoptimized builds pay for every member.
- `vbuild` must generate debugger formatters (LLDB and Visual Studio) that show a referenced object's members instead of
  its handle.
- When accepted, AGENTS.md §6 replaces `VGAMEOBJECT()`, the typed proxy handle and `p.health()` with this model, and the
  Sandbox prototype's global `g_PlayerStorage` becomes a store.

## Open questions

- The marker's name; `VE_DOD_CLASS()` above is a placeholder.
- Whether a store may take ownership of an existing OOP object, for example `store.Adopt(std::unique_ptr<Enemy>)`.
- The handle's bit split: 32-bit slot, 16-bit generation and 16-bit store id, or 24-bit slot and 24-bit generation.
- The loop construct OOP-style code uses to iterate a store, so that per-object access does not undo the SoA layout.
