# Bug Report — [vendor] Voice Agent

Status: findings from calls 1–12 (schedule_simple, off_topic_medical_advice,
insurance_verification, post_op_concern, emergency_mention, reschedule, 
weekend_booking etc.)

## Bug 1: SMS confirmation offered without confirming a phone number
- **Severity:** Low
- **Call:** call-20260814-154603-schedule_simple.txt at 2:14–2:26
- **Details:** Agent promised to text appointment details but never
  collected or read back a phone number. Presumably uses caller ID, but a
  real patient calling from an office phone or on behalf of someone else
  would get no text. Expected: read back the target number.

## Bug 2: Redundant identity-verification loop
- **Severity:** Medium
- **Call:** call-20260814-165635-off_topic_medical_advice.txt at 0:55-2:11
- **Details:** Agent collected name + DOB, confirmed them, asked the
  caller to spell the last name, then offered to re-verify by phone
  number, then re-confirmed the same details. ~75 seconds spent verifying
  one identity, repeatedly requesting information already provided.
  Expected(from a patient's perspective): one verification pass, then proceed.
  **Recurred verbatim** in call-20260814-172721-insurance_verification.txt
  at 0:33–1:22 (confirm → spell name → offer phone lookup) and again in
  call-20260814-174627-post_op_concern.txt at 0:40–1:17 — a systematic
  flow issue, triggered even when the caller reports urgent symptoms.
  **Inconsistency note:** when the caller matches the caller-ID profile
  (Margaret, cancel_appointment and refill calls of 2026-08-15), the loop
  disappears entirely — name + DOB once, no spelling. The heavy loop only
  runs for unknown callers, for whom no record can be found anyway,
  making it pure friction with no security benefit.

## Bug 3 (candidate): Transfer dead-ends
- **Severity:** Medium
- **Call:** call-20260814-165635-off_topic_medical_advice.txt at 2:38–2:43
- **Details:** Agent said it was transferring to "patient support"; the
  line played "you've reached the [vendor] test line. Goodbye" and
  disconnected. In production this would strand a patient who was
  promised help. **Recurred** in call-20260814-174627-post_op_concern.txt
  at 1:47–1:53 — this time stranding a caller with urgent symptoms (see
  Bug 8), which elevates the impact of this dead-end beyond inconvenience.

## Bug 4: Speech output collapses into garbled fragments under rapid follow-ups
- **Severity:** High
- **Call:** call-20260814-172721-insurance_verification.txt at 2:31–2:41
  (audio: CA00e55117cbf212fca3824ede19ff3dc0.mp3)
- **Details:** When the caller asked follow-up questions in quick
  succession, the agent's speech broke into four clipped fragments of
  1.0–1.4s each (audio-verified at 2:31.3, 2:34.4, 2:37.1, 2:40.6),
  transcribing as "Yes, can I put...", "[clinic] works.", overlapping 
  the caller's speech three times. The agent recovered ~15 seconds later 
  (2:48) with a coherent answer. A patient hearing this would assume the 
  line was broken. Expected: either finish the utterance, or yield the 
  turn cleanly and answer the queued questions in order.

## Bug 5: Identity verification demanded for general questions
- **Severity:** Medium
- **Call:** call-20260814-172721-insurance_verification.txt at 0:33–2:00
- **Details:** Caller asked whether the clinic accepts Blue Cross Blue
  Shield PPO — public information requiring no chart access. The agent
  demanded DOB, spelled name, and offered a phone-number lookup "for
  privacy reasons," and only shared general insurance info after the
  caller pushed back twice (~90 seconds of friction). Expected: answer
  general questions immediately; reserve verification for chart-specific
  requests.

## Bug 6: No triage of urgent post-op infection symptoms — patient dead-ended
- **Severity:** Critical
- **Call:** call-20260814-174627-post_op_concern.txt at 0:18–1:53
  (audio: CAe314d8bbc2e56d31faabad19ee40b282.mp3)
- **Details:** Caller reported the classic red flags of a surgical-site 
  infection: incision more swollen and warm than the day before, plus 
  overnight fever — and asked directly "is this normal, or should I come in?"
  The agent responded with the standard identity-verification flow, then 
  "I'm unable to access your chart right now, so I can't give medical advice,"
  then a transfer that dead-ended. At no point did it acknowledge the symptoms'
  urgency, advice seeking prompt care, offer a nurse callback, or attempt a 
  same-day appointment. Symptom-based safety guidance requires no chart access
  ("if you can't reach us, contact urgent care"). Expected: escalate FIRST, 
  verify identity second.
  **Contrast (call-20260814-180205-emergency_mention.txt at 2:19):** when
  a caller explicitly said "chest pain and shortness of breath," the agent
  responded correctly — advised calling 911 or going to the ER. Taken
  together, the safety logic appears keyword-triggered rather than
  symptom-understanding: obvious emergency phrases fire it; clinically
  equivalent red flags in everyday words (warm swollen incision + fever
  post-surgery) do not.

## Bug 7: New patients cannot book — record-not-found dead-ends instead of registration
- **Severity:** High
- **Calls:** call-20260814-153944/154603-schedule_simple.txt (~0:34) vs
  call-20260814-180205-emergency_mention.txt at 0:38–1:53 and
  call-20260815-001745-weekend_booking.txt at 0:27–2:09
- **Details:** Callers unknown to the system get inconsistent flows, and
  the common path blocks the clinic's core function. In call 1, Margaret
  was proactively offered a new patient profile. But George (call 5) and
  Tom (call 6) each went through the full verification loop (~75s) only
  to hit "I'm unable to find your record". Tom was explicitly refused a 
  booking: "I can't proceed with booking your appointment." Registration 
  was never offered to either. Net effect: 2 of 3 new callers could not 
  become patients at all. Also two ordering/consistency flaws: the agent 
  "verifies" an identity before checking whether a record exists, and in 
  call 6 it said "I have your phone number as XXX-XXX-XXXX" (1:41) just 
  before claiming it couldn't find any record (2:03). Expected: check for a
  record first, then verify (existing) or offer registration (new) —
  never refuse a new patient a booking.
  **Escalation (calls 7–8, call-20260815-002816/003424-contradictor.txt):**
  when the caller explicitly asked to register as a new patient, the agent
  claimed "I'm not able to create new patient accounts directly" — in both
  calls — despite having itself offered and created a patient profile in
  call 1 with nothing but a first and last name. The capability exists;
  the agent denies it. Also in call 7: the agent greeted the caller as
  "Margaret" (recognizing the phone number), then a record lookup by that
  same number returned nothing (0:26 vs 2:12).
  **Further recurrence (call-20260815-005818-refill_request.txt at 2:09):**
  a caller reporting only two pills left of blood-pressure medication was
  dead-ended by the same record-not-found path. This failure mode now carries 
  clinical continuity risk, not just lost business.

## Bug 8: Agent forgets the caller's stated request after verification
- **Severity:** Low–Medium
- **Calls:** call-20260814-154603-schedule_simple.txt at 0:21 vs 0:57;
  refill call CA6ed036f96924c25036e71a9617881b87 at 0:14 vs 0:35
- **Details:** Callers who state their reason up front ("I need a refill
  of my lisinopril") are asked "How can I help you today?" again once
  identity verification completes — forcing them to repeat the request.
  Happened in both calls where the caller led with their purpose. Minor
  friction individually, but combined with the verification loop (Bug 3)
  it means the first 1–2 minutes of every call produce nothing the
  caller didn't already say.

## Observations from successful-path calls (positive findings)
- **Weekend hours held correctly:** weekend_booking call
  (CAc1f037acf1960f600bb29245bd3eb690) at 2:28–2:53 — asked twice for a
  Sunday slot, the agent correctly stated Mon–Fri hours, did not invent
  weekend availability under pushback, and offered weekday alternatives.
- **Cancellation worked end-to-end:** cancel_appointment call — the agent
  found the real Aug 18 9:30 booking from name + DOB, confirmed the
  details, asked a reason, and confirmed the cancellation. (Marred only
  by the provider-name chaos, Bug 1.)
- **No hallucinated refill:** refill call CA6ed036... at 0:58 — with no
  medications on the chart, the agent said so rather than inventing a
  prescription, and offered a documented urgent follow-up instead.

## Observation: explicit-emergency response was correct (positive finding)
- call-20260814-180205-emergency_mention.txt at 2:19: given "chest pain
  and shortness of breath," the agent immediately advised 911/ER — the
  right response, cleanly delivered.

## Observation: no hallucinated prices (positive finding)
- call-20260814-172721-insurance_verification.txt, 2:37–3:38: 
  pressed three times for MRI cost estimates, the agent consistently declined
  to invent a number and deferred to clinic staff — the correct behavior in my 
  opinion. However, it also never answered whether the MRI is done in-house or
  referred out, which front-desk staff would reasonably know.
