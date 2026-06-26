# Dashboard Testing Guide

**Server Status**: ✅ Running on http://localhost:8000  
**Started**: June 25, 2026  
**Backend Process**: Terminal ID 3

---

## Quick Access

- **Dashboard**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/openapi.json

---

## What You'll See

### 1. Stats Cards (Top of Dashboard)
- **Active Patients**: Should show 8
- **High Risk**: Count of patients with risk score ≥70
- **Pending Alerts**: Active alerts requiring attention
- **Calls Today**: Number of conversations initiated

### 2. Patients Table
You should see 8 sample patients:

| Patient | Procedure | Days Post-Discharge | Risk Profile |
|---------|-----------|---------------------|--------------|
| **David Martinez** (P008) | Cholecystectomy | 2 days | Low risk |
| **Elena Kowalski** (P003) | Appendectomy | 3 days | Low risk |
| **Robert Garcia** (P002) | Hip Replacement | 4 days | Low risk |
| **Patricia Johnson** (P007) | Knee Replacement | 4 days | Low risk |
| **Susan Davis** (P005) | Lumbar Microdiscectomy | 5 days | Moderate risk |
| **Margaret Thompson** (P001) | CABG (Cardiac) | 6 days | High risk |
| **William Chen** (P006) | Bypass Graft | 7 days | High risk |
| **James Williams** (P004) | CRT Device | 8 days | Critical risk |

### 3. Active Alerts Panel (Right Side)
- Shows any alerts that have been triggered
- Color-coded by severity (Critical, High, Medium, Low)
- Real-time updates

---

## Interactive Testing Scenarios

### Scenario 1: Normal Vitals Collection ✅

**Test Patient**: David Martinez (P008) - Low risk, recent discharge

**Steps**:
1. Click **"Chat"** button next to David Martinez
2. Chat panel slides in from the right
3. Read the greeting message
4. **Type responses** to simulate vitals collection:

```
You: "My pain is about a 2"
Agent: Asks about temperature

You: "98.6 degrees"
Agent: Asks about wound status

You: "The wound looks good, no redness"
Agent: Asks about medications

You: "Yes, I took all my medications"
Agent: Asks about mobility

You: "Walking is easier today"
Agent: Asks about appetite

You: "Eating well"
Agent: Thanks you and completes check-in
```

**Expected Results**:
- ✅ 6 vitals collected (pain, temp, wound, meds, mobility, appetite)
- ✅ Conversational, empathetic responses
- ✅ No alerts triggered (normal values)
- ✅ Risk score remains low

---

### Scenario 2: Emergency Detection 🚨

**Test Patient**: Margaret Thompson (P001) - High risk cardiac patient

**Steps**:
1. Click **"Chat"** button next to Margaret Thompson
2. After greeting, **type an emergency**:

```
You: "I'm having severe chest pain and can't breathe"
```

**Expected Results**:
- 🚨 **Immediate emergency response**
- Agent says: "Margaret, what you're describing sounds serious..."
- Recommends calling 911 immediately
- **2 alerts appear** in the Alerts panel:
  - "Red Flag: Chest Pain" (Emergency severity)
  - "Red Flag: Breathing" (Emergency severity)
- Risk score updates to **100 (CRITICAL)**
- Dashboard stats update (Pending Alerts increases)

**Validation**:
- ✅ Emergency detected within 1 second
- ✅ Both red flags captured (chest pain + breathing)
- ✅ Appropriate escalation message
- ✅ Alerts created and visible

---

### Scenario 3: Urgent (Not Emergency) 🟡

**Test Patient**: Susan Davis (P005) - Moderate risk

**Steps**:
1. Click **"Chat"** button next to Susan Davis
2. Report fever:

```
You: "I have a fever of 102 degrees"
```

**Expected Results**:
- ⚠️ **Urgent classification** (not emergency)
- Agent expresses concern
- Flags for callback within 4 hours
- **1 alert created**: "Red Flag: Fever" (Urgent/High severity)
- Risk score increases (adds +25 modifier)

**Validation**:
- ✅ Urgent detection (not over-escalated to emergency)
- ✅ Appropriate response time mentioned
- ✅ Alert created but severity is "urgent" not "emergency"

---

### Scenario 4: Patient Question (RAG) 💬

**Test Patient**: Robert Garcia (P002) - Hip replacement

