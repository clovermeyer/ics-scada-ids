"""
ids_monitor.py
--------------
Intrusion detection engine for the simulated water-treatment PLC. Start it
after plc_simulator.py, alongside hmi_client.py. Run attacker.py in a
separate terminal to generate alerts.
 
Two detection strategies are combined, as in real ICS monitoring tools,
because they catch different classes of activity:
 
1. STATE-BASED detection: poll the PLC's current register values directly,
   as any read-only Modbus client could, and check them against known-safe
   ranges and against how much they have moved since the last poll. This
   would have caught the Oldsmar incident with no network visibility at all.
   It automates what the human operator did by watching the screen. See
   check_state_anomalies().
 
2. NETWORK-BASED detection: observe who is issuing writes and to what. This
   catches activity that state-based detection alone would miss, such as an
   unauthorized source writing a value that is still in range. See
   check_write_log_anomalies(). In production this data comes from a passive
   network tap; here it is simulated via write_log.jsonl. See
   docs/CONCEPTS.md for the tradeoffs.
"""
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from pymodbus.client import ModbusTcpClient

import config

RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

SEVERITY_COLOR = {"HIGH": RED, "MEDIUM": YELLOW}


def alert(kind, severity, message):
    line = (f"{datetime.now(timezone.utc).isoformat()} "
            f"[{severity}] {kind}: {message}")
    color = SEVERITY_COLOR.get(severity, "")
    print(f"{color}[IDS ALERT] {line}{RESET}")
    with open(config.ALERT_LOG_PATH, "a") as f:
        f.write(line + "\n")


REALERT_SECONDS = 5  # how often to re-remind about a still-ongoing condition


def check_state_anomalies(current, previous, out_of_range_state):
    """
    Range and rate-of-change checks against live register values.
 
    out_of_range_state tracks, per register, the value and time of the last
    alert. This prevents a value stuck outside its safe range from firing a
    new HIGH alert on every poll; it is re-reported only if the value changes
    or REALERT_SECONDS have passed. Without this, a single stuck sensor can
    flood the alert feed and obscure other activity, which an attacker could
    exploit as cover.
    """
    now = time.time()
    for reg, value in current.items():
        name = config.REGISTER_NAMES[reg]
        low, high = config.SAFE_RANGES[reg]

        if not (low <= value <= high):
            last_value, last_time = out_of_range_state.get(reg, (None, 0))
            if value != last_value or (now - last_time) > REALERT_SECONDS:
                alert(
                    "OUT_OF_RANGE", "HIGH",
                    f"{name} = {value} is outside the safe range ({low}-{high})",
                )
                out_of_range_state[reg] = (value, now)
            continue  # don't double-report the same spike as a rate alert too
        else:
            out_of_range_state.pop(reg, None)

        if previous is not None:
            prev_value = previous[reg]
            step = abs(value - prev_value)
            if step > config.MAX_STEP_CHANGE[reg]:
                alert(
                    "ABRUPT_CHANGE", "MEDIUM",
                    f"{name} moved from {prev_value} to {value} in one polling "
                    f"interval (max expected step: {config.MAX_STEP_CHANGE[reg]})",
                )


def check_write_log_anomalies(new_entries, write_history):
    """Source-authorization and write-flood checks against observed writes."""
    now = time.time()

    for entry in new_entries:
        reg = entry["register"]
        source = entry["source"]
        name = entry["register_name"]

        if reg in config.SOURCE_CHECKED_REGISTERS and source not in config.AUTHORIZED_SOURCES:
            alert(
                "UNAUTHORIZED_SOURCE", "HIGH",
                f"write to {name} (value={entry['value']}) from unrecognized "
                f"source '{source}' -- expected one of {config.AUTHORIZED_SOURCES}",
            )

        key = (source, reg)
        write_history[key].append(now)
        # Drop anything older than a 3-second sliding window.
        while write_history[key] and now - write_history[key][0] > 3:
            write_history[key].popleft()
        if len(write_history[key]) > 5:
            alert(
                "WRITE_FLOOD", "MEDIUM",
                f"source '{source}' sent {len(write_history[key])} writes to "
                f"{name} in under 3 seconds",
            )
            write_history[key].clear()  # avoid re-alerting every single tick


def tail_new_lines(path, offset):
    """Read any lines appended to the write log since the last check."""
    entries = []
    try:
        with open(path, "r") as f:
            f.seek(offset)
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
            new_offset = f.tell()
    except FileNotFoundError:
        return [], offset
    return entries, new_offset


def main():
    client = ModbusTcpClient(config.PLC_HOST, port=config.PLC_PORT)
    client.connect()
    print(f"{GREEN}[IDS] Online. Polling every {config.IDS_POLL_INTERVAL_SEC}s. "
          f"Watching registers: {config.REGISTER_NAMES}{RESET}")
    print(f"{GREEN}[IDS] Authorized sources for control setpoints: "
          f"{config.AUTHORIZED_SOURCES}{RESET}")

    # Reset logs for a clean run each time this is launched.
    open(config.ALERT_LOG_PATH, "w").close()
    open(config.WRITE_LOG_PATH, "a").close()

    previous = None
    log_offset = 0
    write_history = defaultdict(deque)
    out_of_range_state = {}

    try:
        while True:
            time.sleep(config.IDS_POLL_INTERVAL_SEC)

            regs = client.read_holding_registers(0, count=5)
            if not regs.isError():
                current = {i: regs.registers[i] for i in range(5)}
                check_state_anomalies(current, previous, out_of_range_state)
                previous = current

            new_entries, log_offset = tail_new_lines(config.WRITE_LOG_PATH, log_offset)
            if new_entries:
                check_write_log_anomalies(new_entries, write_history)

    except KeyboardInterrupt:
        print(f"\n{GREEN}[IDS] Stopped.{RESET}")


if __name__ == "__main__":
    main()
