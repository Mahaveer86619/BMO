cmake_minimum_required(VERSION 3.22)

include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(oled_test C CXX ASM)

pico_sdk_init()

add_executable(oled_test
    src/main.c
    src/ssd1306.c
)

target_include_directories(oled_test PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(oled_test
    pico_stdlib
    hardware_i2c
)

pico_enable_stdio_usb(oled_test 1)
pico_add_extra_outputs(oled_test)
