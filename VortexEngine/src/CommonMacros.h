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
#include "PlatformMacros.h"

#if defined(VE_PLATFORM_WINDOWS)
    #define VE_DLL_EXPORT __declspec(dllexport)
    #define VE_DLL_IMPORT extern __declspec(dllimport)
#else
    #define VE_DLL_EXPORT
    #define VE_DLL_IMPORT
#endif

#if defined(VE_PLATFORM_WINDOWS) && defined(VE_LK_DYNAMIC)
    #ifdef VE_COMPILE_VORTEX
        #define VE_EXPORT VE_DLL_EXPORT
    #else
        #define VE_EXPORT VE_DLL_IMPORT
    #endif
#else
    #define VE_EXPORT
#endif