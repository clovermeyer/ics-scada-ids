# Interview prep: talking about this project

Read `CONCEPTS.md` first -- this sheet assumes you understand it, it doesn't
re-explain it. These are the questions this project is most likely to draw,
with a short answer built from what you actually built. Practice saying
these out loud, in your own words, until you don't need the sheet.

---

**"Walk me through what this project does."**
It's a simulated water-treatment control system -- a PLC, a legitimate
operator, an attacker, and an intrusion detection system -- all talking to
each other over real Modbus TCP, the same protocol a lot of U.S.
infrastructure actually runs on. The attack scenario replays the real
February 2021 Oldsmar, Florida incident, where someone remotely changed a
chemical dosing setpoint to a dangerous level. My IDS catches it two
different ways: by watching the values themselves for anything out of a
safe range or changing too fast, and by watching who's allowed to issue
which commands in the first place.

**"Why Modbus specifically?"**
Because it has no built-in authentication or encryption -- any device that
can reach it can read or write any register. That's not a limitation of my
simulation, that's accurate to the real protocol, and it's exactly why
detection matters so much in this field: you often can't rely on
prevention at the protocol level the way you can with, say, TLS on a modern
web API.

**"What's the hardest part of building this?"**
Getting the detection logic to catch a real attack without drowning in
false positives. My first version re-alerted on every single polling
cycle while a value stayed abnormal, which would bury a real alert feed in
noise. I added de-duplication so a sustained condition only re-announces
itself periodically instead of every 0.5 seconds -- which is also a real
concept in this field: alert fatigue is itself a security problem, since it
gives an attacker cover.

**"How would this scale to a real deployment?"**
The biggest gap is how source identity is captured. Right now each client
self-reports who it is; a real deployment would get that from a passive
network tap parsing actual packet headers, which needs raw socket
privileges I didn't have in this sandbox. The detection logic downstream
of that -- is this source authorized for this register, is this rate of
writes normal -- would barely change; only how the source gets identified
would.

**"What would you add if you kept working on it?"**
Statistical anomaly detection instead of fixed thresholds -- flagging a
value that's unusual relative to its own recent history (a rolling mean and
standard deviation) rather than a hand-set safe range, which would catch
subtler drift. And real packet capture with scapy if I had a less
restricted network environment, to replace the simulated write log with
actual observed traffic.

**"Why does this matter to you / why this over a generic cybersecurity
project?"**
Most student security projects target IT systems -- web apps, password
databases. This targets operational technology specifically, which is a
distinct discipline with a different threat model: you usually can't just
patch and reboot a water treatment plant the way you'd patch a web server,
and the field generally prioritizes keeping the system running
(availability) over keeping data secret (confidentiality) -- almost the
reverse of how most IT security gets taught. That's the actual discipline
behind "critical infrastructure protection," and I wanted a project that
demonstrated I understood that distinction, not just general cybersecurity
vocabulary.

---

## If they ask something you don't have a ready answer for

Don't bluff. Say what you actually know and where the honest edge of your
knowledge is -- "I didn't implement X, but here's how I understand it would
work" is a stronger answer than a confident guess that falls apart under a
follow-up question. Everything in `CONCEPTS.md` is written so you can do
exactly that.
