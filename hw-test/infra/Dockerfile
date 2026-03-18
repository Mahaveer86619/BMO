FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    cmake gcc-arm-none-eabi libnewlib-arm-none-eabi build-essential \
    python3 git && \
    rm -rf /var/lib/apt/lists/*

RUN git clone -b master https://github.com/raspberrypi/pico-sdk.git /opt/pico-sdk && \
    cd /opt/pico-sdk && git submodule update --init

ENV PICO_SDK_PATH=/opt/pico-sdk
WORKDIR /project

CMD ["sh", "-c", "mkdir -p build && cd build && cmake -DPICO_BOARD=pico_w .. && make"]