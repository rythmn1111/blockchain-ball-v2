#!/usr/bin/env python3

import smbus2
import time
import json
import math
from datetime import datetime

# MPU6050 Registers
MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B

# Setup
bus = smbus2.SMBus(1)
bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0)

def read_word(reg):
    high = bus.read_byte_data(MPU_ADDR, reg)
    low = bus.read_byte_data(MPU_ADDR, reg + 1)
    value = (high << 8) + low
    if value > 32767:
        value -= 65536
    return value

def read_accel():
    x = read_word(ACCEL_XOUT_H)
    y = read_word(ACCEL_XOUT_H + 2)
    z = read_word(ACCEL_XOUT_H + 4)
    # convert to 'g' assuming ±2g scale
    return [x / 16384.0, y / 16384.0, z / 16384.0]

# Read for 1.5 seconds
samples = []
start_time = time.time()
while time.time() - start_time < 1.5:
    accel = read_accel()
    samples.append(accel)
    time.sleep(0.01)  # ~100Hz

# Calculate peak acceleration (magnitude)
magnitudes = [math.sqrt(x**2 + y**2 + z**2) for x, y, z in samples]
peak = max(magnitudes)
avg = sum(magnitudes) / len(magnitudes)

# Estimate speed from crude integration (∫a dt)
# Assuming Δt = 0.01s, speed ≈ sum(a * Δt)
speed_est = sum([a * 0.01 for a in magnitudes]) * 9.81  # convert g to m/s²

# Final output
result = {
    "id": f"throw-{int(time.time())}",
    "strength": round(peak, 2),
    "speed": round(speed_est, 2),
    "accel": round(avg, 2),
    "timestamp": datetime.now().isoformat()
}

print(json.dumps(result))

