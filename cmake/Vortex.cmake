# Copyright 2024 André Santos (and_s52@hotmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(VORTEX_MODULES "")
set(VORTEX_MODULES_STATIC "")
set(VORTEX_MODULES_DYNAMIC "")
set(VORTEX_MODULES_DEFINITIONS "-Dc")

# Macro stating that we are compiling Vortex
add_compile_definitions(VE_COMPILE_VORTEX)

# If Vortex Engine is dynamically linked, set the macro definition
if (${VORTEX_ENGINE_DYNAMIC_LINK})
    add_compile_definitions(VE_LK_DYNAMIC)
endif()

function(add_vortex_module MODULE_DIR DYNAMIC_LINK_MODULE)
    # TODO: Per module static linking currently broken, so we ignore this setting
    if(${DYNAMIC_LINK_MODULE})
        set(DYNAMIC_LINK_MODULE ON)
    endif()

    add_subdirectory(${MODULE_DIR})
    set(DYNAMIC_LINK_MODULE ${DYNAMIC_LINK_MODULE} PARENT_SCOPE)
    include_directories(${MODULE_DIR})

    # The list of all modules regardless of linkage
    set(VORTEX_MODULES "${VORTEX_MODULES}${MODULE_DIR};" PARENT_SCOPE)

    if(${DYNAMIC_LINK_MODULE})
        # The list of all dynamically linked modules
        set(VORTEX_MODULES_DYNAMIC "${VORTEX_MODULES_DYNAMIC}${MODULE_DIR};" PARENT_SCOPE)
    else()
        # The list of all statically linked modules
        set(VORTEX_MODULES_STATIC "${VORTEX_MODULES_STATIC}${MODULE_DIR};" PARENT_SCOPE)
    endif()

    # If at least one module is dynamically linked, Vortex Engine needs to be dynamically linked
    if (${DYNAMIC_LINK_MODULE} AND NOT ${VORTEX_ENGINE_DYNAMIC_LINK})
        message( FATAL_ERROR "Cannot dynamically link modules if VORTEX_ENGINE_DYNAMIC_LINK is set to false. Compilation aborted." )
    endif()
endfunction()

function(register_vortex_module MODULE_NAME)
    set(VORTEX_MODULES_DEFINITIONS "${VORTEX_MODULES_DEFINITIONS} -DVE_MODULE_${MODULE_NAME}" PARENT_SCOPE)
endfunction()