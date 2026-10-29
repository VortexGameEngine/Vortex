# Agents: `vbuild`

## Overview

`vbuild` is the transpiling build orchestrator of the **VortexEngine** ecosystem. It coordinates project manifests
(`vortex.yaml`), module manifests (`vortex_module.yaml`), the dependency resolver, the transpiler and the underlying
build system (CMake).

`vbuild` is a source-to-source compiler plus a build driver; it replaces neither the C++ compiler nor CMake. It resolves
the module graph from declarative YAML manifests, copies the project sources into `.vbuild/`, transpiles the Vortex
dialect (`VGAMEOBJECT`, `REACT`, `.cppx`) there into plain C++, generates the CMake and configuration artifacts, and
drives CMake over the result.

---

## Responsibilities
- Parse project manifest **vortex.yaml**
- Parse each module’s **vortex_module.yaml**
- Resolve:
    - Required modules
    - Capabilities
    - Version ranges and constraints
    - Conflicts and exclusivity rules
- Copy the project sources into `.vbuild/` and transpile the Vortex dialect there into plain C++
- Generate deterministic build metadata:
    - `.vbuild/VortexModules.cmake`
    - `.vbuild/VortexConfig.h`
    - `vortex.lock`
- Prepare a fully configured build directory for CMake
- Expose compile-time macros for use inside engine and module code
- Invoke CMake during `vbuild build`

---

## Lifecycle

The typical `vbuild` lifecycle follows four steps:

1. **Initialize** — Create a new project and manifest  
2. **Configure** — Resolve modules, capabilities, and constraints  
3. **Generate** — Copy and transpile sources into `.vbuild/`, write build files and C/C++ macros*
4. **Build** — Invoke CMake and the native build system

*Some macros are generated through CMake, others are are written by `vbuild` in the VortexConfig.h header.

---

## CLI Commands

| Command                               | Purpose                                                              |
|---------------------------------------|----------------------------------------------------------------------|
| `vbuild init [--template <name>]`     | Initialize a new project with a `vortex.yaml` manifest               |
| `vbuild configure [--define KEY=VAL]` | Resolve dependencies and generate build configuration files          |
| `vbuild build [<cmake-args>...]`      | Run CMake and build the project                                      |
| `vbuild add <module>[@version]`       | Add a module to the project manifest                                 |
| `vbuild remove <module>`              | Remove a module from the project manifest                            |
| `vbuild clean`                        | Remove generated `.vbuild/` directory                                |
| `vbuild list`                         | Lists all added modules and their respective version                 |
| `vbuild doctor`                       | Diagnose manifest errors, version conflicts, or missing dependencies |

---

## Generated Artifacts

`vbuild` writes the transpiled sources and the following files into `.vbuild/`; `vortex.lock` goes to the project root:

| File                  | Purpose                                                                                      |
|-----------------------|----------------------------------------------------------------------------------------------|
| `VortexModules.cmake` | CMake include file with `add_subdirectory()` and `find_package()` calls for resolved modules |
| `VortexConfig.h`      | Auto-generated C/C++ header exposing compile-time macros for enabled modules and features    |
| `vortex.lock`         | Lockfile containing resolved module versions for reproducible builds                         |

Everything under `.vbuild/` **must be ignored by version control**; `vortex.lock` is tracked. None of it is edited by
hand.

---

## Resolution Model

### Dependency Resolution Order
1. Load root **vortex.yaml**
2. Read each declared module
3. Load module manifests (`vortex_module.yaml`)
4. Expand recursive dependency closure (`requires`)
5. Validate:
    - Missing modules
    - Version mismatches
    - Capability conflicts
    - Explicit module conflicts
6. Produce the final, topologically sorted module list
7. Emit all artifacts into `.vbuild/`

