"""
Test script to verify the Concierge Triage Agent works.
Run this after setting up your .env file with GOOGLE_API_KEY.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from config import settings
        print(f"✓ Config loaded (LLM configured: {bool(settings.GOOGLE_API_KEY)})")
    except Exception as e:
        print(f"✗ Config error: {e}")
        return False
    
    try:
        from database import init_db, seed_sample_data
        print("✓ Database module loaded")
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False
    
    try:
        from agents.phi_deidentifier import phi_deidentifier
        from agents.vitals_intake import vitals_intake_agent
        from agents.clinical_triage import clinical_triage_agent
        from agents.supervisor import supervisor_agent
        print("✓ All agents loaded")
    except Exception as e:
        print(f"✗ Agents error: {e}")
        return False
    
    try:
        from services.patient_service import patient_service
        from services.vitals_service import vitals_service
        from services.conversation_service import conversation_service
        from services.alert_service import alert_service
        from services.rag_service import rag_service
        print("✓ All services loaded")
    except Exception as e:
        print(f"✗ Services error: {e}")
        return False
    
    try:
        from routers import chat_router, patients_router, alerts_router
        print("✓ All routers loaded")
    except Exception as e:
        print(f"✗ Routers error: {e}")
        return False
    
    return True


def test_database():
    """Test database initialization."""
    print("\nTesting database...")
    
    from database import init_db, seed_sample_data
    
    try:
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database init error: {e}")
        return False
    
    try:
        seed_sample_data()
        print("✓ Sample data seeded")
    except Exception as e:
        print(f"✗ Seed data error: {e}")
        return False
    
    return True


def test_services():
    """Test service operations."""
    print("\nTesting services...")
    
    from services.patient_service import patient_service
    from services.alert_service import alert_service
    
    try:
        patients = patient_service.get_all_patients()
        print(f"✓ Found {len(patients)} patients")
        
        if patients:
            patient = patient_service.get_patient_by_id(patients[0]["id"])
            print(f"✓ Retrieved patient: {patient['first_name']} {patient['last_name']}")
            
            stats = alert_service.get_dashboard_stats()
            print(f"✓ Dashboard stats: {stats.active_patients} active patients, {stats.pending_alerts} pending alerts")
    except Exception as e:
        print(f"✗ Service error: {e}")
        return False
    
    return True


def test_agents():
    """Test agent functionality."""
    print("\nTesting agents...")
    
    from agents.phi_deidentifier import phi_deidentifier
    from agents.clinical_triage import clinical_triage_agent
    
    try:
        # Test PHI deidentification
        test_text = "My name is John Doe and my SSN is 123-45-6789"
        deidentified, mapping = phi_deidentifier.deidentify(test_text, "test_session")
        print(f"✓ PHI deidentification works")
        print(f"  Original: {test_text}")
        print(f"  Deidentified: {deidentified}")
        
        # Test clinical triage
        triage = clinical_triage_agent.analyze_utterance("I have severe chest pain")
        print(f"✓ Clinical triage works")
        print(f"  Urgency: {triage['urgency']}")
        print(f"  Red flags: {len(triage['red_flags'])}")
    except Exception as e:
        print(f"✗ Agent error: {e}")
        return False
    
    return True


def main():
    print("=" * 60)
    print("Concierge Triage Agent - System Test")
    print("=" * 60)
    
    all_passed = True
    
    if not test_imports():
        all_passed = False
    
    if not test_database():
        all_passed = False
    
    if not test_services():
        all_passed = False
    
    if not test_agents():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("\nTo start the server:")
        print("  cd 'd:\\Concierge Triage Agent\\backend'")
        print("  python main.py")
        print("\nOr with uvicorn:")
        print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("✗ Some tests failed. Check the errors above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
