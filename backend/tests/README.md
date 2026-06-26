# Agent Evaluation Suite

Comprehensive testing and evaluation framework for the Concierge Triage Agent system.

## Overview

This evaluation suite provides **unit tests**, **integration tests**, and **accuracy metrics** for all agents and system components.

## Test Modules

### 1. `test_phi_deidentifier.py`
**PHI Deidentifier Agent Tests**

- **HIPAA Compliance**: Validates masking of all PHI types (SSN, phone, email, dates)
- **Reversibility**: Tests re-identification accuracy
- **Session Isolation**: Ensures PHI mappings are isolated by conversation
- **Coverage**: Comprehensive test cases for common and edge-case PHI patterns

**Key Metrics:**
- PHI Leakage: 0% (critical - no PHI should appear in masked output)
- Reversibility: 100% (must restore original text exactly)

---

### 2. `test_vitals_intake.py`
**Vitals Intake Agent Tests**

- **Structured Data Extraction**: Pain level, temperature, wound status, medication adherence, mobility, appetite
- **Checklist Progression**: 6-item intake flow validation
- **Extraction Rules**: Integer, float, boolean, and categorical value extraction
- **Natural Language Understanding**: Handles varied patient responses

**Key Metrics:**
- Pain Extraction Accuracy: ≥75%
- Boolean Extraction Accuracy: ≥75%
- Checklist Completion: 100% (all 6 items collected)

---

### 3. `test_clinical_triage.py`
**Clinical Triage Agent Tests**

- **Red Flag Detection**: Emergency, urgent, and routine classification
- **Pattern Matching**: Chest pain, breathing difficulty, stroke, bleeding, fever, wound infection
- **Risk Scoring**: Vitals-based modifiers (pain, fever, medication adherence)
- **Triage Notes**: Action-oriented clinical documentation

**Key Metrics:**
- Classification Accuracy: ≥80%
- Emergency Recall: 100% (CRITICAL - cannot miss emergencies)
- Risk Modifier Accuracy: Validates all vitals-based score adjustments

---

### 4. `test_supervisor.py`
**Supervisor Agent Tests**

- **Intent Classification**: Question vs vitals collection vs general conversation
- **Agent Routing**: Correct delegation to specialized agents
- **Conversation Orchestration**: Multi-turn state management
- **Emergency Interruption**: Immediate escalation overrides normal flow
- **PHI Pipeline Integration**: End-to-end deidentification workflow

**Key Metrics:**
- Routing Accuracy: ≥75%
- Emergency Response Time: Immediate (1 turn)
- Checklist State Management: 100% consistency

---

### 5. `test_rag_service.py`
**RAG (Retrieval-Augmented Generation) Service Tests**

- **Document Indexing**: Clinical guidelines and discharge summaries
- **Semantic Search**: Vector-based retrieval with ChromaDB
- **Chunking Strategy**: Optimal document segmentation
- **Confidence Filtering**: Threshold-based result filtering
- **Response Generation**: Grounded in clinical evidence

**Key Metrics:**
- Retrieval Accuracy: ≥50%
- Response Safety: No medical advice beyond guidelines
- Fallback Handling: Graceful degradation when RAG unavailable

---

### 6. `test_integration.py`
**Full System Integration Tests**

- **API Endpoints**: `/chat/`, `/patients/`, `/alerts/`
- **Database Operations**: CRUD integrity and transaction management
- **Multi-turn Conversations**: Complete vitals collection, emergency escalation, Q&A flows
- **Concurrent Sessions**: Multiple simultaneous patient conversations
- **Error Handling**: Invalid IDs, mismatched conversations, permission checks

**Key Scenarios:**
- Complete vitals collection (6-turn conversation)
- Emergency detection and escalation
- Patient question answering via RAG
- Conversation state persistence

---

## Running the Evaluation Suite

### Quick Start

Run all tests with comprehensive metrics:

```bash
cd backend/tests
python run_evals.py
```

This will:
1. Run all 6 test modules sequentially
2. Display progress and results in real-time
3. Generate a detailed evaluation report
4. Save results to `evaluation_report.json`

### Run Individual Test Modules

```bash
# PHI Deidentifier tests
pytest test_phi_deidentifier.py -v

# Vitals Intake tests
pytest test_vitals_intake.py -v

# Clinical Triage tests
pytest test_clinical_triage.py -v

# Supervisor tests
pytest test_supervisor.py -v

# RAG Service tests
pytest test_rag_service.py -v

# Integration tests
pytest test_integration.py -v
```

