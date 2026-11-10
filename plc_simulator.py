"""
plc_simulator.py
-----------------
Simulates a small water-treatment PLC (Programmable Logic Controller) as a
Modbus TCP server.

A PLC is the piece of hardware that actually sits between the digital
"setpoints" a human or software sets and the physical equipment -- pumps,
valves, dosing systems -- that those setpoints control. In production these
are purpose-built embedded controllers that often run for a decade or more
without a reboot, which is a big part of why they're hard to patch the way
an ordinary IT server is: you usually can't just take a water plant offline
for Patch Tuesday.

Run this FIRST, before hmi_client.py, attacker.py, or ids_monitor.py.
"""
import threading
import time
import warnings

warnings.filterwarnings("ignore")  # quiet pymodbus's v4-migration deprecation notices for this demo

from pymodbus.server import StartTcpServer
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusServerContext,
    ModbusSequentialDataBlock,
)
from pymodbus.client import ModbusTcpClient

import config

# Initial "nominal" plant state: pump running, valve half-open, water mid-tank,
# chlorine dosing at a normal, safe level.
initial_values = [500, 250, 1, 50, 100]

store = ModbusDeviceContext(hr=ModbusSequentialDataBlock(1, initial_values))
context = ModbusServerContext(devices=store, single=True)


def physics_loop():
    """
    A very simplified model of the physical process, running as its own
    Modbus client against localhost -- the same way any real client would
    talk to this PLC. This is a deliberate design choice: nothing in this
    project reaches into the server's memory directly. Every actor, internal
    or external, legitimate or not, only ever interacts with the plant
    through Modbus reads and writes, exactly as it would on a real network.

    It makes water level and flow rate drift realistically based on pump and
    valve state, which is what makes range- and rate-based anomaly detection
    meaningful instead of just comparing against a number that never moves.
    """
    time.sleep(1.5)  # give the server a moment to come up
    client = ModbusTcpClient(config.PLC_HOST, port=config.PLC_PORT)
    client.connect()

    while True:
        time.sleep(1)
        regs = client.read_holding_registers(0, count=5)
        if regs.isError():
            continue
        level, flow, pump, valve, _chlorine = regs.registers

        inflow = 300 if pump else 0
        outflow = valve * 3
        new_flow = max(0, min(500, inflow - outflow // 2))
        new_level = level + (inflow - outflow) // 20
        new_level = max(0, min(1000, new_level))

        client.write_register(config.REG_FLOW_RATE, new_flow)
        client.write_register(config.REG_WATER_LEVEL, new_level)


if __name__ == "__main__":
    threading.Thread(target=physics_loop, daemon=True).start()
    print(f"[PLC] Simulated water treatment PLC listening on "
          f"{config.PLC_HOST}:{config.PLC_PORT}")
    print(f"[PLC] Registers: {config.REGISTER_NAMES}")
    print(f"[PLC] Initial values: {initial_values}")
    StartTcpServer(context=context, address=(config.PLC_HOST, config.PLC_PORT))
