# ICS/SCADA Intrusion Detection Demo

A simulated water-treatment control system that reproduces and detects the attack pattern used in the February 2021 Oldsmar, Florida water treatment incident. The project models a PLC controlling physical plant equipment, a legitimate operator (HMI), an unauthorized attacker, and an intrusion detection system (IDS) that monitors both.

## Background

This project targets operational technology (OT): the systems that run physical infrastructure such as water, power, and manufacturing. OT has a different threat model and different constraints than traditional IT. Systems often cannot be patched or rebooted without disrupting a physical process, and many industrial protocols were designed without authentication.

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

All four components run as separate processes and communicate only over real Modbus TCP connections. No component accesses another's memory directly, so the demo reflects an actual network security setup rather than a simulation with security-themed variable names.
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

## Expected Behavior
Normal HMI traffic produces no alerts. Attacker traffic triggers [HIGH] and [MEDIUM] alerts in the IDS terminal (Terminal 2), which are also written to alerts.log.

## Design notes

See docs/CONCEPTS.md for details on:

Modbus's lack of built-in authentication
The real incident the attack scenario is modeled on
Why detection is split into two strategies
Known simplifications relative to a production deployment
## Files

| Files |
|---|---|
| `config.py` | Register map, safe ranges, authorized sources |
| `plc_simulator.py` | The Modbus TCP server + the internal physics loop |
| `hmi_client.py` | Simulates the legitimate operator workstation |
| `attacker.py` | Simulates an unauthorized intruder (two scenarios) |
| `ids_monitor.py` | The detection engine |

## Possible extensions, if you want to go further

- Live web dashboard (Flask and a simple chart) in place of console output
- Statistical anomaly detection (e.g., flagging values more than N standard deviations from a rolling mean) as a third detection method alongside fixed thresholds
- Passive packet capture with scapy in place of the simulated write log, in environments that permit raw sockets
- A second simulated process (e.g., a power substation) to show the detection logic generalizes beyond a single register map
