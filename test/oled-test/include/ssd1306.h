#ifndef SSD1306_H
#define SSD1306_H

#include "hardware/i2c.h"

// SSD1306 Commands
#define SSD1306_SETCONTRAST 0x81
#define SSD1306_DISPLAYALLON_RESUME 0xA4
#define SSD1306_DISPLAYALLON 0xA5
#define SSD1306_NORMALDISPLAY 0xA6
#define SSD1306_INVERTDISPLAY 0xA7
#define SSD1306_DISPLAYOFF 0xAE
#define SSD1306_DISPLAYON 0xAF
#define SSD1306_SETDISPLAYOFFSET 0xD3
#define SSD1306_SETCOMPINS 0xDA
#define SSD1306_SETVCOMDETECT 0xDB
#define SSD1306_SETDISPLAYCLOCKDIV 0xD5
#define SSD1306_SETPRECHARGE 0xD9
#define SSD1306_SETMULTIPLEX 0xA8
#define SSD1306_SETLOWCOLUMN 0x00
#define SSD1306_SETHIGHCOLUMN 0x10
#define SSD1306_SETSTARTLINE 0x40
#define SSD1306_MEMORYMODE 0x20
#define SSD1306_COLUMNADDR 0x21
#define SSD1306_PAGEADDR 0x22
#define SSD1306_COMSCANINC 0xC0
#define SSD1306_COMSCANDEC 0xC8
#define SSD1306_SEGREMAP 0xA0
#define SSD1306_CHARGEPUMP 0x8D
#define SSD1306_EXTERNALVCC 0x01
#define SSD1306_SWITCHCAPVCC 0x02

// OLED dimensions
#define SSD1306_WIDTH 128
#define SSD1306_HEIGHT 64
#define SSD1306_I2C_ADDR 0x3C

/**
 * @brief Initialize the SSD1306 display
 * 
 * @param i2c The I2C instance to use
 */
void ssd1306_init(i2c_inst_t *i2c);

/**
 * @brief Clear the internal buffer
 */
void ssd1306_clear();

/**
 * @brief Draw a pixel in the internal buffer
 * 
 * @param x X coordinate
 * @param y Y coordinate
 * @param on True to turn on pixel, False to turn off
 */
void ssd1306_draw_pixel(int x, int y, bool on);

/**
 * @brief Draw a character in the internal buffer
 * 
 * @param x X coordinate
 * @param y Y coordinate
 * @param c Character to draw
 */
void ssd1306_draw_char(int x, int y, char c);

/**
 * @brief Draw a string in the internal buffer
 * 
 * @param x X coordinate
 * @param y Y coordinate
 * @param str String to draw
 */
void ssd1306_draw_string(int x, int y, const char *str);

/**
 * @brief Send the internal buffer to the display
 */
void ssd1306_display();

#endif // SSD1306_H
