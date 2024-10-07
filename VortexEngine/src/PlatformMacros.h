// Copyright 2024 André Santos (and_s52@hotmail.com)
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#pragma once

// Partially adapted from https://stackoverflow.com/a/5920028 in 2024
// Original Author: Evgeny Gavrin
// Edited by: Top-Master
#if defined(WIN32) || defined(_WIN32) || defined(__WIN32__) || defined(__NT__)
    #define VE_PLATFORM_WINDOWS
#elif __APPLE__
    #define VE_PLATFORM_MACOS
#elif __ANDROID__
    // Below __linux__ check should be enough to handle Android,
    // but something may be unique to Android.
    #define VE_PLATFORM_ANDROID
#elif __linux__
    #define VE_PLATFORM_LINUX
#else
#   error "Unsupported compiler platform"
#endif