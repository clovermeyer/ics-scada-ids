# Design notes

The code implements the ideas below; this file is the reasoning behind it --
why Modbus behaves the way it does, what real incident this models, and why
the detection logic is split the way it is.

## 1. What Modbus is, and why it matters

Modbus is a communication protocol from 1979, originally designed for
Modicon's own PLCs. It's still one of the most widely used industrial
protocols in the world, because industrial equipment gets replaced on a
decades-long cycle, not a yearly one.

The important thing about Modbus for security purposes: **it has no
built-in authentication, authorization, or encryption.** Any device that
can reach a Modbus server over the network can read or write any register
it exposes -- function code 3 reads holding registers, 6 and 16 write them,
and the protocol itself has no concept of "who is allowed to do this." It
was designed in an era when these systems lived on physically isolated
factory-floor networks, with no expectation that a stranger could ever
reach them at all. Decades later, many of those same networks got
connected -- sometimes directly, sometimes through a chain of
misconfigurations -- to the internet, and the protocol never changed to
compensate for that.

This is *why* this project's attacker.py can simply connect and write
whatever it wants: that's not a bug in the simulation, that's an accurate
reflection of how the real protocol behaves. The entire reason detection
matters so much in ICS security -- more than in most IT security -- is that
prevention at the protocol level often isn't there to begin with.

## 2. The Oldsmar, Florida incident (what this project models)

On February 5, 2021, someone remotely accessed the control software at a
water treatment plant in Oldsmar, Florida, via remote-access software
(TeamViewer) an operator had left enabled. They changed the sodium
hydroxide (lye) setpoint from its normal level of about 100 ppm to 11,100
ppm -- used in small amounts to control water acidity, but dangerous at that
concentration. A plant operator happened to be watching his screen at the
moment the change was made, saw the number jump, and immediately reversed
it. The change was caught and corrected before any affected water left the
plant.

No automated system caught it. A human happened to be looking at the right
screen at the right second. That's the entire argument for a project like
this one: `ids_monitor.py` does automatically, continuously, and in
milliseconds, what in the real incident depended entirely on human luck.

## 3. Why this project uses two separate detection strategies

### State-based detection (`check_state_anomalies`)
This polls the PLC's current values directly and checks them against known
safe ranges, and against how fast they're changing. This is the
"electronic version of the operator watching the screen" -- it would have
caught Oldsmar with zero network visibility at all, purely by noticing the
number was wrong.

Two sub-checks:
- **Range check** -- is the value outside physically/chemically safe
  bounds? This catches an obviously dangerous value regardless of how it
  got there.
- **Rate-of-change check** -- did the value move further in one interval
  than it realistically should? This catches a fast, deliberate change even
  from an attacker careful enough to land *inside* the safe range but still
  moving suspiciously fast -- something a pure range check would miss
  entirely.

### Network-based detection (`check_write_log_anomalies`)
This watches *who* is issuing commands, which catches a different class of
problem: a value that's perfectly normal but came from somewhere it
shouldn't have. An attacker who's done their homework and sets a value
inside the safe range specifically to avoid tripping a range check is
exactly what this layer is for. It also catches write-flooding -- rapid
repeated commands that could physically damage equipment (hammering a valve
open and closed, for instance) even if no single command looks abnormal on
its own.

Real ICS security products -- Dragos, Claroty, Nozomi Networks, and others
-- combine both of these approaches for exactly this reason: each one
catches attacks the other would miss.

## 4. Known simplifications and their real-world equivalents

A few things are simplified here for a project buildable in a sandboxed
environment without elevated network privileges. Each one is noted below
along with what a production deployment would actually do instead.

**The write log stands in for a passive network tap.** In a real
deployment, network-based detection comes from a switch's SPAN/mirror port
feeding a sensor that parses the source IP and MAC address directly out of
Modbus TCP packets on the wire -- the client never "announces" who it is.
Doing that for real requires raw packet capture (via `scapy` or similar),
which needs elevated network privileges this sandbox doesn't grant. This
project has each client log its own identity to a shared file instead. The
detection *logic* downstream of that (matching source against an
authorized list, rate-limiting by source) is the same either way -- only
*how the source identity is obtained* differs.

**Authorized sources are matched by name, not IP/MAC.** A real deployment
maintains an asset inventory of known engineering workstations, usually
matched by IP or MAC address, and increasingly by TLS client certificates
on protocols that support them (Modbus traditionally doesn't). This project
uses a name string for the same reason as above.

**Everything is a holding register.** Real Modbus deployments often put
read-only sensor telemetry in a genuinely separate register type -- "input
registers," function code 4, which has no corresponding write function
code in the protocol at all. This project puts everything in holding
registers for implementation simplicity. The security-relevant distinction
it's modeling -- "some values are operator-settable, some are just
telemetry" -- is preserved via `config.SOURCE_CHECKED_REGISTERS` instead.

**The IDS polls instead of streaming.** Polling every 0.5 seconds is simple
and reliable but introduces latency and could miss a value that changes and
reverts between polls. A tap-based system sees every packet as it happens.

## 5. The bigger idea: IT security vs. OT security

IT security usually prioritizes **confidentiality** first (don't leak the
data), then integrity, then availability -- the "CIA triad," in that order
by convention. OT/ICS security usually flips that: **availability** comes
first (don't take the water plant offline), then integrity (don't let
anyone falsify what the system is doing), then confidentiality (least
important -- nobody's trying to keep a water tank's level "secret"). That's
why `ids_monitor.py` *alerts* rather than automatically blocking or
shutting anything down: in a real plant, an automated system that
aggressively blocks traffic risks causing the exact availability failure
OT security is trying to avoid, which is why detection-and-alert is the
dominant pattern in this field rather than automated prevention.

This distinction -- availability over confidentiality -- is the single idea
that explains most of the other design choices in this project.