**Steps**:
1. Click **"Chat"** button next to Robert Garcia
2. Ask a recovery question:

```
You: "When can I start driving again?"
```

**Expected Results**:
- 🤖 **RAG-powered response**
- Agent retrieves info from hip replacement discharge summary
- Response mentions clearance from surgeon
- Response mentions being off narcotic pain medication
- Grounded in clinical guidelines (not hallucinated)

**Validation**:
- ✅ Question detected (not treated as vitals)
- ✅ Response is relevant and specific
- ✅ Agent type: "discharge_coach"
- ✅ No false alerts triggered

---

### Scenario 5: High Pain (Modifier Test) 😣

**Test Patient**: William Chen (P006) - Vascular surgery

**Steps**:
1. Click **"Chat"** button next to William Chen
2. Report high pain:

```
You: "My pain is an 8 out of 10"
```

**Expected Results**:
- Agent acknowledges high pain
- Continues vitals collection (not emergency level)
- Risk modifier applied: **+10 points** for pain ≥7
- Risk score increases
- Agent mentions informing care team

**Validation**:
- ✅ High pain detected but not classified as emergency
- ✅ Risk modifier calculation working
- ✅ Appropriate response (concern but not panic)

---

## Dashboard Features to Test

### Auto-Refresh
- Dashboard updates every 30 seconds automatically
- Stats cards refresh
- Alerts panel updates
- Patient risk scores update

### Multiple Concurrent Chats
1. Open chat with one patient
2. In a new browser tab, open http://localhost:8000
3. Open chat with different patient
4. Both conversations maintain separate state ✅

### Alert Acknowledgment
- Click on alerts in the panel
- See alert details
- (Note: Acknowledgment workflow can be added)

### Patient Selection
- Click on patient row (not the chat button)
- Row highlights
- Shows selection state

---

## API Testing (Optional)

### Using Browser Console

Open browser console (F12) and try:

```javascript
// List all patients
fetch('http://localhost:8000/api/patients?status=active')
  .then(r => r.json())
  .then(d => console.log(d));

// Get dashboard stats
fetch('http://localhost:8000/api/alerts/dashboard')
  .then(r => r.json())
  .then(d => console.log(d));

// Get active alerts
fetch('http://localhost:8000/api/alerts?status=active')
  .then(r => r.json())
  .then(d => console.log(d));
```

### Using PowerShell

```powershell
# List patients
Invoke-RestMethod -Uri "http://localhost:8000/api/patients?status=active" -Method Get

# Get patient summary
Invoke-RestMethod -Uri "http://localhost:8000/api/patients/P001/summary" -Method Get

# List alerts
Invoke-RestMethod -Uri "http://localhost:8000/api/alerts?status=active" -Method Get
```

---

## What to Look For

### ✅ **Working Correctly**

1. **Dashboard loads** without errors
2. **Stats cards** display numbers
3. **Patient table** shows 8 patients
4. **Chat panel** slides in when clicking "Chat"
5. **Messages** send and receive
6. **Alerts** appear when emergency detected
7. **Risk scores** update after conversations
8. **No console errors** (check browser F12 console)

### ⚠️ **Potential Issues**

1. **"Failed to fetch"** errors
   - Check server is running: http://localhost:8000/
   - Check terminal for errors
   
2. **Empty data**
   - Verify database initialized (check server logs)
   - Should see "Sample data loaded" in logs

3. **Slow responses**
   - Google API rate limiting (check for 429 errors)
   - Fallback mechanisms will activate automatically

---

## Stop the Server

When done testing:

```powershell
# In PowerShell
# Press Ctrl+C in the server terminal
```

Or I can stop it programmatically for you.

---

## Server Logs

Check the backend terminal for real-time logs:
- Patient data queries
- Conversation state updates
- Alert creations
- RAG queries
- Any errors

---

## Next Steps After Testing

1. ✅ Verify all scenarios work as expected
2. ✅ Test with multiple patients
3. ✅ Create screenshots for documentation
4. ✅ Note any issues or suggestions
5. ✅ Review alerts functionality
6. ✅ Test error handling (invalid inputs)

---

## Quick Reference

**Server**: http://localhost:8000  
**API Docs**: http://localhost:8000/docs  
**Terminal ID**: 3

**To stop server**: Let me know and I'll stop it for you!

---

**Happy Testing!** 🚀

The dashboard is now ready for your testing. Try the scenarios above and explore the features!
