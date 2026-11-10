"""
config.py
---------
Central configuration for the ICS/SCADA security demo.

In a real plant, values like these (safe operating ranges, which systems are
authorized to issue commands) live in engineering and operations
documentation, and increasingly in the policy file of whatever monitoring
tool is watching the network. Centralizing them here -- separate from the
PLC logic itself -- mirrors that split between "what the process does" and
"what we consider safe/authorized for it to do."
"""

PLC_HOST = "127.0.0.1"
PLC_PORT = 15502  # the Modbus TCP port every client (HMI, attacker, IDS) connects to

# --- Register map -----------------------------------------------------
# All five values live in Modbus "holding registers" (function codes 3 to
# read, 6/16 to write). Real deployments often split read-only telemetry
# (sensor readings) into "input registers" -- a protocol-level read-only
# register type -- and keep only operator setpoints in holding registers.
# This demo keeps everything in holding registers for simplicity; see
# docs/CONCEPTS.md for why that's a simplification worth knowing about.
REG_WATER_LEVEL = 0  # cm, sensor telemetry (updated by the physics loop)
REG_FLOW_RATE = 1  # L/min, sensor telemetry (updated by the physics loop)
REG_PUMP_STATUS = 2  # 0 = off, 1 = on -- operator setpoint
REG_VALVE_POSITION = 3  # percent open, 0-100 -- operator setpoint
REG_CHLORINE_PPM = 4  # dosing setpoint, parts per million -- operator setpoint

REGISTER_NAMES = {
    REG_WATER_LEVEL: "water_level_cm",
    REG_FLOW_RATE: "flow_rate_lpm",
    REG_PUMP_STATUS: "pump_status",
    REG_VALVE_POSITION: "valve_position_pct",
    REG_CHLORINE_PPM: "chlorine_dosing_ppm",
}

# --- Safety limits ------------------------------------------------------
# Modeled loosely on real water-treatment engineering limits. The chlorine
# band in particular mirrors the real safe dosing level (around 100 ppm)
# from the February 2021 Oldsmar, Florida incident -- see docs/CONCEPTS.md.
SAFE_RANGES = {
    REG_WATER_LEVEL: (200, 800),
    REG_FLOW_RATE: (0, 500),
    REG_PUMP_STATUS: (0, 1),
    REG_VALVE_POSITION: (0, 100),
    REG_CHLORINE_PPM: (80, 120),
}

# Largest change the IDS will tolerate in a single polling interval before
# flagging an "abrupt change" alert, even if the resulting value is still
# technically in-range. This is what catches a fast, deliberate spike that a
# static range check alone might miss if the attacker is slightly more
# careful than Oldsmar's attacker was.
MAX_STEP_CHANGE = {
    REG_WATER_LEVEL: 150,
    REG_FLOW_RATE: 200,
    REG_PUMP_STATUS: 1,
    REG_VALVE_POSITION: 50,
    REG_CHLORINE_PPM: 30,
}

# Only these three are operator setpoints an external client should ever be
# writing to -- water level and flow rate are telemetry the physics loop
# updates internally, so they're excluded from source-authorization checks.
SOURCE_CHECKED_REGISTERS = {REG_PUMP_STATUS, REG_VALVE_POSITION, REG_CHLORINE_PPM}

# The only source name the IDS will treat as authorized to write to the
# registers above. In a real deployment this would be an asset inventory of
# known engineering workstations/HMIs, usually matched by IP or MAC address
# rather than a self-reported name -- see docs/CONCEPTS.md for why this demo
# simplifies that too.
AUTHORIZED_SOURCES = {"HMI-01"}

# Stand-in for what a passive network tap (a SPAN/mirror port feeding a
# sensor like Dragos or Claroty) would observe on the wire: every write any
# client sends, tagged with who sent it. See docs/CONCEPTS.md.
WRITE_LOG_PATH = "write_log.jsonl"
ALERT_LOG_PATH = "alerts.log"

IDS_POLL_INTERVAL_SEC = 0.5
