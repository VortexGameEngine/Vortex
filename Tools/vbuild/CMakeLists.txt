include_directories(.)
add_executable(vbuild src/main.cpp)
target_link_libraries(vbuild PUBLIC yaml-cpp::yaml-cpp)

if(WIN32 AND MINGW)
    get_filename_component(MINGW_BIN_DIR ${CMAKE_CXX_COMPILER} DIRECTORY)
    add_custom_command(TARGET vbuild POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${MINGW_BIN_DIR}/libgcc_s_seh-1.dll"
            "${MINGW_BIN_DIR}/libstdc++-6.dll"
            "${MINGW_BIN_DIR}/libwinpthread-1.dll"
            $<TARGET_FILE_DIR:vbuild>
    )
endif()