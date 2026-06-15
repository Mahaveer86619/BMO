# Makefile for BMO Sound Sensor Test

BUILD_DIR = build
TARGET    = sound_sensor_test

all: build

build:
	@if not exist $(BUILD_DIR) mkdir $(BUILD_DIR)
	cd $(BUILD_DIR) && cmake .. -G "MinGW Makefiles"
	cd $(BUILD_DIR) && $(MAKE)

flash: build
	@echo "Flashing $(TARGET).uf2 to Pico..."
	picotool load -x $(BUILD_DIR)/$(TARGET).uf2

deploy: flash

clean:
	@if exist $(BUILD_DIR) rd /s /q $(BUILD_DIR)

.PHONY: all build flash deploy clean
