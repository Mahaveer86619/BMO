# Force Generic system to prevent CMake from using Windows linker flags
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================

set(PICO_BOARD pico_w CACHE STRING "Board type" FORCE)
set(PICO_SDK_PATH "C:/Users/Admin/.pico-sdk/sdk/2.2.0" CACHE PATH "Path to the Pico SDK" FORCE)

cmake_minimum_required(VERSION 3.22)

include(${PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(sound_sensor_test C CXX ASM)

pico_sdk_init()

add_executable(sound_sensor_test
    src/main.c
)

target_include_directories(sound_sensor_test PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(sound_sensor_test
    pico_stdlib
    hardware_adc
    pico_cyw43_arch_lwip_threadsafe_background
)

pico_enable_stdio_usb(sound_sensor_test 1)
pico_add_extra_outputs(sound_sensor_test)
