"""
hmi_client.py
-------------
Simulates the legitimate operator workstation: the HMI (Human-Machine
Interface) a plant operator uses to monitor the process and make small,
routine adjustments. It generates the baseline traffic that the IDS should
not alert on.
 
Requires plc_simulator.py to be running. Runs until interrupted (Ctrl+C).
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
    port feeding a sensor) that parses the source IP/MAC from real Modbus
    TCP frames rather than relying on the client to self-report. This demo
    has each client report its own identity because raw packet capture
    requires network privileges that are not available in all environments.
    See docs/CONCEPTS.md for the full tradeoff.
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
