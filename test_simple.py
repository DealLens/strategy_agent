"""간단한 import 테스트"""
import sys
print(f"Python version: {sys.version}")
print(f"sys.path: {sys.path[:3]}")

try:
    from utils.llm_client import get_llm_client
    print("✅ utils.llm_client import 성공")
except Exception as e:
    print(f"❌ import 실패: {e}")

