"""
Test script for MCP Server

Run this to test the MCP server functionality locally before configuring in Claude.
"""

import asyncio
import json
from mcp_server import server

async def test_tools():
    """Test each MCP tool."""
    
    print("=" * 80)
    print("MCP SERVER TEST SUITE")
    print("=" * 80)
    
    # Test 1: List Active Patients
    print("\n1. Testing: list_active_patients")
    print("-" * 80)
    result = await server.call_tool()("list_active_patients", {"risk_level": "all"})
    print(result[0].text)
    
    # Test 2: Analyze Patient Message (Emergency)
    print("\n2. Testing: analyze_patient_message (EMERGENCY)")
    print("-" * 80)
    result = await server.call_tool()(
        "analyze_patient_message",
        {
            "message": "I'm having severe chest pain and can't breathe",
            "patient_context": {
                "diagnosis": "Coronary Artery Disease",
                "procedure": "CABG"
            }
        }
    )
    print(result[0].text)
    
    # Test 3: Extract Vitals
    print("\n3. Testing: extract_vitals")
    print("-" * 80)
    result = await server.call_tool()(
        "extract_vitals",
        {
            "text": "My pain is about a 7 out of 10",
            "vitals_type": "pain_level"
        }
    )
    print(result[0].text)
    
    # Test 4: Search Clinical Guidelines
    print("\n4. Testing: search_clinical_guidelines")
    print("-" * 80)
    result = await server.call_tool()(
        "search_clinical_guidelines",
        {
            "query": "when can patient drive after surgery",
            "procedure_type": "cardiac_surgery"
        }
    )
    print(result[0].text)
    
    # Test 5: Get Active Alerts
    print("\n5. Testing: get_active_alerts")
    print("-" * 80)
    result = await server.call_tool()(
        "get_active_alerts",
        {"severity": "all"}
    )
    print(result[0].text)
    
    # Test 6: Start Conversation
    print("\n6. Testing: start_patient_conversation")
    print("-" * 80)
    result = await server.call_tool()(
        "start_patient_conversation",
        {"patient_id": "P001"}
    )
    conversation_data = json.loads(result[0].text)
    print(result[0].text)
    conversation_id = conversation_data.get("conversation_id")
    
    # Test 7: Send Message
    if conversation_id:
        print("\n7. Testing: send_patient_message")
        print("-" * 80)
        result = await server.call_tool()(
            "send_patient_message",
            {
                "patient_id": "P001",
                "conversation_id": conversation_id,
                "message": "My pain is about a 3"
            }
        )
        print(result[0].text)
    
    # Test 8: Deidentify PHI
    print("\n8. Testing: deidentify_phi")
    print("-" * 80)
    result = await server.call_tool()(
        "deidentify_phi",
        {
            "text": "My name is John Smith, SSN 123-45-6789, call 555-1234",
            "session_id": "test_session"
        }
    )
    print(result[0].text)
    
    # Test 9: Get Patient Summary
    print("\n9. Testing: get_patient_summary")
    print("-" * 80)
    result = await server.call_tool()(
        "get_patient_summary",
        {"patient_id": "P001"}
    )
    print(result[0].text)
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_tools())
