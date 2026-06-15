#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "pico/cyw43_arch.h"
#include "ssd1306.h"

#define I2C_PORT i2c0
#define I2C_SDA 4
#define I2C_SCL 5

void run_i2c_scan() {
    printf("\nI2C Bus Scan\n");
    printf("   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F\n");
    for (int addr = 0; addr < (1 << 7); ++addr) {
        if (addr % 16 == 0) printf("%02x ", addr);
        int ret;
        uint8_t rxdata;
        // Probing address with a 1-byte read
        ret = i2c_read_blocking(I2C_PORT, addr, &rxdata, 1, false);
        printf(ret >= 0 ? " @ " : " . ");
        if (addr % 16 == 15) printf("\n");
    }
    printf("Done.\n\n");
}

int main() {
    stdio_init_all();

    // Give the USB serial port time to enumerate
    sleep_ms(2000);
    printf("\n\nBMO DYNAMIC OLED TEST STARTING\n");
    printf("==============================\n");

    // Initialize Wi-Fi chip (needed for LED on Pico W)
    if (cyw43_arch_init()) {
        printf("WiFi init failed\n");
        return -1;
    }

    // Initialize I2C at 100kHz
    i2c_init(I2C_PORT, 100 * 1000);
    gpio_set_function(I2C_SDA, GPIO_FUNC_I2C);
    gpio_set_function(I2C_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_SDA);
    gpio_pull_up(I2C_SCL);

    // Initial OLED setup
    ssd1306_init(I2C_PORT);
    sleep_ms(100); // let charge pump and panel settle before drawing

    int loop_count = 0;
    char counter_str[32];

    while (true) {
        static bool led_state = false;
        cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, led_state);
        led_state = !led_state;
        
        printf("OLED Test Running... (Loop %d)\n", loop_count);

        // Every 5th loop, run the scanner
        if (loop_count % 5 == 0) {
            run_i2c_scan();
        }

        // Screen Logic
        ssd1306_clear();
        if (loop_count < 10) {
            // Phase 1: Splash Screen (0-10 seconds)
            ssd1306_draw_string(40, 20, "B M O");
            ssd1306_draw_string(30, 40, "Initializing...");
        } else {
            // Phase 2: Dynamic Counter (After 10 seconds)
            ssd1306_draw_string(0, 0, "BMO ACTIVE");
            ssd1306_draw_string(0, 20, "Counter:");
            
            // Format the counter value
            snprintf(counter_str, sizeof(counter_str), "%d", loop_count - 10);
            ssd1306_draw_string(60, 20, counter_str);
            
            // Progress bar-ish line
            for(int i=0; i < (loop_count % 128); i++) {
                ssd1306_draw_pixel(i, 60, true);
            }
        }
        ssd1306_display();

        loop_count++;
        sleep_ms(1000);
    }
}
