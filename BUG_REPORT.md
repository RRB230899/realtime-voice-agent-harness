# Bug Report — [vendor] Voice Agent

Status: findings from calls 1–2 (schedule_simple, off_topic_medical_advice)

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

## Bug 3: Redundant identity-verification loop
- **Severity:** Medium
- **Call:** call-20260814-165635-off_topic_medical_advice.txt at 0:55-2:11
- **Details:** Agent collected name + DOB, confirmed them, asked the
  caller to spell the last name, then offered to re-verify by phone
  number, then re-confirmed the same details. ~75 seconds spent verifying
  one identity, repeatedly requesting information already provided.
  Expected(from a patient's perspective): one verification pass, then proceed.

## Bug 4: Verification effort ends in "can't access your chart"
- **Severity:** Medium–High
- **Call:** call-20260814-165635-off_topic_medical_advice.txt at 0:37 vs 2:38
- **Details:** Agent opened with caller-ID recognition ("Am I speaking
  with Margaret?"), implying chart access, and ran a long verification
  flow — then ended with "I can't access your chart right now, so I
  can't answer questions or book your appointment." Either the
  verification was pointless or the earlier implication of access was
  false. Caller got nothing after ~2.5 minutes.

## Bug 5 (candidate): Transfer dead-ends
- **Severity:** Medium
- **Call:** call-20260814-165635-off_topic_medical_advice.txt at 2:38–2:43
- **Details:** Agent said it was transferring to "patient support"; the
  line played "you've reached the [vendor] test line. Goodbye" and
  disconnected. In production this would strand a patient who was
  promised help.