### Conflict Resolution Rules
| Condition                                           | Result                                                            |
|-----------------------------------------------------|-------------------------------------------------------------------|
| Required module missing                             | Error: unresolved dependency                                      |
| Two modules provide mutually exclusive capabilities | Error: capability conflict                                        |
| Two modules conflict with one another               | Error: module conflict violation                                  |
| Multiple providers allowed                          | vbuild selects based on project preferences or explicit overrides |

---

## Macros and Preprocessor Defines

`vbuild` generates `VortexConfig.h` with a rich set of compile-time macros:

| Macro                                       | Description                                                                                                      |
|---------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `VORTEX_ENGINE_VERSION`                     | Engine version string                                                                                            |
| `VORTEX_LINK_STATIC` / `VORTEX_LINK_SHARED` | Selected link mode                                                                                               |
| `VORTEX_HAS_<MODULE>`                       | Defined if a given module is present (e.g. `VORTEX_HAS_RENDERER_VULKAN`)                                         |
| `VORTEX_MODULE_VERSION_MAJ_<MODULE>`        | Defined if a given module is present with its major version (e.g. `VORTEX_MODULE_VERSION_MAJ_RENDERER_VULKAN`)   |
| `VORTEX_MODULE_VERSION_MIN_<MODULE>`        | Defined if a given module is present with its minor version (e.g. `VORTEX_MODULE_VERSION_MIN_RENDERER_VULKAN`)   |
| `VORTEX_MODULE_VERSION_PATCH_<MODULE>`      | Defined if a given module is present with its patch version (e.g. `VORTEX_MODULE_VERSION_PATCH_RENDERER_VULKAN`) |
| `VORTEX_CAP_<CAPABILITY>`                   | Defined if a capability is satisfied (e.g. `VORTEX_CAP_PHYSICS`)                                                 |
| `VORTEX_FEATURE_<FEATURE>`                  | Defined if a feature is enabled (e.g. `VORTEX_FEATURE_UI_DOCKING`)                                               |

These macros can be included anywhere in the engine or module code:

```c++
#include <VortexConfig.h>

#ifdef VORTEX_HAS_RENDERER_VULKAN
    // Vulkan-specific rendering path
#endif
```

---

## Directory Structure

A standard project using `vbuild` might look like this:

```
project/
├─ vortex.yaml                # Project manifest (tracked)
├─ vortex.lock                # Project lockfile (tracked by default)
├─ modules/
│  ├─ Renderer.Vulkan/
│  │  ├─ vortex_module.yaml   # Module manifest (tracked)
│  │  └─ CMakeLists.txt       # Module build logic (tracked)
│  └─ Physics.Bullet/
│     └─ vortex_module.yaml
├─ .vbuild/                   # Generated build metadata (ignored)
│  ├─ VortexModules.cmake
│  └─ VortexConfig.h
└─ build/                     # CMake build directory (ignored)
```

---

## Integration with CMake

Projects integrate with `vbuild` by including the generated CMake file in their top-level `CMakeLists.txt`:

```cmake
include(${CMAKE_SOURCE_DIR}/.vbuild/VortexModules.cmake)
```

The rest of the build system remains standard CMake.

---

## Design Principles

- **Declarative by design**: YAML manifests are the single source of truth.  
- **Separation of concerns**: `vbuild` handles resolution, transpilation and generation; CMake handles compilation.  
- **Composable**: modules declare capabilities and dependencies without tight coupling.  
- **Reproducible**: lockfile ensures deterministic builds.  
- **Non-invasive**: existing CMake projects require no fundamental rewrites.

---

## Notes

- All `vbuild` commands are idempotent. Running `vbuild configure` multiple times is safe.  
- `vbuild` is designed for **compile-time modules**, not runtime plugins. A separate plugin loader may exist.  
- Projects should **not** commit `.vbuild/` or `build/` directories to version control.  

---

## See Also

- [`vortex.yaml` Reference](Docs/Manifests.md)  
- [`vortex_module.yaml` Reference](Docs/Modules.md)  
- [CMake Integration Guide](Docs/CMake.md)