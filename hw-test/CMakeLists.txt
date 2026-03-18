cmake_minimum_required(VERSION 3.22)

include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(bmo C CXX ASM)

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