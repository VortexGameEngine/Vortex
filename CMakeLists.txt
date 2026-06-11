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

cmake_minimum_required(VERSION 3.28)
project(VortexEngine)

option(ENABLE_CLANG_TIDY "Run clang-tidy during build" ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if (ENABLE_CLANG_TIDY)
    find_program(CLANG_TIDY_EXE NAMES clang-tidy)
    if (CLANG_TIDY_EXE)
        message(STATUS "clang-tidy found: ${CLANG_TIDY_EXE}")
        if(MSVC)
            set(CMAKE_CXX_CLANG_TIDY "${CLANG_TIDY_EXE};-p=${CMAKE_BINARY_DIR};-warnings-as-errors=*;--extra-arg=/EHsc")
        else()
            set(CMAKE_CXX_CLANG_TIDY "${CLANG_TIDY_EXE};-p=${CMAKE_BINARY_DIR};-warnings-as-errors=*")
        endif()
    else()
        message(WARNING "clang-tidy not found!")
    endif()
endif()

if(MSVC)
    add_compile_options("/EHsc")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(VORTEX_ENGINE_DYNAMIC_LINK ON)

include(ThirdParty/yaml-cpp.cmake)
include(cmake/Vortex.cmake)
include_directories(VortexEngine)
include_directories(ThirdParty)

# Add vbuild project
add_subdirectory(tools/vbuild)

###########################################
# Add Vortex modules here
add_vortex_module(VortexHelloWorld ON)
add_vortex_module(VortexGoodbye ON)
###########################################

# Engine and linker setup
if (${VORTEX_ENGINE_DYNAMIC_LINK})
    set(BUILD_SHARED_LIBS ON)
    set(WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

add_library(${PROJECT_NAME}
        VortexEngine/src/Bid.cpp)
target_link_libraries(${PROJECT_NAME} ${VORTEX_MODULES_DYNAMIC} "$<LINK_LIBRARY:WHOLE_ARCHIVE,${VORTEX_MODULES_STATIC}>")

# Add Sandbox project
add_subdirectory(Sandbox)