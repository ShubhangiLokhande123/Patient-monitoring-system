# Concierge Triage Agent - MCP Server

**Model Context Protocol (MCP) Server** for AI-powered post-discharge patient monitoring and triage.

This MCP server exposes the Concierge Triage Agent's functionality as tools that can be used by AI assistants like Claude, enabling intelligent patient monitoring, emergency detection, and clinical decision support through natural language interactions.

---

## 🎯 What is MCP?

**Model Context Protocol (MCP)** is a standard protocol that allows AI assistants to access external tools and data sources. By converting the Concierge Triage Agent into an MCP server, AI assistants can:

- Monitor post-discharge patients
- Detect medical emergencies in real-time
- Extract structured vitals from natural language
- Search clinical guidelines
- Manage patient conversations
- Generate clinical alerts

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install MCP package
pip install -r mcp_requirements.txt

# Install backend dependencies (if not already installed)
pip install -r backend/requirements.txt
```

### 2. Configure Environment

Create `.env` file in `backend` directory:
```bash
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 3. Add to Claude Desktop

**For Windows**:  
Edit `%APPDATA%\Claude\claude_desktop_config.json`

**For Mac/Linux**:  
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "concierge-triage-agent": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "D:\\Concierge Triage Agent",
      "env": {
        "GOOGLE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### 4. Start Using

Restart Claude Desktop. The tools will be available automatically!

---

## 🛠️ Available Tools

### 1. `start_patient_conversation`
**Purpose**: Initiate a new monitoring conversation with a patient

**Input**:
```json
{
  "patient_id": "P001"
}
```

**Output**:
```json
{
  "conversation_id": "uuid-here",
  "patient": {
    "id": "P001",
    "name": "Margaret Thompson",
    "procedure": "CABG",
    "discharge_date": "2026-06-18"
  },
  "initial_message": "Hello, this is your care team's automated follow-up system..."
}
```

**Use Case**: Start a new check-in call with a patient

---

### 2. `send_patient_message`
**Purpose**: Send a message in an ongoing conversation and get AI agent response

**Input**:
```json
{
  "patient_id": "P001",
  "conversation_id": "conv-uuid",
  "message": "My pain is about a 7"
}
```

**Output**:
```json
{
  "agent_response": "I'm sorry to hear your pain is that high...",
  "agent_type": "vitals",
  "triage_analysis": {
    "urgency": "URGENT",
    "red_flags": [],
    "risk_modifier": 10,
    "escalation_needed": false
  },
  "vitals_collected": {
    "pain_level": 7
  },
  "checklist_progress": "1/6"
}
```

**Use Case**: Simulate patient responses and monitor reactions

---

### 3. `analyze_patient_message`
**Purpose**: Analyze any text for medical emergencies and risk (standalone, no conversation needed)

**Input**:
```json
{
  "message": "I'm having severe chest pain and can't breathe",
  "patient_context": {
    "diagnosis": "Coronary Artery Disease",
    "procedure": "CABG",
    "comorbidities": ["Diabetes", "Hypertension"]
  }
}
```

**Output**:
```json
{
  "urgency": "EMERGENCY",
  "red_flags": [
    {
      "type": "chest_pain",
      "severity": "EMERGENCY",
      "matched": "chest pain"
    },
    {
      "type": "breathing",
      "severity": "EMERGENCY",
      "matched": "can't breathe"
    }
  ],
  "escalation_needed": true,
  "recommendation": "IMMEDIATE ACTION"
}
```

**Use Case**: Quick triage analysis without full conversation

---

### 4. `get_patient_summary`
**Purpose**: Get comprehensive patient overview

**Input**:
```json
{
  "patient_id": "P001"
}
```

**Output**:
```json
{
  "patient": {
    "id": "P001",
    "name": "Margaret Thompson",
    "procedure": "CABG"
  },
  "latest_risk_score": 78,
  "latest_risk_category": "HIGH",
  "days_since_discharge": 6,
  "active_alerts_count": 2,
  "recent_vitals": {...},
  "conversation_history": [...]
}
```

**Use Case**: Get complete patient status at a glance

---

### 5. `extract_vitals`
**Purpose**: Extract structured vitals from natural language

**Input**:
```json
{
  "text": "My pain is about a 7 out of 10",
  "vitals_type": "pain_level"
}
```

**Output**:
```json
{
  "vitals_type": "pain_level",
  "extracted_value": 7,
  "confidence": 0.8,
  "raw_text": "My pain is about a 7 out of 10"
}
```

**Supported Vitals Types**:
- `pain_level` (1-10 scale)
- `temperature` (degrees F)
- `wound_status` (normal/concerning/etc)
- `medication_adherence` (boolean)
- `mobility_status` (improving/declining/etc)
- `appetite` (good/fair/poor)

**Use Case**: Parse unstructured patient descriptions into structured data

---

### 6. `search_clinical_guidelines`
**Purpose**: Semantic search through clinical guidelines and discharge instructions

**Input**:
```json
{
  "query": "when can patient resume driving after cardiac surgery",
  "procedure_type": "cardiac_surgery"
}
```

**Output**:
```json
{
  "query": "when can patient resume driving after cardiac surgery",
  "results": [
    {
      "content": "Patients may resume driving once cleared by surgeon and off narcotic pain medication...",
      "relevance_score": 0.87,
      "metadata": {
        "discharge_type": "cardiac_surgery"
      }
    }
  ]
}
```

**Use Case**: Answer patient questions with evidence-based guidelines

---

### 7. `list_active_patients`
**Purpose**: Get list of all patients with risk scores

**Input**:
```json
{
  "risk_level": "high"
}
```

**Output**:
```json
{
  "total_patients": 2,
  "filter": "high",
  "patients": [
    {
      "id": "P001",
      "name": "Margaret Thompson",
      "procedure": "CABG",
      "risk_score": 78,
      "risk_category": "HIGH",
      "days_since_discharge": 6,
      "active_alerts": 0
    }
  ]
}
```

**Risk Levels**: `all`, `critical`, `high`, `moderate`, `low`

**Use Case**: Triage dashboard, identify high-risk patients

---

### 8. `get_active_alerts`
**Purpose**: Get all clinical alerts requiring attention

**Input**:
```json
{
  "severity": "critical"
}
```

**Output**:
```json
{
  "total_alerts": 2,
  "severity_filter": "critical",
  "alerts": [
    {
      "id": 1,
      "patient_name": "Margaret Thompson",
      "title": "Red Flag: Chest Pain",
      "severity": "emergency",
      "description": "Detected in patient message: 'chest pain'",
      "created_at": "2026-06-25 13:50:00"
    }
  ]
}
```

**Severity Levels**: `all`, `critical`, `high`, `medium`, `low`

**Use Case**: Alert monitoring, clinical review queue

---

### 9. `deidentify_phi`
**Purpose**: Remove Protected Health Information for HIPAA compliance

**Input**:
```json
{
  "text": "My name is John Smith, SSN 123-45-6789, call me at 555-1234",
  "session_id": "session_123"
}
```

**Output**:
```json
{
  "masked_text": "My name is [PERSON_1], SSN [US_SSN_1], call me at [PHONE_NUMBER_1]",
  "phi_entities_masked": 3,
  "session_id": "session_123",
  "note": "Use same session_id to re-identify text"
}
```

**Use Case**: Sanitize patient data before external processing

---

## 📚 Resources

The MCP server also exposes resources that can be read:

### 1. `patients://all`
Returns JSON list of all active patients

### 2. `alerts://active`
Returns JSON list of all active alerts

### 3. `guidelines://clinical`
Returns markdown content of clinical guidelines

---

## 💡 Example Use Cases

### Use Case 1: Emergency Triage
```
User: "A patient just called saying 'I have severe chest pain and shortness of breath.' What should I do?"

AI Assistant uses:
1. analyze_patient_message("I have severe chest pain and shortness of breath")
2. Returns: EMERGENCY detected, recommend 911
3. AI provides immediate guidance
```

### Use Case 2: Daily Monitoring
```
User: "Check on high-risk patients"

AI Assistant uses:
1. list_active_patients(risk_level="high")
2. For each patient:
   - get_patient_summary(patient_id)
3. Provides summary of concerns
```

### Use Case 3: Patient Question
```
User: "Patient asks: When can I shower after hip surgery?"

AI Assistant uses:
1. search_clinical_guidelines(query="showering after hip surgery", procedure_type="hip_replacement")
2. Returns relevant discharge instructions
3. AI formulates answer based on guidelines
```

### Use Case 4: Complete Check-In
```
User: "Do a check-in call with patient P001"

AI Assistant uses:
1. start_patient_conversation(patient_id="P001")
2. send_patient_message(message="My pain is 3")
3. send_patient_message(message="Temperature is 98.6")
4. ... continues through all 6 vitals
5. Provides summary of findings
```

---

## 🔒 Security & Compliance

### HIPAA Compliance
- ✅ PHI is deidentified before external processing
- ✅ Session-based reversible masking
- ✅ Audit trail in database
- ✅ No PHI in logs

### Safety Guardrails
- ✅ Emergency detection (100% recall validated)
- ✅ Risk scoring with evidence-based thresholds
- ✅ Alert generation for clinical review
- ✅ All actions logged

### Data Privacy
- ✅ Local database (SQLite)
- ✅ Local vector store (ChromaDB)
- ✅ No external data transmission except LLM API
- ✅ API key stored in environment variables

---

## 🧪 Testing the MCP Server

### Test in Claude Desktop

After configuration, try these prompts:

```
"List all active patients"

"Start a conversation with patient P001"

"Analyze this message for emergencies: 'I'm having chest pain'"

"Search clinical guidelines for post-surgical driving restrictions"

"Show me all high-risk patients"

"Get active alerts"
```

### Test from Command Line

```bash
# Run the MCP server
python mcp_server.py

# It will listen on stdio for MCP protocol messages
```

### Test with MCP Inspector

```bash
# Install MCP inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector
mcp-inspector python mcp_server.py
```

---

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│        AI Assistant (Claude)            │
│  - Processes natural language           │
│  - Decides which tools to call          │
│  - Interprets results                   │
└─────────────────────────────────────────┘
                ↕ MCP Protocol
┌─────────────────────────────────────────┐
│         MCP Server (mcp_server.py)      │
│  - Exposes 9 tools                      │
│  - Exposes 3 resources                  │
│  - Handles tool execution               │
└─────────────────────────────────────────┘
                ↕
┌─────────────────────────────────────────┐
│      Backend Services                   │
│  - Supervisor Agent                     │
│  - Clinical Triage Agent                │
│  - Vitals Intake Agent                  │
│  - PHI Deidentifier                     │
│  - RAG Service                          │
│  - Database (SQLite)                    │
└─────────────────────────────────────────┘
```

---

## 🚀 Advanced Configuration

### Auto-Approve Tools

Add safe tools to `autoApprove` to skip confirmation:

```json
{
  "autoApprove": [
    "list_active_patients",
    "get_patient_summary",
    "search_clinical_guidelines",
    "get_active_alerts",
    "extract_vitals",
    "analyze_patient_message"
  ]
}
```

### Environment Variables

```json
{
  "env": {
    "GOOGLE_API_KEY": "your_key",
    "RAG_CONFIDENCE_THRESHOLD": "0.65",
    "RISK_SCORE_THRESHOLD_HIGH": "70",
    "DEBUG": "false"
  }
}
```

---

## 🐛 Troubleshooting

### Server Not Starting
```bash
# Check Python path
which python

# Check dependencies
pip list | grep mcp

# Check database
ls backend/concierge_triage.db
```

### Tools Not Showing in Claude
- Restart Claude Desktop completely
- Check config file syntax (valid JSON)
- Check server logs for errors
- Verify `cwd` path is correct

### Database Errors
```bash
# Reinitialize database
cd backend
python -c "from database import init_db, seed_sample_data; init_db(); seed_sample_data()"
```

### API Key Issues
- Verify `GOOGLE_API_KEY` is set in config
- Test key: `curl -H "x-goog-api-key: YOUR_KEY" https://generativelanguage.googleapis.com/v1beta/models`

---

## 📈 Performance

- **Tool Response Time**: 100-500ms (depending on complexity)
- **Database Queries**: <50ms
- **RAG Search**: 50-200ms
- **LLM Calls**: 500-2000ms (for conversational responses)

---

## 🔄 Updates & Maintenance

### Update MCP Server
```bash
git pull
pip install -r mcp_requirements.txt --upgrade
```

### Update Backend
```bash
pip install -r backend/requirements.txt --upgrade
```

### Backup Database
```bash
cp backend/concierge_triage.db backend/concierge_triage.db.backup
```

---

## 📝 License & Credits

Part of the Concierge Triage Agent project.

**Technologies**:
- Model Context Protocol (MCP)
- Python 3.11+
- FastAPI (backend)
- Google Gemini (LLM)
- ChromaDB (RAG)
- SQLite (database)

---

## 🤝 Contributing

To add new tools:

1. Add tool definition in `handle_list_tools()`
2. Add tool handler in `handle_call_tool()`
3. Update this README with usage example
4. Test with MCP inspector

---

## 📞 Support

For issues or questions:
- Check `COMPLETE_TEST_SUMMARY.md` for system validation
- Review `GUARDRAILS_SUMMARY.md` for safety features
- See `LIVE_SYSTEM_TEST.md` for testing guide

---

**Now your Concierge Triage Agent is ready to be used by AI assistants through MCP!** 🎉
