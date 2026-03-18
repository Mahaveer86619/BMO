#!/bin/bash

# Resolve project root regardless of where the script is called
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIRMWARE="$PROJECT_ROOT/build/wifi_test.uf2"
SERIAL_PORT="/dev/ttyACM0"