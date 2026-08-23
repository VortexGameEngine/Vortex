// Copyright 2025 André Santos (and_s52@hotmail.com)
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

#include <string_view>
#include "CLI11.hpp"

#ifdef _WIN32
#include <windows.h>
static void enable_ansi() {
    DWORD mode = 0;
    HANDLE stderr_handle = GetStdHandle(STD_ERROR_HANDLE);
    GetConsoleMode(stderr_handle, &mode);
    SetConsoleMode(stderr_handle, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);

    HANDLE stdout_handle = GetStdHandle(STD_OUTPUT_HANDLE);
    GetConsoleMode(stdout_handle, &mode);
    SetConsoleMode(stdout_handle, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
}
#else
static void enable_ansi() {}
#endif

constexpr std::string_view TERMINAL_RED_COLOR = "\x1b[31m";
constexpr std::string_view TERMINAL_DEFAULT_COLOR = "\x1b[0m";

template<typename T>
void append_arg_as_string(std::string &out, const T &val) {
    if constexpr (std::is_constructible_v<std::string_view, T>) {
        out.append(std::string_view(val)); // NOLINT(cppcoreguidelines-pro-bounds-array-to-pointer-decay)
    } else {
        out.append(std::to_string(val));
    }
}

template<const std::string_view &Color, typename... Args>
std::string format_message(const Args &...args) {
    std::string result;
    result.append(Color);
    (append_arg_as_string(result, args), ...);
    result.append(TERMINAL_DEFAULT_COLOR);
    result.push_back('\n');
    return result;
}

template<const std::string_view &Color, std::ostream &Stream, typename... Args>
void print_message(const Args &...args) {
    Stream << format_message<Color>(args...);
}

template<typename... Args>
void print_error(const Args &...args) {
    print_message<TERMINAL_RED_COLOR, std::cout>(args...);
}

template<typename... Args>
void print(const Args &...args) {
    print_message<TERMINAL_DEFAULT_COLOR, std::cout>(args...);
}

int main(int argc, char *argv[]) { // NOLINT(bugprone-exception-escape)
    enable_ansi();

    try {
        CLI::App app{"", "vbuild"};
        argv = app.ensure_utf8(argv);

        // Apply custom formatter to enforce red color for errors on all terminals
        app.failure_message([](const CLI::App *, const CLI::Error &e) {
            return format_message<TERMINAL_RED_COLOR>(e.what());
        });

        std::string filename = "default";
        auto filename_option = app.add_option("-f,--file", filename, "A help string");

        CLI11_PARSE(app, argc, argv);

        print(filename);
        if (!*filename_option) {
            print("Filename option not passed. Using default filename path '", filename, "'");
        }

        print_error("This ", "is ", "a ", "test ", "with ", false); // NOLINT(*-avoid-magic-numbers)
    } catch (const std::exception &e) {
        print_error(e.what());
        return 1;
    }

    return 0;
}
