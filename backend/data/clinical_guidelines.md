# Clinical Triage Guidelines — Post-Discharge Monitoring

## Symptom Classification Rules

### EMERGENCY — Immediate 911 / ER Transfer
The following symptoms require immediate escalation. The AI agent must NOT attempt to manage these and should trigger an immediate handoff:

1. **Chest Pain or Pressure** — Any chest pain, tightness, pressure, or squeezing that lasts more than a few minutes or comes and goes.
2. **Difficulty Breathing** — Sudden shortness of breath, especially at rest or with minimal activity.
3. **Stroke Symptoms (FAST)** — Face drooping, Arm weakness, Speech difficulty, Time to call 911.
4. **Uncontrolled Bleeding** — Active bleeding from a surgical site that does not stop with 10 minutes of direct pressure.
5. **Loss of Consciousness** — Fainting, passing out, or becoming unresponsive.
6. **Severe Allergic Reaction** — Swelling of face/throat, difficulty breathing, widespread hives after taking medication.
7. **Sudden Severe Pain** — Any new, severe pain rated 9-10 out of 10 that came on suddenly.
8. **Signs of Pulmonary Embolism** — Sudden chest pain with shortness of breath, rapid heartbeat, coughing up blood.
9. **Signs of Deep Vein Thrombosis** — Sudden, severe swelling, redness, warmth, and pain in one leg (especially calf).

### URGENT — Contact Surgeon/Clinician Within 4 Hours
These symptoms need timely clinical assessment but are not immediately life-threatening:

1. **Fever** — Temperature above 101°F (38.3°C).
2. **Wound Concerns** — Increasing redness, warmth, swelling, or purulent (yellow/green) drainage from surgical site.
3. **Worsening Pain** — Pain that is getting worse despite medication, or new pain in a different location.
4. **Medication Issues** — Unable to tolerate prescribed medications (vomiting within 30 minutes of taking them).
5. **Persistent Vomiting** — Unable to keep fluids down for more than 8 hours.
6. **Rapid Weight Gain** — More than 3 pounds gained in 24 hours (possible fluid retention in cardiac patients).
7. **New Swelling** — Significant new swelling in extremities not present at discharge.
8. **Confusion or Disorientation** — New confusion, difficulty concentrating, or personality changes.

### ROUTINE — Schedule Regular Follow-up
These are expected post-surgical findings that should be documented and monitored:

1. **Mild Pain** — Pain levels 4-6 that are managed with prescribed medications.
2. **Minor Swelling or Bruising** — Expected post-surgical swelling that is stable or improving.
3. **Fatigue** — Feeling tired, which is normal during recovery.
4. **Decreased Appetite** — Mild decrease in appetite for the first few days.
5. **Constipation** — Related to pain medications and reduced activity.

### SELF-CARE — Patient Education
Non-urgent questions that can be answered with discharge instructions:

1. **When can I shower/bathe?**
2. **When can I drive?**
3. **When can I return to work?**
4. **What should I eat?**
5. **Can I take over-the-counter medications?**
6. **How should I care for my wound?**

## Risk Score Modification Rules

### Vitals-Based Modifiers (applied to LACE base score)
- Pain level ≥ 7/10: +10 points
- Temperature > 100.4°F: +15 points
- Temperature > 101°F: +25 points  
- Medication non-adherence: +15 points
- Wound concerns reported: +10 points
- Reduced mobility (unable to walk): +10 points
- Poor appetite for > 2 days: +5 points
- Reported confusion: +20 points

## Agent Behavioral Rules

### Things the AI Agent Must NEVER Do
1. Prescribe, change, or adjust any medication or dosage.
2. Provide a medical diagnosis.
3. Tell a patient they are "fine" or that symptoms are "nothing to worry about" without clinical grounding.
4. Discuss prognosis or life expectancy.
5. Recommend stopping any prescribed medication.
6. Provide advice outside the scope of the patient's discharge instructions.

### Safe Default Responses
When unsure, the agent should use these templates:
- "I want to make sure you get the best care. Let me flag this for your care team to review."
- "That's an important question. I'd recommend discussing this with your doctor at your next appointment."
- "I'm not able to provide specific medical advice on that topic. Let me connect you with a nurse."
