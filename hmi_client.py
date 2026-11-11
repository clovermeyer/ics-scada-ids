"""
hmi_client.py
--------------
Simulates the legitimate operator workstation -- the HMI (Human-Machine
Interface) a real plant operator would use to watch the process and make
small, normal adjustments. This is the "known good" traffic the IDS should
learn to leave alone.

Run this AFTER plc_simulator.py, in its own terminal. It runs until you
stop it (Ctrl+C).
"""
import json
import random
import time
from datetime import datetime, timezone

from pymodbus.client import ModbusTcpClient

import config

SOURCE_NAME = "HMI-01"


def log_write(register, value):
    """
    Append this write to the shared write log. In a real deployment, this
    log would be populated by a passive network tap (a switch SPAN/mirror
    port feeding a sensor) parsing the source IP/MAC out of real Modbus TCP
    frames -- not self-reported by the client. This demo has each client
    report its own identity directly, because standing up raw packet
    capture needs network privileges this environment doesn't grant. See
    docs/CONCEPTS.md for the full explanation of that tradeoff.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_NAME,
        "register": register,
        "register_name": config.REGISTER_NAMES[register],
        "value": value,
    }
    with open(config.WRITE_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    client = ModbusTcpClient(config.PLC_HOST, port=config.PLC_PORT)
    client.connect()
    print(f"[{SOURCE_NAME}] Connected to PLC. Sending normal operator traffic. Ctrl+C to stop.")

    while True:
        time.sleep(random.uniform(4, 8))

        # A real operator mostly watches the screen -- reads far outnumber
        # writes, and writes are small, occasional adjustments within the
        # plant's normal operating envelope.
        regs = client.read_holding_registers(0, count=5)
        if regs.isError():
            continue
        level, flow, pump, valve, chlorine = regs.registers
        print(f"[{SOURCE_NAME}] status -> level={level} flow={flow} "
              f"pump={pump} valve={valve}% chlorine={chlorine}ppm")

        # Occasionally make a small, realistic adjustment.
        if random.random() < 0.3:
            choice = random.choice(["valve", "chlorine"])
            if choice == "valve":
                new_valve = max(20, min(80, valve + random.randint(-10, 10)))
                client.write_register(config.REG_VALVE_POSITION, new_valve)
                log_write(config.REG_VALVE_POSITION, new_valve)
                print(f"[{SOURCE_NAME}] adjusted valve -> {new_valve}%")
            else:
                new_chlorine = max(90, min(110, chlorine + random.randint(-5, 5)))
                client.write_register(config.REG_CHLORINE_PPM, new_chlorine)
                log_write(config.REG_CHLORINE_PPM, new_chlorine)
                print(f"[{SOURCE_NAME}] adjusted chlorine dosing -> {new_chlorine}ppm")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{SOURCE_NAME}] Stopped.")
