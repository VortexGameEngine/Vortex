## Overview

- Each vortex module is defined by a `vortex_module.yaml` manifest file.
- Each vortex repository is defined by a `vortex_repository.yaml` manifest file. A vortex repository contains one or
more vortex modules.
- Any local installation with vbuild will reference vortex repositories through its local `repositories.yaml` manifest 
file.
- A vortex project is defined by a `vortex.yaml` manifest file. This file references all vortex modules used by the
project as well as potential optional fields such as linkage type, if possible.

## Vortex Module Manifest Files

A vortex module manifest file (`vortex_module.yaml`) defines a vortex module.




## Vortex Repository Files

A vortex repository file (`vortex_repository.yaml`) contains information about a Vortex repository.


```yaml
version: 1
type: repository
repos:
  vortex-modules:
    type: git
    url: https://github.com/vortexengine/modules.git
    description: Official VortexEngine module collection
```