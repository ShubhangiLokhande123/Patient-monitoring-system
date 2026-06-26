"""
Evaluation suite runner with metrics reporting.

Runs all agent tests and generates a comprehensive evaluation report.
"""

import sys
import os
import json
from datetime import datetime
import pytest
from io import StringIO


def run_test_suite():
    """Run all tests and collect metrics."""
    
    print("=" * 80)
    print("CONCIERGE TRIAGE AGENT - EVALUATION SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test modules to run
    test_modules = [
        "test_phi_deidentifier.py",
        "test_vitals_intake.py",
        "test_clinical_triage.py",
        "test_supervisor.py",
        "test_rag_service.py",
        "test_integration.py"
    ]
    
    results = {}
    overall_passed = 0
    overall_failed = 0
    overall_skipped = 0
    
    for module in test_modules:
        print(f"\n{'=' * 80}")
        print(f"Running: {module}")
        print(f"{'=' * 80}\n")
        
        # Run pytest for this module
        exit_code = pytest.main([
            module,
            "-v",
            "-s",
            "--tb=short",
            "--color=yes",
            f"--junit-xml=results_{module}.xml"
        ])
        
        # Collect results
        results[module] = {
            "status": "PASSED" if exit_code == 0 else "FAILED",
            "exit_code": exit_code
        }
        
        if exit_code == 0:
            overall_passed += 1
        else:
            overall_failed += 1
    
    # Print summary
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)
    print(f"\nTest Modules Run: {len(test_modules)}")
    print(f"  ✓ Passed: {overall_passed}")
    print(f"  ✗ Failed: {overall_failed}")
    print(f"  ⊘ Skipped: {overall_skipped}")
    print()
    
    # Detailed results
    print("Module Results:")
    print("-" * 80)
    for module, result in results.items():
        status_icon = "✓" if result["status"] == "PASSED" else "✗"
        print(f"  {status_icon} {module:40} {result['status']}")
    print()
    
    # Component-specific metrics
    print("\n" + "=" * 80)
    print("COMPONENT EVALUATION METRICS")
    print("=" * 80)
    
    print("\n1. PHI Deidentifier Agent")
    print("-" * 80)
    print("   - HIPAA Compliance: Tests PHI masking and session isolation")
    print("   - Reversibility: Validates re-identification accuracy")
    print("   - Coverage: SSN, phone, email, dates, addresses")
    print("   Status:", results.get("test_phi_deidentifier.py", {}).get("status", "N/A"))
    
    print("\n2. Vitals Intake Agent")
    print("-" * 80)
    print("   - Structured Data Extraction: Pain, temperature, wound, meds, mobility, appetite")
    print("   - Checklist Progression: 6-item intake flow")
    print("   - Accuracy Metrics: Pain extraction ≥75%, Boolean extraction ≥75%")
    print("   Status:", results.get("test_vitals_intake.py", {}).get("status", "N/A"))
    
    print("\n3. Clinical Triage Agent")
    print("-" * 80)
    print("   - Red Flag Detection: Emergency, urgent, routine classification")
    print("   - Risk Scoring: Vitals-based modifiers and thresholds")
    print("   - Accuracy Target: ≥80% classification accuracy")
    print("   - Emergency Recall: 100% (critical - cannot miss emergencies)")
    print("   Status:", results.get("test_clinical_triage.py", {}).get("status", "N/A"))
    
    print("\n4. Supervisor Agent")
    print("-" * 80)
    print("   - Intent Classification: Question vs vitals vs general")
    print("   - Agent Routing: Correct delegation to specialized agents")
    print("   - Conversation Flow: Multi-turn state management")
    print("   - Routing Accuracy Target: ≥75%")
    print("   Status:", results.get("test_supervisor.py", {}).get("status", "N/A"))
    
    print("\n5. RAG Service")
    print("-" * 80)
    print("   - Document Indexing: Clinical guidelines and discharge summaries")
    print("   - Semantic Search: Vector-based retrieval with confidence filtering")
    print("   - Response Generation: Grounded in clinical evidence")
    print("   - Retrieval Accuracy Target: ≥50%")
    print("   Status:", results.get("test_rag_service.py", {}).get("status", "N/A"))
    
    print("\n6. System Integration")
    print("-" * 80)
    print("   - API Endpoints: Chat, patients, alerts, vitals")
    print("   - Database Operations: CRUD and transaction integrity")
    print("   - Multi-turn Conversations: Complete workflow scenarios")
    print("   - Error Handling: Graceful degradation and validation")
    print("   Status:", results.get("test_integration.py", {}).get("status", "N/A"))
    
    # Overall assessment
    print("\n" + "=" * 80)
    print("OVERALL ASSESSMENT")
    print("=" * 80)
    
    if overall_failed == 0:
        print("\n✓ All evaluation tests PASSED")
        print("  System is ready for deployment testing")
    else:
        print(f"\n✗ {overall_failed} module(s) FAILED")
        print("  Review failed tests before deployment")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Save results to JSON
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_modules": len(test_modules),
            "passed": overall_passed,
            "failed": overall_failed,
            "skipped": overall_skipped
        },
        "results": results
    }
    
    with open("evaluation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\nDetailed report saved to: evaluation_report.json")
    print()
    
    # Return appropriate exit code
    return 0 if overall_failed == 0 else 1


if __name__ == "__main__":
    # Change to tests directory
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(tests_dir)
    
    exit_code = run_test_suite()
    sys.exit(exit_code)
