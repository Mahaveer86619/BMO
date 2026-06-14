# Makefile for BMO OLED Test

BUILD_DIR = build
TARGET = oled_test

all: build

build:
	@if not exist $(BUILD_DIR) mkdir $(BUILD_DIR)
	cd $(BUILD_DIR) && cmake .. -G "MinGW Makefiles"
	cd $(BUILD_DIR) && $(MAKE)

flash: build
	@echo "Flashing $(TARGET).uf2 to Pico..."
	@echo "Ensure your Pico is in BOOTSEL mode or running a program with USB support."
	picotool load -x $(BUILD_DIR)/$(TARGET).uf2

clean:
	@if exist $(BUILD_DIR) rd /s /q $(BUILD_DIR)

.PHONY: all build flash clean
