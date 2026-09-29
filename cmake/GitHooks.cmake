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

# Git cannot ship hooks in a clone, so point core.hooksPath at the versioned .githooks
# directory during configure. An existing hooksPath is never overwritten. Also runs
# standalone, for contributors who never configure a build: cmake -P cmake/GitHooks.cmake
option(VORTEX_INSTALL_GIT_HOOKS "Point git's core.hooksPath at .githooks during configure" ON)

function(vortex_install_git_hooks)
    if (NOT VORTEX_INSTALL_GIT_HOOKS)
        return()
    endif()

    find_package(Git QUIET)
    if (NOT Git_FOUND)
        message(STATUS "git not found: repository hooks not installed")
        return()
    endif()

    if (CMAKE_SCRIPT_MODE_FILE)
        # cmake -P: locate the repository ourselves so it works from any directory
        execute_process(
                COMMAND "${GIT_EXECUTABLE}" rev-parse --show-toplevel
                OUTPUT_VARIABLE REPO_ROOT
                OUTPUT_STRIP_TRAILING_WHITESPACE
                ERROR_QUIET)
        if (REPO_ROOT STREQUAL "")
            message(FATAL_ERROR "Not inside a git repository; cannot install hooks.")
        endif()
    elseif (PROJECT_IS_TOP_LEVEL)
        set(REPO_ROOT "${CMAKE_SOURCE_DIR}")
    else()
        return()
    endif()

    # A worktree or submodule checkout has .git as a file rather than a directory
    if (NOT EXISTS "${REPO_ROOT}/.git")
        return()
    endif()

    execute_process(
            COMMAND "${GIT_EXECUTABLE}" config --get core.hooksPath
            WORKING_DIRECTORY "${REPO_ROOT}"
            OUTPUT_VARIABLE CURRENT_HOOKS_PATH
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET)

    if (CURRENT_HOOKS_PATH STREQUAL ".githooks")
        message(STATUS "Repository hooks already installed (core.hooksPath=.githooks)")
        return()
    endif()

    if (NOT CURRENT_HOOKS_PATH STREQUAL "")
        message(WARNING "core.hooksPath is set to '${CURRENT_HOOKS_PATH}'; leaving it untouched. "
                "Vortex hooks are inactive — run 'git config core.hooksPath .githooks' to enable them.")
        return()
    endif()

    execute_process(
            COMMAND "${GIT_EXECUTABLE}" config --local core.hooksPath .githooks
            WORKING_DIRECTORY "${REPO_ROOT}"
            RESULT_VARIABLE GIT_CONFIG_RESULT
            ERROR_QUIET)

    if (GIT_CONFIG_RESULT EQUAL 0)
        message(STATUS "Installed repository hooks (core.hooksPath=.githooks)")
    else()
        message(WARNING "Could not set core.hooksPath; run 'git config core.hooksPath .githooks' to enable hooks.")
    endif()
endfunction()

vortex_install_git_hooks()
