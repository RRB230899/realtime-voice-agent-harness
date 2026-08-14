# Bug Report — [vendor] Voice Agent

Status: candidates from call 1

## Bug 1: Provider name stated inconsistently
- **Severity:** Low–Medium
- **Call:** call-20260814-154603-schedule_simple.txt at 1:30 vs 2:11
- **Details:** Availability was offered for "Dr. Zedmaniu Lukoski" but the
  final confirmation said "Dr. Zbigniew Lukowski." If the audio confirms
  two different pronunciations, the agent is rendering the provider's name
  inconsistently, which erodes trust in the confirmation.

## Bug 2: SMS confirmation offered without confirming a phone number
- **Severity:** Low
- **Call:** call-20260814-154603-schedule_simple.txt at 2:14–2:26
- **Details:** Agent promised to text appointment details but never
  collected or read back a phone number. Presumably uses caller ID, but a
  real patient calling from an office phone or on behalf of someone else
  would get no text. Expected: read back the target number.

## Observation (not filed as bug): visit-reason triage
- Agent booked a "routine check-up" at an orthopedics practice without
  asking the reason for the visit. Plausibly fine for a demo clinic;
  noting for pattern-checking in later calls.
