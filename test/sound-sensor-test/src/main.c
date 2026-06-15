#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "hardware/adc.h"

#define SOUND_PIN_AO   26    // GP26, Pin 31 — analog out (ADC0)
#define THRESHOLD     250    // AO must exceed this to count as a trigger
#define DEBOUNCE_MS  1000    // minimum ms between triggers
#define LED_ON_MS     200

int main() {
    stdio_init_all();
    sleep_ms(2000);

    if (cyw43_arch_init()) { printf("WiFi init failed\n"); return -1; }

    adc_init();
    adc_gpio_init(SOUND_PIN_AO);
    adc_select_input(0); // ADC0 = GP26

    printf("\n\nBMO SOUND SENSOR — AO MODE\n");
    printf("===========================\n");
    printf("Threshold: %d / 4095\n", THRESHOLD);
    printf("Idle baseline is ~150. Clap/voice should hit 250+.\n\n");

    int      trigger_count   = 0;
    uint32_t last_trigger_ms = 0;
    uint32_t last_status_ms  = 0;
    uint16_t ao_peak         = 0;

    while (true) {
        uint16_t ao  = adc_read();
        uint32_t now = to_ms_since_boot(get_absolute_time());

        if (ao > ao_peak) ao_peak = ao;

        // Trigger on peak exceeding threshold, debounced
        if (ao_peak > THRESHOLD && (now - last_trigger_ms) > DEBOUNCE_MS) {
            last_trigger_ms = now;
            trigger_count++;
            printf("[%8lu ms]  *** TRIGGER #%d ***  (peak=%u)\n",
                   now, trigger_count, ao_peak);
            cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, 1);
        }

        if ((now - last_trigger_ms) > LED_ON_MS) {
            cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, 0);
        }

        // Heartbeat every second
        if (now - last_status_ms >= 1000) {
            last_status_ms = now;
            printf("[%8lu ms]  idle AO=%u  peak=%u  triggers=%d\n",
                   now, ao, ao_peak, trigger_count);
            ao_peak = 0; // reset peak window
        }

        sleep_ms(5); // 200 Hz sampling
    }
}
