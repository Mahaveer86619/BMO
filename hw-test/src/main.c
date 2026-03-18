#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"

#define WIFI_SSID "Airtel_sidd_4070"
#define WIFI_PASSWORD "air50584"

int main()
{
    stdio_init_all();

    // Give the USB serial port 2 seconds to enumerate
    sleep_ms(2000);
    printf("BMO Booting... Initializing Wi-Fi\n");

    if (cyw43_arch_init())
    {
        printf("Failed to initialize Wi-Fi\n");
        return 1;
    }
    cyw43_arch_enable_sta_mode();

    printf("Connecting to Wi-Fi network: %s...\n", WIFI_SSID);
    if (cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASSWORD, CYW43_AUTH_WPA2_AES_PSK, 10000))
    {
        printf("Failed to connect to Wi-Fi.\n");
        return 1;
    }

    printf("Connected successfully!\n");

    while (true)
    {
        printf("BMO is online and breathing...\n");
        sleep_ms(5000);
    }

    cyw43_arch_deinit();
    return 0;
}