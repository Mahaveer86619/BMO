#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"

int main() {
    stdio_init_all();
    while (true) {
        printf("OLED Test Waiting...\n");
        sleep_ms(1000);
    }
}