### Run with Coverage

```bash
pytest --cov=agents --cov=services --cov-report=html
```

View coverage report at `htmlcov/index.html`

### Run Specific Test Class

```bash
pytest test_clinical_triage.py::TestRedFlagDetection -v
```

### Run Specific Test

```bash
pytest test_supervisor.py::TestIntentClassification::test_question_detection_with_question_mark -v
```

## Evaluation Report

After running `run_evals.py`, you'll get:

### Console Output
- Real-time test progress
- Pass/fail status per module
- Component-specific metrics summary
- Overall assessment

### JSON Report (`evaluation_report.json`)
```json
{
  "timestamp": "2024-06-25T10:30:00",
  "summary": {
    "total_modules": 6,
    "passed": 6,
    "failed": 0,
    "skipped": 0
  },
  "results": {
    "test_phi_deidentifier.py": {"status": "PASSED", "exit_code": 0},
    "test_vitals_intake.py": {"status": "PASSED", "exit_code": 0},
    ...
  }
}
```

## Accuracy Thresholds

| Component | Metric | Threshold | Priority |
|-----------|--------|-----------|----------|
| Clinical Triage | Emergency Recall | **100%** | CRITICAL |
| Clinical Triage | Classification Accuracy | ≥80% | High |
| Vitals Intake | Extraction Accuracy | ≥75% | High |
| Supervisor | Routing Accuracy | ≥75% | Medium |
| RAG Service | Retrieval Accuracy | ≥50% | Medium |
| PHI Deidentifier | PHI Leakage | **0%** | CRITICAL |

## Test Data

### Sample Patients
Tests use sample patients from `data/sample_patients.json`:
- Varied risk profiles (low, moderate, high, critical)
- Different procedures (cardiac, hip, appendectomy)
- Range of comorbidities and demographics

### Ground Truth Labels
Each test module includes labeled test cases for:
- Red flag detection (emergency vs urgent vs routine)
- Intent classification (question vs vitals vs general)
- Data extraction accuracy (pain levels, temperatures, etc.)

## Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Ensure backend dependencies are installed
pip install -r ../requirements.txt
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Agent Evaluation

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run evaluation suite
        run: |
          cd backend/tests
          python run_evals.py
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: evaluation-report
          path: backend/tests/evaluation_report.json
```

## Troubleshooting

### ChromaDB Not Available
Some tests may skip if ChromaDB is not installed:
```bash
pip install chromadb
```

### Google API Key Not Set
RAG and supervisor tests may use fallback responses without API key:
```bash
export GOOGLE_API_KEY=your_api_key_here
```

### Database Initialization
Integration tests require database setup:
```bash
cd backend
python -c "from database import init_db, seed_sample_data; init_db(); seed_sample_data()"
```

### Async Test Issues
Ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

## Adding New Tests

### Test Structure Template

```python
"""
Tests for [Component Name]
"""

import pytest
from [module] import [component]


class Test[Feature]:
    """Test [feature description]."""
    
    @pytest.fixture
    def setup_data(self):
        """Setup test data."""
        # Setup code
        yield
        # Teardown code
    
    def test_[specific_behavior](self, setup_data):
        """Should [expected behavior]."""
        # Arrange
        input_data = ...
        
        # Act
        result = component.method(input_data)
        
        # Assert
        assert result == expected_value
```

### Best Practices

1. **Descriptive test names**: Use `test_should_do_something_when_condition`
2. **Arrange-Act-Assert pattern**: Clear test structure
3. **Fixtures for setup**: Reusable test data
4. **Ground truth labels**: For accuracy metrics
5. **Edge cases**: Test boundary conditions
6. **Error paths**: Validate error handling

## Metrics Tracking

Track evaluation metrics over time:

```bash
# Save historical results
cp evaluation_report.json "reports/eval_$(date +%Y%m%d_%H%M%S).json"

# Compare with baseline
python compare_metrics.py reports/baseline.json evaluation_report.json
```

## Contact

For questions about the evaluation suite:
- Review test documentation in each module
- Check assertions for expected behavior
- Refer to agent implementation in `backend/agents/`

---

**Last Updated**: June 25, 2024  
**Test Coverage**: 6 modules, 100+ test cases  
**Accuracy Targets**: See table above
