# ICS/SCADA Intrusion Detection Demo

A simulated water-treatment control system, built to demonstrate and detect
the same attack pattern used in the real February 2021 Oldsmar, Florida
water treatment attack. Built around critical infrastructure protection:
the PLC that controls physical plant equipment, a legitimate operator
(HMI), an unauthorized attacker, and an intrusion detection system that
watches for both of them.

## Why this project

Most student cybersecurity projects target IT systems -- web apps,
password databases, phishing. This one targets **operational technology
(OT)**: the systems that run physical infrastructure -- water, power,
manufacturing. It's a different threat model with different constraints
(you usually can't just patch and reboot a water plant), and it's the
specific lane that "critical infrastructure protection" refers to.

## Architecture

```
          Modbus TCP (port 15502)
┌───────────┐        │        ┌─────────────────┐
│ hmi_client│────────┼───────▶│                 │
│ (legit)   │        │        │  plc_simulator  │
└───────────┘        │        │  (the "PLC")    │
┌───────────┐        │        │                 │
│ attacker  │────────┼───────▶│  + physics loop │
│ (malicious│        │        └─────────────────┘
└───────────┘        │                 ▲
                      │                 │ polls state
┌───────────┐         │                │
│ids_monitor│─────────┴────────────────┘
│  (the IDS)│  also tails write_log.jsonl
└───────────┘
```

All four pieces are separate processes that only ever talk to each other
over real Modbus TCP connections -- nothing reaches into another script's
memory directly. That's deliberate: it's what makes this an actual network
security demo rather than just a simulation with security-themed variable
names.

## Setup

```bash
pip install -r requirements.txt
```

## Running it

Open **four terminals** in this directory.

**Terminal 1 -- the PLC:**
```bash
python3 plc_simulator.py
```

**Terminal 2 -- the IDS (start after the PLC is up):**
```bash
python3 ids_monitor.py
```

**Terminal 3 -- the legitimate operator:**
```bash
python3 hmi_client.py
```

**Terminal 4 -- run the attack and watch Terminal 2 react:**
```bash
python3 attacker.py oldsmar
# or:
python3 attacker.py flood
```

Watch Terminal 2. You should see the HMI's normal traffic produce no
alerts, and the attacker's traffic immediately trigger red `[HIGH]` and
yellow `[MEDIUM]` alerts, written both to the console and to `alerts.log`.

## Design notes

See **`docs/CONCEPTS.md`** for the reasoning behind this: Modbus's lack of
built-in authentication, the real incident the attack scenario is modeled
on, why detection is split into two strategies, and the known
simplifications versus a production deployment.

## Files

| File | What it does |
|---|---|
| `config.py` | Register map, safe ranges, authorized sources |
| `plc_simulator.py` | The Modbus TCP server + the internal physics loop |
| `hmi_client.py` | Simulates the legitimate operator workstation |
| `attacker.py` | Simulates an unauthorized intruder (two scenarios) |
| `ids_monitor.py` | The detection engine |

## Possible extensions, if you want to go further

- A live web dashboard (Flask + a simple chart) instead of console output
- A third detection method: statistical anomaly detection (e.g. flag values
  more than N standard deviations from a rolling mean) instead of fixed
  thresholds
- Real passive packet capture with `scapy` instead of the simulated write
  log, if you have a sandbox that allows raw sockets
- A second simulated process (e.g. a power substation) to show the
  detection logic generalizes beyond one register map
