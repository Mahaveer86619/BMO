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
set(PICO_BOARD pico_w CACHE STRING "Board type")

cmake_minimum_required(VERSION 3.22)

# Set PICO_SDK_PATH if not provided in environment
if (NOT DEFINED ENV{PICO_SDK_PATH})
    set(ENV{PICO_SDK_PATH} "C:/Users/Admin/.pico-sdk/sdk/2.2.0")
endif()

include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(bmo_wifi_test C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(wifi_test
    src/main.c
)

target_include_directories(wifi_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

target_link_libraries(wifi_test
    pico_stdlib
    pico_cyw43_arch_lwip_threadsafe_background
)

pico_enable_stdio_usb(wifi_test 1)
pico_enable_stdio_uart(wifi_test 0)
pico_add_extra_outputs(wifi_test)