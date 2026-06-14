#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "ssd1306.h"

#define I2C_PORT i2c0
#define I2C_SDA 8
#define I2C_SCL 9

int main() {
    stdio_init_all();

    // I2C is "broken" on some pico boards if not configured correctly
    i2c_init(I2C_PORT, 400 * 1000);
    gpio_set_function(I2C_SDA, GPIO_FUNC_I2C);
    gpio_set_function(I2C_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_SDA);
    gpio_pull_up(I2C_SCL);

    ssd1306_init(I2C_PORT);

    ssd1306_clear();
    ssd1306_draw_string(0, 0, "Hello, BMO!");
    ssd1306_draw_string(0, 10, "SSD1306 Driver");
    ssd1306_draw_string(0, 20, "Test OK");
    ssd1306_display();

    while (true) {
        printf("OLED Test Running...\n");
        sleep_ms(1000);
    }
}
