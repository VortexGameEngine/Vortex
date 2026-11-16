# 0001. Naming convention

**Status:** Accepted

## Context

Engine, module and tool code mixes snake_case and PascalCase functions, and contributors need one rule that `clang-tidy`
can enforce.

## Decision

- **Name types, functions and methods in PascalCase; variables, parameters and data members in snake_case; constants in
  UPPER_SNAKE_CASE.** `.clang-tidy` holds the full rule set and enforces it.
- **Keep names the language or the standard library require in lowercase.** Range-based `for` needs `begin` and `end`,
  structured bindings need `get`, and standard algorithms expect `size`, `data`, `empty` and `swap`.
- **Wrap every third-party API in a façade** that follows this convention, so a library's naming never reaches engine
  code and the library stays replaceable.

## Consequences

- `.clang-tidy` and the existing snake_case functions change together, because the build treats `clang-tidy` warnings as
  errors.
- The macro prefix is not yet unified: existing code uses `VE_`, while `vbuild` documents generated macros as `VORTEX_`.
