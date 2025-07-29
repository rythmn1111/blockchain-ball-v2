import time
import board
import busio
import json
from datetime import datetime
import smbus
from adafruit_bme280 import basic as adafruit_bme280
import os

# === ID TRACKER SETUP ===
ID_FILE = "/home/rythmn/throw_id.txt"

def get_next_id():
    if not os.path.exists(ID_FILE):
        with open(ID_FILE, "w") as f:
            f.write("1")
        return 1
    else:
        with open(ID_FILE, "r+") as f:
            current = int(f.read())
            new_id = current + 1
            f.seek(0)
            f.write(str(new_id))
            f.truncate()
        return new_id

# === MPU6050 SETUP ===
MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B

bus = smbus.SMBus(1)
bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0)

# === BME280 SETUP ===
i2c_bmp = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_bmp, address=0x76)
bme280.sea_level_pressure = 1013.25  # Calibrate if needed

def read_mpu_accel():
    def read_word(reg):
        high = bus.read_byte_data(MPU_ADDR, reg)
        low = bus.read_byte_data(MPU_ADDR, reg + 1)
        value = (high << 8) + low
        return value - 65536 if value > 32767 else value

    x = read_word(ACCEL_XOUT_H)
    y = read_word(ACCEL_XOUT_H + 2)
    z = read_word(ACCEL_XOUT_H + 4)
    return x, y, z

def measure_throw(duration=1.5, interval=0.1):
    accel_data = []
    height_data = []

    start_time = time.time()
    while time.time() - start_time < duration:
        x, y, z = read_mpu_accel()
        ax = x / 16384.0
        ay = y / 16384.0
        az = z / 16384.0
        net_accel = ((ax ** 2 + ay ** 2 + az ** 2) ** 0.5) - 1.0
        accel_data.append(net_accel)

        try:
            height = bme280.altitude
            height_data.append(height)
        except:
            pass

        time.sleep(interval)

    speed = sum(accel_data) * interval
    strength = sum(abs(a) for a in accel_data)
    avg_accel = sum(accel_data) / len(accel_data) if accel_data else 0

    if height_data:
        ground_level = height_data[0]
        relative_height_m = max(height_data) - ground_level
        relative_height_cm = round(relative_height_m * 100, 2)
    else:
        relative_height_cm = 0

    return round(speed, 2), round(strength, 2), round(avg_accel, 2), relative_height_cm

if __name__ == "__main__":
    speed, strength, accel, max_height = measure_throw()
    throw_id = get_next_id()

    result = {
        "id": f"throw-{throw_id}",
        "strength": strength,
        "speed": speed,
        "accel": accel,
        "max_height": max_height,  # in cm
        "timestamp": datetime.utcnow().isoformat()
    }

    print(json.dumps(result))
