# 0002. Module linkage and export macros

**Status:** Accepted

## Context

A module can be linked statically or as a shared library, chosen per module. On Windows, every shared library must mark
its own public symbols `dllexport` while building and `dllimport` while being used, so one export macro cannot serve the
engine core and every module. Linking the same static module into two shared binaries silently duplicates its global
state.

## Decision

- **Give every module its own export macro.** The module's CMake target generates `<Module>Export.h` with CMake's
  `GenerateExportHeader`, defining `<MODULE>_API`. Engine core symbols use the core's own macro.
- **Choose linkage per module in the project manifest.** `vbuild` resolves it and rejects a graph in which a static
  module would be linked into more than one shared binary.
- **Keep the core independent of modules.** The application target (Sandbox or a game) links the core and the modules;
  the core links no module.
- **Register modules with generated code, not static initializers.** `vbuild` generates one source file, compiled into
  the application, that calls each module's entry point in dependency order. Static-initializer registration is rejected
  because its order across translation units is unspecified, and because it forces whole-archive linking.
- **Keep a hand-written, target-based CMake API in `cmake/Vortex.cmake`.** A module's own `CMakeLists.txt` declares its
  target through it, and the generated `.vbuild/VortexModules.cmake` calls it once per resolved module. Generated CMake
  stays small, and a project can still be configured with plain CMake.
- **Expose module presence only through `VortexConfig.h`** (`VORTEX_HAS_<MODULE>`).

## Consequences

- `add_vortex_module` and `register_vortex_module` are replaced by the target-based API; the `VE_MODULE_<NAME>`
  definitions disappear.
- Directory-scoped settings (`include_directories`, `add_definitions`, a module setting `BUILD_SHARED_LIBS`) become
  target properties.
- The shared `VE_EXPORT` macro and the global `VE_COMPILE_VORTEX` definition are replaced by per-target export headers.
- Each module defines an entry point the generated registration file can call.
