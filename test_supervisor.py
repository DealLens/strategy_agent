"""
Test script for DealLens Supervisor Agent
"""

import json
from workflow.supervisor_agent import run_deallens_pipeline

def test_supervisor():
    """Test the supervisor agent pipeline"""
    print("🧪 Testing DealLens Supervisor Agent...")
    
    # Test with sample RFP path
    result = run_deallens_pipeline("sample_rfp.pdf")
    
    print("\n📊 Test Results:")
    print(f"✅ Pipeline executed successfully: {result.get('qa_ready', False)}")
    print(f"📋 Artifacts generated: {len(result.get('artifacts', {}))}")
    print(f"📄 Report length: {len(result.get('deal_brief', ''))}")
    
    # Print summary
    artifacts = result.get('artifacts', {})
    print(f"\n🔍 Artifacts Summary:")
    print(f"  A (RFP Parser): {len(artifacts.get('A', {}).get('requirements', []))} requirements")
    print(f"  B (Internal RAG): {len(artifacts.get('B', {}).get('matches', []))} matches")
    print(f"  C (Competitor): {len(artifacts.get('C', {}).get('profiles', {}))} companies")
    print(f"  D (Strategy): {len(artifacts.get('D', {}).get('actions', []))} actions")
    
    # Test error handling
    print(f"\n🚨 Testing error handling...")
    error_result = run_deallens_pipeline("")
    print(f"  Empty path handled: {error_result.get('error') is not None}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    test_supervisor()
